"""Tests for ``scripts/queue_specs.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_QUEUE_PATH = REPO_ROOT / "scripts" / "queue_specs.py"


def _load_queue():
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("queue_specs", _QUEUE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


queue_specs = _load_queue()


def _write_spec(
    repo_root: Path,
    slug: str,
    *,
    status: str = "drafted",
    risk_tier: str = "T0",
    complexity: str = "low",
    red_zone: dict[str, str] | None = None,
) -> Path:
    if red_zone is None:
        red_zone = {key: "no" for key in queue_specs.RED_ZONE_AXES}
    spec_dir = repo_root / "docs" / "specs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    red_zone_lines = "\n".join(f"- {key}: {value}" for key, value in red_zone.items())
    path = spec_dir / f"{slug}.md"
    path.write_text(
        "\n".join(
            [
                f"# {slug}",
                "",
                "## Metadata",
                f"- spec_id: SPEC-20260518-{slug}",
                "- owner: tests",
                f"- status: {status}",
                f"- complexity: {complexity}",
                f"- risk_tier: {risk_tier}",
                "",
                "## Red-Zone Assessment",
                red_zone_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_queue_discovery_excludes_templates_and_non_drafted(tmp_path: Path) -> None:
    spec_dir = tmp_path / "docs" / "specs"
    spec_dir.mkdir(parents=True)
    _write_spec(tmp_path, "eligible")
    _write_spec(tmp_path, "complete", status="complete")
    for name in ("_template.md", "_postmortem.md", "README.md"):
        (spec_dir / name).write_text("ignored", encoding="utf-8")

    discovered = queue_specs.discover_specs(
        repo_root=tmp_path,
        remote_branches=set(),
        pull_requests=[],
    )

    assert [item["slug"] for item in discovered] == ["eligible"]
    assert discovered[0]["eligible"] is True


def test_eligibility_filter(tmp_path: Path) -> None:
    _write_spec(tmp_path, "eligible")
    _write_spec(tmp_path, "tier", risk_tier="T1")
    _write_spec(tmp_path, "complex", complexity="medium")
    redzone_values = {key: "no" for key in queue_specs.RED_ZONE_AXES}
    redzone_values["infra"] = "yes"
    _write_spec(tmp_path, "redzone", red_zone=redzone_values)

    by_slug = {
        item["slug"]: item
        for item in queue_specs.discover_specs(
            repo_root=tmp_path,
            remote_branches=set(),
            pull_requests=[],
        )
    }

    assert by_slug["eligible"]["eligible"] is True
    assert by_slug["tier"]["skip_reason"] == "risk_tier_ineligible"
    assert by_slug["complex"]["skip_reason"] == "complexity_ineligible"
    assert by_slug["redzone"]["skip_reason"] == "red_zone_yes"


def test_discover_specs_includes_drills_subdirectory(tmp_path: Path) -> None:
    _write_spec(tmp_path, "root-spec")
    drills = tmp_path / "docs" / "specs" / "_drills"
    drills.mkdir(parents=True)
    top_level_drill = _write_spec(tmp_path, "scheduler-drill")
    top_level_drill.rename(drills / "scheduler-drill.md")
    slugs = {
        item["slug"]
        for item in queue_specs.discover_specs(
            repo_root=tmp_path,
            remote_branches=set(),
            pull_requests=[],
        )
    }
    assert "root-spec" in slugs
    assert "scheduler-drill" in slugs


def test_red_zone_partial_axes_are_incomplete(tmp_path: Path) -> None:
    _write_spec(tmp_path, "partial-redzone", red_zone={"auth": "no", "billing": "no"})

    [descriptor] = queue_specs.discover_specs(
        repo_root=tmp_path,
        remote_branches=set(),
        pull_requests=[],
    )

    assert descriptor["eligible"] is False
    assert descriptor["skip_reason"] == "red_zone_incomplete"


def test_red_zone_missing_section_is_missing(tmp_path: Path) -> None:
    _write_spec(tmp_path, "missing-redzone", red_zone={})

    [descriptor] = queue_specs.discover_specs(
        repo_root=tmp_path,
        remote_branches=set(),
        pull_requests=[],
    )

    assert descriptor["eligible"] is False
    assert descriptor["skip_reason"] == "red_zone_missing"


def test_existing_branch_and_pr_reference_skip_dispatch(tmp_path: Path) -> None:
    _write_spec(tmp_path, "branch-exists")
    _write_spec(tmp_path, "pr-exists")
    prs = [
        {
            "state": "OPEN",
            "body": (
                "Implements [docs/specs/pr-exists.md](docs/specs/pr-exists.md).\n\n"
                "dispatch-source: scheduled\n"
            ),
            "headRefName": "someone/else",
        }
    ]

    by_slug = {
        item["slug"]: item
        for item in queue_specs.discover_specs(
            repo_root=tmp_path,
            remote_branches={"spec/branch-exists"},
            pull_requests=prs,
        )
    }

    assert by_slug["branch-exists"]["skip_reason"] == "branch_exists"
    assert by_slug["pr-exists"]["skip_reason"] == "pr_exists"


def test_chore_pr_mentioning_spec_path_does_not_block(tmp_path: Path) -> None:
    _write_spec(tmp_path, "test-hello-world")
    prs = [
        {
            "state": "MERGED",
            "mergedAt": "2026-05-19T00:00:00Z",
            "body": "Renames docs/specs/_drills/test-hello-world.md for clarity.",
            "headRefName": "chore/rename-spec",
        }
    ]

    [descriptor] = queue_specs.discover_specs(
        repo_root=tmp_path,
        remote_branches=set(),
        pull_requests=prs,
    )

    assert descriptor["eligible"] is True


def test_cli_uses_json_fixtures(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    _write_spec(tmp_path, "eligible")
    branches = tmp_path / "branches.json"
    prs = tmp_path / "prs.json"
    branches.write_text(json.dumps([]), encoding="utf-8")
    prs.write_text(json.dumps([]), encoding="utf-8")

    rc = queue_specs.main(
        [
            "--repo-root",
            str(tmp_path),
            "--branches-json",
            str(branches),
            "--prs-json",
            str(prs),
            "--json",
        ]
    )

    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    assert output[0]["slug"] == "eligible"
    assert output[0]["eligible"] is True
