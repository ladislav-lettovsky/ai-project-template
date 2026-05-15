# Document the Phase 3 Reviewer calibration workflow

## Metadata

- spec_id: SPEC-20260515-reviewer-calibration-workflow
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/reviewer-calibration-workflow

## Context

Phase 3 of `docs/blueprint.md` introduces the Codex Reviewer subagent and
its structured-JSON output. The phase's exit criterion is *behavioral*
rather than mechanical: a human scores 10 consecutive PRs against a
three-bucket rubric (useful / noise / missed), confirms 10/10 schema
validation, and confirms via Codex session logs that the Reviewer ran
with `sandbox_mode = "read-only"`. The procedure itself lives in the
`/calibrate-reviewer` skill at `.claude/skills/calibrate-reviewer/SKILL.md`,
and the exit criterion text lives in `docs/blueprint.md` §4 under "Phase 3".

Today there is no spec that ties these pieces together, and no
documentation answers the more subtle question: *where does the
calibration scoring data live, and what is its relationship to the merge
gate?* A future maintainer reading the skill could reasonably conclude
that the scoring worksheet should be promoted to a tracked artifact under
`docs/telemetry/` — or worse, that the worksheet itself becomes a merge
prerequisite. Both conclusions would be wrong. The scoring worksheet is
ephemeral evidence used to *judge whether the system is ready*; it is not
itself part of the system.

This spec is documentation-only. It writes down, in one place, the
Phase 3 calibration workflow, the ephemeral status of the scoring
worksheet, and the durable artifacts (specs, AGENTS.md, scripts,
schemas, hooks, CI) that *are* part of the merge gate. It also
documents the two human verification steps the blueprint already
requires for Phase 3 sign-off (10/10 schema validation, read-only
sandbox confirmed from logs).

## Assumptions

- A1: The `/calibrate-reviewer` skill at
  `.claude/skills/calibrate-reviewer/SKILL.md` is the canonical
  step-by-step procedure for scoring an individual PR. This spec
  references it; it does not duplicate or replace it.
- A2: The blueprint at `docs/blueprint.md` §4 ("Phase 3") is the
  canonical statement of the exit criterion (10 consecutive PRs, 6/10
  useful findings, 10/10 schema-valid, read-only sandbox confirmed).
  This spec references it; it does not redefine the criterion.
- A3: `.scratch/` is git-ignored (contents only) per `AGENTS.md` /
  `CLAUDE.md`. Files placed under `.scratch/` therefore do not enter
  version control and cannot become part of any merge gate.
- A4: `just validate-reviewer <pr-body-file>` is the established
  invocation for `scripts/validate_reviewer.py`, per AGENTS.md
  "Commands you can run without asking".
- A5: The Reviewer's `sandbox_mode = "read-only"` is configured in
  `.codex/config.toml` under `[agents.reviewer]` and is enforced by
  the Codex runtime, not by the Reviewer's prompt. Confirming this
  from session logs is the runtime guarantee referenced by the
  blueprint.

## Decisions

- D1: The calibration workflow is documented as a spec under
  `docs/specs/`, not as a new top-level document under
  `docs/telemetry/`. Rationale: `docs/telemetry/` is reserved for
  Phase 5+ machine-readable telemetry (events.jsonl, dashboard.md).
  Mixing a human procedure document into that directory would imply a
  durability the calibration worksheet does not have, and would
  conflict with the explicit constraint in the originating prompt
  ("Do NOT create `docs/telemetry/reviewer-calibration.md`").
- D2: The scoring worksheet is explicitly ephemeral and lives under
  `.scratch/reviewer-calibration.md` (or a personal notes system at
  the maintainer's discretion). Rationale: per A3, `.scratch/` is
  git-ignored, which makes it structurally impossible for the
  worksheet to become a tracked merge prerequisite. The skill at
  `.claude/skills/calibrate-reviewer/SKILL.md` already names this
  path; this spec ratifies it.
- D3: The `/calibrate-reviewer` skill is treated as authoritative for
  the per-PR scoring procedure and is NOT modified by this spec.
  Rationale: the skill already encodes the three-bucket rubric, the
  6-of-10 exit bar, the iteration triggers, and the failure-mode
  table. Duplicating any of that content into a spec would create two
  sources of truth that drift.
- D4: AGENTS.md and `docs/blueprint.md` are *optionally* updated to
  add a one-line cross-reference to this spec, but only if the
  cross-reference is additive. Rationale: AGENTS.md is canonical (per
  Invariant 8) and red-zone (per the AGENTS.md "Red-zone files"
  list). Editing it for documentation linkage is permitted but should
  be the smallest possible change. If the reference would not add
  load-bearing information, omit it.
- D5: This spec carries `risk_tier: T0` and `complexity: low` because
  the only changes that ship are Markdown additions to `docs/specs/`
  (a non-red-zone path) and at most one-line cross-references in
  AGENTS.md and `docs/blueprint.md`. The Red-Zone Assessment below
  reflects whichever of those edits actually land — see Implementation
  Slices for the branching rule.

## Problem Statement

`docs/blueprint.md` §4 states the Phase 3 exit criterion in one
paragraph. The `/calibrate-reviewer` skill walks through the per-PR
scoring procedure in detail. Neither document explicitly answers:

1. Where does the scoring worksheet live, and is it part of the merge
   gate? (Answer: under `.scratch/`, ephemeral, NOT part of the merge
   gate.)
2. What durable artifacts ARE the system's record of Phase 3
   readiness? (Answer: the spec corpus, AGENTS.md, scripts, schemas,
   hooks, and CI — all of which already exist and are unchanged by
   this spec.)
3. What two verification steps must the human run before declaring
   Phase 3 complete? (Answer: `just validate-reviewer` on each of the
   10 PR bodies, and confirmation from Codex session logs that
   `sandbox_mode = "read-only"` was actually applied at runtime.)

A future maintainer reading the skill in isolation could promote the
worksheet to a tracked artifact, or worse, build CI on top of it. This
spec writes down, in one referenceable place, the boundary between
the calibration *workflow* (ephemeral, human-judgment) and the system
artifacts that enforce the workflow's outputs (durable, machine-checked).

## Requirements (STRICT)

- [ ] R1: A new spec file exists at
  `docs/specs/reviewer-calibration-workflow.md`. The file passes
  `just lint-spec docs/specs/reviewer-calibration-workflow.md` (i.e.
  `scripts/lint_spec.py` exits 0 against it). The file also passes
  `uv run pre-commit run markdownlint-cli2 --files docs/specs/reviewer-calibration-workflow.md`.
- [ ] R2: The spec's Context, Decisions, and Problem Statement
  sections together state explicitly that (a) the Phase 3 calibration
  workflow requires scoring 10 consecutive PRs as useful / noise /
  missed using the `/calibrate-reviewer` skill at
  `.claude/skills/calibrate-reviewer/SKILL.md`, and (b) the scoring
  worksheet is ephemeral evidence that lives at
  `.scratch/reviewer-calibration.md` or in a personal notes system,
  and is NEVER part of the merge gate.
- [ ] R3: The spec's Context or Decisions section names the durable
  artifacts that *are* the system's record of Phase 3 readiness:
  specs under `docs/specs/`, AGENTS.md, scripts under `scripts/`
  (specifically `validate_reviewer.py`), schemas
  (`.reviewer-schema.json`), hooks under `scripts/hooks/`, and CI
  workflows under `.github/workflows/`. The list does not have to be
  exhaustive but must contrast against the ephemeral worksheet so a
  reader cannot confuse the two.
- [ ] R4: The spec's Done When section requires the human to verify
  10/10 Reviewer JSON schema validation via
  `just validate-reviewer <pr-body-file>` (one invocation per PR
  body) AND to confirm from Codex session logs that the Reviewer ran
  with `sandbox_mode = "read-only"` before declaring Phase 3 complete.
  Both conditions are written as checklist items.
- [ ] R5: The spec does NOT instruct any tooling change to
  `.claude/skills/calibrate-reviewer/SKILL.md`,
  `scripts/validate_reviewer.py`, `.reviewer-schema.json`, or
  `.codex/config.toml`. It only documents the workflow that already
  uses these artifacts.
- [ ] R6: The spec does NOT create a file under `docs/telemetry/`.
  The originating prompt for this spec explicitly forbids
  `docs/telemetry/reviewer-calibration.md`; this requirement records
  that constraint.

## Non-Goals

- [ ] NG1: No code change. No new scripts. No edits to existing
  scripts under `scripts/` or `scripts/hooks/`.
- [ ] NG2: No edit to `.claude/skills/calibrate-reviewer/SKILL.md` or
  any other file under `.claude/skills/`. The skill is canonical for
  the per-PR procedure; this spec only points at it.
- [ ] NG3: No edit to `.reviewer-schema.json`,
  `scripts/validate_reviewer.py`, or `.codex/config.toml`. The
  Reviewer's runtime configuration and output contract are unchanged.
- [ ] NG4: No new file under `docs/telemetry/`. The calibration
  worksheet is ephemeral (`.scratch/`); telemetry is a Phase 5+
  concern with a separate, machine-readable shape.
- [ ] NG5: No change to the Phase 3 exit criterion itself. The
  6-of-10 useful-findings bar, the 10/10 schema-valid bar, and the
  read-only sandbox confirmation are all defined by
  `docs/blueprint.md` §4 and are quoted by reference, not redefined.
- [ ] NG6: No CI workflow that asserts the existence or shape of any
  calibration worksheet. The worksheet is not part of the merge gate
  by design.
- [ ] NG7: No automation of the three-bucket scoring (useful / noise /
  missed). Human judgment is the input that calibrates the system;
  automating it would defeat the purpose of Phase 3.

## Interfaces

**Files created:**

- `docs/specs/reviewer-calibration-workflow.md` — this spec.

**Files possibly modified (optional, see D4 and Implementation Slices):**

- `AGENTS.md` — at most one line under "Agent Roles → Reviewer" or
  under a new short subsection cross-referencing this spec. If
  modified, this is a red-zone edit (per the "Red-zone files" list in
  AGENTS.md) and must be made via the documented red-zone edit
  process.
- `docs/blueprint.md` — at most one line at the end of the Phase 3
  paragraph in §4 cross-referencing this spec. The blueprint is not
  on the red-zone list, but it is invariant-protected reading.

**Files NOT modified (per Non-Goals):**

- `.claude/skills/calibrate-reviewer/SKILL.md`
- `scripts/validate_reviewer.py`
- `.reviewer-schema.json`
- `.codex/config.toml`
- Anything under `docs/telemetry/`
- Anything under `scripts/`, `scripts/hooks/`, `.github/workflows/`

No new entrypoints, CLI commands, schemas, or APIs.

## Invariants to Preserve

- [ ] INV1: `just check` (ruff + ty + pytest + lint-changed-specs +
  scan-injection) remains green after this change.
- [ ] INV2: `scripts/lint_spec.py` accepts the new spec file. In
  particular, every `R*` is covered by a `T<n> -> covers R<list>` line
  in Test Plan and a `R* -> <validator>` line in Validation Contract.
- [ ] INV3: AGENTS.md remains canonical (Invariant 8 of AGENTS.md /
  blueprint §2). If this spec modifies AGENTS.md at all, the change
  is additive and minimal.
- [ ] INV4: The Reviewer's `sandbox_mode = "read-only"` configuration
  in `.codex/config.toml` is unchanged. (NG3.)
- [ ] INV5: The `/calibrate-reviewer` skill is unchanged. (NG2.)
- [ ] INV6: No new file appears under `docs/telemetry/`. (NG4 / R6.)

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no

> The default Implementation Slice (Slice 1) only adds
> `docs/specs/reviewer-calibration-workflow.md`, which is NOT on the
> red-zone list. If the optional cross-reference in AGENTS.md is
> taken (Slice 2), the assessment changes: `invariant-protected
> files: yes`, and this spec must be re-tiered to `risk_tier: T1`
> per the rule that any `yes` answer disqualifies T0. See
> Implementation Slices: Slice 2 is conditional and the spec author
> must amend the Metadata block before landing it.

## Test Plan

This spec produces no executable code. The "tests" are deterministic
file/structure assertions runnable via existing tooling.

- [ ] T1 -> covers R1
  Run `uv run python scripts/lint_spec.py docs/specs/reviewer-calibration-workflow.md`.
  Expect exit code 0. Then run
  `uv run pre-commit run markdownlint-cli2 --files docs/specs/reviewer-calibration-workflow.md`.
  Expect exit code 0.
- [ ] T2 -> covers R2, R3
  Grep the committed spec for the substrings (case-insensitive)
  "10 consecutive PRs", "useful", "noise", "missed",
  ".scratch/reviewer-calibration.md", and "never part of the merge
  gate" (or substantively equivalent phrasing). Confirm each
  appears at least once. This is a manual / human-readable check —
  the spec linter does not enforce content, only structure.
- [ ] T3 -> covers R4
  Read the Done When section of the committed spec. Confirm two
  checklist items: one citing `just validate-reviewer` applied to
  10 PR bodies, one citing Codex session log confirmation of
  `sandbox_mode = "read-only"`.
- [ ] T4 -> covers R5, R6
  Run `git diff main -- .claude/skills/ scripts/validate_reviewer.py
  .reviewer-schema.json .codex/config.toml docs/telemetry/`.
  Expect empty diff (no changes in any of those paths).
- [ ] T5 -> covers R1
  Run `just check` from the repo root. Expect exit 0. This is the
  end-to-end gate: pre-commit, ruff, ty, pytest,
  lint-changed-specs, scan-injection all pass.

## Validation Contract

- R1 -> `just lint-spec docs/specs/reviewer-calibration-workflow.md`
  AND `uv run pre-commit run markdownlint-cli2 --files docs/specs/reviewer-calibration-workflow.md`
  AND `just check`
- R2 -> manual content check per T2 (the spec linter validates
  structure, not prose; this requirement is satisfied by reviewer
  reading)
- R3 -> manual content check per T2
- R4 -> manual content check per T3 against the Done When section
- R5 -> `git diff main -- .claude/skills/ scripts/validate_reviewer.py
  .reviewer-schema.json .codex/config.toml` returns empty
- R6 -> `git diff main -- docs/telemetry/` returns empty AND
  `test ! -e docs/telemetry/reviewer-calibration.md`

## Edge Cases

- EC1: A maintainer reads the new spec and concludes that the
  calibration worksheet under `.scratch/` should be checked into
  version control. Mitigation: Decisions D2 and the Problem
  Statement explicitly call out the ephemeral status; `.scratch/` is
  git-ignored (A3) so even an accidental `git add` against it would
  be ignored unless `-f` is used.
- EC2: A maintainer wants to track calibration progress across
  sessions or hand-offs. The skill already documents an in-line
  scoring template; this spec does not require any persistent
  storage. If durable tracking becomes necessary, the right mechanism
  is Phase 5's `events.jsonl`, not a new file under `docs/telemetry/`.
- EC3: AGENTS.md drifts to imply that the worksheet is required for
  merge. The cross-reference from this spec (Slice 2, optional) is
  intended to prevent that drift. If Slice 2 is skipped, drift is
  prevented only by future maintainers reading the spec corpus.
- EC4: The blueprint's Phase 3 paragraph is rewritten in a future
  revision. This spec quotes the exit criterion *by reference*
  (A2 / NG5), so a blueprint revision that changes the bar
  (e.g. 7-of-10 or 12 PRs) does not invalidate this spec — only the
  numbers shift, and the workflow itself is unchanged.
- EC5: A future spec wants to automate part of the calibration loop
  (e.g. auto-extract findings counts from PR bodies). That spec is
  out of scope here; NG7 is about the per-PR scoring judgment, not
  about read-only data extraction. A future automation spec is
  unblocked by this one.

## Security / Prompt-Injection Review

- source: in-process spec content only. The spec text is human-authored
  Markdown that lives in the repo. No data is sourced from MCP tools,
  web search, external docs, network responses, or LLM output. The
  spec does not flow into any LLM prompt at runtime — it is read by
  human maintainers.
- risk: low
- mitigation: not required. `scripts/scan_injection.py` runs over
  `docs/specs/` as part of `just check` and will independently
  reject the spec if any known injection pattern slips into the
  prose.

## Observability

None required. This is a documentation-only change. There is
deliberately no telemetry attached to the calibration workflow at
this phase — Phase 5's `events.jsonl` is the right home for that
when it lands. (See EC2.)

## Rollback / Recovery

Purely additive. To roll back, revert the commit that adds
`docs/specs/reviewer-calibration-workflow.md` (and, if Slice 2 was
taken, revert the one-line additions to AGENTS.md and
`docs/blueprint.md`). No data, schema, or runtime behavior depends
on this spec; rollback is a no-op for the running system.

## Implementation Slices

1. **Slice 1 (default, single commit, T0):** Add
   `docs/specs/reviewer-calibration-workflow.md` on branch
   `spec/reviewer-calibration-workflow`. Run
   `just lint-spec docs/specs/reviewer-calibration-workflow.md` and
   `just check` locally. Open PR; PR body links this spec; PR body
   carries the `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->`
   block per Invariant 1. Stop here unless Slice 2 is judged useful.
2. **Slice 2 (optional, conditional re-tier to T1):** If the spec
   author judges that AGENTS.md and/or `docs/blueprint.md` should
   carry a one-line cross-reference to this spec for findability
   (per D4), make those edits in a follow-up commit on the same
   branch. Editing AGENTS.md is a red-zone edit per the AGENTS.md
   "Red-zone files" list, so the spec's Metadata block must be
   updated to `risk_tier: T1` *before* the AGENTS.md edit lands, and
   the Red-Zone Assessment block above must flip
   `invariant-protected files` to `yes`. The lint check
   `check_redzone_tier_consistency` will enforce this automatically.
   Skip Slice 2 if the cross-reference adds no load-bearing information.

## Done When

- [ ] R1–R6 all satisfied.
- [ ] D1–D5 preserved or any deviation noted in the PR.
- [ ] T1–T5 executed with the documented expected outcomes.
- [ ] Validation Contract satisfied: every R\* maps to a passing
  validator.
- [ ] `just lint-spec docs/specs/reviewer-calibration-workflow.md`
  exits 0.
- [ ] `uv run pre-commit run markdownlint-cli2 --files docs/specs/reviewer-calibration-workflow.md`
  exits 0.
- [ ] `just check` green locally.
- [ ] CI green on the PR branch.
- [ ] Invariants INV1–INV6 hold.
- [ ] Branch name is `spec/reviewer-calibration-workflow` (Invariant 1:
  merge-bound PR branches use `spec/<slug>` or `fix/<slug>`).
- [ ] PR description links this spec.
- [ ] PR body contains a `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->`
  block.
- [ ] **Phase 3 sign-off prerequisites (schema validation):** before
  declaring Phase 3 complete, the human has run
  `just validate-reviewer <pr-body-file>` against each of the 10
  scored PR bodies and confirmed all 10 exit 0.
- [ ] **Phase 3 sign-off prerequisites (sandbox confirmation):** before
  declaring Phase 3 complete, the human has read the Codex session
  log for at least one Reviewer invocation and confirmed
  `sandbox_mode = "read-only"` was applied at runtime (per
  blueprint §4 Phase 3 exit criterion).
