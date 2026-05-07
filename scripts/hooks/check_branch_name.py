"""UserPromptSubmit hook: reject prompts on improperly-named branches.

Invoked by Claude Code when the user submits a prompt. Reads the current
git branch; permits 'main', branches starting with 'spec/', and branches
starting with 'fix/' (Invariant 1). Rejects anything else with guidance.

Exit codes:

* 0 — allow the prompt to proceed (current branch is acceptable, OR git is
      unavailable / not a repo, in which case we fail open).
* 2 — BLOCK the prompt; stderr is surfaced to the user.
"""

from __future__ import annotations

import subprocess
import sys


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

    if branch.startswith("spec/") or branch.startswith("fix/"):
        return 0

    print(
        f"BLOCKED by branch-name hook: current branch is '{branch}'.\n"
        f"\n"
        f"Invariant 1 requires work branches to start with 'spec/<slug>' or\n"
        f"'fix/<slug>'. Either:\n"
        f"  - rename:  git branch -m {branch} spec/<slug>\n"
        f"  - or check out an appropriate branch before continuing.\n",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
