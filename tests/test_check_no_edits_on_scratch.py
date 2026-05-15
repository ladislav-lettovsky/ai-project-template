"""Tests for ``scripts/hooks/check_no_edits_on_scratch.py``."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / "scripts" / "hooks" / "check_no_edits_on_scratch.py"

TOOL_JSON = '{"tool_input":{"file_path":"src/foo.py"}}'


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


def _run_hook(cwd: Path, stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=stdin,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_scratch_blocks_with_rename_guidance(tmp_path: Path) -> None:
    repo = _bootstrap_repo(tmp_path, "scratch")
    result = _run_hook(repo, TOOL_JSON)
    assert result.returncode == 2
    assert "git branch -m scratch spec/<slug>" in result.stderr
    assert "git branch -m scratch fix/<slug>" in result.stderr


@pytest.mark.parametrize("branch", ["main", "spec/foo", "fix/bar"])
def test_non_scratch_allows(tmp_path: Path, branch: str) -> None:
    repo = _bootstrap_repo(tmp_path, branch)
    result = _run_hook(repo, TOOL_JSON)
    assert result.returncode == 0, result.stderr


def test_no_git_fails_open(tmp_path: Path) -> None:
    nogit = tmp_path / "nogit"
    nogit.mkdir()
    result = _run_hook(nogit, TOOL_JSON)
    assert result.returncode == 0


def test_malformed_stdin_fails_open_on_scratch(tmp_path: Path) -> None:
    repo = _bootstrap_repo(tmp_path, "scratch")
    result = _run_hook(repo, "not json {{{")
    assert result.returncode == 0


@pytest.fixture(autouse=True)
def _quiet_subprocess_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
