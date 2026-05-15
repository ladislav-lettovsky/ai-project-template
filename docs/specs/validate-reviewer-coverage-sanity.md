# Reject impossible coverage numbers in validate_reviewer.py

## Metadata

- spec_id: SPEC-20260515-validate-reviewer-coverage-sanity
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/validate-reviewer-coverage-sanity

## Context

`scripts/validate_reviewer.py` is the gate that decides whether the
Reviewer subagent's structured JSON in a PR body is acceptable.
Invariant 5 (AGENTS.md, blueprint §2) says "Reviewer output is structured
JSON, not prose," and this validator is the mechanical tripwire behind
that invariant — it is run by `just validate-reviewer <pr-body-file>` and
by the Phase 4 route-pr CI workflow. Any review that fails validation
routes the PR to `review:human`.

The JSON Schema at `.reviewer-schema.json` constrains the four `coverage`
fields (`requirements_total`, `requirements_covered`, `tests_expected`,
`tests_present`) only to be non-negative integers. JSON Schema cannot
naturally express the cross-field invariants "covered must be ≤ total"
and "present must be ≤ expected" without either custom keywords or the
2020-12 `$data` extension (which `jsonschema`'s `Draft202012Validator`
does not enforce). Consequently, a Reviewer (or a malformed hand-typed
review) can today claim `requirements_covered: 5` against
`requirements_total: 3` and the validator will pass it. That is exactly
the kind of false negative the validator exists to prevent: the Phase 4
Router gates auto-merge on `requirements_covered == requirements_total`,
so a "5 of 3 covered" review would route the PR to auto-merge despite
being internally inconsistent.

This spec adds a small Python-level post-schema check that rejects the
two impossible orderings. It is deliberately scoped — no schema change,
no new fields, no new dependency, no CLI flags — because the schema is a
red-zone file and the validator's responsibility is well-defined.

## Assumptions

- A1: The Reviewer JSON, when it reaches the post-schema check, has
  already been schema-validated. In particular, `coverage` exists as an
  object and all four fields exist as non-negative integers. The
  post-schema check can therefore index them directly without defensive
  fallbacks.
- A2: The two impossible orderings to check are exactly the two named in
  the prompt: `requirements_covered > requirements_total` and
  `tests_present > tests_expected`. The reverse orderings (e.g.,
  `tests_expected > tests_present`) are legitimate ("3 tests planned,
  only 1 shipped"). Equality is legitimate ("all required tests are
  present").
- A3: The `validate(pr_body, schema) -> list[str]` function in
  `scripts/validate_reviewer.py` is the natural integration point. Its
  return contract (empty list = valid; non-empty list of strings = each
  string is one error printed by `main()` to stderr) is the same contract
  the new check returns.
- A4: Error message phrasing follows the example in the prompt:
  `"requirements_covered (5) exceeds requirements_total (3)"`. The pair
  is explicitly named, with both values shown.

## Decisions

- D1: Implement as a separate function
  `check_coverage_consistency(instance: dict) -> list[str]` in
  `scripts/validate_reviewer.py`, following the same return-shape contract
  as `validate(...)`. Rationale: keeps the check independently
  unit-testable and keeps `validate()` a thin orchestrator that runs the
  schema first, then the post-schema check.
- D2: Run the post-schema check **only when schema validation produces
  zero errors**. Rationale: if the schema rejected `coverage` (e.g., a
  field is missing or non-integer), reporting an "impossible ordering"
  error on top would be noise — the schema error is the real cause.
  Failing fast on the first stage is consistent with the existing
  pattern (extraction errors short-circuit the JSON parse step, JSON
  parse errors short-circuit schema validation).
- D3: Do not modify `.reviewer-schema.json`. Rationale: the schema is
  listed under red-zone files (AGENTS.md), and JSON Schema 2020-12 has
  no clean native way to express cross-field comparisons — encoding the
  rule in Python keeps the schema additive-only and the validator
  internally consistent (other behavioral checks like "exactly one fence
  pair" are already Python-side).
- D4: Each impossible ordering produces its own error message. Rationale:
  the two pairs are independent — both can be wrong simultaneously, and
  the human reading the CI failure benefits from seeing both. The
  ordering in the returned list is fixed (`requirements` pair first,
  `tests` pair second) so tests can assert on it without fragility.
- D5: Error message format is exactly
  `"<larger_field> (<larger_value>) exceeds <smaller_field> (<smaller_value>)"`.
  Rationale: the prompt specifies this shape, and it is grep-friendly
  and unambiguous in CI logs.

## Problem Statement

`scripts/validate_reviewer.py` currently passes any Reviewer JSON whose
`coverage` block satisfies the schema's type and minimum constraints,
even when the values are internally impossible:

- `coverage.requirements_covered > coverage.requirements_total` — the
  Reviewer claims more requirements were satisfied than the spec
  contains.
- `coverage.tests_present > coverage.tests_expected` — the Reviewer
  claims more tests are present than the spec's Test Plan declared.

Neither case is rejectable by JSON Schema as written. The validator must
catch them at the Python layer.

## Requirements (STRICT)

- [ ] R1: `scripts/validate_reviewer.py` defines a function
  `check_coverage_consistency(instance: dict) -> list[str]` that returns
  an error-message list (empty list = clean), following the same return
  contract as the existing `validate(...)` function.
- [ ] R2: When `instance["coverage"]["requirements_covered"] >
  instance["coverage"]["requirements_total"]`,
  `check_coverage_consistency` returns a list containing the error
  string `"requirements_covered (<covered>) exceeds requirements_total
  (<total>)"`, with `<covered>` and `<total>` substituted as the actual
  integer values.
- [ ] R3: When `instance["coverage"]["tests_present"] >
  instance["coverage"]["tests_expected"]`,
  `check_coverage_consistency` returns a list containing the error
  string `"tests_present (<present>) exceeds tests_expected
  (<expected>)"`, with `<present>` and `<expected>` substituted as the
  actual integer values.
- [ ] R4: When both impossible orderings hold simultaneously,
  `check_coverage_consistency` returns both error strings in the order
  [requirements-pair, tests-pair].
- [ ] R5: When `requirements_covered == requirements_total` and
  `tests_present == tests_expected` (the all-equal case), and in any
  other case where covered ≤ total and present ≤ expected,
  `check_coverage_consistency` returns `[]`.
- [ ] R6: `validate(pr_body, schema)` runs `check_coverage_consistency`
  only after schema validation succeeds (zero schema errors) and the
  JSON parsed successfully. Its returned errors are appended to the
  overall error list and surface through `main()` to stderr with the
  same `ERROR: <message>` prefix as schema errors. When the schema check
  itself fails, `check_coverage_consistency` is not run.

## Non-Goals

- [ ] NG1: No changes to `.reviewer-schema.json`. The cross-field
  invariants are enforced in Python, not in the schema.
- [ ] NG2: No new CLI flags (`--strict`, `--no-coverage-check`, etc.).
  The check is always on, the same way schema validation is always on.
- [ ] NG3: No changes to the existing error message format for
  schema violations (`"schema violation at <path>: <message>"`). The
  new check uses its own, distinct format (D5).
- [ ] NG4: No additional cross-field checks (e.g., "if `findings`
  contains a `critical` item then `confidence` should be low"). Only
  the two coverage orderings named in the prompt are in scope.
- [ ] NG5: No new dependencies. The check is a few integer comparisons
  in stdlib Python.
- [ ] NG6: No changes to the `extract_json_text` function, the fence
  regexes, or any behavior outside the post-schema stage.

## Interfaces

**Files modified:**

- `scripts/validate_reviewer.py` — adds
  `check_coverage_consistency(instance: dict) -> list[str]` and calls
  it from `validate(pr_body, schema)` after schema validation succeeds.
  No public-API change: the module's documented entrypoints remain
  `extract_json_text`, `validate`, and `main`, with their existing
  signatures.
- `tests/test_validate_reviewer.py` — adds four new test functions
  (see Test Plan). Existing tests must continue to pass unchanged.

No files created. No CLI flags added or changed. No changes to
`.reviewer-schema.json`, `justfile`, `pyproject.toml`, pre-commit
config, or any hook.

## Invariants to Preserve

- [ ] INV1: `just check` (ruff + ty + pytest + lint-changed-specs +
  scan-injection) remains green after this change.
- [ ] INV2: Invariant 5 of AGENTS.md ("Reviewer output is structured
  JSON, not prose") is strengthened, not weakened. Every previously
  accepted-and-valid Reviewer JSON continues to be accepted.
- [ ] INV3: `extract_json_text(pr_body)` and `main(argv)` keep their
  existing signatures and behavior. Only `validate(pr_body, schema)`
  gains additional internal logic; its signature and return contract
  (list of error strings) are unchanged.
- [ ] INV4: Return-code contract of `main()` is preserved: 0 = clean,
  1 = validation errors, 2 = usage errors. The new coverage errors are
  reported under exit code 1, the same as schema errors.
- [ ] INV5: `.reviewer-schema.json` is not modified by this change.
  Invariant 7 ("hooks are tripwires") and the red-zone listing of the
  schema file remain undisturbed.
- [ ] INV6: All existing tests in `tests/test_validate_reviewer.py`
  continue to pass without modification, including
  `test_valid_review_passes` (whose `VALID_REVIEWER_JSON` has all
  coverage values equal to 1 — i.e., satisfies the new check too).

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no

This change edits `scripts/validate_reviewer.py` and
`tests/test_validate_reviewer.py`. Neither is on the red-zone list in
AGENTS.md — the red-zone list covers `.reviewer-schema.json` (which is
explicitly NOT modified, per D3 and NG1) and `scripts/hooks/**` (not
`scripts/*.py`). No `pyproject.toml`, `uv.lock`, `justfile`,
`.pre-commit-config.yaml`, `AGENTS.md`, `.claude/`, `.codex/`,
`.github/workflows/`, or hook edits are required. CI configuration is
untouched; the existing `just check` gate exercises the new tests
without modification.

## Test Plan

All tests live in `tests/test_validate_reviewer.py`. Each builds on the
existing `VALID_REVIEWER_JSON` fixture and the `_wrap` / `_write`
helpers, mutating the coverage block minimally to construct the case
under test.

- [ ] T1 -> covers R2, R6
  `test_coverage_requirements_covered_exceeds_total_fails`: mutate
  `VALID_REVIEWER_JSON` so `coverage.requirements_total = 3` and
  `coverage.requirements_covered = 5`. Call `main([path])`. Assert
  `rc == 1` and that stderr contains the substring
  `"requirements_covered (5) exceeds requirements_total (3)"`.
  Confirms both the error-message shape (R2) and that the check is
  wired into the main code path through `validate()` (R6).
- [ ] T2 -> covers R3, R6
  `test_coverage_tests_present_exceeds_expected_fails`: mutate
  `VALID_REVIEWER_JSON` so `coverage.tests_expected = 2` and
  `coverage.tests_present = 4`. Call `main([path])`. Assert
  `rc == 1` and that stderr contains the substring
  `"tests_present (4) exceeds tests_expected (2)"`. Confirms message
  shape (R3) and wiring (R6).
- [ ] T3 -> covers R1, R5
  `test_coverage_equal_pairs_pass`: mutate `VALID_REVIEWER_JSON` so
  `coverage = {"requirements_total": 2, "requirements_covered": 2,
  "tests_expected": 3, "tests_present": 3}`. Call `main([path])`.
  Assert `rc == 0`. Additionally, import `check_coverage_consistency`
  directly from the validator module and assert it returns `[]` on
  the same instance — confirming the function exists with the declared
  signature (R1) and the equality case is permitted (R5).
- [ ] T4 -> covers R4
  `test_coverage_both_orderings_inverted_reports_both`: mutate
  `VALID_REVIEWER_JSON` so both pairs are impossible:
  `requirements_total=1, requirements_covered=2, tests_expected=1,
  tests_present=2`. Call `main([path])`. Assert `rc == 1` and that
  stderr contains both the `requirements_covered` and `tests_present`
  error substrings, with the requirements error appearing before the
  tests error (D4 ordering).

## Validation Contract

| Requirement | Validator |
| --- | --- |
| R1 | `pytest tests/test_validate_reviewer.py::test_coverage_equal_pairs_pass` |
| R2 | `pytest tests/test_validate_reviewer.py::test_coverage_requirements_covered_exceeds_total_fails` |
| R3 | `pytest tests/test_validate_reviewer.py::test_coverage_tests_present_exceeds_expected_fails` |
| R4 | `pytest tests/test_validate_reviewer.py::test_coverage_both_orderings_inverted_reports_both` |
| R5 | `pytest tests/test_validate_reviewer.py::test_coverage_equal_pairs_pass` |
| R6 | `pytest tests/test_validate_reviewer.py::test_coverage_requirements_covered_exceeds_total_fails` and `pytest tests/test_validate_reviewer.py::test_coverage_tests_present_exceeds_expected_fails` |

All validators are exercised by `just check`.

## Edge Cases

- EC1: All four coverage values are `0`. `0 > 0` is false in both
  comparisons; `check_coverage_consistency` returns `[]`. Legitimate
  "empty spec, empty diff" case is permitted.
- EC2: `requirements_covered == requirements_total` (or
  `tests_present == tests_expected`) — strict inequality only. Equality
  is allowed (R5).
- EC3: Reverse orderings — `requirements_total > requirements_covered`
  (legitimate: "5 requirements, only 3 satisfied"), or
  `tests_expected > tests_present` (legitimate: "4 tests planned, only
  2 shipped"). Returns `[]`. These are the cases where the Phase 4
  Router would correctly *not* route to auto-merge; the validator does
  not need to second-guess them.
- EC4: Schema-invalid coverage (e.g., `requirements_covered` missing,
  negative, or a string). Schema validation reports the error and
  `check_coverage_consistency` is not run (D2). No duplicate or
  confusing error is produced.
- EC5: `coverage` itself missing or non-object. Same as EC4 — schema
  catches it first.
- EC6: Very large values (e.g., `requirements_covered: 10000,
  requirements_total: 0`). Standard integer comparison; error is
  produced with the actual large values rendered into the message.
- EC7: A `coverage` key with an unexpected extra field (e.g.,
  `coverage.bonus_field`). The schema does not set
  `additionalProperties: false`, so the extra is accepted (consistent
  with `test_extra_field_is_accepted`). The new check ignores the
  extra and operates on the four known fields.

## Security / Prompt-Injection Review

- source: in-process Python function arguments. `check_coverage_consistency`
  consumes a dict that was parsed from a PR-body file (which itself
  came from `gh pr view` or a local file). The dict has already been
  validated against `.reviewer-schema.json`, so every field consumed by
  this check is a Python `int`. No MCP tools, no web search, no LLM
  output is consumed.
- risk: low
- mitigation: not required. The check performs only integer comparisons
  and string formatting; it does not exec, eval, shell-out, or pass
  any value back to an LLM. The error messages are emitted to stderr
  by `main()`, not interpreted further.

## Observability

None required. The validator is a one-shot CLI tool; errors go to
stderr, exit code goes to `just check` / the Phase 4 route-pr CI
workflow. No structured logging or telemetry is added — the rest of
the validator is silent on success and prints `ERROR: <message>` on
failure, and this change follows that convention exactly.

## Rollback / Recovery

Purely additive change to a validator. Rollback by reverting the
commit that adds `check_coverage_consistency` and the three tests. No
PR body content needs to be rewritten on rollback because every
Reviewer JSON that was valid before this change remains valid after
(INV2, INV6). After rollback, the only behavior loss is that
impossible coverage orderings would once again pass — i.e., the state
before this spec.

## Implementation Slices

1. **Slice 1 (single commit):** Add
   `check_coverage_consistency(instance: dict) -> list[str]` to
   `scripts/validate_reviewer.py`, call it from `validate(pr_body,
   schema)` after schema validation succeeds (and only then), and
   append its errors to the returned list. Add tests T1–T4 in
   `tests/test_validate_reviewer.py`. Run `just check`. Confirm every
   existing test continues to pass and the four new tests pass.

## Done When

- [ ] All requirement IDs R1–R6 satisfied.
- [ ] Decisions D1–D5 preserved, or any deviation noted in the PR.
- [ ] Tests T1–T4 present in `tests/test_validate_reviewer.py` with
  docstrings citing requirement IDs.
- [ ] Validation Contract satisfied: every R* maps to a passing test.
- [ ] `just check` green locally.
- [ ] CI green on the PR branch.
- [ ] Invariants INV1–INV6 hold; `.reviewer-schema.json` is unchanged;
  every previously passing Reviewer JSON example continues to pass.
- [ ] Branch name starts with `spec/validate-reviewer-coverage-sanity`.
- [ ] PR description links this spec.
- [ ] PR body contains a `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block.
