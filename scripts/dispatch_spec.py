"""Dispatch one eligible eligible spec (branch + open PR, or legacy issue stub).

Usage:
    uv run scripts/dispatch_spec.py --spec docs/specs/<slug>.md --dry-run
    uv run scripts/dispatch_spec.py --spec docs/specs/<slug>.md --transport pr
    uv run scripts/dispatch_spec.py --spec docs/specs/<slug>.md --transport issue
"""

from __future__ import annotations

import argparse
import json
import os
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
SCHEDULER_QUEUE_LABEL = "scheduler-queue"
DEFAULT_TRANSPORT = "pr"


def build_pr_body(spec_path: str) -> str:
    return (
        f"Implements [{spec_path}]({spec_path}).\n\n"
        "dispatch-source: scheduled\n\n"
        f"{REVIEWER_FENCE}\n"
    )


def build_issue_body(descriptor: dict[str, Any], pr_body: str) -> str:
    return (
        "Queued spec dispatch (legacy issue transport) (legacy issue transport).\n\n"
        f"- Spec: [{descriptor['path']}]({descriptor['path']})\n"
        f"- Branch: `spec/{descriptor['slug']}`\n"
        "- Transport: `issue`\n\n"
        "Planned PR body:\n\n"
        "```markdown\n"
        f"{pr_body}"
        "```\n"
    )


def resolve_spec_path(spec_path: Path, repo_root: Path) -> Path:
    candidate = spec_path if spec_path.is_absolute() else (repo_root / spec_path)
    return candidate.resolve()


def load_descriptor(spec_path: Path, repo_root: Path) -> dict[str, Any]:
    resolved = resolve_spec_path(spec_path, repo_root)
    descriptor = queue_specs.parse_spec_descriptor(resolved, repo_root)
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


def git_action_env() -> dict[str, str]:
    """Ensure empty seed commits work on fresh CI checkouts."""
    env = os.environ.copy()
    defaults = {
        "GIT_AUTHOR_NAME": "github-actions[bot]",
        "GIT_AUTHOR_EMAIL": "github-actions[bot]@users.noreply.github.com",
        "GIT_COMMITTER_NAME": "github-actions[bot]",
        "GIT_COMMITTER_EMAIL": "github-actions[bot]@users.noreply.github.com",
    }
    for key, value in defaults.items():
        env.setdefault(key, value)
    return env


def seed_dispatch_branch(remote: str, branch_name: str, *, message: str) -> bool:
    """Push an empty commit when *branch_name* still points at *main* (enables PR open)."""
    git_env = git_action_env()
    subprocess.run(["git", "fetch", remote, branch_name], check=True, env=git_env)
    main_sha = resolve_ref(f"{remote}/main")
    branch_sha = resolve_ref(f"{remote}/{branch_name}")
    if branch_sha != main_sha:
        return False
    previous = resolve_ref("HEAD")
    subprocess.run(
        ["git", "checkout", "-B", branch_name, f"{remote}/{branch_name}"],
        check=True,
        env=git_env,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", message],
        check=True,
        env=git_env,
    )
    subprocess.run(["git", "push", remote, branch_name], check=True, env=git_env)
    subprocess.run(["git", "checkout", previous], check=True, env=git_env)
    return True


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


def find_open_pr_url(*, branch: str, repo: str | None) -> str | None:
    gh_path = shutil.which("gh")
    if gh_path is None:
        raise RuntimeError("gh executable not found in PATH")
    cmd = [
        "gh",
        "pr",
        "list",
        "--head",
        branch,
        "--state",
        "open",
        "--json",
        "url",
        "--limit",
        "1",
    ]
    if repo:
        cmd.extend(["--repo", repo])
    cp = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(cp.stdout)
    if isinstance(data, list) and data:
        return str(data[0].get("url") or "") or None
    return None


def open_pull_request(
    *,
    branch: str,
    title: str,
    body: str,
    repo: str | None,
) -> str:
    existing = find_open_pr_url(branch=branch, repo=repo)
    if existing:
        return existing
    gh_path = shutil.which("gh")
    if gh_path is None:
        raise RuntimeError("gh executable not found in PATH")
    cmd = [
        "gh",
        "pr",
        "create",
        "--base",
        "main",
        "--head",
        branch,
        "--title",
        title,
        "--body",
        body,
    ]
    if repo:
        cmd.extend(["--repo", repo])
    cp = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return cp.stdout.strip()


def build_dispatch_payload(descriptor: dict[str, Any], *, transport: str) -> dict[str, Any]:
    branch_name = f"spec/{descriptor['slug']}"
    pr_body = build_pr_body(descriptor["path"])
    slug = descriptor["slug"]
    payload: dict[str, Any] = {
        "transport": transport,
        "spec": descriptor,
        "branch": branch_name,
        "pr_body": pr_body,
    }
    if transport == "issue":
        payload["issue"] = {
            "title": f"Scheduler queue: {slug}",
            "label": SCHEDULER_QUEUE_LABEL,
            "body": build_issue_body(descriptor, pr_body),
        }
    else:
        payload["pr"] = {
            "title": f"spec: {slug}",
            "body": pr_body,
        }
    return payload


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


def dispatch_open_pr(
    *,
    payload: dict[str, Any],
    remote: str,
    repo: str | None,
) -> dict[str, Any]:
    branch = payload["branch"]
    slug = payload["spec"]["slug"]
    created_branch = False
    seeded_commit = False
    if not branch_exists(remote, branch):
        create_remote_branch(remote, branch)
        created_branch = True
    seeded_commit = seed_dispatch_branch(
        remote,
        branch,
        message=f"chore(scheduler): initialize spec/{slug} for scheduled dispatch",
    )
    pr_meta = payload["pr"]
    pr_url = open_pull_request(
        branch=branch,
        title=pr_meta["title"],
        body=pr_meta["body"],
        repo=repo,
    )
    return {
        "ok": True,
        "transport": "pr",
        "branch": branch,
        "created_branch": created_branch,
        "seeded_commit": seeded_commit,
        "pr_url": pr_url,
    }


def argv_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dispatch a single eligible eligible spec.")
    parser.add_argument("--spec", type=Path, required=True, help="Path to docs/specs/<slug>.md")
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--repo", help='GitHub "owner/repo" for gh CLI')
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--transport",
        choices=("pr", "issue", "codex"),
        default=DEFAULT_TRANSPORT,
        help="pr=open GitHub PR (D1 v1); issue=legacy tracking issue; codex=deferred",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = argv_parser().parse_args(argv)
    if args.transport == "codex":
        print(
            "ERROR: codex exec in CI is deferred; configure CODEX_API_KEY and see "
            "docs/archive/spikes/phase6-d1/NOTES.md",
            file=sys.stderr,
        )
        return 2
    try:
        spec_path = resolve_spec_path(args.spec, args.repo_root)
        descriptor = load_descriptor(spec_path, args.repo_root)
        payload = build_dispatch_payload(descriptor, transport=args.transport)
        if args.dry_run:
            print(json.dumps({"dry_run": True, **payload}, indent=2))
            return 0
        if args.transport == "issue":
            result = dispatch_issue_stub(payload=payload, remote=args.remote, repo=args.repo)
        else:
            result = dispatch_open_pr(payload=payload, remote=args.remote, repo=args.repo)
    except (OSError, ValueError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
