"""Tests for ``scripts/lint_spec.py``.

The linter gates ``just check``; if it accepts a malformed spec or
rejects a well-formed one, every downstream contract breaks. These tests
exercise the parser shape directly rather than via ``subprocess``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Load lint_spec.py as a module without requiring scripts/ to be a package.
REPO_ROOT = Path(__file__).resolve().parents[1]
LINT_SPEC_PATH = REPO_ROOT / "scripts" / "lint_spec.py"
_spec = importlib.util.spec_from_file_location("lint_spec", LINT_SPEC_PATH)
assert _spec is not None and _spec.loader is not None
lint_spec_module = importlib.util.module_from_spec(_spec)
sys.modules["lint_spec"] = lint_spec_module
_spec.loader.exec_module(lint_spec_module)


def _minimal_valid_spec() -> str:
    """Return a synthetic spec text that should lint clean.

    Kept inline so a test failure surfaces the exact spec under test.
    """
    return """\
# Test Feature

## Metadata
- spec_id: SPEC-20260507-test
- owner: Tester
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template

## Context
Why now.

## Assumptions
- A1: assumption.

## Decisions
- D1: decided.

## Problem Statement
Problem.

## Requirements (STRICT)
- [ ] R1: do the thing.

## Non-Goals
- [ ] NG1: not the other thing.

## Interfaces
None.

## Invariants to Preserve
- [ ] INV1: stay true.

## Red-Zone Assessment
- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no

## Test Plan
- [ ] T1 -> covers R1

## Validation Contract
- R1 -> `just check`

## Edge Cases
- EC1: nothing notable.

## Security / Prompt-Injection Review
- source: in-process function argument.
- risk: low
- mitigation: not required.

## Observability
None required.

## Rollback / Recovery
Revert the commit.

## Implementation Slices
1. Slice 1: ship the thing.

## Done When
- [ ] R1 satisfied
- [ ] just check green
"""


def test_minimal_valid_spec_lints_clean(tmp_path: Path) -> None:
    """The hand-rolled minimal spec covers every required section."""
    spec_path = tmp_path / "minimal.md"
    spec_path.write_text(_minimal_valid_spec(), encoding="utf-8")
    assert lint_spec_module.lint_spec(spec_path) == []


def test_real_example_spec_lints_clean() -> None:
    """The committed example spec must remain valid (regression target).

    Covers REQ-LINT-real: ``add-greet-module.md`` is the canonical example
    of a §5.1-conformant spec; if a parser change breaks it, the parser
    is wrong.
    """
    spec_path = REPO_ROOT / "docs" / "specs" / "add-greet-module.md"
    if not spec_path.is_file():
        pytest.skip(f"{spec_path} not present in this checkout")
    errors = lint_spec_module.lint_spec(spec_path)
    assert errors == [], f"add-greet-module.md should lint clean; got: {errors}"


def test_missing_section_is_reported(tmp_path: Path) -> None:
    """Removing a required section produces a 'missing required section' error."""
    text = _minimal_valid_spec().replace("## Edge Cases\n- EC1: nothing notable.\n\n", "")
    spec_path = tmp_path / "no-edge-cases.md"
    spec_path.write_text(text, encoding="utf-8")
    errors = lint_spec_module.lint_spec(spec_path)
    assert any("Edge Cases" in e for e in errors), errors


def test_unknown_risk_tier_is_reported(tmp_path: Path) -> None:
    """``risk_tier: T9`` is not in the allowed enum."""
    text = _minimal_valid_spec().replace("risk_tier: T0", "risk_tier: T9")
    spec_path = tmp_path / "bad-tier.md"
    spec_path.write_text(text, encoding="utf-8")
    errors = lint_spec_module.lint_spec(spec_path)
    assert any("risk_tier" in e and "T9" in e for e in errors), errors


def test_unknown_complexity_is_reported(tmp_path: Path) -> None:
    """``complexity: extreme`` is not in the allowed enum."""
    text = _minimal_valid_spec().replace("complexity: low", "complexity: extreme")
    spec_path = tmp_path / "bad-complexity.md"
    spec_path.write_text(text, encoding="utf-8")
    errors = lint_spec_module.lint_spec(spec_path)
    assert any("complexity" in e and "extreme" in e for e in errors), errors


def test_requirement_without_test_is_reported(tmp_path: Path) -> None:
    """A requirement R2 with no T -> covers R2 line is rejected."""
    text = _minimal_valid_spec().replace(
        "- [ ] R1: do the thing.",
        "- [ ] R1: do the thing.\n- [ ] R2: do the other thing.",
    )
    # No T2 added — R2 has no coverage.
    spec_path = tmp_path / "uncovered.md"
    spec_path.write_text(text, encoding="utf-8")
    errors = lint_spec_module.lint_spec(spec_path)
    assert any("R2" in e and "Test Plan" in e for e in errors), errors


def test_requirement_without_validation_is_reported(tmp_path: Path) -> None:
    """A requirement with a Test entry but no Validation Contract entry is rejected."""
    text = (
        _minimal_valid_spec()
        .replace(
            "- [ ] R1: do the thing.",
            "- [ ] R1: do the thing.\n- [ ] R2: do the other thing.",
        )
        .replace(
            "- [ ] T1 -> covers R1",
            "- [ ] T1 -> covers R1\n- [ ] T2 -> covers R2",
        )
    )
    # No R2 -> validator entry under Validation Contract.
    spec_path = tmp_path / "unvalidated.md"
    spec_path.write_text(text, encoding="utf-8")
    errors = lint_spec_module.lint_spec(spec_path)
    assert any("R2" in e and "Validation Contract" in e for e in errors), errors


def test_req_dash_form_is_recognized(tmp_path: Path) -> None:
    """The ``REQ-DOMAIN-NN`` ID shape (used by add-greet-module.md) is supported."""
    text = (
        _minimal_valid_spec()
        .replace("- [ ] R1: do the thing.", "- [ ] REQ-FOO-01: do the thing.")
        .replace("- [ ] T1 -> covers R1", "- [ ] T1 -> covers REQ-FOO-01")
        .replace("- R1 -> `just check`", "- REQ-FOO-01 -> `just check`")
    )
    spec_path = tmp_path / "req-form.md"
    spec_path.write_text(text, encoding="utf-8")
    assert lint_spec_module.lint_spec(spec_path) == []


def test_duplicate_short_form_id_is_reported(tmp_path: Path) -> None:
    """Covers R1: duplicate short-form requirement IDs are reported."""
    text = _minimal_valid_spec().replace(
        "- [ ] R1: do the thing.",
        "- [ ] R1: do the thing.\n- [ ] R1: do the other thing.",
    )
    spec_path = tmp_path / "duplicate-short-form.md"
    spec_path.write_text(text, encoding="utf-8")
    errors = lint_spec_module.lint_spec(spec_path)
    assert "requirement 'R1' is declared more than once" in errors


def test_duplicate_long_form_id_is_reported(tmp_path: Path) -> None:
    """Covers R2: duplicate long-form requirement IDs are reported."""
    text = (
        _minimal_valid_spec()
        .replace(
            "- [ ] R1: do the thing.",
            "- [ ] REQ-FOO-01: do the thing.\n- [ ] REQ-FOO-01: do the other thing.",
        )
        .replace("- [ ] T1 -> covers R1", "- [ ] T1 -> covers REQ-FOO-01")
        .replace("- R1 -> `just check`", "- REQ-FOO-01 -> `just check`")
    )
    spec_path = tmp_path / "duplicate-long-form.md"
    spec_path.write_text(text, encoding="utf-8")
    errors = lint_spec_module.lint_spec(spec_path)
    assert "requirement 'REQ-FOO-01' is declared more than once" in errors


def test_triple_duplicate_emits_single_error(tmp_path: Path) -> None:
    """Covers R3: three declarations of the same ID produce one duplicate error."""
    text = _minimal_valid_spec().replace(
        "- [ ] R1: do the thing.",
        "- [ ] R1: do the thing.\n- [ ] R1: do the other thing.\n- [ ] R1: do a third thing.",
    )
    spec_path = tmp_path / "triple-duplicate.md"
    spec_path.write_text(text, encoding="utf-8")
    errors = lint_spec_module.lint_spec(spec_path)
    assert errors.count("requirement 'R1' is declared more than once") == 1


def test_duplicate_does_not_amplify_mapping_errors(tmp_path: Path) -> None:
    """Covers R4: duplicate declarations do not amplify downstream mapping errors."""
    text = (
        _minimal_valid_spec()
        .replace(
            "- [ ] R1: do the thing.",
            "- [ ] R1: do the thing.\n- [ ] R1: do the other thing.",
        )
        .replace("- [ ] T1 -> covers R1\n", "")
    )
    spec_path = tmp_path / "duplicate-missing-test.md"
    spec_path.write_text(text, encoding="utf-8")
    errors = lint_spec_module.lint_spec(spec_path)

    duplicate_error = "requirement 'R1' is declared more than once"
    mapping_error = "requirement 'R1' has no matching 'T<n> -> covers R1' entry in Test Plan"
    assert duplicate_error in errors
    assert errors.count(mapping_error) == 1


def test_main_returns_zero_for_valid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``main`` returns 0 when every input file lints clean."""
    spec_path = tmp_path / "ok.md"
    spec_path.write_text(_minimal_valid_spec(), encoding="utf-8")
    rc = lint_spec_module.main([str(spec_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err == ""


def test_main_returns_one_for_invalid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``main`` returns 1 when at least one file fails lint."""
    text = _minimal_valid_spec().replace("## Edge Cases\n- EC1: nothing notable.\n\n", "")
    spec_path = tmp_path / "bad.md"
    spec_path.write_text(text, encoding="utf-8")
    rc = lint_spec_module.main([str(spec_path)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "Edge Cases" in captured.err


def test_main_returns_two_for_no_args(capsys: pytest.CaptureFixture[str]) -> None:
    """``main`` returns 2 when invoked with no paths."""
    rc = lint_spec_module.main([])
    assert rc == 2
    captured = capsys.readouterr()
    assert "usage" in captured.err.lower()
