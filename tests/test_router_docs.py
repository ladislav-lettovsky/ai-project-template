"""Documentation presence checks for the deterministic PR Router."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_contributing_documents_router() -> None:
    text = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "route-pr" in text
    assert "review:human" in text


def test_readme_documents_router() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "route-pr.yml" in readme
    assert "Router" in readme


def test_route_pr_workflow_exists() -> None:
    yml = REPO_ROOT / ".github/workflows/route-pr.yml"
    assert yml.is_file()


def test_agents_documents_router_invariants() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    blob = agents.lower()
    assert "router is deterministic python" in blob
    assert "risk tier" in blob and "routing input" in blob
