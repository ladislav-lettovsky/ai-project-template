"""Tests for ``scripts/validate_reviewer.py``.

The validator is what every PR's Reviewer JSON will be measured
against. False positives (reject a valid review) cost human time;
false negatives (accept a malformed review) defeat the entire point
of structured output.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_reviewer.py"
_spec = importlib.util.spec_from_file_location("validate_reviewer", VALIDATOR_PATH)
assert _spec is not None and _spec.loader is not None
validator_module = importlib.util.module_from_spec(_spec)
sys.modules["validate_reviewer"] = validator_module
_spec.loader.exec_module(validator_module)


VALID_REVIEWER_JSON: dict = {
    "summary": "Implementation looks correct; one weak-test nit.",
    "findings": [
        {
            "id": "F1",
            "type": "weak_test",
            "severity": "nit",
            "requirement_ids": ["R1"],
            "description": "T1 only checks the happy path; no negative-case branch.",
            "evidence": "tests/test_widget.py:14",
            "suggested_action": "Add a parametrized test with at least one None input.",
        }
    ],
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
    "confidence": 78,
}


def _wrap(obj_or_text) -> str:
    """Wrap a JSON object (or raw string) in a PR-body-style fenced block."""
    body = obj_or_text if isinstance(obj_or_text, str) else json.dumps(obj_or_text, indent=2)
    return (
        "## Verification\n\nblah blah\n\n"
        f"<!-- REVIEWER_JSON -->\n```json\n{body}\n```\n<!-- /REVIEWER_JSON -->\n\n"
        "More PR body text.\n"
    )


def _write(tmp_path: Path, pr_body: str) -> Path:
    f = tmp_path / "pr-body.md"
    f.write_text(pr_body, encoding="utf-8")
    return f


def test_valid_review_passes(tmp_path: Path) -> None:
    rc = validator_module.main([str(_write(tmp_path, _wrap(VALID_REVIEWER_JSON)))])
    assert rc == 0


def test_empty_findings_array_is_valid(tmp_path: Path) -> None:
    """A review with findings: [] is legitimate ('I reviewed it, found nothing')."""
    obj = json.loads(json.dumps(VALID_REVIEWER_JSON))
    obj["findings"] = []
    rc = validator_module.main([str(_write(tmp_path, _wrap(obj)))])
    assert rc == 0


def test_no_fence_markers_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = validator_module.main([str(_write(tmp_path, "Just a regular PR body."))])
    assert rc == 1
    assert "no <!-- REVIEWER_JSON" in capsys.readouterr().err


def test_multiple_fence_pairs_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Two REVIEWER_JSON blocks => fail loudly, do not silently pick first."""
    one = _wrap(VALID_REVIEWER_JSON)
    rc = validator_module.main([str(_write(tmp_path, one + "\n\n" + one))])
    assert rc == 1
    assert "expected exactly one" in capsys.readouterr().err


def test_empty_fence_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pr_body = "<!-- REVIEWER_JSON --><!-- /REVIEWER_JSON -->"
    rc = validator_module.main([str(_write(tmp_path, pr_body))])
    assert rc == 1
    assert "empty" in capsys.readouterr().err


def test_malformed_json_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pr_body = "<!-- REVIEWER_JSON -->\n```json\n{not valid json\n```\n<!-- /REVIEWER_JSON -->"
    rc = validator_module.main([str(_write(tmp_path, pr_body))])
    assert rc == 1
    assert "JSON parse error" in capsys.readouterr().err


def test_missing_required_field_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    obj = json.loads(json.dumps(VALID_REVIEWER_JSON))
    del obj["confidence"]
    rc = validator_module.main([str(_write(tmp_path, _wrap(obj)))])
    assert rc == 1
    assert "confidence" in capsys.readouterr().err


def test_invalid_enum_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    obj = json.loads(json.dumps(VALID_REVIEWER_JSON))
    obj["findings"][0]["severity"] = "blocker"  # not in critical/warning/nit
    rc = validator_module.main([str(_write(tmp_path, _wrap(obj)))])
    assert rc == 1
    assert "blocker" in capsys.readouterr().err


def test_invalid_type_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    obj = json.loads(json.dumps(VALID_REVIEWER_JSON))
    obj["confidence"] = "high"  # should be integer 0-100
    rc = validator_module.main([str(_write(tmp_path, _wrap(obj)))])
    assert rc == 1
    assert "confidence" in capsys.readouterr().err


def test_confidence_out_of_range_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    obj = json.loads(json.dumps(VALID_REVIEWER_JSON))
    obj["confidence"] = 150
    rc = validator_module.main([str(_write(tmp_path, _wrap(obj)))])
    assert rc == 1


def test_no_inner_md_fence_is_ok(tmp_path: Path) -> None:
    """JSON without the inner ```json fence is also acceptable."""
    body = json.dumps(VALID_REVIEWER_JSON, indent=2)
    pr_body = f"<!-- REVIEWER_JSON -->\n{body}\n<!-- /REVIEWER_JSON -->"
    rc = validator_module.main([str(_write(tmp_path, pr_body))])
    assert rc == 0


def test_extra_field_is_accepted(tmp_path: Path) -> None:
    """Schema does not set additionalProperties: false; extras pass through."""
    obj = json.loads(json.dumps(VALID_REVIEWER_JSON))
    obj["future_field"] = "from a hypothetical Reviewer v2"
    rc = validator_module.main([str(_write(tmp_path, _wrap(obj)))])
    assert rc == 0


def test_no_args_returns_two(capsys: pytest.CaptureFixture[str]) -> None:
    rc = validator_module.main([])
    assert rc == 2
    assert "usage" in capsys.readouterr().err.lower()


def test_file_not_found_returns_two(capsys: pytest.CaptureFixture[str]) -> None:
    rc = validator_module.main(["/nonexistent/file.md"])
    assert rc == 2
    assert "file not found" in capsys.readouterr().err


def test_stdin_input_works(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Argument '-' reads from stdin."""
    pr_body = _wrap(VALID_REVIEWER_JSON)
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(pr_body))
    rc = validator_module.main(["-"])
    assert rc == 0
