"""Codex-in-CI helpers for Phase 6.1 scheduled automation.

Builds role-specific prompts, optionally invokes ``codex exec`` locally, and
merges Reviewer JSON into PR bodies. GitHub Actions uses ``openai/codex-action@v1``
with prompts written by :func:`write_prompt`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

Role = Literal["executor", "reviewer"]

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FENCE_RE = re.compile(
    r"<!--\s*REVIEWER_JSON\s*-->(.*?)<!--\s*/REVIEWER_JSON\s*-->",
    re.DOTALL,
)
_MD_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\n(.*?)\n\s*```\s*$",
    re.DOTALL,
)


def executor_prompt(spec_path: str) -> str:
    return (
        "You are the Executor for this repository.\n\n"
        f"Implement the authorized spec at `{spec_path}` literally.\n"
        "Run `just check` before finishing. Do not modify red-zone files listed in "
        "AGENTS.md. Commit your changes on the current branch.\n"
        "Leave an empty `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block "
        "in the PR description for the Reviewer step.\n"
    )


def reviewer_prompt(spec_path: str, *, spec_excerpt: str | None = None) -> str:
    excerpt = spec_excerpt or _read_spec_excerpt(spec_path)
    return (
        "You are the Reviewer for this repository.\n\n"
        f"Review the PR diff against the spec at `{spec_path}`.\n"
        "Output ONLY valid JSON conforming to `.reviewer-schema.json`, wrapped in:\n"
        "<!-- REVIEWER_JSON -->\n```json\n{ ... }\n```\n<!-- /REVIEWER_JSON -->\n\n"
        "Spec excerpt:\n"
        f"{excerpt}\n"
    )


def _read_spec_excerpt(spec_path: str, *, max_lines: int = 120) -> str:
    path = Path(spec_path)
    if not path.is_file():
        path = _REPO_ROOT / spec_path
    if not path.is_file():
        return f"(spec file not found: {spec_path})"
    lines = path.read_text(encoding="utf-8").splitlines()
    clipped = lines[:max_lines]
    text = "\n".join(clipped)
    if len(lines) > max_lines:
        text += f"\n... ({len(lines) - max_lines} more lines omitted)"
    return text


def write_prompt(*, role: Role, spec_path: str, output: Path) -> None:
    text = executor_prompt(spec_path) if role == "executor" else reviewer_prompt(spec_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def codex_api_key_present() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("CODEX_API_KEY"))


def run_codex_exec(
    prompt: str,
    *,
    sandbox: str,
    cwd: Path | None = None,
) -> str:
    """Run ``codex exec`` when the CLI and API key are available."""
    codex = shutil.which("codex")
    if codex is None:
        msg = "codex CLI not found in PATH"
        raise RuntimeError(msg)
    if not codex_api_key_present():
        msg = "OPENAI_API_KEY or CODEX_API_KEY is not set"
        raise RuntimeError(msg)
    cmd = [codex, "exec", "--sandbox", sandbox, prompt]
    cp = subprocess.run(
        cmd,
        cwd=cwd or _REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if cp.returncode != 0:
        msg = f"codex exec failed ({cp.returncode}): {cp.stderr or cp.stdout}"
        raise RuntimeError(msg)
    return cp.stdout


def extract_reviewer_json_block(text: str) -> dict[str, Any]:
    """Best-effort parse of Reviewer JSON from codex stdout or a PR body."""
    match = _FENCE_RE.search(text)
    payload = match.group(1) if match else text
    payload = payload.strip()
    inner = _MD_FENCE_RE.match(payload)
    if inner:
        payload = inner.group(1).strip()
    # If still wrapped only in fences without HTML markers
    if payload.startswith("```"):
        inner2 = _MD_FENCE_RE.match(payload)
        if inner2:
            payload = inner2.group(1).strip()
    return json.loads(payload)


def merge_reviewer_into_body(body: str, reviewer: dict[str, Any]) -> str:
    block = f"<!-- REVIEWER_JSON -->\n{json.dumps(reviewer, indent=2)}\n<!-- /REVIEWER_JSON -->"
    if _FENCE_RE.search(body):
        return _FENCE_RE.sub(block, body, count=1)
    return body.rstrip() + "\n\n" + block + "\n"


def gh_pr_body(*, pr_number: int, repo: str | None) -> str:
    gh = shutil.which("gh")
    if gh is None:
        raise RuntimeError("gh executable not found in PATH")
    cmd = [gh, "pr", "view", str(pr_number), "--json", "body", "-q", ".body"]
    if repo:
        cmd.extend(["--repo", repo])
    cp = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return cp.stdout


def gh_set_pr_body(*, pr_number: int, body: str, repo: str | None) -> None:
    gh = shutil.which("gh")
    if gh is None:
        raise RuntimeError("gh executable not found in PATH")
    cmd = [gh, "pr", "edit", str(pr_number), "--body", body]
    if repo:
        cmd.extend(["--repo", repo])
    subprocess.run(cmd, check=True)


def apply_reviewer_to_pr(
    *,
    pr_number: int,
    reviewer: dict[str, Any],
    repo: str | None,
) -> None:
    body = gh_pr_body(pr_number=pr_number, repo=repo)
    gh_set_pr_body(pr_number=pr_number, body=merge_reviewer_into_body(body, reviewer), repo=repo)


def parse_pr_number(pr_url: str) -> int:
    match = re.search(r"/pull/(\d+)\s*$", pr_url.strip())
    if not match:
        msg = f"cannot parse PR number from URL: {pr_url!r}"
        raise ValueError(msg)
    return int(match.group(1))


def argv_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex CI prompt and local exec helpers.")
    sub = parser.add_subparsers(dest="command", required=True)

    wp = sub.add_parser("write-prompt", help="Write a Codex prompt file for CI or local use.")
    wp.add_argument("--role", choices=("executor", "reviewer"), required=True)
    wp.add_argument("--spec", required=True, help="Authorizing spec path.")
    wp.add_argument("--output", type=Path, required=True)

    ex = sub.add_parser("exec", help="Run codex exec locally (requires codex CLI + API key).")
    ex.add_argument("--role", choices=("executor", "reviewer"), required=True)
    ex.add_argument("--spec", required=True)
    ex.add_argument(
        "--sandbox",
        default="workspace-write",
        help="Codex sandbox for executor; use read-only for reviewer.",
    )

    ar = sub.add_parser("apply-reviewer", help="Merge Reviewer JSON into a PR body via gh.")
    ar.add_argument("--pr", type=int, required=True)
    ar.add_argument("--reviewer-json", type=Path, required=True)
    ar.add_argument("--repo", help='GitHub "owner/repo"')

    return parser


def main(argv: list[str] | None = None) -> int:
    args = argv_parser().parse_args(argv)
    if args.command == "write-prompt":
        write_prompt(role=args.role, spec_path=args.spec, output=args.output)
        print(args.output)
        return 0
    if args.command == "exec":
        prompt = (
            executor_prompt(args.spec) if args.role == "executor" else reviewer_prompt(args.spec)
        )
        sandbox = args.sandbox
        if args.role == "reviewer":
            sandbox = "read-only"
        out = run_codex_exec(prompt, sandbox=sandbox)
        sys.stdout.write(out)
        return 0
    if args.command == "apply-reviewer":
        reviewer = json.loads(args.reviewer_json.read_text(encoding="utf-8"))
        apply_reviewer_to_pr(pr_number=args.pr, reviewer=reviewer, repo=args.repo)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
