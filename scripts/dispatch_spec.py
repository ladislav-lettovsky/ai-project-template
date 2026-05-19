"""Dispatch one eligible Phase 6 spec using the v1 issue-stub transport.

Usage:
    uv run scripts/dispatch_spec.py --spec docs/specs/<slug>.md --dry-run
    uv run scripts/dispatch_spec.py --spec docs/specs/<slug>.md --transport issue
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import queue_specs  # noqa: E402

REVIEWER_STUB = {
    "summary": "Placeholder until Reviewer runs.",
    "findings": [],
    "coverage": {
        "requirements_total": 0,
        "requirements_covered": 0,
        "tests_expected": 0,
        "tests_present": 0,
    },
    "risk_assessment": {
        "scope_fit": "correct",
        "invariant_risk": "high",
        "production_risk": "high",
    },
    "confidence": 0,
}
REVIEWER_FENCE = (
    f"<!-- REVIEWER_JSON -->\n{json.dumps(REVIEWER_STUB, indent=2)}\n<!-- /REVIEWER_JSON -->"
)
PHASE6_QUEUE_LABEL = "phase6-queue"


def build_pr_body(spec_path: str) -> str:
    return f"Implements [{spec_path}]({spec_path}).\n\n{REVIEWER_FENCE}\n"


def build_issue_body(descriptor: dict[str, Any], pr_body: str) -> str:
    return (
        "Phase 6 queued spec dispatch stub.\n\n"
        f"- Spec: [{descriptor['path']}]({descriptor['path']})\n"
        f"- Branch: `spec/{descriptor['slug']}`\n"
        "- Transport: `issue`\n\n"
        "Planned PR body:\n\n"
        "```markdown\n"
        f"{pr_body}"
        "```\n"
    )


def load_descriptor(spec_path: Path, repo_root: Path) -> dict[str, Any]:
    descriptor = queue_specs.parse_spec_descriptor(spec_path, repo_root)
    skip_reason = queue_specs.metadata_skip_reason(descriptor)
    if skip_reason is None:
        skip_reason = queue_specs.eligibility_skip_reason(descriptor)
    if skip_reason is not None:
        msg = f"spec is not eligible for dispatch: {skip_reason}"
        raise ValueError(msg)
    descriptor["eligible"] = True
    return descriptor


def branch_exists(remote: str, branch_name: str) -> bool:
    cp = subprocess.run(
        ["git", "ls-remote", "--heads", remote, f"refs/heads/{branch_name}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(cp.stdout.strip())


def resolve_ref(ref: str) -> str:
    cp = subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        check=True,
        capture_output=True,
        text=True,
    )
    return cp.stdout.strip()


def create_remote_branch(remote: str, branch_name: str) -> None:
    main_ref = f"{remote}/main"
    main_sha = resolve_ref(main_ref)
    head_sha = resolve_ref("HEAD")
    if head_sha != main_sha:
        msg = f"local HEAD ({head_sha}) does not match {main_ref} ({main_sha})"
        raise RuntimeError(msg)
    subprocess.run(
        ["git", "push", remote, f"{main_sha}:refs/heads/{branch_name}"],
        check=True,
    )


def open_tracking_issue(
    *,
    title: str,
    body: str,
    label: str,
    repo: str | None = None,
) -> str:
    gh_path = shutil.which("gh")
    if gh_path is None:
        raise RuntimeError("gh executable not found in PATH")
    cmd = ["gh", "issue", "create", "--title", title, "--body", body, "--label", label]
    if repo:
        cmd.extend(["--repo", repo])
    cp = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return cp.stdout.strip()


def build_dispatch_payload(descriptor: dict[str, Any], *, transport: str) -> dict[str, Any]:
    branch_name = f"spec/{descriptor['slug']}"
    pr_body = build_pr_body(descriptor["path"])
    issue_body = build_issue_body(descriptor, pr_body)
    return {
        "transport": transport,
        "spec": descriptor,
        "branch": branch_name,
        "issue": {
            "title": f"Phase 6 queue: {descriptor['slug']}",
            "label": PHASE6_QUEUE_LABEL,
            "body": issue_body,
        },
        "pr_body": pr_body,
    }


def dispatch_issue_stub(
    *,
    payload: dict[str, Any],
    remote: str,
    repo: str | None,
) -> dict[str, Any]:
    branch = payload["branch"]
    created_branch = False
    if not branch_exists(remote, branch):
        create_remote_branch(remote, branch)
        created_branch = True
    issue = payload["issue"]
    issue_url = open_tracking_issue(
        title=issue["title"],
        body=issue["body"],
        label=issue["label"],
        repo=repo,
    )
    return {
        "ok": True,
        "transport": "issue",
        "branch": branch,
        "created_branch": created_branch,
        "issue_url": issue_url,
    }


def argv_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dispatch a single eligible Phase 6 spec.")
    parser.add_argument("--spec", type=Path, required=True, help="Path to docs/specs/<slug>.md")
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--repo", help='GitHub "owner/repo" for gh CLI')
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--transport", choices=("issue", "codex"), default="issue")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = argv_parser().parse_args(argv)
    if args.transport == "codex":
        print("ERROR: codex transport is reserved for a later Phase 6 slice", file=sys.stderr)
        return 2
    try:
        descriptor = load_descriptor(args.spec, args.repo_root)
        payload = build_dispatch_payload(descriptor, transport=args.transport)
        if args.dry_run:
            print(json.dumps({"dry_run": True, **payload}, indent=2))
            return 0
        result = dispatch_issue_stub(payload=payload, remote=args.remote, repo=args.repo)
    except (OSError, ValueError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
