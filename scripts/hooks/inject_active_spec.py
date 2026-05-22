"""SessionStart hook: inject the authorising spec when on a spec/* or fix/* branch.

Reads the current git branch, finds docs/specs/<slug>.md if it exists, and
prints its full content to stdout so Claude Code can prepend it to the session
context as active-spec context. Always exits 0 — failure to locate or read the
spec must never block session start.

Exit codes:
  0 — always; this hook is informational only.
"""

from __future__ import annotations

import contextlib
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_SPEC_PREFIXES: tuple[str, ...] = ("spec/", "fix/")


def _current_branch() -> str | None:
    """Return the current git branch name, or None on any error (fail open)."""
    with contextlib.suppress(Exception):
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
            cwd=str(REPO_ROOT),
        )
        return result.stdout.strip()
    return None


def main() -> int:
    branch = _current_branch()
    if branch is None:
        return 0  # Not in a git repo or git unavailable — fail open.

    for prefix in _SPEC_PREFIXES:
        if branch.startswith(prefix):
            slug = branch[len(prefix) :]
            # Drill specs live at docs/specs/_drills/{slug}.md — one level deeper.
            # The hook intentionally does not fall back to that path: drills are
            # scheduler fixtures, not implementation specs, and must not be injected.
            spec_path = REPO_ROOT / "docs" / "specs" / f"{slug}.md"
            if spec_path.is_file():
                spec_text = spec_path.read_text(encoding="utf-8", errors="ignore")
                print(
                    f"[Active spec — docs/specs/{slug}.md]\n"
                    f"\n"
                    f"{spec_text.rstrip()}\n"
                    f"\n"
                    f"[End of active spec]",
                )
            else:
                print(
                    f"[inject_active_spec] Branch '{branch}' implies spec slug '{slug}' "
                    f"but docs/specs/{slug}.md does not exist yet. "
                    f"Create it before implementing.",
                )
            break  # Only the first matching prefix matters.

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
