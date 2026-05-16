"""Append one telemetry event line for a PR routing decision (Phase 5).

Reads ``pr.json`` from ``build_pr_context`` and ``route.json`` from ``route_pr``.
Appends a single JSON object as one line to ``docs/telemetry/events.jsonl``.

Usage::

    uv run scripts/append_event.py --pr pr.json --route route.json
    uv run scripts/append_event.py --pr pr.json --route route.json \\
        --pr-number 42 --head-sha abc123 --merge-outcome merged
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import lint_spec  # noqa: E402

DEFAULT_EVENTS_PATH = _REPO_ROOT / "docs" / "telemetry" / "events.jsonl"
SEVERITIES = ("critical", "warning", "nit")


def findings_count_by_severity(reviewer: dict) -> dict[str, int]:
    counts = {s: 0 for s in SEVERITIES}
    for item in reviewer.get("findings") or []:
        if not isinstance(item, dict):
            continue
        sev = item.get("severity")
        if sev in counts:
            counts[sev] += 1
    return counts


def parse_spec_id(repo_root: Path, pr: dict) -> str | None:
    spec_path = (pr.get("spec") or {}).get("path")
    if not spec_path:
        return None
    abs_path = repo_root / str(spec_path)
    if not abs_path.is_file():
        return None
    sections = lint_spec.split_sections(abs_path.read_text(encoding="utf-8"))
    meta = lint_spec.parse_metadata(sections.get("Metadata", ""))
    return meta.get("spec_id")


def build_event(
    pr: dict,
    route: dict,
    *,
    pr_number: int | None = None,
    head_sha: str | None = None,
    ci_outcome: str = "pending",
    merge_outcome: str = "open",
) -> dict:
    reviewer = pr.get("reviewer") or {}
    spec_meta = pr.get("spec") or {}
    reviewer_val = pr.get("reviewer_validation") or {}
    return {
        "recorded_at": datetime.now(UTC).isoformat(),
        "pr_number": pr_number,
        "head_sha": head_sha,
        "repository": pr.get("repository"),
        "branch_name": pr.get("branch_name"),
        "spec_id": parse_spec_id(_REPO_ROOT, pr),
        "spec_slug": spec_meta.get("slug"),
        "risk_tier": spec_meta.get("risk_tier"),
        "complexity": spec_meta.get("complexity"),
        "changed_files_count": len(pr.get("changed_files") or []),
        "diff_lines": int(pr.get("diff_lines") or 0),
        "reviewer_validation_status": reviewer_val.get("status"),
        "reviewer_confidence": reviewer.get("confidence"),
        "findings_count_by_severity": findings_count_by_severity(reviewer),
        "route_decision": route.get("route"),
        "route_reasons": route.get("reasons") or [],
        "ci_outcome": ci_outcome,
        "merge_outcome": merge_outcome,
    }


def load_events(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    events: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            events.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            msg = f"invalid JSON on line {line_no} of {path}: {exc}"
            raise ValueError(msg) from exc
    return events


def event_key(event: dict) -> tuple[object, ...]:
    """Dedup key: one record per PR number when present, else head_sha."""
    prn = event.get("pr_number")
    if prn is not None:
        return ("pr", prn)
    return ("sha", event.get("head_sha"))


def append_event(path: Path, event: dict, *, replace_existing: bool = True) -> bool:
    """Append ``event`` to ``path``. Return False if skipped as duplicate."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_events(path)
    new_key = event_key(event)
    if replace_existing:
        existing = [e for e in existing if event_key(e) != new_key]
    elif any(event_key(e) == new_key for e in existing):
        return False
    existing.append(event)
    lines = [json.dumps(e, separators=(",", ":")) for e in existing]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Append a Phase 5 telemetry event.")
    p.add_argument("--pr", type=Path, required=True, help="pr.json from build_pr_context")
    p.add_argument("--route", type=Path, required=True, help="route.json from route_pr")
    p.add_argument("--out", type=Path, default=DEFAULT_EVENTS_PATH, help="events.jsonl path")
    p.add_argument("--pr-number", type=int, default=None)
    p.add_argument("--head-sha", default=None)
    p.add_argument(
        "--ci-outcome",
        default="pending",
        choices=("pending", "success", "failure", "unknown"),
    )
    p.add_argument(
        "--merge-outcome",
        default="open",
        choices=("open", "merged", "closed"),
    )
    p.add_argument(
        "--no-replace",
        action="store_true",
        help="Skip append when an event for the same PR already exists",
    )
    args = p.parse_args(argv)

    pr_blob = json.loads(args.pr.read_text(encoding="utf-8"))
    route_blob = json.loads(args.route.read_text(encoding="utf-8"))
    event = build_event(
        pr_blob,
        route_blob,
        pr_number=args.pr_number,
        head_sha=args.head_sha,
        ci_outcome=args.ci_outcome,
        merge_outcome=args.merge_outcome,
    )
    written = append_event(args.out, event, replace_existing=not args.no_replace)
    if written:
        print(json.dumps(event, indent=2))
    else:
        print("skipped duplicate event", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
