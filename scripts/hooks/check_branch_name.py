"""UserPromptSubmit hook: reject prompts on improperly-named branches.

Invoked by Claude Code when the user submits a prompt. Reads the current
git branch; permits ``main``, the parking branch ``scratch`` (prompt intake
only; see ``check_no_edits_on_scratch.py``), and branches starting with
``chore/``, ``docs/``, ``feat/``, ``fix/``, ``refactor/``, ``spec/``, or
``test/``. Rejects anything else with guidance. (Mergeable PRs still follow
Invariant 1: ``spec/<slug>`` or ``fix/<slug>``.)

Spec: SPEC-20260514-branch-name-hook-allowlist

Exit codes:

* 0 — allow the prompt to proceed (current branch is acceptable, OR git is
      unavailable / not a repo, in which case we fail open).
* 2 — BLOCK the prompt; stderr is surfaced to the user.
"""

from __future__ import annotations

import subprocess
import sys

# Conventional work prefixes (see ``.cursor/rules/00-always.mdc``). Prompt-time
# acceptance is wider than Invariant 1: PRs still require spec/<slug> or
# fix/<slug> when merging traceable work.
_ALLOWED_PREFIXES: tuple[str, ...] = (
    "chore/",
    "docs/",
    "feat/",
    "fix/",
    "refactor/",
    "spec/",
    "test/",
)


def current_branch() -> str | None:
    """Return the current git branch, or None if git can't tell us."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    return result.stdout.strip()


def main() -> int:
    branch = current_branch()
    if branch is None:
        # Not in a git repo, or git timed out — fail open.
        return 0

    # 'main' is permitted: read-only conversation is fine; any actual commit
    # is caught by the no-commit-to-branch pre-commit hook anyway.
    if branch == "main":
        return 0

    # Parking branch: prompts allowed so the agent can run ``git branch -m``.
    if branch == "scratch":
        return 0

    if any(branch.startswith(p) for p in _ALLOWED_PREFIXES):
        return 0

    human_prefixes = ", ".join(repr(p.rstrip("/")) for p in _ALLOWED_PREFIXES)
    print(
        f"BLOCKED by branch-name hook: current branch is '{branch}'.\n"
        f"\n"
        f"Permitted names: 'main', 'scratch', or a prefix in {human_prefixes}.\n"
        f"Open PRs that must satisfy Invariant 1 still use 'spec/<slug>' or "
        f"'fix/<slug>'.\n"
        f"\n"
        f"Either:\n"
        f"  - rename:  git branch -m {branch} spec/<slug>  "
        f"(or fix/<slug>, feat/<name>, …)\n"
        f"  - or check out an appropriate branch before continuing.\n",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
