"""Tests for ``scripts/hooks/check_branch_name.py``."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / "scripts" / "hooks" / "check_branch_name.py"


def _git(args: list[str], cwd: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
    )
    subprocess.run(["git", *args], cwd=cwd, check=True, env=env, capture_output=True)


def _bootstrap_repo(tmp_path: Path, branch: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-q", "-b", "main"], cwd=repo)
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    _git(["add", "README.md"], cwd=repo)
    _git(["commit", "-q", "-m", "init"], cwd=repo)
    if branch != "main":
        _git(["checkout", "-q", "-b", branch], cwd=repo)
    return repo


def _run_hook(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "branch",
    [
        "main",
        "scratch",
        "spec/foo",
        "fix/bar",
        "feat/x",
        "chore/deps",
        "docs/readme",
        "refactor/core",
        "test/hook",
    ],
)
def test_allowed_branches(tmp_path: Path, branch: str) -> None:
    repo = _bootstrap_repo(tmp_path, branch)
    result = _run_hook(repo)
    assert result.returncode == 0, result.stderr


def test_invalid_branch_blocks(tmp_path: Path) -> None:
    repo = _bootstrap_repo(tmp_path, "not-a-work-branch")
    result = _run_hook(repo)
    assert result.returncode == 2
    assert "BLOCKED by branch-name hook" in result.stderr
    assert "Permitted names" in result.stderr
    assert "spec/<slug>" in result.stderr
    assert "fix/<slug>" in result.stderr


def test_prefix_without_slash_is_blocked(tmp_path: Path) -> None:
    repo = _bootstrap_repo(tmp_path, "feat")
    result = _run_hook(repo)
    assert result.returncode == 2


def test_not_a_repo_fails_open(tmp_path: Path) -> None:
    nogit = tmp_path / "nogit"
    nogit.mkdir()
    result = _run_hook(nogit)
    assert result.returncode == 0


@pytest.fixture(autouse=True)
def _quiet_subprocess_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
