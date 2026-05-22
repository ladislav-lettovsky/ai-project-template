"""Parity check: AGENTS.md red-zone list matches red_zone_paths.py enforcement.

Prevents drift between the canonical human-facing list in AGENTS.md and the actual
enforcement code. The drift that motivated this test: auth/**, billing/**,
migrations/**, infra/** were enforced by the code but missing from AGENTS.md for
an extended period (fixed in PR #132).

Four assertions — both directions, both sets (exact paths and prefix wildcards) —
so any future mismatch is caught at CI time rather than in a manual doc review.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RZ_MOD_PATH = REPO_ROOT / "scripts" / "red_zone_paths.py"


def _load_rz():
    spec = importlib.util.spec_from_file_location("red_zone_paths", RZ_MOD_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("red_zone_paths", mod)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _parse_agents_md_red_zone() -> tuple[set[str], set[str]]:
    """Return (exact_paths, prefix_strings) parsed from AGENTS.md's code block.

    prefix_strings have '/**' stripped to the bare 'dir/' form (matching
    RED_ZONE_PREFIXES which ends with '/').
    """
    text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    match = re.search(r"## Red-zone files.*?```text\n(.*?)```", text, re.DOTALL)
    assert match, "Could not find '## Red-zone files' fenced code block in AGENTS.md"

    exact: set[str] = set()
    prefixes: set[str] = set()

    for line in match.group(1).splitlines():
        # Take the first token on the line; skip blank lines and comment-only lines.
        tokens = line.split()
        if not tokens:
            continue
        raw = tokens[0]
        if raw.endswith("/**"):
            prefixes.add(raw[:-2])  # strip '**', keep trailing '/' → e.g. 'auth/'
        else:
            exact.add(raw)

    return exact, prefixes


_rz = _load_rz()
_agents_exact, _agents_prefixes = _parse_agents_md_red_zone()


def test_agents_md_exact_paths_present_in_code() -> None:
    """Every exact path in AGENTS.md must be in red_zone_paths.RED_ZONE_PATHS."""
    missing = _agents_exact - _rz.RED_ZONE_PATHS
    assert not missing, (
        f"In AGENTS.md red-zone block but absent from RED_ZONE_PATHS: {sorted(missing)}\n"
        f"Add them to scripts/red_zone_paths.py or remove from AGENTS.md."
    )


def test_code_exact_paths_present_in_agents_md() -> None:
    """Every exact path in RED_ZONE_PATHS must be documented in AGENTS.md."""
    missing = _rz.RED_ZONE_PATHS - _agents_exact
    assert not missing, (
        f"In RED_ZONE_PATHS but absent from AGENTS.md red-zone block: {sorted(missing)}\n"
        f"Add them to the '## Red-zone files' section in AGENTS.md."
    )


def test_agents_md_prefixes_present_in_code() -> None:
    """Every '/**' wildcard in AGENTS.md must be a prefix in RED_ZONE_PREFIXES."""
    code_prefixes = set(_rz.RED_ZONE_PREFIXES)
    missing = _agents_prefixes - code_prefixes
    assert not missing, (
        f"In AGENTS.md as '/**' patterns but absent from RED_ZONE_PREFIXES: {sorted(missing)}\n"
        f"Add them to scripts/red_zone_paths.py or remove from AGENTS.md."
    )


def test_code_prefixes_present_in_agents_md() -> None:
    """Every prefix in RED_ZONE_PREFIXES must appear in AGENTS.md as a '/**' pattern."""
    code_prefixes = set(_rz.RED_ZONE_PREFIXES)
    missing = code_prefixes - _agents_prefixes
    assert not missing, (
        f"In RED_ZONE_PREFIXES but absent from AGENTS.md (as '/**' entries): {sorted(missing)}\n"
        f"Add them to the '## Red-zone files' section in AGENTS.md."
    )
