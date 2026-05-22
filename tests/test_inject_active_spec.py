"""Tests for the SessionStart hook ``scripts/hooks/inject_active_spec.py``.

The hook must:
  * print the full spec content when on a spec/* branch with an existing spec;
  * print a "not found" notice when the spec file is absent;
  * print nothing when on main, scratch, or a branch without a recognised prefix;
  * always exit 0 (fail open — session start must never be blocked);
  * fail open when git is unavailable.
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / "scripts" / "hooks" / "inject_active_spec.py"


def _load_hook() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("inject_active_spec", HOOK_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture()
def hook():
    return _load_hook()


def _make_branch_mock(branch: str):
    """Return a subprocess.run mock that reports the given branch name."""
    mock_result = MagicMock()
    mock_result.stdout = branch
    mock_result.returncode = 0
    return MagicMock(return_value=mock_result)


# ---------------------------------------------------------------------------
# Core injection behaviour
# ---------------------------------------------------------------------------


def test_spec_branch_with_existing_spec_prints_content(
    hook: types.ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On spec/<slug> with a matching spec file, full spec text is printed to stdout."""
    spec_dir = tmp_path / "docs" / "specs"
    spec_dir.mkdir(parents=True)
    spec_file = spec_dir / "my-feature.md"
    spec_file.write_text("# My Feature\n\nSpec body here.\n", encoding="utf-8")

    monkeypatch.setattr(hook, "REPO_ROOT", tmp_path)
    with patch("subprocess.run", _make_branch_mock("spec/my-feature")):
        rc = hook.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert "docs/specs/my-feature.md" in captured.out
    assert "Spec body here." in captured.out
    assert "[Active spec" in captured.out
    assert "[End of active spec]" in captured.out


def test_fix_branch_with_existing_spec_prints_content(
    hook: types.ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """fix/* branches are also eligible for spec injection."""
    spec_dir = tmp_path / "docs" / "specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "auth-bug.md").write_text("# Auth Bug Fix\n", encoding="utf-8")

    monkeypatch.setattr(hook, "REPO_ROOT", tmp_path)
    with patch("subprocess.run", _make_branch_mock("fix/auth-bug")):
        rc = hook.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert "docs/specs/auth-bug.md" in captured.out
    assert "Auth Bug Fix" in captured.out


def test_spec_branch_missing_spec_prints_notice(
    hook: types.ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the spec file does not exist yet, a notice is printed (not an error)."""
    (tmp_path / "docs" / "specs").mkdir(parents=True)

    monkeypatch.setattr(hook, "REPO_ROOT", tmp_path)
    with patch("subprocess.run", _make_branch_mock("spec/new-thing")):
        rc = hook.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert "new-thing" in captured.out
    assert "does not exist" in captured.out


# ---------------------------------------------------------------------------
# Branches that should produce no output
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("branch", ["main", "scratch", "feat/something", "chore/cleanup"])
def test_non_spec_branch_produces_no_output(
    hook: types.ModuleType,
    capsys: pytest.CaptureFixture[str],
    branch: str,
) -> None:
    """Branches without spec/* or fix/* prefix produce no stdout output."""
    with patch("subprocess.run", _make_branch_mock(branch)):
        rc = hook.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""


# ---------------------------------------------------------------------------
# Fail-open: git unavailable
# ---------------------------------------------------------------------------


def test_git_unavailable_exits_zero(
    hook: types.ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When git is unavailable the hook must exit 0 and produce no output."""

    with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
        rc = hook.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""


# ---------------------------------------------------------------------------
# Settings registration
# ---------------------------------------------------------------------------


def test_session_start_hook_registered_in_settings() -> None:
    """SessionStart hook must be wired up in .claude/settings.json."""
    import json

    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    session_start = settings.get("hooks", {}).get("SessionStart", [])
    all_commands = [
        h["command"]
        for entry in session_start
        for h in entry.get("hooks", [])
        if h.get("type") == "command"
    ]
    assert any("inject_active_spec.py" in cmd for cmd in all_commands), (
        f"inject_active_spec.py not found in SessionStart hooks: {all_commands}"
    )
