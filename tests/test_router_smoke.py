"""Smoke test for the in-process PR router happy path."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTE_PR_PATH = REPO_ROOT / "scripts" / "route_pr.py"


def _load_route_decision():
    spec = importlib.util.spec_from_file_location("route_pr_smoke_mod", ROUTE_PR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["route_pr_smoke_mod"] = module
    spec.loader.exec_module(module)
    return module.route_decision


def test_router_smoke_routes_policy_eligible_pr_to_codex() -> None:
    route_decision = _load_route_decision()
    policy = json.loads((REPO_ROOT / ".routing-policy.json").read_text(encoding="utf-8"))
    pr = {
        "changed_files": ["tests/test_router_smoke.py"],
        "diff_lines": 20,
        "multiple_authorizing_specs_changed": False,
        "reviewer_validation": {"status": "valid", "errors": []},
        "spec_validation": {"status": "valid", "errors": []},
        "reviewer": {
            "findings": [],
            "coverage": {
                "requirements_total": 1,
                "requirements_covered": 1,
                "tests_expected": 1,
                "tests_present": 1,
            },
            "confidence": 72,
        },
        "spec": {
            "slug": "phase4-router-smoke",
            "path": "docs/specs/phase4-router-smoke.md",
            "risk_tier": "T0",
            "complexity": "low",
        },
    }

    route, _reasons = route_decision(pr, policy)

    assert route == "review:codex"
