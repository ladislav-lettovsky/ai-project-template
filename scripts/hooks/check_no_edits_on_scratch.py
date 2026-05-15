"""PreToolUse hook: block Edit/Write/MultiEdit while on parking branch ``scratch``.

Allows prompt submission on ``scratch`` (see ``check_branch_name.py``) but
prevents file mutations until the branch is renamed to ``spec/<slug>`` or
``fix/<slug>``.

Detached HEAD and other non-``scratch`` branch names are not blocked here.
Fail-open when git cannot resolve the branch (same policy as
``check_branch_name.py``).

Spec: SPEC-20260514-scratch-branch-edit-guard

Exit codes:

* 0 — allow the tool call (not on ``scratch``, malformed PreToolUse JSON, or
      git unavailable).
* 2 — BLOCK the edit; stderr instructs the agent to rename the branch.
"""

from __future__ import annotations

import json
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
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Malformed PreToolUse payload — fail open (match ``check_red_zone``).
        return 0

    branch = current_branch()
    if branch is None:
        return 0

    if branch == "scratch":
        print(
            "BLOCKED: file edits are not allowed on the parking branch "
            "'scratch'.\n"
            "\n"
            "Rename to a work branch first, then edit files:\n"
            "  git branch -m scratch spec/<slug>\n"
            "  git branch -m scratch fix/<slug>\n",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
