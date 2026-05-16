"""Tests for ``scripts/telemetry_dashboard.py``."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_DASH_PATH = REPO_ROOT / "scripts" / "telemetry_dashboard.py"


def _load_dashboard():
    spec = importlib.util.spec_from_file_location("telemetry_dashboard", _DASH_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dash_mod = _load_dashboard()


def test_render_dashboard_includes_counts() -> None:
    events = [
        {"route_decision": "review:codex", "risk_tier": "T0", "reviewer_confidence": 80},
        {"route_decision": "blocked", "risk_tier": "T0", "reviewer_confidence": 70},
    ]
    md = dash_mod.render_dashboard(events)
    assert "review:codex" in md
    assert "blocked" in md
    assert "Average reviewer confidence" in md
    assert "75.0" in md


def test_main_writes_file(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    out_path = tmp_path / "dashboard.md"
    events_path.write_text(
        json.dumps({"route_decision": "review:human", "risk_tier": "T1"}) + "\n",
        encoding="utf-8",
    )
    rc = dash_mod.main(["--events", str(events_path), "--out", str(out_path)])
    assert rc == 0
    assert out_path.is_file()
    assert "review:human" in out_path.read_text(encoding="utf-8")
