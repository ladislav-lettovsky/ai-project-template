"""Tests for ``scripts/red_zone_paths.py`` canonical path sets."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RZ_PATH = REPO_ROOT / "scripts" / "red_zone_paths.py"


def _load():
    spec = importlib.util.spec_from_file_location("red_zone_paths", RZ_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["red_zone_paths"] = mod
    spec.loader.exec_module(mod)
    return mod


red_zone_paths = _load()


def test_red_zone_exact_match_pyproject_in_set() -> None:
    assert red_zone_paths.is_red_zone("pyproject.toml")


def test_red_zone_github_workflow_prefix() -> None:
    assert red_zone_paths.is_red_zone(".github/workflows/route-pr.yml")


def test_router_touches_aggregate() -> None:
    assert red_zone_paths.touches_red_zone(["LICENSE", ".github/workflows/ci.yml"])
