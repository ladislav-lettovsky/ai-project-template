"""PreToolUse hook: reject Edit/Write/MultiEdit on red-zone paths."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.red_zone_paths import is_red_zone  # noqa: E402


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_input = payload.get("tool_input", {})
    target = tool_input.get("file_path", "")
    if not target:
        return 0

    repo_root = Path.cwd().resolve()
    try:
        rel = str(Path(target).resolve().relative_to(repo_root))
    except ValueError:
        return 0

    if is_red_zone(rel):
        print(
            f"BLOCKED by red-zone hook: {rel}\n\n"
            f"This path is governed by Invariant 7 + the red-zone list in AGENTS.md.\n"
            f"Use a human-authored commit outside agent sessions.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
