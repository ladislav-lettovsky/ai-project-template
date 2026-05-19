"""Tests for ``dispatch_source`` telemetry schema (Phase 6 Slice 2)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_APPEND_PATH = REPO_ROOT / "scripts" / "append_event.py"
_DISPATCH_PATH = REPO_ROOT / "scripts" / "dispatch_spec.py"


def _load_module(path: Path, name: str):
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


append_event = _load_module(_APPEND_PATH, "append_event")
dispatch_spec = _load_module(_DISPATCH_PATH, "dispatch_spec")

MINIMAL_ROUTE = {"route": "review:codex", "reasons": []}


def test_dispatch_source_defaults_to_manual() -> None:
    pr = {"pr_body": "Implements [docs/specs/x.md](docs/specs/x.md)."}
    event = append_event.build_event(pr, MINIMAL_ROUTE)
    assert event["dispatch_source"] == "manual"


def test_dispatch_source_from_pr_body_marker() -> None:
    pr = {
        "pr_body": (
            "Implements [docs/specs/foo.md](docs/specs/foo.md).\n\ndispatch-source: scheduled\n"
        )
    }
    event = append_event.build_event(pr, MINIMAL_ROUTE)
    assert event["dispatch_source"] == "scheduled"


def test_dispatch_source_from_commit_trailer(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: demo\n\ndispatch-source: scheduled"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    pr = {"pr_body": "No marker in body."}
    event = append_event.build_event(pr, MINIMAL_ROUTE, head_sha=sha, repo_root=tmp_path)
    assert event["dispatch_source"] == "scheduled"


def test_jsonl_round_trip_with_and_without_dispatch_source(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    manual = append_event.build_event({"pr_body": ""}, MINIMAL_ROUTE, pr_number=1)
    scheduled_pr = {
        "pr_body": "dispatch-source: scheduled\n",
    }
    scheduled = append_event.build_event(scheduled_pr, MINIMAL_ROUTE, pr_number=2)
    append_event.append_event(events_path, manual)
    append_event.append_event(events_path, scheduled)
    loaded = append_event.load_events(events_path)
    by_pr = {e["pr_number"]: e for e in loaded}
    assert by_pr[1]["dispatch_source"] == "manual"
    assert by_pr[2]["dispatch_source"] == "scheduled"
    for event in loaded:
        line = json.dumps(event, separators=(",", ":"))
        round_trip = json.loads(line)
        assert round_trip["dispatch_source"] in append_event.DISPATCH_SOURCE_VALUES


def test_dispatch_spec_pr_body_includes_scheduled_marker() -> None:
    body = dispatch_spec.build_pr_body("docs/specs/hello.md")
    assert "dispatch-source: scheduled" in body
