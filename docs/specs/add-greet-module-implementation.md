# Implement `greet` module (add-greet-module)

## Metadata

- spec_id: SPEC-20260513-add-greet-module-implementation
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/add-greet-module-implementation

## Context

The design and contract for the canonical `greet` worked example are already
specified in `docs/specs/add-greet-module.md`. That document is the authority
for semantics, requirement IDs, and acceptance criteria. This spec exists
because the implementation files were never landed: `src/your_package/greet.py`
and `tests/test_greet.py` are still missing while the template and docs refer
to greet as the primary example.

The Executor implements **only** what this spec and the parent spec require.
Structural patterns (validation order, docstring shape, test layout) should
match `src/your_package/farewell.py` and `tests/test_farewell.py` so the
package has two consistent minimal modules. Ambiguous interpretation defers
to `docs/specs/add-greet-module.md`.

## Assumptions

- A1: The package layout is `src/your_package/` (src layout, per CLAUDE.md
  "Where things live").
- A2: `tests/` at the repo root is the pytest test suite location.
- A3: `your_package` already has an importable `__init__.py`; this work does
  not modify it (see NG3 and Interfaces).
- A4: Python 3.12+ is available (per CLAUDE.md stack).
- A5: `ruff` and `ty` configurations in the repo accept the conventions used
  here (PEP 604 unions, `from __future__ import annotations` not required,
  Google- or PEP-257-style docstring).
- A6: If anything in this implementation spec conflicts with
  `docs/specs/add-greet-module.md`, the parent spec wins.

## Decisions

- D1: `greet` lives in its own module `src/your_package/greet.py` rather than
  being added to `__init__.py`. Rationale: keeps the module a clean,
  importable unit and makes future extensions (e.g., locale-aware greetings)
  straightforward without churn in `__init__.py`.
- D2: Empty-string input raises `ValueError`, not a sentinel return.
  Rationale: an empty greeter name is a programmer error in this contract,
  not a runtime input to be tolerated. Failing loudly preserves the
  precondition.
- D3: Non-string input raises `TypeError`, not coercion via `str(name)`.
  Rationale: silent coercion (e.g., `greet(None)` returning
  `"Hello, None!"`) is a footgun. The signature is typed `str`; runtime
  enforcement matches the type annotation.
- D4: The error messages name the offending parameter (`name`) and describe
  the expected shape, so the caller can fix the call without reading the
  source. Rationale: helpful errors are part of the contract, not polish.

## Problem Statement

`docs/specs/add-greet-module.md` defines `greet(name: str) -> str` and the
required tests, but `src/your_package/greet.py` and `tests/test_greet.py` do
not exist. The repository cannot serve as a complete worked example until
those files are added. This work lands the implementation without changing the
requirement text or redesigning behaviour.

## Requirements (STRICT)

- [ ] REQ-GREET-01: `greet(name)` returns the string `"Hello, <name>!"` when
  `name` is a non-empty `str`. The exact format includes the comma, the
  space, and the trailing exclamation point.
- [ ] REQ-GREET-02: `greet("")` raises `ValueError` with a message that
  identifies the parameter as `name` and states that an empty string is not
  permitted.
- [ ] REQ-GREET-03: `greet(name)` raises `TypeError` when `name` is not an
  instance of `str` (e.g., `None`, `int`, `list`). The message must identify
  the parameter as `name` and state that a `str` was expected, including the
  actual type received.
- [ ] REQ-GREET-04: The `greet` function has a complete type-annotated
  signature (`name: str`) and an annotated return type (`-> str`).
- [ ] REQ-GREET-05: The `greet` function has a docstring that contains
  exactly one usage example (e.g., a `>>> greet("World")` block or an
  `Example:` section showing one call and its expected return value).

## Non-Goals

- [ ] NG1: No locale-, timezone-, or time-of-day-aware greetings (no
  "Good morning" variants). The signature is `(name: str) -> str` only.
- [ ] NG2: No internationalization or translation infrastructure.
- [ ] NG3: No changes to `src/your_package/__init__.py`'s public re-exports
  beyond what is necessary for the file to remain importable. (Adding
  `greet` to `__all__` is explicitly out of scope; callers import from
  `your_package.greet`.)
- [ ] NG4: No CLI entry point. `greet` is a library function only.
- [ ] NG5: No logging, telemetry, or observability inside `greet`. It is a
  pure function.
- [ ] NG6: No async variant.

## Interfaces

**New files:**

- `src/your_package/greet.py` — defines `def greet(name: str) -> str: ...`.
  Mirror the structure of `src/your_package/farewell.py` (module docstring,
  `isinstance(name, str)` then empty-string check, typed errors, formatted
  return string per REQ-GREET-01).
- `tests/test_greet.py` — pytest module mirroring `tests/test_farewell.py`
  (module docstring, `inspect.signature` assertions, single `Example:` and
  `>>>`, parametrized non-`str` cases with `typing.cast` for the call).

**Explicitly out of scope for file edits:**

- `src/your_package/__init__.py` — do not modify.

**Public API surface added:**

- `your_package.greet.greet(name: str) -> str`

**Behavioural contract:**

| Input                 | Output / Effect                               |
|-----------------------|-----------------------------------------------|
| `"World"`             | returns `"Hello, World!"`                     |
| `""`                  | raises `ValueError` (REQ-GREET-02)            |
| `None`, `42`, `["x"]` | raises `TypeError` (REQ-GREET-03)             |
| `"  "` (whitespace)   | returns `"Hello,   !"` (non-empty; see EC1)   |

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

All tests live in `tests/test_greet.py`. Each test function's docstring cites
the requirement ID(s) it covers.

- [ ] **T1** → covers REQ-GREET-01, REQ-GREET-04, REQ-GREET-05
  `test_greet_returns_hello_for_non_empty_name`: asserts
  `greet("World") == "Hello, World!"`. The test docstring also asserts
  `greet.__doc__` is non-empty and contains at least one example marker
  (`>>>` or `Example`) to cover REQ-GREET-05.
- [ ] **T2** → covers REQ-GREET-02
  `test_greet_raises_value_error_on_empty_string`: uses
  `pytest.raises(ValueError)` on `greet("")` and asserts the exception
  message mentions `name`.
- [ ] **T3** → covers REQ-GREET-03
  `test_greet_raises_type_error_on_non_string`: parametrized over
  `[None, 42, 3.14, ["x"], {"a": 1}, b"bytes"]`. Uses
  `pytest.raises(TypeError)` and asserts the exception message mentions
  both `name` and `str`.

All three tests are deterministic (no API calls); no `@pytest.mark.integration`
marker is needed.

## Validation Contract

| Requirement | Validator |
| --- | --- |
| REQ-GREET-01 | `pytest tests/test_greet.py::test_greet_returns_hello_for_non_empty_name` |
| REQ-GREET-02 | `pytest tests/test_greet.py::test_greet_raises_value_error_on_empty_string` |
| REQ-GREET-03 | `pytest tests/test_greet.py::test_greet_raises_type_error_on_non_string` |
| REQ-GREET-04 | `ty` passes against `src/your_package/greet.py` in `just type` |
| REQ-GREET-05 | Assertion inside T1 that `greet.__doc__` contains an example marker |

All validators are exercised by `just check`.

## Edge Cases

- EC1: Whitespace-only input (`"  "`, `"\n"`) is non-empty; returns `"Hello,   !"`.
  This spec does not strip whitespace — that is a UI concern.
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

Purely additive change — no existing module imports `greet`. Rollback by
reverting the commit that added `greet.py` and `test_greet.py`.

## Implementation Slices

1. **Slice 1 (single commit):** Add `src/your_package/greet.py` and
   `tests/test_greet.py`, mirroring `farewell.py` / `test_farewell.py` as
   described under Interfaces, satisfying REQ-GREET-01 through REQ-GREET-05.
   Do not edit `__init__.py`. Run `just check`. Open one PR linking this spec;
   the PR may also reference `docs/specs/add-greet-module.md` for design
   history.

## Done When

- [ ] All requirement IDs REQ-GREET-01 through REQ-GREET-05 satisfied.
- [ ] Decisions D1–D4 preserved, or any deviation noted in the PR with rationale.
- [ ] Tests T1, T2, T3 present with docstrings citing requirement IDs.
- [ ] Validation Contract satisfied: every REQ-GREET-* maps to a passing check.
- [ ] `just check` green locally (ruff + ty + pytest).
- [ ] CI green on the PR branch.
- [ ] Invariants INV1–INV5 hold.
- [ ] Branch name starts with `spec/add-greet-module-implementation` (Invariant 1).
- [ ] PR description links this spec at `docs/specs/add-greet-module-implementation.md`.
- [ ] PR body contains a `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block
  (empty fenced block acceptable until Phase 3 Reviewer lands).
