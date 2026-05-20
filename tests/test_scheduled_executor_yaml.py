"""Smoke checks for ``.github/workflows/scheduled-executor.yml`` (scheduled executor workflow)."""

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
    assert "group: scheduled-executor" in text
    assert "cancel-in-progress: false" in text
    assert "github.event.repository.fork == false" in text
    assert "queue_specs.py" in text
    assert "dispatch_spec.py" in text
    assert "codex_executor" in text
    assert "codex_reviewer" in text
    assert text.count("openai/codex-action@v1") == 2
    assert text.count("safety-strategy: drop-sudo") == 2
    assert "safety-strategy: read-only" not in text
    assert "codex-home: ${{ runner.temp }}/codex-executor" in text
    assert "codex-home: ${{ runner.temp }}/codex-reviewer" in text
    assert "OPENAI_API_KEY" in text
    assert "codex_enabled" in text
    assert "codex_gate" in text
    assert "Detect Codex CI availability" in text
    assert "secrets.OPENAI_API_KEY != ''" not in text
    assert "pull-requests: write" in text
    assert "scheduler-failure" in text
    assert "|| true" not in text
    assert "continue-on-error: true" not in text
    assert "validate_reviewer.py .scratch/pr-body.md" in text
    assert "trigger_pr_checks" in text
    assert "gh workflow run ci.yml" in text
    assert "gh workflow run route-pr.yml" in text


def test_scheduled_executor_documented() -> None:
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    blueprint = (REPO_ROOT / "docs" / "blueprint.md").read_text(encoding="utf-8")
    assert "Scheduled executor" in contributing
    assert "scheduled-executor.yml" in contributing
    assert "Scheduled executor" in blueprint
    assert "Codex in CI" in blueprint
    assert "implemented" in blueprint
    assert (
        REPO_ROOT / "docs" / "archive" / "exit-drills" / "scheduled-executor" / "STATUS.md"
    ).is_file()
