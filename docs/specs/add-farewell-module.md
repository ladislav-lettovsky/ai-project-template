# Add `farewell` module to `your_package`

## Metadata
- spec_id: SPEC-20260508-add-farewell-module
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/add-farewell-module

## Context
The repository now has a `greet` module (`add-greet-module.md`) as a worked
example of the spec-driven flow. A second, symmetrical module serves two
purposes:

1. It proves the pattern is repeatable — a second module exercises the same
   conventions (typing, validation, docstring, tests with requirement-ID
   citations) without being a copy of the first.
2. It gives the template a minimal "hello / goodbye" pair that makes the
   pattern legible to forks: callers import `your_package.greet.greet` or
   `your_package.farewell.farewell` depending on intent, and both follow
   exactly the same contract shape.

The feature itself is intentionally trivial. Its purpose is structural, not
functional.

## Assumptions
- A1: The package layout is `src/your_package/` (src layout, per CLAUDE.md
  "Where things live").
- A2: `tests/` at the repo root is the pytest test suite location.
- A3: `your_package` already has an `__init__.py`; if it does not, the
  Executor will create one alongside `farewell.py` (no other module exports
  change).
- A4: Python 3.12+ is available (per CLAUDE.md stack).
- A5: `ruff` and `ty` configurations in the repo accept the conventions used
  in `greet.py` (PEP 604 unions, Google- or PEP-257-style docstring) — the
  same conventions apply here.

## Decisions
- D1: `farewell` lives in its own module `src/your_package/farewell.py` rather
  than being added to `__init__.py` or to `greet.py`. Rationale: mirrors the
  `greet` module decision (D1 in `add-greet-module.md`); keeps each module a
  clean, importable unit.
- D2: Empty-string input raises `ValueError`, not a sentinel return. Rationale:
  mirrors `greet` decision D2 — an empty name is a programmer error in this
  contract, not a runtime input to be tolerated.
- D3: Non-string input raises `TypeError`, not coercion via `str(name)`.
  Rationale: mirrors `greet` decision D3 — silent coercion (e.g.,
  `farewell(None)` returning `"Goodbye, None!"`) is a footgun.
- D4: Error messages name the offending parameter (`name`) and describe the
  expected shape. Rationale: mirrors `greet` decision D4 — helpful errors are
  part of the contract, not polish.

## Problem Statement
The `greet` module established the convention for a minimal public function, but
there is no complementary exit function. Add a public function
`farewell(name: str) -> str` returning `"Goodbye, <name>!"` that mirrors
`greet` in validation discipline, typing, docstring, and test coverage.

## Requirements (STRICT)
- [ ] REQ-FAREWELL-01: `farewell(name)` returns the string `"Goodbye, <name>!"`
  when `name` is a non-empty `str`. The exact format includes the comma, the
  space, and the trailing exclamation point.
- [ ] REQ-FAREWELL-02: `farewell("")` raises `ValueError` with a message that
  identifies the parameter as `name` and states that an empty string is not
  permitted.
- [ ] REQ-FAREWELL-03: `farewell(name)` raises `TypeError` when `name` is not
  an instance of `str` (e.g., `None`, `int`, `list`). The message must
  identify the parameter as `name` and state that a `str` was expected,
  including the actual type received.
- [ ] REQ-FAREWELL-04: The `farewell` function has a complete type-annotated
  signature (`name: str`) and an annotated return type (`-> str`).
- [ ] REQ-FAREWELL-05: The `farewell` function has a docstring that contains
  exactly one usage example (e.g., a `>>> farewell("World")` block or an
  `Example:` section showing one call and its expected return value).

## Non-Goals
- [ ] NG1: No locale-, timezone-, or time-of-day-aware farewells. The signature
  is `(name: str) -> str` only.
- [ ] NG2: No internationalization or translation infrastructure.
- [ ] NG3: No changes to `src/your_package/__init__.py`'s public re-exports
  beyond what is necessary for the file to remain importable. (Adding
  `farewell` to `__all__` is explicitly out of scope; callers import from
  `your_package.farewell`.)
- [ ] NG4: No CLI entry point. `farewell` is a library function only.
- [ ] NG5: No logging, telemetry, or observability inside `farewell`. It is a
  pure function.
- [ ] NG6: No async variant.

## Interfaces
**New files:**
- `src/your_package/farewell.py` — defines `def farewell(name: str) -> str: ...`.
- `tests/test_farewell.py` — pytest test module covering all behaviours.

**Public API surface added:**
- `your_package.farewell.farewell(name: str) -> str`

**Behavioural contract:**

| Input                 | Output / Effect                                   |
|-----------------------|---------------------------------------------------|
| `"World"`             | returns `"Goodbye, World!"`                       |
| `""`                  | raises `ValueError` (REQ-FAREWELL-02)             |
| `None`, `42`, `["x"]` | raises `TypeError` (REQ-FAREWELL-03)              |
| `"  "` (whitespace)   | returns `"Goodbye,   !"` (non-empty; see EC1)     |

No existing entrypoints, CLI commands, schemas, or UI surfaces are modified.

## Invariants to Preserve
- [ ] INV1: `just check` (ruff + ty + pytest) remains green after this change.
- [ ] INV2: No new `print()` calls in production code — the function returns;
  it does not print (per CLAUDE.md "Before saying done" #3).
- [ ] INV3: The src-layout convention is preserved (`src/your_package/...`).
- [ ] INV4: No new runtime dependencies are added to `pyproject.toml`. This
  module uses only the standard library.
- [ ] INV5: Red-zone files are not touched (Invariant 7 in AGENTS.md).

## Red-Zone Assessment
- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no

This change creates two new files under `src/your_package/` and `tests/`,
neither of which is on the red-zone list in AGENTS.md. No `pyproject.toml`,
`uv.lock`, `justfile`, `.pre-commit-config.yaml`, `AGENTS.md`, `.claude/`,
`.codex/`, `.github/workflows/`, or `scripts/hooks/` edits are required.

## Test Plan

All tests live in `tests/test_farewell.py`. Each test function's docstring
cites the requirement ID(s) it covers.

- [ ] **T1** → covers REQ-FAREWELL-01, REQ-FAREWELL-04, REQ-FAREWELL-05
  `test_farewell_returns_goodbye_for_non_empty_name`: asserts
  `farewell("World") == "Goodbye, World!"`. The test docstring also asserts
  `farewell.__doc__` is non-empty and contains at least one example marker
  (`>>>` or `Example`) to cover REQ-FAREWELL-05.
- [ ] **T2** → covers REQ-FAREWELL-02
  `test_farewell_raises_value_error_on_empty_string`: uses
  `pytest.raises(ValueError)` on `farewell("")` and asserts the exception
  message mentions `name`.
- [ ] **T3** → covers REQ-FAREWELL-03
  `test_farewell_raises_type_error_on_non_string`: parametrized over
  `[None, 42, 3.14, ["x"], {"a": 1}, b"bytes"]`. Uses
  `pytest.raises(TypeError)` and asserts the exception message mentions
  both `name` and `str`.

All three tests are deterministic (no API calls); no `@pytest.mark.integration`
marker is needed.

## Validation Contract

| Requirement      | Validator                                                                        |
|------------------|----------------------------------------------------------------------------------|
| REQ-FAREWELL-01  | `pytest tests/test_farewell.py::test_farewell_returns_goodbye_for_non_empty_name`   |
| REQ-FAREWELL-02  | `pytest tests/test_farewell.py::test_farewell_raises_value_error_on_empty_string`   |
| REQ-FAREWELL-03  | `pytest tests/test_farewell.py::test_farewell_raises_type_error_on_non_string`      |
| REQ-FAREWELL-04  | `ty` passes against `src/your_package/farewell.py` in `just type`               |
| REQ-FAREWELL-05  | Assertion inside T1 that `farewell.__doc__` contains an example marker           |

All validators are exercised by `just check`.

## Edge Cases
- EC1: Whitespace-only input (`"  "`, `"\n"`) is non-empty; returns
  `"Goodbye,   !"`. This spec does not strip whitespace — that is a UI concern.
- EC2: Very long names. No length limit; memory is the caller's concern.
- EC3: Names containing format specifiers or shell metacharacters. Treated as
  literal strings; no shell execution occurs.
- EC4: Unicode names (`"世界"`, `"🌍"`). Returns the formatted string verbatim.
- EC5: `bool` input. `bool` is a subclass of `int`, not `str`; raises `TypeError`.
- EC6: `str` subclass. `isinstance(name, str)` is `True`; call succeeds.

## Security / Prompt-Injection Review
- source: in-process Python function argument. No MCP tools, web search,
  file reads, network responses, or LLM output.
- risk: low
- mitigation: not required. The function does not interpolate `name` into
  shell commands, SQL, HTML, or LLM prompts. Callers that pass output into
  a sensitive sink are responsible for context-appropriate escaping.

## Observability
None required. The function is pure, synchronous, and in-process; no I/O
boundaries, retries, error rates, or latency properties to capture.

## Rollback / Recovery
Purely additive change — no existing module imports `farewell`. Rollback by
reverting the commit that added `farewell.py` and `test_farewell.py`.

## Implementation Slices
1. **Slice 1 (single commit):** create `src/your_package/farewell.py` and
   `tests/test_farewell.py`. Run `just check`. Open one PR. The change is small
   enough that splitting adds churn without value.

## Done When
- [ ] All requirement IDs REQ-FAREWELL-01 through REQ-FAREWELL-05 satisfied.
- [ ] Decisions D1–D4 preserved, or any deviation noted in the PR with rationale.
- [ ] Tests T1, T2, T3 present with docstrings citing requirement IDs.
- [ ] Validation Contract satisfied: every REQ-FAREWELL-* maps to a passing check.
- [ ] `just check` green locally (ruff + ty + pytest).
- [ ] CI green on the PR branch.
- [ ] Invariants INV1–INV5 hold.
- [ ] Branch name starts with `spec/add-farewell-module` (Invariant 1).
- [ ] PR description links this spec at `docs/specs/add-farewell-module.md`.
- [ ] PR body contains a `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block
  (empty fenced block acceptable until Phase 3 Reviewer lands).
