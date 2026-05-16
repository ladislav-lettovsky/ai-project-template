"""Tests for ``scripts/adapt_thresholds.py``."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_ADAPT_PATH = REPO_ROOT / "scripts" / "adapt_thresholds.py"


def _load_adapt():
    spec = importlib.util.spec_from_file_location("adapt_thresholds", _ADAPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


adapt_mod = _load_adapt()

BASE_POLICY = {
    "version": 1,
    "max_changed_files": 3,
    "max_diff_lines": 150,
    "min_reviewer_confidence": 60,
    "auto_review_allowed_risk_tiers": ["T0"],
    "auto_review_allowed_complexity": ["low"],
    "adaptive": {
        "enabled": False,
        "floor_max_diff_lines": 50,
        "ceiling_min_reviewer_confidence": 85,
    },
}


def test_no_changes_without_signals() -> None:
    events = [{"route_decision": "review:codex", "reviewer_validation_status": "valid"}]
    updated, notes = adapt_mod.adapt(events, BASE_POLICY)
    assert updated["max_diff_lines"] == 150
    assert updated["min_reviewer_confidence"] == 60
    assert any("No threshold" in n for n in notes)


def test_blocked_tightens_diff_lines() -> None:
    events = [{"route_decision": "blocked", "reviewer_validation_status": "valid"}]
    updated, notes = adapt_mod.adapt(events, BASE_POLICY)
    assert updated["max_diff_lines"] == 125
    assert any("max_diff_lines" in n for n in notes)


def test_invalid_reviewer_raises_confidence_floor() -> None:
    events = [{"route_decision": "review:human", "reviewer_validation_status": "invalid"}]
    updated, notes = adapt_mod.adapt(events, BASE_POLICY)
    assert updated["min_reviewer_confidence"] == 65
    assert any("min_reviewer_confidence" in n for n in notes)


def test_respects_floor_and_ceiling() -> None:
    policy = json.loads(json.dumps(BASE_POLICY))
    policy["max_diff_lines"] = 55
    events = [{"route_decision": "blocked"}]
    updated, _ = adapt_mod.adapt(events, policy)
    assert updated["max_diff_lines"] == 50

    policy["min_reviewer_confidence"] = 84
    events = [{"reviewer_validation_status": "invalid"}]
    updated, _ = adapt_mod.adapt(events, policy)
    assert updated["min_reviewer_confidence"] == 85
