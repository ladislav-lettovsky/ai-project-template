"""Canonical red-zone paths for hook enforcement and deterministic PR routing.

The list matches AGENTS.md + docs/blueprint.md §5.5. Imported by:

* ``scripts/hooks/check_red_zone.py`` — PreToolUse rejects edits before they occur.
* ``scripts/route_pr.py`` — declares ``review:human`` when a PR touches any path.
"""

from __future__ import annotations

from collections.abc import Iterable

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
        ".routing-policy.json",
        ".reviewer-schema.json",
    }
)

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
    """Return True if the repo-relative path is individually red-zone."""
    if rel_path in RED_ZONE_PATHS:
        return True
    return any(rel_path.startswith(prefix) for prefix in RED_ZONE_PREFIXES)


def touches_red_zone(changed_paths: Iterable[str]) -> bool:
    """Return True if any repo-relative changed path overlaps the red zone."""
    return any(is_red_zone(p) for p in changed_paths)
