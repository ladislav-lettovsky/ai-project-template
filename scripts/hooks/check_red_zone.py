"""PreToolUse hook: reject Edit/Write/MultiEdit on red-zone paths.

Invoked by Claude Code before any Edit/Write/MultiEdit tool call. Receives
the tool-call JSON via stdin. Exit codes:

* 0 — allow the tool call to proceed.
* 2 — BLOCK the tool call; stderr is surfaced to the model.

Fail-open semantics: if the input is malformed, git is unavailable, or any
other framework-side problem occurs, the hook returns 0. Hooks must never
break the session over their own bugs — that would be worse than the harm
they prevent.

The canonical red-zone list lives in AGENTS.md (section 'Red-zone files')
and docs/blueprint.md §5.5. Keep all three in sync.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Exact-match paths.
RED_ZONE_PATHS: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "CLAUDE.md",
        ".claude/settings.json",
        ".codex/config.toml",
        "pyproject.toml",
        "uv.lock",
        ".pre-commit-config.yaml",
        "justfile",
        ".routing-policy.json",  # Phase 4
        ".reviewer-schema.json",  # Phase 3
    }
)

# Prefix-match paths (anything starting with these is red-zone).
RED_ZONE_PREFIXES: tuple[str, ...] = (
    ".claude/agents/",
    ".claude/skills/",
    ".cursor/rules/",
    ".github/workflows/",
    "scripts/hooks/",
    "auth/",
    "billing/",
    "migrations/",
    "infra/",
)


def is_red_zone(rel_path: str) -> bool:
    """Return True if the given repo-relative path is in the red zone."""
    if rel_path in RED_ZONE_PATHS:
        return True
    return any(rel_path.startswith(prefix) for prefix in RED_ZONE_PREFIXES)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Malformed input — fail open.
        return 0

    tool_input = payload.get("tool_input", {})
    target = tool_input.get("file_path", "")
    if not target:
        return 0

    # Normalize to a path relative to the repo root (cwd at hook invocation).
    repo_root = Path.cwd().resolve()
    try:
        rel = str(Path(target).resolve().relative_to(repo_root))
    except ValueError:
        # Target is outside the repo — let other layers handle it.
        return 0

    if is_red_zone(rel):
        print(
            f"BLOCKED by red-zone hook: {rel}\n"
            f"\n"
            f"This path is governed by Invariant 7 + the red-zone list in "
            f"AGENTS.md.\n"
            f"Edits require explicit human action outside the agent session "
            f"(open the\n"
            f"file in your editor and commit it manually, or branch protection "
            f"rules\n"
            f"can be intentionally relaxed for a single PR).",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
