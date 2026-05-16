"""Tests for deterministic PR routing (`scripts/route_pr.py`)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_ROUT_PATH = REPO_ROOT / "scripts" / "route_pr.py"


def _load_route_module():
    spec = importlib.util.spec_from_file_location("route_pr_mod", _ROUT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["route_pr_mod"] = module
    spec.loader.exec_module(module)
    return module


route_module = _load_route_module()

BASE_POLICY: dict = {
    "max_changed_files": 3,
    "max_diff_lines": 150,
    "min_reviewer_confidence": 60,
    "auto_review_allowed_risk_tiers": ["T0"],
    "auto_review_allowed_complexity": ["low"],
}

VALID_REVIEW: dict = {
    "summary": "ok",
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
    "confidence": 72,
}


def _valid_pr_skeleton() -> dict:
    return {
        "changed_files": ["src/foo.py"],
        "diff_lines": 20,
        "multiple_authorizing_specs_changed": False,
        "reviewer_validation": {"status": "valid", "errors": []},
        "spec_validation": {"status": "valid", "errors": []},
        "reviewer": VALID_REVIEW,
        "spec": {"slug": "x", "path": "docs/specs/x.md", "risk_tier": "T0", "complexity": "low"},
    }


def test_reviewer_validation_invalid_human() -> None:
    pr = _valid_pr_skeleton()
    pr["reviewer_validation"] = {"status": "invalid", "errors": ["x"]}
    label, reasons = route_module.route_decision(pr, BASE_POLICY)
    assert label == "review:human"
    assert reasons[0].startswith("Reviewer JSON")


def test_spec_validation_invalid_human() -> None:
    pr = _valid_pr_skeleton()
    pr["spec_validation"] = {"status": "invalid", "errors": ["lint failed"]}
    label, reasons = route_module.route_decision(pr, BASE_POLICY)
    assert label == "review:human"
    assert "Spec lint" in reasons[0]


def test_multiple_specs_human() -> None:
    pr = _valid_pr_skeleton()
    pr["multiple_authorizing_specs_changed"] = True
    label, reasons = route_module.route_decision(pr, BASE_POLICY)
    assert label == "review:human"
    assert "docs/specs" in reasons[0]


def test_red_zone_human() -> None:
    pr = _valid_pr_skeleton()
    pr["changed_files"] = ["AGENTS.md"]
    label, reasons = route_module.route_decision(pr, BASE_POLICY)
    assert label == "review:human"
    assert "red-zone" in reasons[0]


def test_critical_blocked() -> None:
    inst = dict(VALID_REVIEW)
    inst["findings"] = [
        {
            "id": "f1",
            "type": "invariant_risk",
            "severity": "critical",
            "requirement_ids": [],
            "description": "",
            "evidence": "",
            "suggested_action": "",
        }
    ]
    pr = _valid_pr_skeleton()
    pr["reviewer"] = inst
    label, reasons = route_module.route_decision(pr, BASE_POLICY)
    assert label == "blocked"


def test_tier_human() -> None:
    pr = _valid_pr_skeleton()
    spec = dict(pr["spec"])
    spec["risk_tier"] = "T1"
    pr["spec"] = spec
    label, _ = route_module.route_decision(pr, BASE_POLICY)
    assert label == "review:human"


def test_too_many_files_human() -> None:
    pr = _valid_pr_skeleton()
    pr["changed_files"] = ["a.py", "b.py", "c.py", "d.py"]
    label, reasons = route_module.route_decision(pr, BASE_POLICY)
    assert label == "review:human"
    assert "Changed files" in reasons[0]


def test_large_diff_human() -> None:
    pr = _valid_pr_skeleton()
    pr["diff_lines"] = 500
    label, reasons = route_module.route_decision(pr, BASE_POLICY)
    assert label == "review:human"
    assert "Diff lines" in reasons[0]


def test_low_confidence_human() -> None:
    pr = _valid_pr_skeleton()
    reviewer = dict(VALID_REVIEW)
    reviewer["confidence"] = 40
    pr["reviewer"] = reviewer
    label, reasons = route_module.route_decision(pr, BASE_POLICY)
    assert label == "review:human"
    assert "confidence" in reasons[0]


def test_incomplete_coverage_human() -> None:
    pr = _valid_pr_skeleton()
    reviewer = dict(VALID_REVIEW)
    reviewer["coverage"] = {
        "requirements_total": 3,
        "requirements_covered": 1,
        "tests_expected": 2,
        "tests_present": 2,
    }
    pr["reviewer"] = reviewer
    label, reasons = route_module.route_decision(pr, BASE_POLICY)
    assert label == "review:human"
    assert "coverage" in reasons[0]


def test_happy_path_codex() -> None:
    pr = _valid_pr_skeleton()
    label, reasons = route_module.route_decision(pr, BASE_POLICY)
    assert label == "review:codex"
    assert "satisfied" in reasons[0].lower()


def test_cli_writes_json_stdout(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Smoke end-to-end: load pr.json policy file routing."""
    pr_path = tmp_path / "pr.json"
    policy_path = REPO_ROOT / ".routing-policy.json"
    assert policy_path.is_file()
    pr_path.write_text(json.dumps(_valid_pr_skeleton()), encoding="utf-8")
    rc = route_module.main([str(pr_path), "--policy", str(policy_path)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert data["route"] == "review:codex"
