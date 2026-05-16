"""Bounded mechanical updates to ``.routing-policy.json`` from telemetry (Phase 5).

Reads ``docs/telemetry/events.jsonl`` and emits an updated policy when signals
warrant small nudges. Floors/ceilings in the ``adaptive`` block prevent runaway.

Usage::

    uv run scripts/adapt_thresholds.py
    uv run scripts/adapt_thresholds.py --write
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVENTS = _REPO_ROOT / "docs" / "telemetry" / "events.jsonl"
DEFAULT_POLICY = _REPO_ROOT / ".routing-policy.json"


def adapt(events: list[dict], policy: dict) -> tuple[dict, list[str]]:
    new = json.loads(json.dumps(policy))
    notes: list[str] = []
    adaptive = new.get("adaptive") or {}

    blocked_count = sum(1 for e in events if e.get("route_decision") == "blocked")
    invalid_reviewer_count = sum(
        1 for e in events if e.get("reviewer_validation_status") not in {None, "valid"}
    )

    if blocked_count > 0:
        floor = int(adaptive.get("floor_max_diff_lines", 50))
        old = int(new["max_diff_lines"])
        new["max_diff_lines"] = max(floor, old - 25)
        if new["max_diff_lines"] != old:
            notes.append(
                f"max_diff_lines {old} → {new['max_diff_lines']} (blocked_count={blocked_count})"
            )

    if invalid_reviewer_count > 0:
        ceiling = int(adaptive.get("ceiling_min_reviewer_confidence", 85))
        old = int(new["min_reviewer_confidence"])
        new["min_reviewer_confidence"] = min(ceiling, old + 5)
        if new["min_reviewer_confidence"] != old:
            notes.append(
                f"min_reviewer_confidence {old} → {new['min_reviewer_confidence']} "
                f"(invalid_reviewer_count={invalid_reviewer_count})"
            )

    if not notes:
        notes.append("No threshold changes suggested.")
    return new, notes


def load_events(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            out.append(json.loads(stripped))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Adapt routing policy from telemetry.")
    p.add_argument("--events", type=Path, default=DEFAULT_EVENTS)
    p.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    p.add_argument("--write", action="store_true", help="Write updated policy to --policy")
    args = p.parse_args(argv)

    events = load_events(args.events)
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    updated, notes = adapt(events, policy)

    result = {"notes": notes, "policy": updated}
    print(json.dumps(result, indent=2))

    if args.write:
        args.policy.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
