# Reject duplicate requirement IDs in `lint_spec.py`

## Metadata

- spec_id: SPEC-20260514-lint-spec-duplicate-ids
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/lint-spec-duplicate-ids

## Context

`scripts/lint_spec.py` is the single gate that decides whether a spec is well-formed. It already enforces required sections, ordering, metadata enums, and the requirement → test → validation chain. One structural failure mode it does *not* currently catch: the same requirement ID declared twice under `## Requirements (STRICT)`.

Today, if a spec contains two bullets that both start with `R1:` (or two bullets that both start with `REQ-GREET-01`), the linter silently deduplicates them inside `collect_requirements` (which uses a `seen: set[str]` precisely to avoid yielding the same ID twice). The downstream T-coverage and Validation-Contract checks then pass against a single phantom requirement, even though the spec really declares two different acceptance criteria under one ID. The Executor would then implement only one of the two, and the Reviewer would have no signal that the spec was malformed.

This is a low-cost, high-value tightening: duplicate IDs are always a spec authoring bug, and the linter is the right place to surface them — early, deterministically, before any code is written.

## Assumptions

- A1: The Requirements section heading is exactly `## Requirements (STRICT)` (already enforced by `REQUIRED_SECTIONS` in `scripts/lint_spec.py`).
- A2: Requirement IDs always appear inside bullet lines that start with `-` or `*`, matching the existing scan in `collect_requirements`. Prose mentions of an ID inside the section body are intentionally ignored, as they are today.
- A3: A "duplicate" means the *same* exact ID string appearing as a leading token on two or more bullet lines (e.g., two `R1:` bullets, or two `REQ-FOO-01:` bullets). Casing is not normalized — `R1` and `r1` would be treated as different (and `r1` would not be a valid ID under the existing `REQ_ID_RE` anyway).
- A4: The two ID shapes (`R<digits>` and `REQ-<UPPER-AND-DIGITS-AND-DASHES>`) are the only ones in scope, matching the single-source `REQ_ID_ALT` regex already in `scripts/lint_spec.py`.
- A5: A single bullet may legitimately mention multiple IDs in prose (e.g. "supersedes R1"). Only the *first* ID per bullet is treated as the bullet's declaring ID. Existing bullets in committed specs follow the convention "one bullet, one declaring ID at the start", so this rule does not regress any current spec.
- A6: The Executor (Codex) will run `just check` against every committed spec after the change, so any latent duplicate-ID bug in existing specs will be caught immediately.

## Decisions

- D1: The duplicate check lives in `collect_requirements` (or a sibling helper called from `lint_spec`) — not in a new top-level pass. Rationale: the function already iterates the Requirements section line-by-line and is the single place that produces the canonical requirement-ID list. Adding the check there keeps the parser line-oriented and stdlib-only (per `lint_spec.py` design notes) and avoids a second traversal.
- D2: The function's *return contract* changes from "deduplicated list of IDs" to "ordered list possibly containing duplicates"; a separate helper (or an enriched return shape) surfaces the duplicates as errors. Rationale: silently deduplicating was the bug. The parser must report what is actually written in the file, and let the checker decide whether duplicates are an error. The simplest realization: `collect_requirements` returns the ordered list of *declaring* IDs (one per bullet), and `lint_spec` computes duplicates from that list.
- D3: The error message format is fixed: `requirement '<ID>' is declared more than once`. Rationale: matches the user's example verbatim and follows the existing message style in `check_requirement_mapping` (single-quoted ID, lowercase noun, no trailing period). Stable wording lets future tests grep for the message.
- D4: The duplicate check fires *before* the requirement → test and requirement → validation mapping checks run, and the duplicate ID is collapsed to a single ID for the purpose of those downstream checks. Rationale: a spec with `R1` declared twice should not also produce two "R1 has no T entry" errors per duplicate; the user gets one clear duplicate error per ID, and the downstream checks behave as if `R1` were declared once. This keeps error output proportional to the bug.
- D5: Each duplicated ID produces *one* error, regardless of how many times it is duplicated. Rationale: noise reduction. If `R1` appears three times, the user gets one `requirement 'R1' is declared more than once` error, not two.

## Problem Statement

`scripts/lint_spec.py` accepts specs that declare the same requirement ID more than once. The current `collect_requirements` function maintains a `seen: set[str]` and skips IDs it has already yielded:

```python
for match in REQ_ID_RE.finditer(line):
    ident = match.group(1)
    if ident not in seen:
        seen.add(ident)
        ids.append(ident)
```

Concrete failure: a spec with two bullets

```text
- [ ] R1: do thing A.
- [ ] R1: do thing B.
```

passes the linter as long as there is a single `T<n> -> covers R1` and a single `R1 ->` validation entry. The Executor then has no deterministic way to know which of "thing A" or "thing B" is the canonical R1, and the Reviewer cannot detect that the spec contradicts itself. The same failure mode applies to the long ID form (`REQ-GREET-01`).

## Requirements (STRICT)

- [ ] R1: `scripts/lint_spec.py` returns a non-zero exit code when the same requirement ID (short form, e.g. `R1`) is declared on more than one bullet under `## Requirements (STRICT)`. The error message printed to stderr matches `requirement '<ID>' is declared more than once`.
- [ ] R2: `scripts/lint_spec.py` returns a non-zero exit code when the same requirement ID (long form, e.g. the `REQ-<SLUG>-<NN>` shape) is declared on more than one bullet under `## Requirements (STRICT)`. The error message printed to stderr matches `requirement '<ID>' is declared more than once`.
- [ ] R3: When an ID is duplicated three or more times, exactly one duplicate-ID error is emitted for that ID (no per-extra-occurrence amplification).
- [ ] R4: When duplicates exist, the downstream "no matching `T<n> -> covers <ID>`" and "no matching `<ID> ->` Validation Contract" checks behave as if each duplicated ID were declared once — i.e. they do not emit additional errors per duplicate occurrence.
- [ ] R5: Specs that do not contain any duplicate requirement IDs continue to lint exactly as before. Specifically: `docs/specs/add-greet-module.md` and the in-test `_minimal_valid_spec()` continue to lint clean.

## Non-Goals

- [ ] NG1: No detection of duplicate IDs in other sections (Test Plan `T<n>`, Decisions `D<n>`, Assumptions `A<n>`, Edge Cases `EC<n>`, Non-Goals `NG<n>`, Invariants `INV<n>`). Only requirement IDs are in scope; the other ID families do not flow into the requirement → test → validation chain that gates downstream agents.
- [ ] NG2: No semantic comparison of requirement bodies. Two bullets with the same ID *and* identical body text are still a duplicate-ID error; the linter does not try to "merge" them.
- [ ] NG3: No new ID-shape support (e.g. `FR-01`, `NFR-01`). The existing `REQ_ID_ALT` alternation is unchanged.
- [ ] NG4: No reformatting of the existing error messages. Other error strings in `lint_spec.py` (missing-section, mapping, metadata) are untouched.
- [ ] NG5: No change to `docs/specs/_template.md` or `docs/specs/README.md` content beyond what (if anything) is required to mention the new check. (Optional only; not required by this spec.)
- [ ] NG6: No new dependencies (per task constraints). Stdlib + existing regex only.

## Interfaces

**Files modified:**

- `scripts/lint_spec.py` — `collect_requirements` (or its replacement) returns a list that may contain duplicates; `lint_spec` adds a duplicate-ID check before requirement-mapping; downstream mapping consumes a deduplicated view.
- `tests/test_lint_spec.py` — add deterministic tests for both ID shapes (R-form and REQ-form duplicates), and for triple-duplication producing a single error.

**Files created:** none.

**Public API surface changed:** none externally. Internally, `collect_requirements` either:

- (a) returns a list with duplicates intact (signature unchanged: `(body: str) -> list[str]`), and `lint_spec` computes duplicates by tracking first-seen vs. later occurrences, or
- (b) is split into `collect_requirements` (deduplicated, as today) plus a new `find_duplicate_requirements(body: str) -> list[str]` helper that returns the IDs that appear more than once, in first-occurrence order.

The Executor selects (a) or (b); both satisfy the requirements. The recommended shape is (a) because it keeps the function name accurate to "what is in the file" and centralizes duplicate detection in `lint_spec`.

**CLI behaviour:** the existing exit-code contract is preserved (0 = clean, 1 = lint errors, 2 = usage). Duplicate-ID failures contribute to the existing exit-code-1 path; no new exit code is introduced.

## Invariants to Preserve

- [ ] INV1: `just check` (ruff + ty + pytest + lint-changed-specs + scan-injection) remains green after this change.
- [ ] INV2: No new runtime or dev dependencies added to `pyproject.toml` (per task constraints; AGENTS.md red-zone protection of `pyproject.toml` dependency sections).
- [ ] INV3: `scripts/lint_spec.py` remains stdlib-only and line-oriented, per its module docstring.
- [ ] INV4: The single-source `REQ_ID_ALT` regex remains the only place where ID shapes are defined.
- [ ] INV5: Existing exit-code semantics preserved (0/1/2 as documented in the module docstring).
- [ ] INV6: `docs/specs/add-greet-module.md` continues to lint clean — it is the canonical example spec and its duplication-free state is a regression target (already covered by `test_real_example_spec_lints_clean`).
- [ ] INV7: The error message vocabulary already in use (`'<ID>' has no matching ...`) remains unchanged for the existing checks; only a new message string is added.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no

`scripts/lint_spec.py` is *not* on the red-zone list in `AGENTS.md` (`scripts/hooks/**` is, but `scripts/lint_spec.py` lives one directory up and is not enumerated). The change adds a check inside an existing script, modifies its companion test file, and touches nothing else.

`risk_tier: T0` is appropriate: the change is a tightening of an existing parser, single-file in production code (plus its test file), no behaviour change for valid specs, and rolls back by reverting one commit.

## Test Plan

All tests live in `tests/test_lint_spec.py`. Each test docstring cites the requirement ID(s) it covers. Tests are deterministic — they construct synthetic spec text in `tmp_path` and call `lint_spec_module.lint_spec()` directly, matching the existing test style.

- [ ] **T1** -> covers R1
  `test_duplicate_short_form_id_is_reported`: starting from `_minimal_valid_spec()`, replace the single `- [ ] R1: do the thing.` bullet with two bullets that both declare `R1:`. Assert that the returned errors list contains an entry matching exactly `requirement 'R1' is declared more than once`.
- [ ] **T2** -> covers R2
  `test_duplicate_long_form_id_is_reported`: starting from `_minimal_valid_spec()`, switch to the `REQ-FOO-01` ID form (mirroring `test_req_dash_form_is_recognized`) and declare it on two bullets. Assert the errors list contains exactly `requirement 'REQ-FOO-01' is declared more than once`.
- [ ] **T3** -> covers R3
  `test_triple_duplicate_emits_single_error`: declare `R1` on three bullets. Assert exactly one error string for `R1` of the form `requirement 'R1' is declared more than once` (use `errors.count(...)` or filter and assert `len == 1`).
- [ ] **T4** -> covers R4
  `test_duplicate_does_not_amplify_mapping_errors`: declare `R1` on two bullets but *remove* the `T1 -> covers R1` line (or remove the `R1 ->` validation line). Assert that the "no matching Test Plan" / "no matching Validation Contract" error for `R1` appears at most once in the returned errors, alongside the duplicate-ID error.
- [ ] **T5** -> covers R5
  `test_existing_clean_specs_still_lint_clean`: re-run `lint_spec_module.lint_spec` on (a) `_minimal_valid_spec()` written to `tmp_path` and (b) `docs/specs/add-greet-module.md` if present, and assert both return `[]`. (T5 may be satisfied by the already-existing `test_minimal_valid_spec_lints_clean` and `test_real_example_spec_lints_clean`; the Executor may add an explicit T5 test or note in the PR that R5 is covered by those two existing tests by name.)

All tests are deterministic; no `@pytest.mark.integration` marker is needed.

## Validation Contract

| Requirement | Validator |
| --- | --- |
| R1 | `pytest tests/test_lint_spec.py::test_duplicate_short_form_id_is_reported` |
| R2 | `pytest tests/test_lint_spec.py::test_duplicate_long_form_id_is_reported` |
| R3 | `pytest tests/test_lint_spec.py::test_triple_duplicate_emits_single_error` |
| R4 | `pytest tests/test_lint_spec.py::test_duplicate_does_not_amplify_mapping_errors` |
| R5 | `pytest tests/test_lint_spec.py::test_minimal_valid_spec_lints_clean tests/test_lint_spec.py::test_real_example_spec_lints_clean` |

All validators are exercised by `just check` (which runs `pytest`).

## Edge Cases

- EC1: A bullet that mentions an ID in prose only (e.g. `- supersedes R1 — see history`) but does not declare a new requirement starting with `R1:` should not count as a duplicate. The existing convention already takes the *first* ID match per bullet as the declaring ID; if the first ID on a bullet matches an earlier bullet's first ID, that is the duplicate.
- EC2: A bullet with no ID at all (e.g. an indentation continuation) is ignored, as today. Lines that are not bulleted are also ignored.
- EC3: Mixed forms in one spec: `R1` and `REQ-FOO-01` both present and each unique → no duplicate error. Each ID family is checked against itself by exact-string equality, not by alternation across families.
- [ ] EC4: An ID that appears once in Requirements but twice in the *same* bullet (e.g. `- [ ] R1: see also R1 below`) is not a duplicate — it is one declaring bullet. The first match on that single line is the declaring ID; subsequent matches on the same line are prose references.
- EC5: Whitespace and checkbox-prefix variations (`- [ ] R1`, `- [x] R1`, `* R1`, `-   R1`) all count as the same declaring bullet shape, matching `collect_requirements`'s existing prefix tolerance (`stripped.startswith(("-", "*"))`).
- EC6: A spec with zero requirement bullets continues to fail with the existing `no requirements found under '## Requirements (STRICT)'` error; the new duplicate check produces no additional errors when the list is empty.

## Security / Prompt-Injection Review

- source: in-process Python — `lint_spec` reads spec markdown files committed to the repo. No MCP tool, web search, external doc, or untrusted user input is involved at lint time.
- risk: low
- mitigation: not required. `scripts/scan_injection.py` (run as part of `just check`) already scans spec content for known prompt-injection patterns; this spec does not change that pipeline.

## Observability

None required. `scripts/lint_spec.py` already prints `ERROR: <path>: <message>` lines to stderr for every violation; the new check uses the same channel and the same prefix. No metrics, no telemetry, no new logging.

## Rollback / Recovery

Purely additive lint check. Roll back by reverting the single commit that adds the duplicate-ID check and its tests. No data, no schema, no migration. If the new check produces a false positive against a real-world spec post-merge, the safe interim is to revert and re-spec the corner case.

## Implementation Slices

1. **Slice 1 (single commit):** Modify `scripts/lint_spec.py` to detect duplicate requirement IDs; add the four new tests (T1–T4) to `tests/test_lint_spec.py`; confirm T5 is already covered by existing tests (or add an explicit assertion). Run `just check`. Open one PR.

## Done When

- [ ] Requirements R1, R2, R3, R4, R5 satisfied.
- [ ] Decisions D1–D5 preserved, or any deviation noted in the PR with rationale.
- [ ] Tests T1–T4 present in `tests/test_lint_spec.py` with docstrings citing requirement IDs; T5 covered by existing or new tests.
- [ ] Validation Contract satisfied: every R* maps to a passing pytest invocation.
- [ ] `just check` green locally (ruff + ty + pytest + lint-changed-specs + scan-injection).
- [ ] CI green on the PR branch.
- [ ] Invariants INV1–INV7 hold.
- [ ] Branch name starts with `spec/lint-spec-duplicate-ids` (Invariant 1).
- [ ] PR description links this spec at `docs/specs/lint-spec-duplicate-ids.md`.
- [ ] PR body contains a `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block.
