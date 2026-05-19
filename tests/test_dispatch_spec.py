"""Tests for ``scripts/dispatch_spec.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
_DISPATCH_PATH = REPO_ROOT / "scripts" / "dispatch_spec.py"


def _load_dispatch():
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("dispatch_spec", _DISPATCH_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dispatch_spec = _load_dispatch()
validate_reviewer = importlib.import_module("validate_reviewer")


def _write_spec(repo_root: Path, slug: str, *, risk_tier: str = "T0") -> Path:
    spec_dir = repo_root / "docs" / "specs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    path = spec_dir / f"{slug}.md"
    path.write_text(
        f"""# {slug}

## Metadata
- spec_id: SPEC-20260518-{slug}
- owner: tests
- status: drafted
- complexity: low
- risk_tier: {risk_tier}

## Red-Zone Assessment
- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no
""",
        encoding="utf-8",
    )
    return path


def test_resolve_spec_path_relative_to_repo_root(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path, "widget")
    rel = Path("docs/specs/widget.md")
    resolved = dispatch_spec.resolve_spec_path(rel, tmp_path)
    assert resolved == spec_path.resolve()


def test_build_pr_body_links_spec_and_contains_reviewer_fence() -> None:
    body = dispatch_spec.build_pr_body("docs/specs/widget.md")

    assert "[docs/specs/widget.md](docs/specs/widget.md)" in body
    assert "<!-- REVIEWER_JSON -->" in body
    assert "<!-- /REVIEWER_JSON -->" in body
    json_text = body.split("<!-- REVIEWER_JSON -->", 1)[1].split("<!-- /REVIEWER_JSON -->", 1)[0]
    reviewer = json.loads(json_text)
    assert reviewer == dispatch_spec.REVIEWER_STUB
    assert validate_reviewer.validate(body, validate_reviewer.load_reviewer_schema()) == []


def test_dry_run_payload_default_pr_transport(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    spec_path = _write_spec(tmp_path, "widget")

    rc = dispatch_spec.main(
        [
            "--repo-root",
            str(tmp_path),
            "--spec",
            str(spec_path),
            "--dry-run",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["transport"] == "pr"
    assert payload["branch"] == "spec/widget"
    assert payload["pr"]["title"] == "spec: widget"
    assert "<!-- REVIEWER_JSON -->" in payload["pr_body"]


def test_dry_run_codex_transport_metadata(tmp_path: Path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    spec_path = _write_spec(tmp_path, "widget")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    rc = dispatch_spec.main(
        [
            "--repo-root",
            str(tmp_path),
            "--spec",
            str(spec_path),
            "--dry-run",
            "--transport",
            "codex",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["transport"] == "codex"
    assert payload["codex_agents"]["enabled_in_ci"] is True


def test_dry_run_issue_transport(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    spec_path = _write_spec(tmp_path, "widget")
    rc = dispatch_spec.main(
        [
            "--repo-root",
            str(tmp_path),
            "--spec",
            str(spec_path),
            "--dry-run",
            "--transport",
            "issue",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["transport"] == "issue"
    assert payload["issue"]["label"] == "scheduler-queue"


def test_dispatch_open_pr_monkeypatch(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    spec_path = _write_spec(tmp_path, "widget")
    calls: list[str] = []

    def fake_branch_exists(_remote: str, _branch: str) -> bool:
        return False

    def fake_create_branch(_remote: str, _branch: str) -> None:
        calls.append("create")

    def fake_seed(_remote: str, _branch: str, *, message: str) -> bool:
        calls.append(message)
        return True

    def fake_open_pr(*, branch: str, title: str, body: str, repo: str | None) -> str:
        calls.append(f"pr:{branch}:{title}:{repo}")
        assert "dispatch-source: scheduled" in body
        return "https://example.com/pull/1"

    monkeypatch.setattr(dispatch_spec, "branch_exists", fake_branch_exists)
    monkeypatch.setattr(dispatch_spec, "create_remote_branch", fake_create_branch)
    monkeypatch.setattr(dispatch_spec, "seed_dispatch_branch", fake_seed)
    monkeypatch.setattr(dispatch_spec, "open_pull_request", fake_open_pr)

    result = dispatch_spec.dispatch_open_pr(
        payload=dispatch_spec.build_dispatch_payload(
            dispatch_spec.load_descriptor(spec_path, tmp_path),
            transport="pr",
        ),
        remote="origin",
        repo="org/repo",
    )
    assert result["pr_url"] == "https://example.com/pull/1"
    assert "create" in calls


def test_ineligible_spec_is_rejected(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    spec_path = _write_spec(tmp_path, "unsafe", risk_tier="T1")

    rc = dispatch_spec.main(
        [
            "--repo-root",
            str(tmp_path),
            "--spec",
            str(spec_path),
            "--dry-run",
        ]
    )

    assert rc == 2
    assert "risk_tier_ineligible" in capsys.readouterr().err


def test_create_remote_branch_pushes_resolved_origin_main(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_: Any):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        if cmd[:3] == ["git", "rev-parse", "--verify"] and cmd[3] == "origin/main":
            return type("CP", (), {"stdout": "abc123\n"})()
        if cmd[:3] == ["git", "rev-parse", "--verify"] and cmd[3] == "HEAD":
            return type("CP", (), {"stdout": "abc123\n"})()
        if cmd[:2] == ["git", "push"]:
            return type("CP", (), {"stdout": ""})()
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(dispatch_spec.subprocess, "run", fake_run)

    dispatch_spec.create_remote_branch("origin", "spec/widget")

    assert calls[-1] == ["git", "push", "origin", "abc123:refs/heads/spec/widget"]


def test_create_remote_branch_errors_when_head_is_not_origin_main(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_run(cmd: list[str], **_: Any):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "rev-parse", "--verify"] and cmd[3] == "origin/main":
            return type("CP", (), {"stdout": "abc123\n"})()
        if cmd[:3] == ["git", "rev-parse", "--verify"] and cmd[3] == "HEAD":
            return type("CP", (), {"stdout": "def456\n"})()
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(dispatch_spec.subprocess, "run", fake_run)

    try:
        dispatch_spec.create_remote_branch("origin", "spec/widget")
    except RuntimeError as exc:
        assert "does not match origin/main" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
