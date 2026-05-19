"""Tests for ``scripts/try_auto_merge.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_TRY_AUTO_MERGE_PATH = REPO_ROOT / "scripts" / "try_auto_merge.py"


def _load_try_auto_merge():
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("try_auto_merge", _TRY_AUTO_MERGE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try_auto_merge = _load_try_auto_merge()


def test_try_merge_skips_without_review_codex_label(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_view(*, pr_number: int, repo: str | None) -> dict[str, Any]:
        assert pr_number == 7
        assert repo == "o/r"
        return {"labels": [{"name": "review:human"}], "mergeStateStatus": "CLEAN"}

    monkeypatch.setattr(try_auto_merge, "gh_pr_view", fake_view)
    result = try_auto_merge.try_merge(pr_number=7, repo="o/r")
    assert result["action"] == "skipped"
    assert "review:codex" in result["reason"]


def test_try_merge_merges_when_labeled_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_view(*, pr_number: int, repo: str | None) -> dict[str, Any]:
        return {"labels": [{"name": "review:codex"}], "mergeStateStatus": "CLEAN"}

    def fake_which(name: str) -> str | None:
        return "/usr/bin/gh" if name == "gh" else None

    def fake_run(cmd: list[str], **kwargs: object) -> object:  # noqa: ARG001
        calls.append(cmd)
        return object()

    monkeypatch.setattr(try_auto_merge, "gh_pr_view", fake_view)
    monkeypatch.setattr(try_auto_merge.shutil, "which", fake_which)
    monkeypatch.setattr(try_auto_merge.subprocess, "run", fake_run)

    result = try_auto_merge.try_merge(pr_number=9, repo="o/r")
    assert result["action"] == "merged"
    assert calls and calls[0][:4] == ["/usr/bin/gh", "pr", "merge", "9"]


def test_main_prints_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        try_auto_merge,
        "try_merge",
        lambda *, pr_number, repo: {"action": "skipped", "reason": "test"},
    )
    rc = try_auto_merge.main(["--pr", "1", "--repo", "o/r"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "skipped"
