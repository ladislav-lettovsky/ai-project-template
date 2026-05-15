"""Lint a spec file under docs/specs/ for the structure required by §5.1.

Usage:
    uv run scripts/lint_spec.py docs/specs/<slug>.md [docs/specs/<other>.md ...]

Exit codes:
    0 — every spec is valid.
    1 — one or more specs failed the lint. Errors printed to stderr, one
        per violation, prefixed ``ERROR: <path>: <message>``.
    2 — usage error (no paths supplied, path not found, etc.).

Design notes:
    The parser is intentionally line-oriented and stdlib-only. Specs are
    plain Markdown with a rigid §5.1 structure; a full markdown AST is
    overkill and pulls in a dependency. Twenty lines of regex are easier
    to audit than a parser.

    Requirement IDs are matched as either ``R<digits>`` or
    ``REQ-<UPPER-AND-DIGITS-AND-DASHES>``; both forms appear in the wild
    (the blueprint template uses ``R1``; the example spec uses
    ``REQ-GREET-01``).
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration — keep in sync with docs/specs/README.md and §5.1.
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS: tuple[str, ...] = (
    "Metadata",
    "Context",
    "Assumptions",
    "Decisions",
    "Problem Statement",
    "Requirements (STRICT)",
    "Non-Goals",
    "Interfaces",
    "Invariants to Preserve",
    "Red-Zone Assessment",
    "Test Plan",
    "Validation Contract",
    "Edge Cases",
    "Security / Prompt-Injection Review",
    "Observability",
    "Rollback / Recovery",
    "Implementation Slices",
    "Done When",
)

ALLOWED_RISK_TIERS: frozenset[str] = frozenset({"T0", "T1", "T2", "T3"})
ALLOWED_COMPLEXITY: frozenset[str] = frozenset({"low", "medium", "high"})

# Requirement-ID alternation. Single source of truth for every regex
# below that matches a requirement ID. Add new ID conventions (e.g.
# ``FR-01``) here and they will be picked up everywhere automatically.
REQ_ID_ALT = r"R\d+|REQ-[A-Z0-9][A-Z0-9-]*"

# ``R1``, ``R12``, ``REQ-GREET-01`` — must start at a word boundary, not
# mid-word. Used to scan Requirements bullets and Test Plan ID lists.
REQ_ID_RE = re.compile(rf"\b({REQ_ID_ALT})\b")

# Requirement declaration line under ``## Requirements (STRICT)``. Only the
# leading ID after the bullet/optional checkbox is the declaring ID.
REQ_DECL_RE = re.compile(rf"^\s*[-*]\s*(?:\[[ xX]\]\s*)?(?P<id>{REQ_ID_ALT})\b")

# ``## Section Name`` at column 0.
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")

# ``- key: value`` (Metadata block).
META_LINE_RE = re.compile(r"^-\s+(?P<key>[a-z_]+)\s*:\s*(?P<value>.+?)\s*$")

# ``- key: yes|no`` (Red-Zone Assessment block).
REDZONE_LINE_RE = re.compile(r"^\s*-\s*(?P<key>.+?)\s*:\s*(?P<value>yes|no)\s*$", re.IGNORECASE)

# Test Plan mapping line. We accept both checked and unchecked checkboxes
# and bullet-prefixed lines: ``- [ ] T1 -> covers R1, R2`` or
# ``- **T1** → covers REQ-GREET-01``. Both ASCII ``->`` and the Unicode
# arrow ``→`` are accepted; both render identically in prose Markdown.
ARROW = r"(?:->|→)"
TEST_MAP_RE = re.compile(
    rf"\bT\d+\b.*?{ARROW}\s*covers\s+(?P<ids>[A-Za-z0-9_,\s\-]+?)(?:\.|$)",
    re.IGNORECASE,
)

# Validation Contract line: ``R1 -> just check``, or table rows where the
# first cell is ``REQ-GREET-01`` and a later token is ``just check``. We
# match the requirement ID followed by ``->`` (in a list line) or by ``|``
# in a markdown table — both shapes appear in the example spec.
VALIDATION_LIST_RE = re.compile(
    rf"^\s*[-*]\s*(?P<id>{REQ_ID_ALT})\s*{ARROW}",
    re.MULTILINE,
)
VALIDATION_TABLE_RE = re.compile(
    rf"^\s*\|\s*`?(?P<id>{REQ_ID_ALT})`?\s*\|",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Section split
# ---------------------------------------------------------------------------


def split_sections(text: str) -> dict[str, str]:
    """Return a dict mapping ``## Section`` heading text → section body.

    Body excludes the heading line. Order is preserved by Python 3.7+ dict
    semantics, but callers should not rely on it; ``check_section_order``
    handles ordering separately.
    """
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = match.group(1).strip()
            buffer = []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "\n".join(buffer).strip()
    return sections


def heading_order(text: str) -> list[str]:
    """Return ``## Section`` headings in document order."""
    return [m.group(1).strip() for line in text.splitlines() if (m := HEADING_RE.match(line))]


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_required_sections(headings: list[str]) -> list[str]:
    """Every required heading must be present (order checked separately)."""
    missing = [s for s in REQUIRED_SECTIONS if s not in headings]
    return [f"missing required section: '## {s}'" for s in missing]


def check_section_order(headings: list[str]) -> list[str]:
    """Required headings must appear in the canonical order."""
    indices: list[tuple[int, str]] = []
    for required in REQUIRED_SECTIONS:
        if required in headings:
            indices.append((headings.index(required), required))
    last_idx = -1
    last_name = ""
    errors: list[str] = []
    for idx, name in indices:
        if idx < last_idx:
            errors.append(
                f"section '## {name}' appears before '## {last_name}' "
                f"but should follow it (canonical order: {' > '.join(REQUIRED_SECTIONS)})"
            )
        last_idx = idx
        last_name = name
    return errors


def parse_metadata(body: str) -> dict[str, str]:
    """Parse the ``- key: value`` lines out of the Metadata section body."""
    out: dict[str, str] = {}
    for line in body.splitlines():
        m = META_LINE_RE.match(line)
        if m:
            out[m.group("key")] = m.group("value").strip()
    return out


def check_metadata(metadata: dict[str, str]) -> list[str]:
    """Metadata must include valid ``risk_tier`` and ``complexity``."""
    errors: list[str] = []
    risk = metadata.get("risk_tier")
    if risk is None:
        errors.append("Metadata is missing 'risk_tier'")
    elif risk not in ALLOWED_RISK_TIERS:
        errors.append(f"Metadata 'risk_tier: {risk}' is not one of {sorted(ALLOWED_RISK_TIERS)}")
    complexity = metadata.get("complexity")
    if complexity is None:
        errors.append("Metadata is missing 'complexity'")
    elif complexity not in ALLOWED_COMPLEXITY:
        errors.append(
            f"Metadata 'complexity: {complexity}' is not one of {sorted(ALLOWED_COMPLEXITY)}"
        )
    return errors


def check_redzone_tier_consistency(metadata: dict[str, str], redzone_body: str) -> list[str]:
    """T0 specs cannot mark any Red-Zone Assessment item as ``yes``."""
    if metadata.get("risk_tier") != "T0":
        return []

    yes_keys: list[str] = []
    for line in redzone_body.splitlines():
        match = REDZONE_LINE_RE.match(line)
        if match and match.group("value").lower() == "yes":
            yes_keys.append(match.group("key"))

    if not yes_keys:
        return []

    return [
        "Red-Zone Assessment marks yes for "
        f"{', '.join(yes_keys)}; spec cannot ship as risk_tier: T0"
    ]


def collect_requirements(body: str) -> list[str]:
    """Extract requirement IDs from the body of the Requirements section.

    Considers only lines that start with a bullet (``-`` or ``*``) — IDs
    referenced inside prose under Requirements are intentionally ignored.
    """
    ids: list[str] = []
    for line in body.splitlines():
        if match := REQ_DECL_RE.match(line):
            ids.append(match.group("id"))
    return ids


def duplicate_requirement_errors(requirements: Iterable[str]) -> list[str]:
    """Return one duplicate-ID error per duplicated requirement, in order."""
    seen: set[str] = set()
    reported: set[str] = set()
    errors: list[str] = []
    for req in requirements:
        if req in seen and req not in reported:
            errors.append(f"requirement '{req}' is declared more than once")
            reported.add(req)
        seen.add(req)
    return errors


def collect_test_coverage(body: str) -> set[str]:
    """Set of requirement IDs cited in Test Plan ``T<n> -> covers R<list>`` lines."""
    covered: set[str] = set()
    for line in body.splitlines():
        m = TEST_MAP_RE.search(line)
        if m:
            for token in REQ_ID_RE.findall(m.group("ids")):
                covered.add(token)
    return covered


def collect_validation_ids(body: str) -> set[str]:
    """Set of requirement IDs that appear as a validator key.

    Matches both list shape (``- R1 -> just check``) and the markdown-table
    shape used in the example spec (``| REQ-GREET-01 | pytest ... |``).
    """
    ids: set[str] = set()
    for m in VALIDATION_LIST_RE.finditer(body):
        ids.add(m.group("id"))
    for m in VALIDATION_TABLE_RE.finditer(body):
        ids.add(m.group("id"))
    return ids


def check_requirement_mapping(
    requirements: Iterable[str], test_covered: set[str], validated: set[str]
) -> list[str]:
    """Every requirement must be both T-covered and have a Validation entry."""
    errors: list[str] = []
    for req in requirements:
        if req not in test_covered:
            errors.append(
                f"requirement '{req}' has no matching 'T<n> -> covers {req}' entry in Test Plan"
            )
        if req not in validated:
            errors.append(
                f"requirement '{req}' has no matching '{req} -> ...' entry in Validation Contract"
            )
    return errors


# ---------------------------------------------------------------------------
# Top-level entrypoint
# ---------------------------------------------------------------------------


def lint_spec(path: Path) -> list[str]:
    """Return a list of human-readable error messages. Empty list = clean."""
    text = path.read_text(encoding="utf-8")
    headings = heading_order(text)
    sections = split_sections(text)

    errors: list[str] = []
    errors += check_required_sections(headings)
    errors += check_section_order(headings)

    metadata = parse_metadata(sections.get("Metadata", ""))
    errors += check_metadata(metadata)
    errors += check_redzone_tier_consistency(metadata, sections.get("Red-Zone Assessment", ""))

    requirements = collect_requirements(sections.get("Requirements (STRICT)", ""))
    if not requirements:
        errors.append("no requirements found under '## Requirements (STRICT)'")
    errors += duplicate_requirement_errors(requirements)
    mapped_requirements = list(dict.fromkeys(requirements))

    test_covered = collect_test_coverage(sections.get("Test Plan", ""))
    validated = collect_validation_ids(sections.get("Validation Contract", ""))
    errors += check_requirement_mapping(mapped_requirements, test_covered, validated)

    return errors


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: lint_spec.py <spec-path> [<spec-path> ...]", file=sys.stderr)
        return 2

    overall_errors: list[str] = []
    for arg in args:
        path = Path(arg)
        if not path.is_file():
            print(f"ERROR: {path}: file not found", file=sys.stderr)
            overall_errors.append(str(path))
            continue
        for err in lint_spec(path):
            print(f"ERROR: {path}: {err}", file=sys.stderr)
            overall_errors.append(str(path))

    return 1 if overall_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
