"""Tests for ``scripts/codex_ci.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_CODEX_CI_PATH = REPO_ROOT / "scripts" / "codex_ci.py"


def _load_codex_ci():
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("codex_ci", _CODEX_CI_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


codex_ci = _load_codex_ci()


def test_executor_prompt_names_spec() -> None:
    text = codex_ci.executor_prompt("docs/specs/foo.md")
    assert "docs/specs/foo.md" in text
    assert "just check" in text


def test_write_prompt_creates_file(tmp_path: Path) -> None:
    out = tmp_path / "prompt.md"
    codex_ci.write_prompt(role="reviewer", spec_path="docs/specs/x.md", output=out)
    assert out.is_file()
    assert "REVIEWER_JSON" in out.read_text(encoding="utf-8")


def test_merge_reviewer_into_body_replaces_fence() -> None:
    body = "Intro\n\n<!-- REVIEWER_JSON -->\n{}\n<!-- /REVIEWER_JSON -->\n"
    reviewer = {"summary": "ok", "findings": [], "confidence": 80}
    merged = codex_ci.merge_reviewer_into_body(body, reviewer)
    assert '"summary": "ok"' in merged
    assert merged.count("REVIEWER_JSON") == 2


def test_extract_reviewer_json_from_fence() -> None:
    payload = {
        "summary": "s",
        "findings": [],
        "coverage": {
            "requirements_total": 1,
            "requirements_covered": 1,
            "tests_expected": 1,
            "tests_present": 1,
        },
        "risk_assessment": {
            "scope_fit": "correct",
            "invariant_risk": "low",
            "production_risk": "low",
        },
        "confidence": 90,
    }
    text = f"<!-- REVIEWER_JSON -->\n```json\n{json.dumps(payload)}\n```\n<!-- /REVIEWER_JSON -->"
    parsed = codex_ci.extract_reviewer_json_block(text)
    assert parsed["confidence"] == 90


def test_parse_pr_number() -> None:
    assert codex_ci.parse_pr_number("https://github.com/o/r/pull/42") == 42


def test_codex_api_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CODEX_API_KEY", raising=False)
    assert codex_ci.codex_api_key_present() is False
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert codex_ci.codex_api_key_present() is True
