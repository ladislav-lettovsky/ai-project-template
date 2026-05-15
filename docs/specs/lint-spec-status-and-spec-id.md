# Lint spec `status` and `spec_id` frontmatter validation

## Metadata

- spec_id: SPEC-20260515-lint-spec-status-and-spec-id
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T1
- repo: ai-project-template
- branch: spec/lint-spec-status-and-spec-id

## Context

`docs/specs/README.md` documents two Metadata constraints that `scripts/lint_spec.py` does not currently enforce: `status:` must be one of `drafted | in-progress | complete | archived`, and `spec_id:` must follow the shape `SPEC-<YYYYMMDD>-<slug>`. Today the linter checks only `risk_tier` and `complexity` from the Metadata block, so divergence between the documented contract and the gate accumulates silently. Two committed specs already use `status: implemented` — a value that looks plausible but is not in the allowed set — and would have been caught at commit-time had the gate matched the documentation.

The cost of this drift compounds as more specs land. Tightening the linter to match its own README closes the gap, prevents future drift, and gives the Reviewer and any future Phase-4 Router a trustworthy `status` field for routing decisions.

## Assumptions

- A1: The §5.1 structure in `docs/specs/README.md` is the authoritative contract for Metadata field values (`status` enum and `spec_id` pattern).
- A2: `scripts/lint_spec.py` remains stdlib-only and line-oriented per the existing design notes at the top of the file.
- A3: The committed specs `branch-name-hook-allowlist.md` and `scratch-branch-edit-guard.md` are the only existing specs that currently violate the documented `status` enum; all other committed `status:` and `spec_id:` values are conformant. (Verified on 2026-05-15.)
- A4: `complete` is the correct migration target for the two specs currently using `status: implemented` — both describe features that have shipped to `main`.

## Decisions

- D1: Implement both validations as small extensions to the existing `parse_metadata` / `check_metadata` flow rather than as new sections — they are Metadata field-value checks of the same shape as the existing `risk_tier` / `complexity` checks. Consistency over novelty.
- D2: Define `ALLOWED_STATUS` as a `frozenset` alongside `ALLOWED_RISK_TIERS` and `ALLOWED_COMPLEXITY`, and `SPEC_ID_RE` as a module-level compiled regex alongside the existing `*_RE` constants. Keeps the single-source-of-truth pattern intact.
- D3: The `spec_id` pattern is `^SPEC-\d{8}-[a-z0-9]+(?:-[a-z0-9]+)*$` — `SPEC-` literal, eight digits, dash, then a slug that is one or more lowercase-alphanumeric segments separated by single hyphens. This matches every existing committed `spec_id:` value and rejects uppercase, underscores, leading/trailing dashes, double dashes, and empty slugs.
- D4: Error messages mirror the existing Metadata error style verbatim — `"Metadata 'status: <value>' is not one of <sorted-list>"` and `"Metadata 'spec_id: <value>' does not match pattern 'SPEC-YYYYMMDD-<slug>'"` — so downstream parsers (humans, future tooling) see a consistent shape.
- D5: Migrate the two existing non-conforming `status: implemented` specs to `status: complete` in the same PR (as Slice 0), so the new validation lands without immediately breaking `just lint-changed-specs` on `main`. The alternative — adding `implemented` to the enum — contradicts the documented contract.

## Problem Statement

`scripts/lint_spec.py` accepts spec files whose `status:` value is outside the documented enum and whose `spec_id:` value does not match the documented shape, because the linter never inspects those fields. Concretely:

- A spec with `status: implemented` (not in `{drafted, in-progress, complete, archived}`) lints clean today; two such specs already exist on `main`.
- A spec with `spec_id: spec-20260515-foo` (lowercase prefix), `SPEC-2026515-foo` (seven-digit date), or `SPEC-20260515-Foo_Bar` (uppercase / underscore in slug) lints clean today.
- The documented contract in `docs/specs/README.md` says these should fail.

Fix: extend `check_metadata` to enforce both fields against the documented contract, and update the two non-conforming specs in the same change.

## Requirements (STRICT)

- [ ] R1: `lint_spec.py` reports an error when the Metadata block is missing a `status:` line, with message containing the substring `"status"`.
- [ ] R2: `lint_spec.py` reports an error when the Metadata block contains `status: <value>` where `<value>` is not in `{drafted, in-progress, complete, archived}`, with the offending value cited in the message.
- [ ] R3: `lint_spec.py` accepts every value in `{drafted, in-progress, complete, archived}` for `status:` without raising a status-related error.
- [ ] R4: `lint_spec.py` reports an error when the Metadata block is missing a `spec_id:` line, with message containing the substring `"spec_id"`.
- [ ] R5: `lint_spec.py` reports an error when the Metadata block contains `spec_id: <value>` where `<value>` does not match `^SPEC-\d{8}-[a-z0-9]+(?:-[a-z0-9]+)*$`, with the offending value cited in the message.
- [ ] R6: `lint_spec.py` accepts `spec_id:` values matching the pattern (e.g. `SPEC-20260515-foo`, `SPEC-20260515-foo-bar-baz`) without raising a spec_id-related error.
- [ ] R7: `docs/specs/branch-name-hook-allowlist.md` and `docs/specs/scratch-branch-edit-guard.md` have their `status:` migrated from `implemented` to `complete`, so the existing spec corpus lints clean under the new rules.

## Non-Goals

- [ ] NG1: This spec does not introduce a state-machine check across `status` values (e.g. forbidding `drafted` → `archived` directly). The enum is a value check, not a transition check.
- [ ] NG2: This spec does not validate that the `spec_id:` date matches today's date or the file's commit date — only the shape.
- [ ] NG3: This spec does not validate that the `<slug>` portion of `spec_id:` matches the filename slug or the branch name. That cross-field check is a future improvement.
- [ ] NG4: This spec does not modify `docs/specs/_template.md`, `docs/specs/README.md`, or the `write-spec` skill — the documented contract already matches the validation being added.
- [ ] NG5: This spec does not add `status: implemented` to the allowed enum. Rationale captured in D5.

## Interfaces

Files modified:

- `scripts/lint_spec.py` — add `ALLOWED_STATUS` frozenset, `SPEC_ID_RE` compiled regex, and extend `check_metadata` to validate both fields. No new functions exported.
- `tests/test_lint_spec.py` — add parametrized tests for the new validations (see Test Plan).
- `docs/specs/branch-name-hook-allowlist.md` — change `status: implemented` → `status: complete`.
- `docs/specs/scratch-branch-edit-guard.md` — change `status: implemented` → `status: complete`.

No new files. No public API surface change — `check_metadata` keeps its existing signature `(metadata: dict[str, str]) -> list[str]` and continues to return a list of human-readable error strings.

Behavioural contract (additions to `check_metadata`):

| Input metadata | New output behavior |
| --- | --- |
| No `status:` key | Append `"Metadata is missing 'status'"` |
| `status: implemented` | Append `"Metadata 'status: implemented' is not one of ['archived', 'complete', 'drafted', 'in-progress']"` |
| `status: drafted` | No status-related error |
| No `spec_id:` key | Append `"Metadata is missing 'spec_id'"` |
| `spec_id: SPEC-2026515-foo` (7-digit date) | Append `"Metadata 'spec_id: SPEC-2026515-foo' does not match pattern 'SPEC-YYYYMMDD-<slug>'"` |
| `spec_id: SPEC-20260515-foo` | No spec_id-related error |

## Invariants to Preserve

- [ ] INV1: `scripts/lint_spec.py` remains stdlib-only (no new dependencies). Invariant 4.
- [ ] INV2: The existing `lint_spec` test suite continues to pass — adding validations must not regress existing checks (missing sections, requirement mapping, duplicate IDs, red-zone consistency).
- [ ] INV3: `docs/specs/add-greet-module.md` (the canonical example spec) continues to lint clean after the change. Existing test `test_real_example_spec_lints_clean` enforces this.
- [ ] INV4: `just check` stays green on `main` after merge. This requires Slice 0 (migration) to land before or with the validation slice.
- [ ] INV5: Error-message shape for existing checks is unchanged — only new error messages are added.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: yes

> `scripts/lint_spec.py` is not in the red-zone enumeration in `AGENTS.md`, but it is invariant-protected via Invariant 3 ("Specs are documentation in `docs/specs/`, lint-enforced"). Tightening the gate is the explicit intent of this spec. The `yes` answer here drives `risk_tier: T1`. The Reviewer should confirm the linter change matches the documented contract in `docs/specs/README.md`.

## Test Plan

- [ ] T1 -> covers R1. `test_missing_status_is_reported` — write a spec with the `- status: drafted` line removed; assert an error containing `"status"` is returned.
- [ ] T2 -> covers R2. `test_unknown_status_is_reported` (parametrized over `["implemented", "wip", "DRAFTED", "", "done"]`) — write a spec with each invalid value; assert an error containing both `"status"` and the offending value.
- [ ] T3 -> covers R3. `test_allowed_status_lints_clean` (parametrized over `["drafted", "in-progress", "complete", "archived"]`) — write a spec with each allowed value; assert no status-related error in the returned list.
- [ ] T4 -> covers R4. `test_missing_spec_id_is_reported` — write a spec with the `- spec_id:` line removed; assert an error containing `"spec_id"`.
- [ ] T5 -> covers R5. `test_malformed_spec_id_is_reported` (parametrized over `["spec-20260515-foo", "SPEC-2026515-foo", "SPEC-20260515-Foo", "SPEC-20260515-foo_bar", "SPEC-20260515-", "SPEC-20260515--foo", "SPEC-20260515", "FOO-20260515-bar"]`) — write a spec with each malformed value; assert an error containing `"spec_id"` and the offending value.
- [ ] T6 -> covers R6. `test_valid_spec_id_lints_clean` (parametrized over `["SPEC-20260515-foo", "SPEC-20260515-foo-bar", "SPEC-20260101-a", "SPEC-20991231-z9-z9-z9"]`) — write a spec with each valid value; assert no spec_id-related error.
- [ ] T7 -> covers R7. `test_all_committed_specs_lint_clean` — enumerate every `docs/specs/*.md` (excluding `_template.md` and `_postmortem.md`) and assert each lints clean. Regression target so future corpus drift is caught at unit-test time, not only at `just lint-changed-specs` time.

## Validation Contract

| Requirement | Validator |
| --- | --- |
| R1 | `uv run pytest tests/test_lint_spec.py::test_missing_status_is_reported` |
| R2 | `uv run pytest tests/test_lint_spec.py::test_unknown_status_is_reported` |
| R3 | `uv run pytest tests/test_lint_spec.py::test_allowed_status_lints_clean` |
| R4 | `uv run pytest tests/test_lint_spec.py::test_missing_spec_id_is_reported` |
| R5 | `uv run pytest tests/test_lint_spec.py::test_malformed_spec_id_is_reported` |
| R6 | `uv run pytest tests/test_lint_spec.py::test_valid_spec_id_lints_clean` |
| R7 | `just lint-spec docs/specs/branch-name-hook-allowlist.md docs/specs/scratch-branch-edit-guard.md` (and `just check`) |

## Edge Cases

- EC1: A `status:` value with leading/trailing whitespace (for example, `status: drafted` with extra spaces around `drafted`) — `META_LINE_RE` already strips the value via `.strip()` in `parse_metadata`, so the new enum check sees the stripped value. No special handling needed.
- EC2: A `status:` value with mixed case (e.g. `Drafted`) — rejected. The enum is lowercase by documented contract; no case-folding. Covered by T2 (`"DRAFTED"`).
- EC3: An empty `status:` value (`- status:`) — `META_LINE_RE` requires `\s*:\s*(?P<value>.+?)` where `.+?` requires at least one character, so the line does not parse and the field appears missing. Handled by R1's missing-field branch.
- EC4: A `spec_id:` value with a future date (e.g. `SPEC-30000101-foo`) — accepted. Pattern is shape-only per NG2.
- EC5: A `spec_id:` value with month `13` or day `32` — accepted. Pattern is `\d{8}`, not a calendar check per D3.
- EC6: A `spec_id:` slug with a single character (e.g. `SPEC-20260515-a`) — accepted. Pattern allows segments of length ≥ 1.
- EC7: A `spec_id:` slug that is purely numeric (e.g. `SPEC-20260515-123`) — accepted. Character class `[a-z0-9]+` includes pure digits.

## Security / Prompt-Injection Review

- source: in-process file reads of `docs/specs/*.md` only; no MCP, no web search, no external docs, no user input flowing to an LLM.
- risk: low
- mitigation: not required.

## Observability

None required. The linter already prints `ERROR: <path>: <message>` to stderr for every violation; the two new error categories use the same channel.

## Rollback / Recovery

Revert the commit. The change is purely additive within `check_metadata` plus two one-line edits to existing specs and new test cases. No migrations, no feature flags, no persisted state. Reverting restores the prior (looser) lint behavior; the two migrated specs remain at `status: complete`, which is valid even under the looser rules.

## Implementation Slices

1. **Slice 0 — Migration.** Edit `docs/specs/branch-name-hook-allowlist.md` and `docs/specs/scratch-branch-edit-guard.md`: change `- status: implemented` to `- status: complete`. Verify with `just lint-spec` on each file (passes under current rules). This slice must land before or with Slice 1.

2. **Slice 1 — Validation logic.** In `scripts/lint_spec.py`:
   - Add `ALLOWED_STATUS: frozenset[str] = frozenset({"drafted", "in-progress", "complete", "archived"})` alongside the existing `ALLOWED_*` constants.
   - Add `SPEC_ID_RE = re.compile(r"^SPEC-\d{8}-[a-z0-9]+(?:-[a-z0-9]+)*$")` alongside the existing module-level regexes.
   - Extend `check_metadata` with status enum + spec_id pattern checks following the exact shape of the existing `risk_tier` and `complexity` checks. Preserve error-message style per D4.
   - No changes to `lint_spec`, `main`, or any other function.

3. **Slice 2 — Tests.** In `tests/test_lint_spec.py`:
   - Add `test_missing_status_is_reported`, `test_unknown_status_is_reported` (parametrized), `test_allowed_status_lints_clean` (parametrized).
   - Add `test_missing_spec_id_is_reported`, `test_malformed_spec_id_is_reported` (parametrized), `test_valid_spec_id_lints_clean` (parametrized).
   - Add `test_all_committed_specs_lint_clean` enumerating `docs/specs/*.md` (excluding `_template.md` and `_postmortem.md`).
   - Each test uses the existing `_minimal_valid_spec()` helper with targeted substitutions to keep the failure surface tight.
   - Run `just check` after this slice; commit.

## Done When

- [ ] R1–R7 satisfied
- [ ] D1–D5 preserved or explicitly deferred
- [ ] Tests T1–T7 mapped and passing
- [ ] Validation Contract satisfied (all listed pytest invocations pass; `just lint-spec` passes on the two migrated specs)
- [ ] `just check` green locally
- [ ] CI green
- [ ] No invariant violations (INV1–INV5)
- [ ] Branch name is `spec/lint-spec-status-and-spec-id` (Invariant 1)
- [ ] PR description links this spec
- [ ] PR body contains `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block
