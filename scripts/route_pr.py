"""Deterministic PR Router — Phase 4 (blueprint §4 + §5.3).

Consumes ``pr.json`` emitted by ``build_pr_context`` plus ``.routing-policy.json``.
Writes JSON ``{"route": "...", "reasons": [...]}`` to stdout. No LLM calls.

Gate order mirrors the authorizing spec
``docs/specs/phase-4-deterministic-router.md`` §R4:

1. ``reviewer_validation.status != valid`` → ``review:human``
2. ``spec_validation.status != valid`` → ``review:human``
3. ``multiple_authorizing_specs_changed`` → ``review:human``
4. red-zone path touch in ``changed_files`` → ``review:human``
5. any reviewer finding ``severity == critical`` → ``blocked``
6. ``spec.risk_tier`` / ``spec.complexity`` outside policy allow-list → ``review:human``
7. caps on changed file count / diff_lines → ``review:human``
8. reviewer ``confidence`` below policy minimum → ``review:human``
9. ``requirements_covered < requirements_total`` → ``review:human``
10. otherwise ``review:codex``

Usage::

    uv run scripts/route_pr.py pr.json [--policy .routing-policy.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from red_zone_paths import touches_red_zone  # noqa: E402

REPO_ROOT = _SCRIPTS_DIR.parent
DEFAULT_POLICY = REPO_ROOT / ".routing-policy.json"


def route_decision(pr: dict, policy: dict) -> tuple[str, list[str]]:
    reviewer_val = pr.get("reviewer_validation") or {}
    if reviewer_val.get("status") != "valid":
        return "review:human", ["Reviewer JSON did not validate against schema."]

    spec_val = pr.get("spec_validation") or {}
    if spec_val.get("status") != "valid":
        return "review:human", ["Spec lint failed or authorizing branch/spec is unresolved."]

    if pr.get("multiple_authorizing_specs_changed") is True:
        return (
            "review:human",
            ["PR changes more than one authorizing docs/specs/*.md file (narrow to one scope)."],
        )

    changed = pr.get("changed_files") or []
    if touches_red_zone(changed):
        return "review:human", ["PR touches red-zone or invariant-protected files."]

    reviewer = pr.get("reviewer") or {}
    for item in reviewer.get("findings", []) or []:
        if isinstance(item, dict) and item.get("severity") == "critical":
            return "blocked", ["Reviewer reported at least one critical finding."]

    spec_meta = pr.get("spec") or {}

    tiers = policy.get("auto_review_allowed_risk_tiers") or []
    compl = policy.get("auto_review_allowed_complexity") or []
    risk_tier = spec_meta.get("risk_tier")
    complexity = spec_meta.get("complexity")

    if risk_tier not in set(tiers):
        return (
            "review:human",
            [f"Risk tier {risk_tier!r} not auto-review eligible per policy."],
        )
    if complexity not in set(compl):
        return (
            "review:human",
            [f"Complexity {complexity!r} not auto-review eligible per policy."],
        )

    max_files = int(policy.get("max_changed_files", 0))
    if len(changed) > max_files:
        return "review:human", [
            f"Changed files ({len(changed)}) > policy max_changed_files ({max_files})."
        ]

    diff_lines = int(pr.get("diff_lines", 0) or 0)
    max_lines = int(policy.get("max_diff_lines", 0))
    if diff_lines > max_lines:
        return "review:human", [f"Diff lines ({diff_lines}) > policy max_diff_lines ({max_lines})."]

    min_conf = int(policy["min_reviewer_confidence"])
    confidence = int(reviewer.get("confidence", 0) or 0)
    if confidence < min_conf:
        return "review:human", [f"Reviewer confidence ({confidence}) < policy min ({min_conf})."]

    cov = reviewer.get("coverage") or {}
    reqs_total = int(cov.get("requirements_total", 0) or 0)
    reqs_cov = int(cov.get("requirements_covered", 0) or 0)
    if reqs_cov < reqs_total:
        return "review:human", ["Reviewer reports incomplete requirement coverage."]

    return "review:codex", ["All policy thresholds satisfied."]


def load_policy(policy_path: Path) -> dict:
    return json.loads(policy_path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Route a PR deterministically.")
    p.add_argument("pr_json", type=Path, help="Context JSON emitted by build_pr_context")
    p.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY,
        help=".routing-policy.json path",
    )
    args = p.parse_args(argv)
    pr_blob = json.loads(args.pr_json.read_text(encoding="utf-8"))
    policy_blob = load_policy(args.policy)
    route_label, reasons = route_decision(pr_blob, policy_blob)
    print(json.dumps({"route": route_label, "reasons": reasons}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
