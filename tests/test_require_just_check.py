"""Tests for the Stop hook ``scripts/hooks/require_just_check.py``.

The hook must:
  * pass (rc 0) when no spec files are modified or untracked;
  * pass (rc 0) when modified specs are clean;
  * fail (rc 2) when modified specs fail the linter;
  * detect *untracked* specs as well as *modified* ones (regression test
    for the case where ``git diff HEAD`` alone misses newly-created files);
  * skip scaffolding files (``_template.md``, ``README.md``, ``_postmortem.md``);
  * fail open on infrastructure errors (no git, no lint_spec).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / "scripts" / "hooks" / "require_just_check.py"
LINT_SPEC = REPO_ROOT / "scripts" / "lint_spec.py"

VALID_SPEC = """\
# Test Feature

## Metadata
- spec_id: SPEC-20260507-test
- owner: Tester
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template

## Context
Why now.

## Assumptions
- A1: assumption.

## Decisions
- D1: decided.

## Problem Statement
Problem.

## Requirements (STRICT)
- [ ] R1: do the thing.

## Non-Goals
- [ ] NG1: not the other thing.

## Interfaces
None.

## Invariants to Preserve
- [ ] INV1: stay true.

## Red-Zone Assessment
- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no

## Test Plan
- [ ] T1 -> covers R1

## Validation Contract
- R1 -> `just check`

## Edge Cases
- EC1: nothing notable.

## Security / Prompt-Injection Review
- source: in-process function argument.
- risk: low
- mitigation: not required.

## Observability
None required.

## Rollback / Recovery
Revert the commit.

## Implementation Slices
1. Slice 1: ship the thing.

## Done When
- [ ] R1 satisfied
"""


def _git(args: list[str], cwd: Path) -> None:
    """Run ``git`` with a quiet env so tests don't pick up the real user's config."""
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


def _bootstrap_repo(tmp_path: Path) -> Path:
    """Create a fresh git repo with the hook + linter copied in.

    The hook resolves ``REPO_ROOT`` from its own location, so we replicate
    the directory layout the hook expects: ``scripts/hooks/`` + ``scripts/``.
    """
    repo = tmp_path / "repo"
    (repo / "scripts" / "hooks").mkdir(parents=True)
    (repo / "docs" / "specs").mkdir(parents=True)
    (repo / "scripts" / "hooks" / "require_just_check.py").write_text(
        HOOK_PATH.read_text(), encoding="utf-8"
    )
    (repo / "scripts" / "lint_spec.py").write_text(LINT_SPEC.read_text(), encoding="utf-8")
    _git(["init", "-q", "-b", "main"], cwd=repo)
    _git(["add", "."], cwd=repo)
    _git(["commit", "-q", "-m", "initial"], cwd=repo)
    return repo


def _run_hook(repo: Path) -> subprocess.CompletedProcess[str]:
    """Run the hook script with ``{}`` on stdin (Claude Code feeds JSON)."""
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "hooks" / "require_just_check.py")],
        input="{}",
        capture_output=True,
        text=True,
        cwd=repo,
        check=False,
    )


def test_clean_repo_passes(tmp_path: Path) -> None:
    """No modified or untracked specs → exit 0."""
    repo = _bootstrap_repo(tmp_path)
    result = _run_hook(repo)
    assert result.returncode == 0, result.stderr


def test_modified_clean_spec_passes(tmp_path: Path) -> None:
    """A tracked spec file modified to a still-valid form → exit 0."""
    repo = _bootstrap_repo(tmp_path)
    spec = repo / "docs" / "specs" / "feature.md"
    spec.write_text(VALID_SPEC, encoding="utf-8")
    _git(["add", str(spec)], cwd=repo)
    _git(["commit", "-q", "-m", "add feature spec"], cwd=repo)
    # Now modify the (still-valid) spec.
    spec.write_text(VALID_SPEC.replace("Why now.", "Why now, with a tweak."), encoding="utf-8")
    result = _run_hook(repo)
    assert result.returncode == 0, result.stderr


def test_modified_invalid_spec_blocks(tmp_path: Path) -> None:
    """A tracked spec broken by the modification → exit 2."""
    repo = _bootstrap_repo(tmp_path)
    spec = repo / "docs" / "specs" / "feature.md"
    spec.write_text(VALID_SPEC, encoding="utf-8")
    _git(["add", str(spec)], cwd=repo)
    _git(["commit", "-q", "-m", "add feature spec"], cwd=repo)
    # Remove a required section.
    broken = VALID_SPEC.replace("## Edge Cases\n- EC1: nothing notable.\n\n", "")
    spec.write_text(broken, encoding="utf-8")
    result = _run_hook(repo)
    assert result.returncode == 2, result.stderr
    assert "Edge Cases" in result.stderr


def test_untracked_invalid_spec_blocks(tmp_path: Path) -> None:
    """A brand-new (untracked) spec is still scanned. Regression for git-diff-only.

    Without this check, an agent could create a malformed spec file in a
    fresh session and ``Stop`` would let the session end clean.
    """
    repo = _bootstrap_repo(tmp_path)
    spec = repo / "docs" / "specs" / "new-feature.md"
    broken = VALID_SPEC.replace("## Edge Cases\n- EC1: nothing notable.\n\n", "")
    spec.write_text(broken, encoding="utf-8")  # never `git add`-ed
    result = _run_hook(repo)
    assert result.returncode == 2, result.stderr
    assert "Edge Cases" in result.stderr


def test_scaffolding_files_are_skipped(tmp_path: Path) -> None:
    """Modifying _template.md must not trigger the hook (it intentionally fails)."""
    repo = _bootstrap_repo(tmp_path)
    template = repo / "docs" / "specs" / "_template.md"
    template.write_text("# Template\n\nplaceholder content\n", encoding="utf-8")
    result = _run_hook(repo)
    assert result.returncode == 0, result.stderr


def test_no_git_fails_open(tmp_path: Path) -> None:
    """Run the hook in a directory that's not a git repo → must not block."""
    workdir = tmp_path / "no-git"
    (workdir / "scripts" / "hooks").mkdir(parents=True)
    (workdir / "scripts" / "hooks" / "require_just_check.py").write_text(
        HOOK_PATH.read_text(), encoding="utf-8"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(workdir / "scripts" / "hooks" / "require_just_check.py"),
        ],
        input="{}",
        capture_output=True,
        text=True,
        cwd=workdir,
        check=False,
    )
    assert result.returncode == 0


def test_malformed_stdin_fails_open(tmp_path: Path) -> None:
    """Garbage on stdin must not block — the hook ignores it."""
    repo = _bootstrap_repo(tmp_path)
    result = subprocess.run(
        [sys.executable, str(repo / "scripts" / "hooks" / "require_just_check.py")],
        input="not json at all",
        capture_output=True,
        text=True,
        cwd=repo,
        check=False,
    )
    # No specs touched → still rc 0; the test is mainly that we didn't crash.
    assert result.returncode == 0


def test_clean_untracked_spec_passes(tmp_path: Path) -> None:
    """A brand-new spec that lints clean must pass even though it's untracked."""
    repo = _bootstrap_repo(tmp_path)
    spec = repo / "docs" / "specs" / "fresh.md"
    spec.write_text(VALID_SPEC, encoding="utf-8")
    result = _run_hook(repo)
    assert result.returncode == 0, result.stderr


@pytest.fixture(autouse=True)
def _quiet_subprocess_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid noise from a global git config; tests use their own author env."""
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
