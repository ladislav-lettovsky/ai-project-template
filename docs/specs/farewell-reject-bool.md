# Reject `bool` input in `farewell` (regression guard)

## Metadata

- spec_id: SPEC-20260514-farewell-reject-bool
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/farewell-reject-bool

## Context

`docs/specs/add-farewell-module.md` lists Edge Case EC5: "`bool` input. `bool`
is a subclass of `int`, not `str`; raises `TypeError`." The current
implementation in `src/your_package/farewell.py` already satisfies this — the
`isinstance(name, str)` guard rejects `True` and `False` because `bool`
inherits from `int`, not `str`. However, the parametrized test
`test_farewell_raises_type_error_on_non_string` in `tests/test_farewell.py`
covers `None`, `int`, `float`, `list`, `dict`, and `bytes` but does not include
`True` or `False`. The edge case is documented but unguarded by a test.

A future refactor changing the guard from `isinstance(name, str)` to, say,
`if name is None or isinstance(name, (int, float, list, dict, bytes))` — or to
a duck-typed `try: name + ""` check — could silently start accepting `True` /
`False` and returning `"Goodbye, True!"`. Stringifying booleans is a classic
Python footgun and the documented contract forbids it. This spec adds the
regression guard.

## Assumptions

- A1: The current implementation in `src/your_package/farewell.py` already
  raises `TypeError` for `farewell(True)` and `farewell(False)` via its
  `isinstance(name, str)` check. The Executor will verify this by running the
  new parametrized test cases before considering any implementation change.
- A2: `bool` is a subclass of `int` in Python (`issubclass(bool, int) is True`)
  and not a subclass of `str` (`issubclass(bool, str) is False`). No
  Python-version-specific gating is required for the project's Python 3.12+
  baseline.
- A3: The existing parametrized test `test_farewell_raises_type_error_on_non_string`
  is the correct location for the new cases — it already covers REQ-FAREWELL-03
  and the same requirement governs `bool` rejection.
- A4: No new test file is needed; extending the existing `@pytest.mark.parametrize`
  list is the minimal change.

## Decisions

- D1: Extend the existing `@pytest.mark.parametrize` list in
  `test_farewell_raises_type_error_on_non_string` to include `True` and `False`,
  rather than adding a separate test function. Rationale: `bool` rejection is the
  same behavioural contract as `None` / `int` / `float` rejection (REQ-FAREWELL-03);
  parametrization is the existing idiom in this file.
- D2: Do not edit `src/your_package/farewell.py`. Rationale: the implementation
  already behaves correctly (A1). Editing production code without a behaviour
  change adds review surface for no observable benefit.
- D3: Reuse the existing exception assertion regex `"name.*str.*got"`. The
  implementation message `f"name must be a str, got {type(name).__name__}"` yields
  `"name must be a str, got bool"` for both `True` and `False`, which already
  matches. No new error-message contract is needed.
- D4: If the test unexpectedly fails on the existing implementation (i.e., the
  Executor finds `farewell(True)` returns `"Goodbye, True!"` rather than raising),
  the Executor STOPS and re-routes via a clarifying PR comment. The spec authorises
  test-only work; production-code edits are out of scope by D2.

## Problem Statement

`tests/test_farewell.py` has no test case asserting that `farewell(True)` or
`farewell(False)` raises `TypeError`. The contract in
`docs/specs/add-farewell-module.md` (REQ-FAREWELL-03 plus EC5) requires this
behaviour. The production code satisfies it today via `isinstance(name, str)`,
but a future guard refactor could silently regress and start returning
stringified-bool farewells. A deterministic test pins down the documented edge
case.

## Requirements (STRICT)

- [ ] R1: `tests/test_farewell.py::test_farewell_raises_type_error_on_non_string`
  is parametrized to include `True` as one of the inputs, and asserts that
  `farewell(True)` raises `TypeError` whose message matches the regex
  `"name.*str.*got"`.
- [ ] R2: `tests/test_farewell.py::test_farewell_raises_type_error_on_non_string`
  is parametrized to include `False` as one of the inputs, and asserts that
  `farewell(False)` raises `TypeError` whose message matches the regex
  `"name.*str.*got"`.
- [ ] R3: `src/your_package/farewell.py` is unchanged by this PR. The Executor
  confirms this by running `git diff --name-only origin/main..HEAD` before
  declaring done; the output must not include `src/your_package/farewell.py`.

## Non-Goals

- [ ] NG1: No change to `src/your_package/farewell.py`'s implementation,
  signature, docstring, or error messages.
- [ ] NG2: No change to existing test cases in
  `test_farewell_raises_type_error_on_non_string` — the current parameter list
  (`None`, `42`, `3.14`, `["x"]`, `{"a": 1}`, `b"bytes"`) is preserved verbatim;
  `True` and `False` are appended.
- [ ] NG3: No new test functions. The change is purely an extension of the
  existing parametrized list.
- [ ] NG4: No new edge cases beyond `bool`. Other subclass-of-a-non-string-builtin
  cases (e.g., `IntEnum` members, `numpy.bool_`) are out of scope.
- [ ] NG5: No edit to `docs/specs/add-farewell-module.md`. EC5 there already
  documents the behaviour; this spec adds the test, not the documentation.

## Interfaces

Files modified:

- `tests/test_farewell.py` — the `@pytest.mark.parametrize` decorator on
  `test_farewell_raises_type_error_on_non_string` gains two new parameters:
  `True` and `False`.

Files created:

- `docs/specs/farewell-reject-bool.md` (this spec).

Files NOT modified:

- `src/your_package/farewell.py` — see R3 and D2.

Behavioural contract (unchanged by this PR, asserted by new tests):
both `farewell(True)` and `farewell(False)` raise `TypeError` with message
`"name must be a str, got bool"`.

## Invariants to Preserve

- [ ] INV1: `just check` (ruff + ty + pytest + lint-changed-specs + scan-injection)
  remains green after this change.
- [ ] INV2: No new runtime or dev dependencies (per AGENTS.md red-zone protection
  of `pyproject.toml` dependency sections).
- [ ] INV3: `src/your_package/farewell.py` is byte-identical before and after
  this PR (R3 / D2).
- [ ] INV4: The existing six parameter cases in
  `test_farewell_raises_type_error_on_non_string` continue to pass — the new
  `True` / `False` cases are appended, not substituted.
- [ ] INV5: REQ-FAREWELL-03 from `docs/specs/add-farewell-module.md` continues
  to hold; this spec strengthens its test coverage, it does not replace it.
- [ ] INV6: Red-zone files are not touched (AGENTS.md Invariant 7) — this PR
  edits only `tests/test_farewell.py` plus this spec file, neither of which is
  in the red-zone list.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no

This PR adds two parameters to an existing parametrized test and creates this
spec file. No red-zone path is touched. `risk_tier: T0` is appropriate:
test-only addition, no production code change, rolls back by reverting one
commit.

## Test Plan

All tests live in `tests/test_farewell.py`. The change is to the existing
parametrized test; the test function name is unchanged.

- [ ] T1 -> covers R1. `test_farewell_raises_type_error_on_non_string[True]`
  asserts `pytest.raises(TypeError, match="name.*str.*got")` with `name=True`.
- [ ] T2 -> covers R2. `test_farewell_raises_type_error_on_non_string[False]`
  asserts `pytest.raises(TypeError, match="name.*str.*got")` with `name=False`.
- [ ] T3 -> covers R3. The Executor runs `git diff --name-only origin/main..HEAD`
  after committing and confirms `src/your_package/farewell.py` does not appear
  in the output. Verified manually before declaring the slice done.

All cases are deterministic; no `@pytest.mark.integration` marker is needed.

## Validation Contract

- R1 -> `pytest "tests/test_farewell.py::test_farewell_raises_type_error_on_non_string[True]"`
- R2 -> `pytest "tests/test_farewell.py::test_farewell_raises_type_error_on_non_string[False]"`
- R3 -> `git diff --name-only origin/main..HEAD` must not list `src/your_package/farewell.py`

All pytest validators run inside `just check`. R3's diff-shape check is
verified by the Executor manually and is visible in the PR diff.

## Edge Cases

- EC1: `True` and `False` are the only two `bool` instances in Python; no third
  value to test.
- EC2: `numpy.bool_(True)` would still be rejected by `isinstance(name, str)`,
  but `numpy` is not a project dependency and this case is out of scope (NG4).
- EC3: A `bool`-like custom class that does subclass `str` (e.g.,
  `class Truthy(str): ...`) would be accepted by the guard. This is consistent
  with EC6 (`str` subclass) in `docs/specs/add-farewell-module.md` and is out
  of scope here.
- EC4: If a future PR rewrites the guard to `if type(name) is not str`, then
  `str` subclasses would start raising `TypeError` — that would regress EC6,
  not this spec. `True` / `False` are not `str` subclasses, so T1 and T2 would
  still pass.

## Security / Prompt-Injection Review

- source: in-process Python function argument inside a pytest test case. No MCP
  tools, web search, external docs, file reads, network responses, LLM output,
  or user input.
- risk: low
- mitigation: not required.

## Observability

None required. The change is a deterministic, in-process pytest parametrization;
no logs, metrics, traces, or telemetry are added or relied on.

## Rollback / Recovery

Purely additive test change. Roll back by reverting the single commit that adds
the two parametrized cases and this spec. No data, schema, migration, or
production-code impact.

## Implementation Slices

1. Slice 1 (single commit): append `True` and `False` to the
   `@pytest.mark.parametrize` list in
   `tests/test_farewell.py::test_farewell_raises_type_error_on_non_string`.
   Run `just check`. If both new cases pass, the PR ships as-is. If either
   fails, STOP per D4 and re-route via a clarifying PR comment — do NOT edit
   `src/your_package/farewell.py` under this spec.

## Done When

- [ ] R1, R2, R3 satisfied.
- [ ] Decisions D1–D4 preserved, or any deviation noted in the PR with rationale.
- [ ] `tests/test_farewell.py` contains `True` and `False` in the parametrized
  list of `test_farewell_raises_type_error_on_non_string`.
- [ ] `src/your_package/farewell.py` is unchanged (`git diff` against `main`
  shows no edits to that file).
- [ ] `just check` green locally (ruff + ty + pytest + lint-changed-specs +
  scan-injection).
- [ ] CI green on the PR branch.
- [ ] Invariants INV1–INV6 hold.
- [ ] Branch name starts with `spec/farewell-reject-bool` (Invariant 1).
- [ ] PR description links this spec at `docs/specs/farewell-reject-bool.md`.
- [ ] PR body contains a `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->`
  block (empty fenced block acceptable until Phase 3 Reviewer lands).
