"""Smoke checks for ``.github/workflows/scheduled-executor.yml`` (Phase 6 Slice 3)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github/workflows" / "scheduled-executor.yml"


def test_scheduled_executor_workflow_exists() -> None:
    assert WORKFLOW.is_file()


def test_scheduled_executor_yaml_contract() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "schedule:" in text
    assert 'cron: "0 9 * * 1-5"' in text
    assert "workflow_dispatch:" in text
    assert "group: phase6-scheduled-executor" in text
    assert "cancel-in-progress: false" in text
    assert "github.event.repository.fork == false" in text
    assert "queue_specs.py" in text
    assert "dispatch_spec.py" in text
    assert "phase6-failure" in text
    assert "|| true" not in text
    assert "continue-on-error: true" not in text


def test_phase6_documentation_slice3() -> None:
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    blueprint = (REPO_ROOT / "docs" / "blueprint.md").read_text(encoding="utf-8")
    assert "Phase 6" in contributing
    assert "scheduled-executor.yml" in contributing
    assert "Phase 6" in blueprint
    assert "in-progress" in blueprint
