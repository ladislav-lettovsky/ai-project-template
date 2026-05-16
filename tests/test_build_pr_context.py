"""Tests for ``scripts/build_pr_context.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_BUILD_PATH = REPO_ROOT / "scripts" / "build_pr_context.py"


def _load_build():
    """Load ``build_pr_context`` with ``scripts/`` import path (matches CI)."""
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("build_pr_context", _BUILD_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build_pr_context = _load_build()


def _minimal_reviewer_fence() -> str:
    reviewer = {
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
        "confidence": 80,
    }
    blob = json.dumps(reviewer)
    return f"Intro\n<!-- REVIEWER_JSON -->\n{blob}\n<!-- /REVIEWER_JSON -->\n"


@pytest.fixture(scope="session")
def example_gh_blob() -> dict:
    slug_branch = "spec/phase-4-deterministic-router"
    return {
        "headRefName": slug_branch,
        "body": _minimal_reviewer_fence(),
        "files": [{"path": "docs/specs/phase-4-deterministic-router.md"}],
        "additions": 5,
        "deletions": 2,
    }


def test_slug_from_branch() -> None:
    assert build_pr_context.slug_from_branch("spec/foo-bar") == "foo-bar"
    assert build_pr_context.slug_from_branch("fix/foo-bar") == "foo-bar"
    assert build_pr_context.slug_from_branch("feat/x") is None


def test_build_context_fork_flag_inference(tmp_path: Path) -> None:
    ev_path = tmp_path / "evt.json"
    ev_path.write_text(
        json.dumps(
            {
                "pull_request": {
                    "head": {"repo": {"full_name": "fork/nested"}},
                }
            }
        ),
        encoding="utf-8",
    )
    inferred = build_pr_context.detect_fork_via_event(ev_path, base_full_name="orig/template")
    assert inferred is True
    inferred_same = build_pr_context.detect_fork_via_event(ev_path, base_full_name="fork/nested")
    assert inferred_same is False


def test_build_context_dict_happy(example_gh_blob: dict) -> None:
    canonical = REPO_ROOT / "docs" / "specs" / "phase-4-deterministic-router.md"
    assert canonical.is_file()

    blob = build_pr_context.build_context_dict(
        repo_full_name="test/ci",
        gh_json=example_gh_blob,
        repo_root=REPO_ROOT,
        fork_pr=False,
    )

    assert blob["branch_name"] == example_gh_blob["headRefName"]
    assert blob["fork_pr"] is False
    assert blob["diff_lines"] == 7
    assert blob["multiple_authorizing_specs_changed"] is False
    assert blob["reviewer_validation"]["status"] == "valid"
    assert blob["spec_validation"]["status"] == "valid"
    assert blob["spec"]["risk_tier"] == "T1"


def test_multiple_authorizing_specs_flag(example_gh_blob: dict) -> None:
    dup = dict(example_gh_blob)
    dup["files"] = [
        {"path": "docs/specs/foo.md"},
        {"path": "docs/specs/bar.md"},
    ]
    blob = build_pr_context.build_context_dict(
        repo_full_name="z/z",
        gh_json=dup,
        repo_root=REPO_ROOT,
        fork_pr=False,
    )
    assert blob["multiple_authorizing_specs_changed"] is True
