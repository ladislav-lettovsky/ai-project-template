"""Dispatch one eligible spec (branch + open PR, legacy issue, or codex CI handoff).

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
        "Queued spec dispatch (legacy issue transport).\n\n"
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


def _run_git(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    """Run git without writing progress to stdout (CI pipes stdout to dispatch.json)."""
    subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)


def create_remote_branch(remote: str, branch_name: str) -> None:
    main_ref = f"{remote}/main"
    main_sha = resolve_ref(main_ref)
    head_sha = resolve_ref("HEAD")
    if head_sha != main_sha:
        msg = f"local HEAD ({head_sha}) does not match {main_ref} ({main_sha})"
        raise RuntimeError(msg)
    _run_git(["git", "push", remote, f"{main_sha}:refs/heads/{branch_name}"])


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
    _run_git(["git", "fetch", remote, branch_name], env=git_env)
    main_sha = resolve_ref(f"{remote}/main")
    branch_sha = resolve_ref(f"{remote}/{branch_name}")
    if branch_sha != main_sha:
        return False
    previous = resolve_ref("HEAD")
    _run_git(
        ["git", "checkout", "-B", branch_name, f"{remote}/{branch_name}"],
        env=git_env,
    )
    _run_git(["git", "commit", "--allow-empty", "-m", message], env=git_env)
    _run_git(["git", "push", remote, branch_name], env=git_env)
    _run_git(["git", "checkout", previous], env=git_env)
    return True


def emit_result(result: dict[str, Any], *, json_out: Path | None) -> None:
    text = json.dumps(result, indent=2)
    if json_out is not None:
        json_out.write_text(f"{text}\n", encoding="utf-8")
    else:
        print(text)


def _gh_hint(action: str, detail: str) -> str:
    lowered = detail.lower()
    if action == "pr create" and (
        "not permitted" in lowered or "resource not accessible" in lowered
    ):
        return (
            " Enable GitHub repo Settings → Actions → General → Workflow permissions: "
            "Read and write, and check 'Allow GitHub Actions to create and approve "
            "pull requests'."
        )
    return ""


def _run_gh(cmd: list[str], *, action: str) -> str:
    gh_path = shutil.which("gh")
    if gh_path is None:
        raise RuntimeError("gh executable not found in PATH")
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        detail = (cp.stderr or cp.stdout or "").strip()
        msg = f"gh {action} failed"
        if detail:
            msg = f"{msg}: {detail}"
        msg += _gh_hint(action, detail)
        raise RuntimeError(msg)
    return cp.stdout.strip()


def open_tracking_issue(
    *,
    title: str,
    body: str,
    label: str,
    repo: str | None = None,
) -> str:
    cmd = ["gh", "issue", "create", "--title", title, "--body", body, "--label", label]
    if repo:
        cmd.extend(["--repo", repo])
    return _run_gh(cmd, action="issue create")


def find_open_pr_url(*, branch: str, repo: str | None) -> str | None:
    """Return an open PR URL for ``branch``, if any.

      Uses the REST pulls API (not ``gh pr list``) so fine-grained PATs with only
    pull-request scopes work reliably in Actions.
    """
    if not repo:
        raise RuntimeError("repo owner/name required for find_open_pr_url")
    owner, name = repo.split("/", 1)
    head = f"{owner}:{branch}"
    url = _run_gh(
        [
            "gh",
            "api",
            f"repos/{owner}/{name}/pulls",
            "-f",
            f"head={head}",
            "-f",
            "state=open",
            "--jq",
            'if length > 0 then .[0].html_url else "" end',
        ],
        action="pulls list",
    )
    return url or None


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
    return _run_gh(cmd, action="pr create")


def codex_agents_metadata() -> dict[str, Any]:
    return {
        "enabled_in_ci": bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("CODEX_API_KEY")),
        "note": "Run scheduled-executor codex_agents job or `uv run scripts/codex_ci.py exec`.",
    }


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
    parser = argparse.ArgumentParser(description="Dispatch a single eligible spec.")
    parser.add_argument("--spec", type=Path, required=True, help="Path to docs/specs/<slug>.md")
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--repo", help='GitHub "owner/repo" for gh CLI')
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--transport",
        choices=("pr", "issue", "codex"),
        default=DEFAULT_TRANSPORT,
        help="pr=open GitHub PR; issue=legacy tracking issue; codex=open PR for CI agents (6.1)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Write dispatch result JSON to this file (avoids mixing git stdout with JSON).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = argv_parser().parse_args(argv)
    try:
        spec_path = resolve_spec_path(args.spec, args.repo_root)
        descriptor = load_descriptor(spec_path, args.repo_root)
        payload = build_dispatch_payload(descriptor, transport=args.transport)
        if args.dry_run:
            if args.transport == "codex":
                payload["codex_agents"] = codex_agents_metadata()
            emit_result({"dry_run": True, **payload}, json_out=args.json_out)
            return 0
        if args.transport == "issue":
            result = dispatch_issue_stub(payload=payload, remote=args.remote, repo=args.repo)
        else:
            result = dispatch_open_pr(payload=payload, remote=args.remote, repo=args.repo)
            if args.transport == "codex":
                result["transport"] = "codex"
                result["codex_agents"] = codex_agents_metadata()
    except (OSError, ValueError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    emit_result(result, json_out=args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
