"""Scan LLM-input-bearing files for known prompt-injection patterns.

Specs flow into the Planner's context window, agent / skill / cursor rules
flow into every agent invocation, and persisted MCP-tool or web-search
artifacts under ``docs/external/`` flow wherever you reference them. All
of these are user-controlled inputs from the LLM's perspective; treating
them as untrusted is the v2 widening of this scan (per blueprint §5.6).

Usage:
    uv run scripts/scan_injection.py                       # default scan set
    uv run scripts/scan_injection.py docs/specs/foo.md ... # explicit paths

Exit codes:
    0 — no injection patterns found (or no files matched the scan set).
    1 — at least one match. Each match is printed to stdout as
        ``ERROR: <path>: <pattern>``.

Design notes:
    The pattern list is intentionally a literal ``in`` substring match
    against the lower-cased file body. False positives are tolerable —
    any document that legitimately discusses these patterns will trigger
    the scan and either get rewritten to discuss them indirectly or be
    excluded from the scan set. False negatives (a clever attacker
    encoding the payload in base64 or with non-ASCII lookalikes) are
    out of scope until we see one in the wild.
"""

from __future__ import annotations

import sys
from pathlib import Path

INJECTION_PATTERNS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore the above",
    "system prompt",
    "developer message",
    "you are now",
    "override instructions",
    "<system>",
    "###instruction",
    "### instructions:",
    # MCP / web-source patterns added in v2:
    "tool_call_override",
    "skip approval",
    "disregard safety",
)

# File extensions worth scanning. ``.md``/``.mdc``/``.txt`` cover
# specs, agent definitions, skills, and Cursor rules; ``.json`` covers
# persisted MCP responses, ``.html`` covers persisted web fetches.
SCAN_EXTENSIONS: frozenset[str] = frozenset({".md", ".mdc", ".txt", ".json", ".html"})

# Default scan set when no paths are supplied. Each entry is either a
# file (scanned directly) or a directory (recursed into).
DEFAULT_SCAN_TARGETS: tuple[str, ...] = (
    "docs/specs",
    "docs/external",
    ".claude/agents",
    ".claude/skills",
    ".cursor/rules",
    "AGENTS.md",
)


def scan_file(path: Path) -> list[str]:
    """Return the list of patterns matched in ``path`` (case-insensitive)."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return []
    text = " ".join(text.split())
    return [p for p in INJECTION_PATTERNS if p in text]


def iter_targets(args: list[str]) -> list[Path]:
    """Expand a list of file/dir arguments into the set of files to scan.

    A non-existent path is silently skipped; the default scan set may
    reference paths that don't exist on every checkout (e.g.
    ``docs/external`` on a fresh repo).
    """
    paths: list[Path] = []
    for arg in args:
        p = Path(arg)
        if not p.exists():
            continue
        if p.is_file():
            paths.append(p)
        else:
            for child in p.rglob("*"):
                if child.is_file() and child.suffix in SCAN_EXTENSIONS:
                    paths.append(child)
    return paths


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    targets = iter_targets(args or list(DEFAULT_SCAN_TARGETS))
    hits: list[str] = []
    for target in targets:
        for pattern in scan_file(target):
            hits.append(f"ERROR: {target}: {pattern}")

    for h in hits:
        print(h)

    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
