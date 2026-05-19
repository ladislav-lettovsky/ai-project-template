"""Optional auto-merge when a PR is labeled ``review:codex`` and checks are green."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any


def gh_pr_view(*, pr_number: int, repo: str | None) -> dict[str, Any]:
    gh = shutil.which("gh")
    if gh is None:
        raise RuntimeError("gh executable not found in PATH")
    cmd = [gh, "pr", "view", str(pr_number), "--json", "labels,mergeStateStatus"]
    if repo:
        cmd.extend(["--repo", repo])
    cp = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(cp.stdout)


def try_merge(*, pr_number: int, repo: str | None) -> dict[str, str]:
    pr = gh_pr_view(pr_number=pr_number, repo=repo)
    labels = {item["name"] for item in pr.get("labels", []) if isinstance(item, dict)}
    if "review:codex" not in labels:
        return {"action": "skipped", "reason": "missing review:codex label"}
    state = str(pr.get("mergeStateStatus") or "")
    if state not in {"CLEAN", "HAS_HOOKS"}:
        return {"action": "skipped", "reason": f"mergeStateStatus={state!r}"}
    gh = shutil.which("gh")
    assert gh is not None
    cmd = [gh, "pr", "merge", str(pr_number), "--squash", "--delete-branch"]
    if repo:
        cmd.extend(["--repo", repo])
    subprocess.run(cmd, check=True)
    return {"action": "merged", "reason": "review:codex and merge state clean"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Squash-merge PR when review:codex and checks pass."
    )
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--repo", help='GitHub "owner/repo"')
    args = parser.parse_args(argv)
    try:
        result = try_merge(pr_number=args.pr, repo=args.repo)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
