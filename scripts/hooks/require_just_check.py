"""Stop hook: refuse session completion if touched specs fail the linter.

Invoked by Claude Code when the agent declares the session done. Reads
``git diff HEAD --name-only`` to identify modified-but-uncommitted spec
files under ``docs/specs/``, then runs ``scripts/lint_spec.py`` against
each. If any spec fails, exit code 2 surfaces stderr back to the model
and blocks the "done" signal — the agent must fix the spec before the
session can end.

Design notes:

* Scope is intentionally narrow: ``git diff HEAD`` (working tree + index
  vs. the last commit). Already-committed specs are out of scope — they
  were presumably valid when committed; revalidating them would surface
  retroactive lint-rule changes that the agent did not cause (see Quiz
  #1 / Q5: specs are append-only history).
* Scaffolding files (``_template.md``, ``README.md``, ``_postmortem.md``)
  are skipped — they exist to be intentionally non-conforming.
* Fail-open semantics: any infrastructure problem (git missing,
  ``lint_spec.py`` missing, malformed input on stdin, etc.) returns 0.
  A hook that breaks the session over its own bugs is worse than the
  harm it prevents.

Exit codes:

* 0 — allow the agent to declare the session done.
* 2 — BLOCK; stderr is surfaced to the model.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LINT_SPEC = REPO_ROOT / "scripts" / "lint_spec.py"

SCAFFOLDING_NAMES: frozenset[str] = frozenset({"_template.md", "README.md", "_postmortem.md"})


def _git_lines(args: list[str]) -> list[str]:
    """Run a ``git`` command and return stdout lines. Empty list on any error."""
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
            cwd=str(REPO_ROOT),
        ).stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return []
    return [line for line in out.splitlines() if line.strip()]


def _modified_specs() -> list[Path]:
    """Return the list of ``docs/specs/*.md`` files touched in the working tree.

    Catches three states:
      * tracked + modified (``git diff HEAD``);
      * staged but not yet committed (also covered by ``git diff HEAD``);
      * untracked but not gitignored (``git ls-files --others --exclude-standard``).

    Returns an empty list on any git error — fail open.
    """
    # Tracked + dirty (working tree or index vs. HEAD).
    tracked = _git_lines(["diff", "HEAD", "--name-only", "--", "docs/specs/*.md"])
    # New, never-tracked files.
    untracked = _git_lines(["ls-files", "--others", "--exclude-standard", "--", "docs/specs/*.md"])
    seen: set[str] = set()
    paths: list[Path] = []
    for rel in (*tracked, *untracked):
        if rel in seen:
            continue
        seen.add(rel)
        if Path(rel).name in SCAFFOLDING_NAMES:
            continue
        full = REPO_ROOT / rel
        if full.is_file():
            paths.append(full)
    return paths


def _run_lint(paths: list[Path]) -> tuple[int, str]:
    """Run ``lint_spec.py`` against each path. Returns (exit_code, stderr_text)."""
    if not paths:
        return 0, ""
    if not LINT_SPEC.is_file():
        return 0, ""  # Fail open — Phase 2 not fully bootstrapped yet.
    try:
        completed = subprocess.run(
            [sys.executable, str(LINT_SPEC), *[str(p) for p in paths]],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return 0, ""
    return completed.returncode, completed.stderr


def main() -> int:
    # Drain stdin (Claude Code feeds JSON, but we don't need any of it).
    with contextlib.suppress(Exception):
        sys.stdin.read()

    specs = _modified_specs()
    if not specs:
        return 0

    rc, lint_stderr = _run_lint(specs)
    if rc == 0:
        return 0

    print(
        "BLOCKED by require_just_check Stop hook.\n"
        "\n"
        "The current branch has modified spec files that fail "
        "`scripts/lint_spec.py`. Fix the lint errors below before "
        "declaring the session done. (Run `just lint-spec <path>` to "
        "iterate.)\n"
        "\n"
        f"{lint_stderr.rstrip()}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
