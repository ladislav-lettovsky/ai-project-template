"""Registration and doc alignment for scratch parking hooks."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _pre_edit_hooks(host: str) -> list[dict[str, str]]:
    path = REPO_ROOT / host
    data = json.loads(path.read_text(encoding="utf-8"))
    blocks = data["hooks"]["PreToolUse"]
    for block in blocks:
        if block.get("matcher") == "Edit|Write|MultiEdit":
            return list(block["hooks"])
    raise AssertionError(f"no Edit|Write|MultiEdit block in {path}")


def test_claude_pretool_sequence() -> None:
    hooks = _pre_edit_hooks(".claude/settings.json")
    assert [h["command"] for h in hooks] == [
        "uv run scripts/hooks/check_red_zone.py",
        "uv run scripts/hooks/check_no_edits_on_scratch.py",
    ]


def test_codex_pretool_sequence() -> None:
    hooks = _pre_edit_hooks(".codex/hooks.json")
    assert [h["command"] for h in hooks] == [
        "uv run scripts/hooks/check_red_zone.py",
        "uv run scripts/hooks/check_no_edits_on_scratch.py",
    ]


def test_agents_documents_scratch_lifecycle() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "prompt intake and branch selection" in agents
    assert "check_no_edits_on_scratch.py" in agents


def test_blueprint_documents_scratch_exception() -> None:
    bp = (REPO_ROOT / "docs" / "blueprint.md").read_text(encoding="utf-8")
    assert "parking branch `scratch`" in bp
    assert "check_no_edits_on_scratch.py" in bp
