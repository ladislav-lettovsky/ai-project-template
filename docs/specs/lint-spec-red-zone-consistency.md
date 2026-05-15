# Enforce risk_tier / Red-Zone consistency in lint_spec.py

## Metadata

- spec_id: SPEC-20260515-lint-spec-red-zone-consistency
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/lint-spec-red-zone-consistency

## Context

The blueprint and the spec template both state the same rule in prose: if
any line under `## Red-Zone Assessment` is `yes`, the spec cannot ship as
`risk_tier: T0`. The template repeats this immediately under the Red-Zone
block ("Any `yes` answer means this work cannot ship as `risk_tier: T0`,
regardless of diff size."), and `docs/blueprint.md` step 6 of the Planner
guidance says the same thing.

`scripts/lint_spec.py` already parses both ends of this rule — `risk_tier`
is validated against the `T0/T1/T2/T3` enum in `check_metadata`, and the
Red-Zone Assessment body is one of the sections that `split_sections`
extracts — but the cross-field consistency check is missing. A spec that
declares `risk_tier: T0` while marking `auth: yes` (or any other red-zone
flag) lints clean today. That defeats the tripwire: the rule that exists
to keep consequential work off the auto-merge path is enforced only by
human attention.

This spec adds the missing mechanical check so the rule is enforced the
same way the rest of §5.1 is — by `scripts/lint_spec.py`, gated by
`just check`, gated by CI.

## Assumptions

- A1: The Red-Zone Assessment section bullets follow the template shape
  `- <key>: yes|no`, with optional leading/trailing whitespace and
  case-insensitive values. This shape is used by every committed spec
  (e.g., `docs/specs/add-greet-module.md`).
- A2: The set of red-zone keys is documented in `docs/specs/_template.md`
  but is not authoritative for this check. The linter only needs to
  detect "at least one line says yes," not validate the key list.
- A3: `parse_metadata` already returns `risk_tier` as a plain string
  (e.g., `"T0"`), per the existing `META_LINE_RE` capture. No changes to
  the metadata parser are required.
- A4: The linter remains stdlib-only and line-oriented (per the module
  docstring's design notes). No new dependencies, no markdown AST.

## Decisions

- D1: Add a new top-level check function
  `check_redzone_tier_consistency(metadata: dict[str, str], redzone_body: str) -> list[str]`,
  following the shape of the existing `check_metadata(metadata)` helper.
  Rationale: keeps every individual check independently unit-testable
  and keeps `lint_spec()` a thin orchestrator.
- D2: Multiple `yes` lines produce a single combined error that names
  every offending key, not one error per `yes` line. Rationale: it is a
  single policy violation ("this should not be T0"), not N independent
  violations. A combined message is simpler to assert against in tests
  and reads better in CI output. The message still names each offending
  key so the human gets the full picture.
- D3: The Red-Zone parsing logic lives inside
  `check_redzone_tier_consistency`, not in a separate
  `parse_redzone(body)` helper. Rationale: nothing else in the linter
  consumes the Red-Zone body today, and Non-Goal NG2 explicitly excludes
  any other parsing purpose. A dedicated parser would be speculative.
- D4: Value matching is case-insensitive for `yes`/`no` (template uses
  lowercase; a stray `Yes` should still trip the check). Keys are
  preserved verbatim in the error message so the human sees the exact
  text from the spec.
- D5: Lines that are not in the `- key: yes|no` shape are ignored. The
  Red-Zone section sometimes contains a trailing prose paragraph (see
  `add-greet-module.md`) and an explanatory blockquote. Treating those
  as parse failures would force every spec to delete prose it currently
  has.
- D6: The check fires only when `risk_tier` is exactly `T0`. T1/T2/T3
  specs with red-zone `yes` lines are intentionally allowed — the rule
  is about T0 eligibility, not about whether red-zone work is permitted
  at all.

## Problem Statement

`scripts/lint_spec.py` does not enforce the cross-field rule that a spec
with `risk_tier: T0` must have every Red-Zone Assessment line set to
`no`. Today a spec that declares `risk_tier: T0` while marking
`auth: yes` lints clean — the rule exists only as prose in the template
and the blueprint, with no mechanical tripwire.

Concretely, in the current `lint_spec()` (lines 268–291), the Red-Zone
section is split out by `split_sections(text)` and made available as
`sections.get("Red-Zone Assessment", "")`, but no check ever reads it.

## Requirements (STRICT)

- [ ] R1: `scripts/lint_spec.py` defines a new function
  `check_redzone_tier_consistency(metadata: dict[str, str], redzone_body: str) -> list[str]`
  that returns an error-message list (empty list = clean), following the
  same shape and return contract as `check_metadata`.
- [ ] R2: When `metadata["risk_tier"]` is `"T0"` AND at least one line in
  `redzone_body` matches the pattern `- <key>: yes` (case-insensitive on
  the value), `check_redzone_tier_consistency` returns exactly one error
  message. The message names every offending key in the order they
  appear in `redzone_body` and explicitly states that the spec cannot
  ship as `risk_tier: T0`.
- [ ] R3: When `metadata["risk_tier"]` is `"T1"`, `"T2"`, or `"T3"`,
  `check_redzone_tier_consistency` returns `[]` regardless of how many
  red-zone lines are `yes`. The rule is about T0 eligibility only.
- [ ] R4: When `metadata["risk_tier"]` is `"T0"` AND every red-zone line
  is `no` (or the section contains only prose),
  `check_redzone_tier_consistency` returns `[]`.
- [ ] R5: `lint_spec(path)` invokes `check_redzone_tier_consistency` with
  the parsed metadata and the body of the `## Red-Zone Assessment`
  section, and appends its errors to the overall error list, in the same
  way other checks are wired in today.

## Non-Goals

- [ ] NG1: No change to which values are allowed on Red-Zone lines.
  Enforcing that values must be exactly `yes` or `no` (vs.
  `maybe`/`tbd`/blank) is out of scope; that is a human-review concern.
- [ ] NG2: No parsing of the Red-Zone Assessment section for any purpose
  beyond this T0-consistency check. No reusable
  `parse_redzone(body)` helper, no enumeration of keys, no validation
  that every canonical key is present.
- [ ] NG3: No new CLI flag (`--strict`, `--no-redzone-check`, etc.). The
  check is always on, the same way every other check in `lint_spec.py`
  is always on.
- [ ] NG4: No changes to the spec template, the blueprint, or
  `docs/specs/README.md`. The prose is already correct; only the
  enforcement is missing.
- [ ] NG5: No changes to the `risk_tier` enum or `complexity` enum.
- [ ] NG6: No changes to existing committed specs. Both
  `docs/specs/add-greet-module.md` and the synthetic
  `_minimal_valid_spec()` already pass this rule (T0 + all `no`).

## Interfaces

**Files modified:**

- `scripts/lint_spec.py` — adds
  `check_redzone_tier_consistency(metadata, redzone_body) -> list[str]`
  and wires it into `lint_spec(path)`. No public-API change; the
  module's only documented entrypoints are `lint_spec(path)` and
  `main(argv)`, and both keep their signatures.
- `tests/test_lint_spec.py` — adds four new test functions (see Test
  Plan).

No files created. No CLI flags added or changed. No changes to
`justfile`, `pyproject.toml`, or pre-commit config.

## Invariants to Preserve

- [ ] INV1: `just check` (ruff + ty + pytest + lint-changed-specs +
  scan-injection) remains green after this change.
- [ ] INV2: Every committed spec under `docs/specs/` continues to lint
  clean. In particular `docs/specs/add-greet-module.md` (T0 + all `no`)
  and this spec itself (T0 + all `no`) must pass.
- [ ] INV3: The linter remains stdlib-only and line-oriented (per the
  module docstring's design notes). No new dependencies; no markdown AST.
- [ ] INV4: `lint_spec(path)` and `main(argv)` keep their existing
  signatures and return-code contract (0 = clean, 1 = errors, 2 = usage).
- [ ] INV5: No red-zone files (per AGENTS.md) are touched. This change
  modifies only `scripts/lint_spec.py` (not a red-zone path) and
  `tests/test_lint_spec.py`.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no

This change edits `scripts/lint_spec.py` and `tests/test_lint_spec.py`.
Neither is on the red-zone list in AGENTS.md (the red-zone list covers
`scripts/hooks/**` but not `scripts/*.py`). No `pyproject.toml`,
`uv.lock`, `justfile`, `.pre-commit-config.yaml`, `AGENTS.md`,
`.claude/`, `.codex/`, `.github/workflows/`, or hook edits are required.

## Test Plan

All tests live in `tests/test_lint_spec.py`. Each builds on the existing
`_minimal_valid_spec()` fixture (which is already T0 + all `no`) and
mutates it minimally to construct the case under test.

- [ ] T1 -> covers R1, R4
  `test_redzone_check_clean_for_t0_all_no`: the unmodified
  `_minimal_valid_spec()` already has `risk_tier: T0` and every red-zone
  line set to `no`. Assert `lint_spec(path)` returns `[]`. Also calls
  `check_redzone_tier_consistency` directly with a synthetic metadata
  dict and Red-Zone body to confirm the function exists, has the
  declared signature, and returns `[]` for the all-no case.
- [ ] T2 -> covers R3
  `test_redzone_check_allows_t1_with_yes`: mutate the fixture to set
  `risk_tier: T1` and flip `- auth: no` to `- auth: yes`. Assert
  `lint_spec(path)` returns no error mentioning Red-Zone or `risk_tier`.
  Parametrize over `T1`, `T2`, `T3`.
- [ ] T3 -> covers R2, R5
  `test_redzone_check_errors_for_t0_with_yes`: mutate the fixture to
  flip `- auth: no` to `- auth: yes` (leaving `risk_tier: T0`). Assert
  `lint_spec(path)` returns at least one error that mentions `T0`,
  `auth`, and the words `Red-Zone`. Confirms both message content (R2)
  and that `lint_spec` wires the check in (R5).
- [ ] T4 -> covers R2
  `test_redzone_check_combines_multiple_yes_into_one_error`: flip three
  red-zone lines to `yes` (e.g., `auth`, `CI`, `secrets`). Assert that
  `lint_spec(path)` returns exactly **one** Red-Zone/T0 consistency
  error, and that the single error names all three keys.

## Validation Contract

| Requirement | Validator |
| --- | --- |
| R1 | `pytest tests/test_lint_spec.py::test_redzone_check_clean_for_t0_all_no` |
| R2 | `pytest tests/test_lint_spec.py::test_redzone_check_errors_for_t0_with_yes` and `pytest tests/test_lint_spec.py::test_redzone_check_combines_multiple_yes_into_one_error` |
| R3 | `pytest tests/test_lint_spec.py::test_redzone_check_allows_t1_with_yes` |
| R4 | `pytest tests/test_lint_spec.py::test_redzone_check_clean_for_t0_all_no` |
| R5 | `pytest tests/test_lint_spec.py::test_redzone_check_errors_for_t0_with_yes` |

All validators are exercised by `just check`.

## Edge Cases

- EC1: Red-Zone line with mixed-case value, e.g. `- auth: Yes`. Treated
  as `yes` (D4, case-insensitive matching). A spec author who capitalises
  is still flagged.
- EC2: Red-Zone line with extra whitespace, e.g. `-   auth :   yes`
  with trailing spaces after `yes`. Parsed correctly; flagged.
- EC3: Red-Zone section containing trailing prose or a blockquote (as in
  the template). Non-bullet lines are ignored (D5); prose does not cause
  a spurious error.
- EC4: Red-Zone section completely missing. `check_required_sections`
  already emits a "missing required section" error. The new check sees
  an empty body, finds no `yes` lines, and returns `[]` — no duplicate
  error.
- EC5: `risk_tier` missing or set to an unknown value. `check_metadata`
  already reports that. The new check returns `[]` in that case to avoid
  amplifying errors.
- EC6: Red-Zone line with an unknown key (e.g. `- pii: yes`). Counts as
  a `yes` and trips the check for a T0 spec (NG2 — key list not
  validated here).
- EC7: A Red-Zone-shaped line inside a fenced code block. The
  line-oriented parser does not understand fences and would match it.
  This is acceptable: no committed spec embeds Red-Zone-shaped examples
  inside code fences, and every other linter section has the same
  limitation.

## Security / Prompt-Injection Review

- source: in-process Python function arguments. The check reads a
  metadata dict (already parsed from the spec file) and the Red-Zone
  section body (a string from the same file). No MCP tools, web search,
  network responses, or LLM output.
- risk: low
- mitigation: not required. The check returns a list of strings; it does
  not exec, eval, shell-out, or pass any value to an LLM.

## Observability

None required. The linter is a one-shot CLI tool; errors go to stderr,
exit code goes to `just check` / CI.

## Rollback / Recovery

Purely additive change to a linter. Rollback by reverting the commit
that adds `check_redzone_tier_consistency` and its tests. No committed
specs need to be rewritten on rollback because every committed spec
already satisfies the new rule.

## Implementation Slices

1. **Slice 1 (single commit):** Add
   `check_redzone_tier_consistency(metadata, redzone_body)` to
   `scripts/lint_spec.py`, wire it into `lint_spec(path)` after
   `check_metadata`, and add tests T1–T4 in
   `tests/test_lint_spec.py`. Run `just check`. Confirm
   `docs/specs/add-greet-module.md` and this spec still lint clean.

## Done When

- [ ] All requirement IDs R1–R5 satisfied.
- [ ] Decisions D1–D6 preserved, or any deviation noted in the PR.
- [ ] Tests T1–T4 present in `tests/test_lint_spec.py` with docstrings
  citing requirement IDs.
- [ ] Validation Contract satisfied: every R* maps to a passing test.
- [ ] `just check` green locally.
- [ ] CI green on the PR branch.
- [ ] Invariants INV1–INV5 hold; both `docs/specs/add-greet-module.md`
  and this spec lint clean.
- [ ] Branch name starts with `spec/lint-spec-red-zone-consistency`.
- [ ] PR description links this spec.
- [ ] PR body contains a `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block.
