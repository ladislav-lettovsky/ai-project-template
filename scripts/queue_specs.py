"""Discover eligible specs queued for scheduled Executor dispatch.

Usage:
    uv run scripts/queue_specs.py [--remote origin] [--json]

The script scans ``docs/specs/*.md`` and emits descriptors for drafted
specs that are relevant to the queue. ``eligible: true`` is the only
dispatchable state; every other returned descriptor carries ``skip_reason``.
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

import lint_spec  # noqa: E402

EXCLUDED_SPEC_NAMES = frozenset({"_template.md", "_postmortem.md", "README.md"})
RED_ZONE_VALUES = frozenset({"yes", "no"})
RED_ZONE_AXES = (
    "auth",
    "billing",
    "dependencies",
    "CI",
    "migrations",
    "secrets",
    "infra",
    "invariant-protected files",
)


def slug_from_path(path: Path) -> str:
    return path.stem


def spec_repo_path(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def parse_red_zone(body: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in body.splitlines():
        match = lint_spec.REDZONE_LINE_RE.match(line)
        if not match:
            continue
        values[match.group("key").strip()] = match.group("value").strip().lower()
    return values


def parse_spec_descriptor(path: Path, repo_root: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    sections = lint_spec.split_sections(text)
    metadata = lint_spec.parse_metadata(sections.get("Metadata", ""))
    red_zone = parse_red_zone(sections.get("Red-Zone Assessment", ""))
    slug = slug_from_path(path)
    return {
        "slug": slug,
        "path": spec_repo_path(path, repo_root),
        "metadata": metadata,
        "status": metadata.get("status"),
        "risk_tier": metadata.get("risk_tier"),
        "complexity": metadata.get("complexity"),
        "red_zone": red_zone,
        "eligible": False,
    }


def metadata_skip_reason(descriptor: dict[str, Any]) -> str | None:
    metadata = descriptor.get("metadata") or {}
    required = ("status", "risk_tier", "complexity")
    if any(not metadata.get(field) for field in required):
        return "metadata_invalid"
    if descriptor.get("status") != "drafted":
        return "status_not_drafted"
    return None


def eligibility_skip_reason(descriptor: dict[str, Any]) -> str | None:
    if descriptor.get("risk_tier") != "T0":
        return "risk_tier_ineligible"
    if descriptor.get("complexity") != "low":
        return "complexity_ineligible"
    red_zone = descriptor.get("red_zone") or {}
    if not red_zone:
        return "red_zone_missing"
    missing_axes = [key for key in RED_ZONE_AXES if key not in red_zone]
    if missing_axes:
        return "red_zone_incomplete"
    invalid_values = [key for key, value in red_zone.items() if value not in RED_ZONE_VALUES]
    if invalid_values:
        return "red_zone_invalid"
    yes_axes = [key for key, value in red_zone.items() if value == "yes"]
    if yes_axes:
        return "red_zone_yes"
    return None


def list_remote_spec_branches(remote: str) -> set[str]:
    cp = subprocess.run(
        ["git", "ls-remote", "--heads", remote, "refs/heads/spec/*"],
        check=True,
        capture_output=True,
        text=True,
    )
    branches: set[str] = set()
    for line in cp.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("refs/heads/"):
            branches.add(parts[1].removeprefix("refs/heads/"))
    return branches


def list_pull_requests(repo: str | None = None) -> list[dict[str, Any]]:
    gh_path = shutil.which("gh")
    if gh_path is None:
        raise RuntimeError("gh executable not found in PATH")
    cmd = [
        "gh",
        "pr",
        "list",
        "--state",
        "all",
        "--json",
        "number,state,body,headRefName,url,mergedAt",
        "--limit",
        "200",
    ]
    if repo:
        cmd.extend(["--repo", repo])
    cp = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(cp.stdout)
    if not isinstance(data, list):
        msg = "gh pr list returned non-list JSON"
        raise RuntimeError(msg)
    return data


def pr_references_spec(pr: dict[str, Any], spec_path: str, *, slug: str) -> bool:
    """True when a PR is an in-flight or completed scheduler dispatch for this spec.

      Substring match on ``spec_path`` alone is too broad (e.g. a chore PR that
    mentions the path in its description). Match ``spec/<slug>`` head branches or
      bodies shaped like ``dispatch_spec.build_pr_body`` (spec link +
      ``dispatch-source: scheduled``).
    """
    state = str(pr.get("state") or "").upper()
    merged_at = pr.get("mergedAt")
    if state not in {"OPEN", "MERGED"} and not merged_at:
        return False
    head = str(pr.get("headRefName") or "")
    if head == f"spec/{slug}":
        return True
    body = str(pr.get("body") or "")
    return spec_path in body and "dispatch-source: scheduled" in body


def iter_spec_paths(spec_dir: Path) -> list[Path]:
    paths = [p for p in spec_dir.glob("*.md") if p.name not in EXCLUDED_SPEC_NAMES]
    drills = spec_dir / "_drills"
    if drills.is_dir():
        paths.extend(p for p in drills.glob("*.md") if p.name not in EXCLUDED_SPEC_NAMES)
    return sorted(paths, key=lambda p: p.as_posix())


def discover_specs(
    *,
    repo_root: Path,
    remote_branches: set[str],
    pull_requests: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    spec_dir = repo_root / "docs" / "specs"
    descriptors: list[dict[str, Any]] = []
    for path in iter_spec_paths(spec_dir):
        descriptor = parse_spec_descriptor(path, repo_root)
        skip_reason = metadata_skip_reason(descriptor)
        if skip_reason == "status_not_drafted":
            continue
        if skip_reason is None:
            branch_name = f"spec/{descriptor['slug']}"
            if branch_name in remote_branches:
                skip_reason = "branch_exists"
            elif any(
                pr_references_spec(pr, descriptor["path"], slug=descriptor["slug"])
                for pr in pull_requests
            ):
                skip_reason = "pr_exists"
            else:
                skip_reason = eligibility_skip_reason(descriptor)

        if skip_reason is None:
            descriptor["eligible"] = True
        else:
            descriptor["eligible"] = False
            descriptor["skip_reason"] = skip_reason
        descriptors.append(descriptor)
    return descriptors


def read_fixture_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def argv_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover queued eligible specs.")
    parser.add_argument(
        "--remote", default="origin", help="Git remote to inspect for spec branches"
    )
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--repo", help='GitHub "owner/repo" for gh CLI')
    parser.add_argument("--json", action="store_true", help="Emit JSON list on stdout")
    parser.add_argument(
        "--branches-json", type=Path, help="Test fixture: JSON list of branch names"
    )
    parser.add_argument("--prs-json", type=Path, help="Test fixture: gh pr list JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = argv_parser().parse_args(argv)
    try:
        if args.branches_json is not None:
            branches = set(read_fixture_json(args.branches_json))
        else:
            branches = list_remote_spec_branches(args.remote)
        if args.prs_json is not None:
            prs = read_fixture_json(args.prs_json)
        else:
            prs = list_pull_requests(args.repo)
        descriptors = discover_specs(
            repo_root=args.repo_root,
            remote_branches=branches,
            pull_requests=prs,
        )
    except (OSError, subprocess.CalledProcessError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(descriptors, indent=2 if args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
