"""Build ``pr.json`` for the deterministic Phase 4 Router.

``pr.json`` schema (minimal contract):
  * branch_name — head ref short name string
  * changed_files — list of repo-relative paths (forward slashes)
  * diff_lines — int (additions + deletions proxy from gh)
  * fork_pr — bool
  * multiple_authorizing_specs_changed — bool
  * pr_body — verbatim PR markdown body string
  * spec_validation — {\"status\": \"valid\"|\"invalid\", \"errors\": [...]}
  * reviewer_validation — {\"status\": \"valid\"|\"invalid\", \"errors\": [...]}
  * reviewer — parsed reviewer object when valid, else `{}`
  * spec — {\"slug\",\"path\",\"risk_tier\",\"complexity\"}; values may be null

Usage::
    uv run scripts/build_pr_context.py --repo owner/name --pr 123 --out pr.json

Optional::
    uv run scripts/build_pr_context.py --fixture tests/fixtures/pr_event_fork.json ...

When ``GITHUB_EVENT_PATH`` is set it is consulted for fork detection in
``--fork-mode auto`` (use ``yes`` / ``no`` to override).

CI example::
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    run: >-
      uv run scripts/build_pr_context.py
      --repo "${{ github.repository }}"
      --pr "${{ github.event.pull_request.number }}"
      --out pr.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import lint_spec  # noqa: E402
import validate_reviewer  # noqa: E402

EXCLUDED_SPEC_DOC_NAMES = frozenset(
    {"README.md", "_template.md", "_postmortem.md", ".gitkeep"},
)


def slug_from_branch(head_ref_name: str) -> str | None:
    """Return slug from ``spec/<slug>`` or ``fix/<slug>``, else ``None``."""
    for prefix in ("spec/", "fix/"):
        if head_ref_name.startswith(prefix):
            slug = head_ref_name[len(prefix) :].strip()
            return slug if slug else None
    return None


def is_authorizing_spec_doc(repo_rel_path: str) -> bool:
    if not repo_rel_path.startswith("docs/specs/"):
        return False
    name = Path(repo_rel_path).name
    return name not in EXCLUDED_SPEC_DOC_NAMES and name.endswith(".md")


def count_authorizing_specs_changed(paths: list[str]) -> int:
    return sum(1 for p in paths if is_authorizing_spec_doc(p))


def detect_fork_via_event(event_path: Path | None, base_full_name: str) -> bool:
    if event_path is None or not event_path.is_file():
        return False
    try:
        event = json.loads(event_path.read_text(encoding="utf-8"))
        head_repo = (
            event.get("pull_request", {}).get("head", {}).get("repo")
            if "pull_request" in event
            else None
        )
        head_fn = head_repo.get("full_name") if head_repo else None
        if head_fn is None:
            # Head deleted or fork metadata missing → treat conservative.
            return False
        return head_fn != base_full_name
    except (OSError, json.JSONDecodeError):
        return False


def gh_pr_view(repo: str, pr_number: int) -> dict:
    cp = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            ",".join(
                [
                    "body",
                    "files",
                    "headRefName",
                    "additions",
                    "deletions",
                ]
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(cp.stdout)


def build_context_dict(
    *,
    repo_full_name: str,
    gh_json: dict,
    repo_root: Path,
    fork_pr: bool,
) -> dict:
    branch_name = str(gh_json.get("headRefName") or "")
    body = str(gh_json.get("body") or "")
    files = gh_json.get("files") or []
    changed_paths: list[str] = []
    # gh returns list of Path objects keyed as {"path":"..."}; tolerate both.
    if isinstance(files, list) and files and all(isinstance(f, dict) for f in files):
        changed_paths = [str(f["path"]) for f in files if "path" in f]
    else:
        changed_paths = []

    additions = int(gh_json.get("additions") or 0)
    deletions = int(gh_json.get("deletions") or 0)
    diff_lines = additions + deletions

    slug = slug_from_branch(branch_name)
    spec_errors: list[str] = []

    meta_risk_tier: str | None = None
    meta_complexity: str | None = None
    spec_abs: Path | None = None

    if slug is None:
        spec_errors.append(
            "branch head must match spec/<slug> or fix/<slug> when using authorizing specs"
        )
    else:
        spec_abs = repo_root / "docs" / "specs" / f"{slug}.md"
        if not spec_abs.is_file():
            spec_errors.append(f"authorizing spec file missing at docs/specs/{slug}.md")
        else:
            spec_errors += lint_spec.lint_spec(spec_abs)
            section_text = lint_spec.split_sections(spec_abs.read_text(encoding="utf-8"))
            parsed = lint_spec.parse_metadata(section_text.get("Metadata", ""))
            meta_risk_tier = parsed.get("risk_tier")
            meta_complexity = parsed.get("complexity")

    spec_validity = {"status": "valid" if not spec_errors else "invalid", "errors": spec_errors}

    schema_dict = validate_reviewer.load_reviewer_schema(
        schema_path=repo_root / ".reviewer-schema.json"
    )
    reviewer_obj, reviewer_errs = validate_reviewer.parse_validated_review_or_errors(
        body, schema_dict
    )
    reviewer_validity = {
        "status": "valid" if not reviewer_errs else "invalid",
        "errors": reviewer_errs,
    }
    reviewer_out = reviewer_obj if reviewer_obj is not None else {}

    multi_specs = count_authorizing_specs_changed(changed_paths) > 1

    spec_block: dict[str, str | None] = {
        "slug": slug,
        "path": str(spec_abs.relative_to(repo_root)) if spec_abs and spec_abs.is_file() else None,
        "risk_tier": meta_risk_tier,
        "complexity": meta_complexity,
    }

    return {
        "repository": repo_full_name,
        "branch_name": branch_name,
        "changed_files": sorted(changed_paths),
        "diff_lines": diff_lines,
        "fork_pr": fork_pr,
        "multiple_authorizing_specs_changed": multi_specs,
        "pr_body": body,
        "spec_validation": spec_validity,
        "reviewer_validation": reviewer_validity,
        "reviewer": reviewer_out,
        "spec": spec_block,
    }


def argv_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build pr.json Router context.")
    p.add_argument("--repo", required=True, help='GitHub "owner/repo" for gh CLI')
    p.add_argument("--pr", "--pr-number", type=int, required=True, dest="pr_number")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--fork-mode",
        choices=("auto", "yes", "no"),
        default="auto",
        help="Fork detection: infer from GITHUB_EVENT_PATH (auto); force fork (yes); deny fork (no).",
    )
    p.add_argument(
        "--fixture-json",
        type=Path,
        help="Gh ``pr view`` JSON blob (skips invoking ``gh``; for tests/offline fixtures).",
    )
    return p


def resolve_fork_flag(fork_mode: str, event_inferred: bool) -> bool:
    if fork_mode == "yes":
        return True
    if fork_mode == "no":
        return False
    return event_inferred


def main(argv: list[str] | None = None) -> int:
    args = argv_parser().parse_args(argv)
    event_path_raw = os.environ.get("GITHUB_EVENT_PATH")
    event_path = Path(event_path_raw) if event_path_raw else None

    if args.fixture_json is not None:
        gh_blob = json.loads(args.fixture_json.read_text(encoding="utf-8"))
    else:
        gh_path = shutil.which("gh")
        if gh_path is None:
            print("ERROR: gh executable not found in PATH", file=sys.stderr)
            return 2
        gh_blob = gh_pr_view(args.repo, args.pr_number)

    inferred_fork = detect_fork_via_event(event_path, args.repo)
    fork_bool = resolve_fork_flag(args.fork_mode, inferred_fork)

    blob = build_context_dict(
        repo_full_name=args.repo,
        gh_json=gh_blob,
        repo_root=_REPO_ROOT,
        fork_pr=fork_bool,
    )
    args.out.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
