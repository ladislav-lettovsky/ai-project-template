"""Tests for ``scripts/append_event.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_APPEND_PATH = REPO_ROOT / "scripts" / "append_event.py"


def _load_append():
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("append_event", _APPEND_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


append_event_mod = _load_append()

MINIMAL_PR = {
    "repository": "org/repo",
    "branch_name": "spec/widget",
    "changed_files": ["src/a.py", "docs/specs/widget.md"],
    "diff_lines": 10,
    "spec": {
        "slug": "widget",
        "path": "docs/specs/widget.md",
        "risk_tier": "T0",
        "complexity": "low",
    },
    "reviewer_validation": {"status": "valid", "errors": []},
    "reviewer": {
        "summary": "ok",
        "findings": [{"severity": "nit", "type": "weak_test"}],
        "confidence": 72,
        "coverage": {
            "requirements_total": 1,
            "requirements_covered": 1,
            "tests_expected": 1,
            "tests_present": 1,
        },
    },
}

MINIMAL_ROUTE = {"route": "review:codex", "reasons": ["All policy thresholds satisfied."]}


def test_build_event_fields() -> None:
    event = append_event_mod.build_event(
        MINIMAL_PR,
        MINIMAL_ROUTE,
        pr_number=7,
        head_sha="deadbeef",
        ci_outcome="success",
        merge_outcome="merged",
    )
    assert event["pr_number"] == 7
    assert event["route_decision"] == "review:codex"
    assert event["changed_files_count"] == 2
    assert event["findings_count_by_severity"]["nit"] == 1
    assert event["ci_outcome"] == "success"


def test_findings_count_by_severity() -> None:
    reviewer = {
        "findings": [
            {"severity": "critical"},
            {"severity": "warning"},
            {"severity": "warning"},
        ]
    }
    counts = append_event_mod.findings_count_by_severity(reviewer)
    assert counts == {"critical": 1, "warning": 2, "nit": 0}


def test_append_dedup_by_pr_number(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    event_a = {"pr_number": 1, "route_decision": "review:codex"}
    event_b = {"pr_number": 1, "route_decision": "blocked"}
    append_event_mod.append_event(events_path, event_a)
    append_event_mod.append_event(events_path, event_b)
    loaded = append_event_mod.load_events(events_path)
    assert len(loaded) == 1
    assert loaded[0]["route_decision"] == "blocked"


def test_append_no_replace_skips_duplicate(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    event = {"pr_number": 2, "route_decision": "review:human"}
    assert append_event_mod.append_event(events_path, event, replace_existing=False) is True
    assert append_event_mod.append_event(events_path, event, replace_existing=False) is False


def test_parse_spec_id_from_fixture_spec(tmp_path: Path) -> None:
    spec_dir = tmp_path / "docs" / "specs"
    spec_dir.mkdir(parents=True)
    spec_path = spec_dir / "demo.md"
    spec_path.write_text(
        "## Metadata\n- spec_id: SPEC-20260516-demo\n- risk_tier: T0\n",
        encoding="utf-8",
    )
    pr = {"spec": {"path": str(spec_path.relative_to(tmp_path))}}
    monkeypatch_repo = tmp_path

    original_root = append_event_mod._REPO_ROOT
    append_event_mod._REPO_ROOT = monkeypatch_repo
    try:
        assert append_event_mod.parse_spec_id(monkeypatch_repo, pr) == "SPEC-20260516-demo"
    finally:
        append_event_mod._REPO_ROOT = original_root


def test_main_writes_jsonl(tmp_path: Path) -> None:
    pr_file = tmp_path / "pr.json"
    route_file = tmp_path / "route.json"
    out_file = tmp_path / "events.jsonl"
    pr_file.write_text(json.dumps(MINIMAL_PR), encoding="utf-8")
    route_file.write_text(json.dumps(MINIMAL_ROUTE), encoding="utf-8")
    rc = append_event_mod.main(
        [
            "--pr",
            str(pr_file),
            "--route",
            str(route_file),
            "--out",
            str(out_file),
            "--pr-number",
            "9",
        ]
    )
    assert rc == 0
    lines = out_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    blob = json.loads(lines[0])
    assert blob["pr_number"] == 9
