"""Smoke checks for ``.github/workflows/ci.yml`` workflow_dispatch follow-up."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPO_ROOT / ".github/workflows" / "ci.yml"
ROUTE_WORKFLOW = REPO_ROOT / ".github/workflows" / "route-pr.yml"


def test_ci_workflow_supports_scheduler_dispatch() -> None:
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "inputs:" in text
    assert "ref:" in text
    assert "github.event_name == 'workflow_dispatch'" in text


def test_route_workflow_supports_scheduler_dispatch() -> None:
    text = ROUTE_WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "pr_number:" in text
    assert "Resolve PR metadata" in text
    assert "steps.pr_meta.outputs.pr_number" in text
    assert "--github-event" in text
    assert "skip_label_apply" in text
