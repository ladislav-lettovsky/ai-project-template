# Verify Codex Reviewer ran with read-only sandbox enforcement

## Metadata

- spec_id: SPEC-20260515-codex-reviewer-readonly-sandbox-verification
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/codex-reviewer-readonly-sandbox-verification

## Context

Phase 3 of `docs/blueprint.md` concluded with two human-verifiable sign-off
prerequisites at the end of Reviewer subagent calibration: (1)
10/10 Reviewer JSON outputs validated against `.reviewer-schema.json`,
and (2) a human confirmed from Codex session logs that the Reviewer
actually ran with `sandbox_mode = "read-only"`. The first is mechanical
(`just validate-reviewer <pr-body-file>` exits 0). The second is not:
there is no command in this repo today that reads from
`CODEX_HOME` and asserts "this Reviewer run was sandboxed". The
maintainer had to look it up from logs.

This spec is documentation-only. It writes down, in one place, *where*
to look under `CODEX_HOME` (default `~/.codex`), *what* to look for,
*what counts as strong evidence vs weak or inconclusive evidence*, and
*how* the verification fits into the calibration workflow documented
in `docs/specs/reviewer-calibration-workflow.md`. It exists because the
sibling spec stops at "confirm from session logs" without prescribing
the procedure, and because Codex's on-disk layout under `CODEX_HOME`
is undocumented in this repo and likely to drift across Codex
versions.

The runtime guarantee being verified is that `sandbox_mode` is
enforced by the Codex runtime — configured under `[agents.reviewer]`
in `.codex/config.toml` — and is *not* something the Reviewer's prompt
can override. This spec documents how to confirm the runtime honored
that configuration; it does not modify the configuration itself.

## Assumptions

- A1: The Reviewer subagent is configured in `.codex/config.toml`
  under `[agents.reviewer]` with `sandbox_mode = "read-only"` and
  `model_reasoning_effort = "high"` per AGENTS.md "Agent Roles". This
  spec does not modify that file.
- A2: `CODEX_HOME` defaults to `~/.codex` on macOS and Linux when the
  environment variable is unset. A maintainer who has overridden
  `CODEX_HOME` should substitute their path in every command below.
- A3: The Codex CLI writes session artifacts under `CODEX_HOME` in
  some combination of `history.jsonl`, `sessions/<date-folder>/`, and
  `session_index.jsonl`. **Exact filenames and on-disk layout can
  change across Codex versions.** The paths in this spec are starting
  points for the search, not stable contracts.
- A4: The maintainer running the verification has `rg` (ripgrep) and
  `jq` available locally. Both are standard tools in this repo's
  development environment and are referenced from existing scripts.
- A5: `.scratch/` is git-ignored (contents only) per AGENTS.md.
  Captured log excerpts under `.scratch/reviewer-calibration.md` are
  therefore structurally prevented from entering version control and
  cannot become part of any merge gate.
- A6: The sibling spec at
  `docs/specs/reviewer-calibration-workflow.md` is the canonical
  statement of the broader Phase 3 calibration workflow; this spec is
  its companion for the sandbox-confirmation half of the exit gate.

## Decisions

- D1: The verification procedure is documented as a spec under
  `docs/specs/`, alongside the broader calibration workflow spec. It
  is not promoted to AGENTS.md, the blueprint, or a top-level
  procedure doc. Rationale: the procedure is load-bearing only at
  Phase 3 sign-off and at any future moment a maintainer suspects the
  Reviewer escaped its sandbox. A spec is the right venue —
  durable, lint-enforced, and discoverable from the calibration spec.
- D2: The captured log excerpt lives in
  `.scratch/reviewer-calibration.md` *only*. It is ephemeral. Rationale:
  Codex session artifacts may contain PR-body text, agent reasoning
  traces, and references to local file paths. Promoting any of that to
  a tracked artifact would be a confidentiality and prompt-injection
  hygiene risk for no merge-gate benefit. The `.scratch/` location
  matches D2 of the sibling calibration-workflow spec.
- D3: Evidence is classified as **strong** or **weak/inconclusive**.
  Rationale: a maintainer skimming the docs needs an unambiguous bar.
  A literal token match for `sandbox_mode` with value `"read-only"` in
  a session artifact associated with the Reviewer invocation is the
  strong-evidence bar. Anything else (proximity matches, the word
  "reviewer" near unrelated config text, absence of write-attempt
  errors) is weak.
- D4: The on-disk paths under `CODEX_HOME` are documented as
  "starting points, expected to drift". Rationale: per A3, Codex
  versions can rename or restructure these files. Documenting them as
  authoritative would invite a future maintenance burden the spec
  cannot meet. The spec instructs the maintainer to grep broadly under
  `CODEX_HOME` rather than relying on any one file.
- D5: This spec carries `risk_tier: T0` and `complexity: low`. The
  only change that ships is a new Markdown file under `docs/specs/`
  and a one-line cross-link in `docs/specs/reviewer-calibration-workflow.md`.
  Both paths are outside the red-zone list in AGENTS.md.

## Problem Statement

`docs/blueprint.md` Phase 3 requires a human to confirm, from Codex
session logs, that the Reviewer ran with `sandbox_mode = "read-only"`.
`docs/specs/reviewer-calibration-workflow.md` Done When repeats that
requirement as a checklist item. Neither document answers:

1. *Where* under `CODEX_HOME` (default `~/.codex`) is the evidence?
   Today, a maintainer has to guess across `history.jsonl`,
   `sessions/<date>/`, and `session_index.jsonl` without guidance.
2. *What search commands* return useful results? A naive
   `rg sandbox_mode ~/.codex/` may surface unrelated configuration
   echoes that are not evidence of the Reviewer's actual runtime mode.
3. *What counts as evidence?* The maintainer needs a strong/weak bar,
   not a vibes-based "I saw the word read-only somewhere".
4. *Where does the captured excerpt go?* Without a sanctioned home,
   maintainers will paste session log fragments into PR bodies or
   commit messages, which is a confidentiality and injection hygiene
   risk.

The result of these gaps is that the Phase 3 sandbox-confirmation
checkbox is informally satisfied by "I looked, it seemed fine" — which
is exactly the failure mode the blueprint's structured-evidence
discipline is meant to prevent.

## Requirements (STRICT)

- [ ] R1: A new spec file exists at
  `docs/specs/codex-reviewer-readonly-sandbox-verification.md`. The
  file passes
  `uv run python scripts/lint_spec.py docs/specs/codex-reviewer-readonly-sandbox-verification.md`
  (exit 0) and
  `uv run pre-commit run markdownlint-cli2 --files docs/specs/codex-reviewer-readonly-sandbox-verification.md`
  (exit 0).
- [ ] R2: The spec contains a runtime-guarantee reminder stating that
  `sandbox_mode` is enforced by the Codex runtime (via
  `[agents.reviewer]` in `.codex/config.toml`) and cannot be
  overridden by the Reviewer's prompt. This reminder appears in
  Context, Decisions, or a dedicated Observability subsection.
- [ ] R3: The spec lists the artifact paths under `CODEX_HOME`
  (default `~/.codex`) that are starting points for the search:
  `~/.codex/history.jsonl`, `~/.codex/sessions/<date-folder>/`, and
  `~/.codex/session_index.jsonl`. The spec also contains an explicit
  note that these paths can drift across Codex versions and are not
  guaranteed stable contracts.
- [ ] R4: The spec lists concrete search commands using `rg` and
  `jq`, including at minimum:
  `rg "read-only" ~/.codex/`,
  `rg "sandbox_mode" ~/.codex/`,
  `rg "reviewer" ~/.codex/`, and a `jq` filter shape such as
  `jq 'select(.agent == "reviewer")' ~/.codex/session_index.jsonl`
  (or substantively equivalent). The commands are presented as
  starting points, not as guaranteed-to-match queries.
- [ ] R5: The spec classifies evidence as **strong** vs
  **weak/inconclusive**. The strong-evidence bar is a literal
  `sandbox_mode = "read-only"` (or equivalent JSON encoding) inside a
  session artifact associated with the Reviewer invocation. The
  weak/inconclusive cases (proximity matches, ambient config echoes,
  absence-of-error) are named explicitly so a maintainer cannot
  confuse them with strong evidence.
- [ ] R6: The spec contains a step-by-step Procedure subsection (may
  live under Implementation Slices or as its own narrative) with at
  least three steps in this order: (a) run the Codex Reviewer on the
  PR that implements this spec; (b) search for `sandbox_mode`
  evidence in `CODEX_HOME` artifacts using the commands from R4;
  (c) capture the relevant log excerpt into
  `.scratch/reviewer-calibration.md` only, never into version
  control.
- [ ] R7: The spec's Done When section is cross-linked, in one
  sentence, from the sibling spec
  `docs/specs/reviewer-calibration-workflow.md` (in its Done When or
  Context section). The cross-link is the only edit made to the
  sibling spec; no other content changes there.
- [ ] R8: The spec does NOT instruct any change to
  `.codex/config.toml`, `.claude/` (any path), `scripts/hooks/`,
  `pyproject.toml`, `.reviewer-schema.json`,
  `scripts/validate_reviewer.py`, or any other path on the AGENTS.md
  "Red-zone files" list. This is a structural / lint-checkable
  requirement on the diff.

## Non-Goals

- [ ] NG1: No automation. The spec does not propose a script that
  parses `CODEX_HOME` artifacts and asserts read-only-ness. Per A3
  and D4, the on-disk layout is expected to drift; a brittle parser
  would be a worse merge-gate input than a human read.
- [ ] NG2: No change to `.codex/config.toml`. The Reviewer's
  `sandbox_mode = "read-only"` configuration is the *subject* of
  verification, not its target.
- [ ] NG3: No change to `.reviewer-schema.json` or
  `scripts/validate_reviewer.py`. Schema validation is the *other*
  Phase 3 prerequisite; this spec is scoped to the sandbox half.
- [ ] NG4: No change to `.claude/skills/calibrate-reviewer/SKILL.md`.
  The skill describes per-PR scoring; this spec describes a
  one-time-per-phase runtime check. They are complementary.
- [ ] NG5: No CI workflow that asserts read-only sandbox use. The
  verification is a human read at Phase 3 sign-off, not a per-PR
  gate.
- [ ] NG6: No file under `docs/telemetry/`. Captured log excerpts
  live under `.scratch/` per D2 and are ephemeral.
- [ ] NG7: No documentation of Codex's internal session-artifact
  schema. Per A3 / D4, that schema is owned upstream and may change;
  this spec deliberately stops at "starting points for search".

## Interfaces

**Files created:**

- `docs/specs/codex-reviewer-readonly-sandbox-verification.md` — this
  spec.

**Files modified:**

- `docs/specs/reviewer-calibration-workflow.md` — one-sentence
  cross-link addition in its Done When section (per R7). No other
  changes to that file.

**Files NOT modified (per NG2–NG6, R8):**

- `.codex/config.toml`
- `.claude/` (any path), including
  `.claude/skills/calibrate-reviewer/SKILL.md`
- `scripts/hooks/`
- `pyproject.toml`
- `.reviewer-schema.json`
- `scripts/validate_reviewer.py`
- `.github/workflows/`
- Anything under `docs/telemetry/`

No new entrypoints, CLI commands, schemas, or APIs. The spec
documents an existing manual procedure; it does not introduce one.

## Invariants to Preserve

- [ ] INV1: `just check` (ruff + ty + pytest + lint-changed-specs +
  scan-injection) remains green after this change.
- [ ] INV2: `scripts/lint_spec.py` accepts the new spec file. Every
  `R*` is covered by a `T<n> -> covers R<list>` line in Test Plan and
  a `R* -> <validator>` line in Validation Contract.
- [ ] INV3: AGENTS.md (Invariant 8: canonical) is unchanged. CLAUDE.md
  (symlink) is unchanged.
- [ ] INV4: `.codex/config.toml` is unchanged. The Reviewer's
  `sandbox_mode = "read-only"` configuration is the subject of
  verification, not a target of edits.
- [ ] INV5: The `/calibrate-reviewer` skill is unchanged. (NG4.)
- [ ] INV6: No new file appears under `docs/telemetry/`. (NG6.)
- [ ] INV7: Captured log excerpts never enter version control. They
  live in `.scratch/reviewer-calibration.md`, which is git-ignored
  per AGENTS.md.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no

> The two files that ship are
> `docs/specs/codex-reviewer-readonly-sandbox-verification.md` (new)
> and a one-line cross-link in
> `docs/specs/reviewer-calibration-workflow.md`. Neither is on the
> AGENTS.md "Red-zone files" list. `risk_tier: T0` is justified.

## Test Plan

This spec produces no executable code. The "tests" are deterministic
file/structure assertions runnable via existing tooling, plus a small
number of human content checks.

- [ ] T1 -> covers R1
  Run `uv run python scripts/lint_spec.py docs/specs/codex-reviewer-readonly-sandbox-verification.md`.
  Expect exit 0. Then run
  `uv run pre-commit run markdownlint-cli2 --files docs/specs/codex-reviewer-readonly-sandbox-verification.md`.
  Expect exit 0. Then run `just check` from the repo root and expect
  exit 0.
- [ ] T2 -> covers R2
  Grep the committed spec for the substrings "enforced by the Codex
  runtime" and "cannot be overridden" (or substantively equivalent
  phrasing); confirm at least one occurrence of each. Manual content
  check.
- [ ] T3 -> covers R3
  Grep the committed spec for `~/.codex/history.jsonl`,
  `~/.codex/sessions/`, and `~/.codex/session_index.jsonl`. Confirm
  all three appear, and confirm a "paths can drift" caveat sentence
  is present. Manual content check.
- [ ] T4 -> covers R4
  Grep the committed spec for the literal commands
  `rg "read-only" ~/.codex/`, `rg "sandbox_mode" ~/.codex/`,
  `rg "reviewer" ~/.codex/`, and a `jq 'select(.agent == "reviewer")'`
  shape (or substantively equivalent). Confirm all four appear.
  Manual content check.
- [ ] T5 -> covers R5
  Read the Evidence Classification subsection of the committed spec.
  Confirm the **strong** bar is defined as a literal
  `sandbox_mode = "read-only"` match in a Reviewer-associated
  artifact, and the **weak/inconclusive** cases are enumerated
  (proximity matches, ambient config echoes, absence-of-error).
  Manual content check.
- [ ] T6 -> covers R6
  Read the Procedure subsection of the committed spec. Confirm at
  least three ordered steps: (a) run Reviewer on this PR, (b) search
  `CODEX_HOME`, (c) capture excerpt to `.scratch/reviewer-calibration.md`
  only. Manual content check.
- [ ] T7 -> covers R7
  `git diff main -- docs/specs/reviewer-calibration-workflow.md`
  shows exactly one additive sentence in the Done When section,
  cross-linking this spec. No other lines changed in that file.
- [ ] T8 -> covers R8
  Run `git diff main -- .codex/config.toml .claude/ scripts/hooks/
  pyproject.toml .reviewer-schema.json scripts/validate_reviewer.py
  .github/workflows/ docs/telemetry/`. Expect empty diff.

## Validation Contract

- R1 -> `just lint-spec docs/specs/codex-reviewer-readonly-sandbox-verification.md`
  AND `uv run pre-commit run markdownlint-cli2 --files docs/specs/codex-reviewer-readonly-sandbox-verification.md`
  AND `just check`
- R2 -> manual content check per T2 (linter validates structure, not
  prose)
- R3 -> manual content check per T3
- R4 -> manual content check per T4
- R5 -> manual content check per T5
- R6 -> manual content check per T6
- R7 -> `git diff main -- docs/specs/reviewer-calibration-workflow.md`
  shows one additive sentence in Done When; no other line changes
- R8 -> `git diff main -- .codex/config.toml .claude/ scripts/hooks/
  pyproject.toml .reviewer-schema.json scripts/validate_reviewer.py
  .github/workflows/ docs/telemetry/` returns empty

## Edge Cases

- EC1: A maintainer runs the search commands and finds zero matches
  for `sandbox_mode` anywhere under `CODEX_HOME`. This is
  weak/inconclusive evidence — it may mean Codex changed where it
  records sandbox state, or that this maintainer's session was not
  the Reviewer invocation. Mitigation: rerun the Reviewer with a
  recognizable PR identifier, then search again with that identifier
  to scope results. If still no match, escalate — do not check the
  Phase 3 box.
- EC2: `rg "read-only" ~/.codex/` returns a match in a config-echo
  line that is not associated with the Reviewer invocation (e.g.
  Codex prints its config at startup unrelated to any specific
  agent). Per D3, this is weak evidence. Mitigation: require the
  match to co-occur with a Reviewer-scoped identifier (the agent
  name, the PR number, or the session ID associated with the
  Reviewer invocation).
- EC3: The maintainer overrode `CODEX_HOME` to a non-default path.
  All commands in the spec must be re-rooted at that path. The spec
  documents this via A2. Mitigation: A2 instructs substitution.
- EC4: Codex changes its on-disk layout between the time this spec
  is written and the time it is exercised. Per A3 and D4, the spec
  is deliberately written to survive this — the named paths are
  starting points, and the verification ultimately depends on a
  human grep across `CODEX_HOME`, not on any specific filename.
- EC5: A maintainer pastes the captured log excerpt into the PR
  body or a commit message. This is a confidentiality and
  prompt-injection-hygiene risk (the excerpt may contain
  agent reasoning traces or local paths). Mitigation: D2 and R6
  are explicit that the excerpt lives in `.scratch/` only.
  `scripts/scan_injection.py` will also independently scan
  committed content for known injection patterns.
- EC6: A future spec proposes to automate the read-only verification
  (e.g. a script that parses `~/.codex/session_index.jsonl` and
  asserts read-only-ness). That spec is out of scope here; NG1 is
  about *this* spec's scope, not a prohibition forever. A future
  automation spec is unblocked by this one.

## Security / Prompt-Injection Review

- source: human-authored Markdown only. The spec text is read by
  human maintainers; it does not flow into any LLM prompt at
  runtime. Captured log excerpts under `.scratch/` may contain
  agent reasoning traces (LLM output) and references to local
  paths, but those excerpts never enter version control (`.scratch/`
  is git-ignored).
- risk: low
- mitigation: not required for the committed spec. For the
  ephemeral excerpt, the structural mitigation is `.scratch/`'s
  git-ignored status; the procedural mitigation is R6 / D2
  forbidding promotion of the excerpt out of `.scratch/`.
  `scripts/scan_injection.py` runs over `docs/specs/` as part of
  `just check` and will independently reject the spec if any known
  injection pattern appears in the committed prose.

## Observability

None required from this spec. The verification *is* an
observability act — a human reading Codex's own session artifacts to
confirm runtime behavior — but the act produces no telemetry of its
own at this phase. Phase 5's `events.jsonl` is the appropriate home
if durable tracking of sandbox-confirmation outcomes becomes
desirable. Until then, the captured excerpt under `.scratch/` is the
only artifact, and it is ephemeral by design.

The runtime guarantee being observed: `sandbox_mode = "read-only"`
is enforced by the Codex runtime via `[agents.reviewer]` in
`.codex/config.toml`. The Reviewer's prompt cannot override or
relax this; only the runtime configuration can.

## Rollback / Recovery

Purely additive. To roll back, revert the commit that adds
`docs/specs/codex-reviewer-readonly-sandbox-verification.md` and
the one-line cross-link addition to
`docs/specs/reviewer-calibration-workflow.md`. No data, schema, or
runtime behavior depends on this spec; rollback is a no-op for the
running system.

## Implementation Slices

This spec implements as a single commit. There is no Slice 2.

1. **Slice 1 (single commit, T0):** On branch
   `spec/codex-reviewer-readonly-sandbox-verification`, add
   `docs/specs/codex-reviewer-readonly-sandbox-verification.md` and
   add the one-sentence cross-link in
   `docs/specs/reviewer-calibration-workflow.md` Done When. Run
   `just lint-spec docs/specs/codex-reviewer-readonly-sandbox-verification.md`,
   `uv run pre-commit run markdownlint-cli2 --files docs/specs/codex-reviewer-readonly-sandbox-verification.md docs/specs/reviewer-calibration-workflow.md`,
   and `just check` locally — all must exit 0. Open the PR; PR body
   links this spec; PR body carries the
   `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block per
   Invariant 1.

### Procedure (the workflow this spec documents)

The following is the human procedure for verifying the Reviewer
ran with read-only sandbox enforcement. It is the workflow a
maintainer executes at Phase 3 sign-off (and at any later moment
they suspect the Reviewer escaped its sandbox). It is *not* part of
the implementation steps of this spec.

1. **Run the Codex Reviewer on the PR that implements this spec.**
   Use the Reviewer subagent as configured in `.codex/config.toml`
   under `[agents.reviewer]`. Note the timestamp of the invocation
   and any PR identifier that will appear in session artifacts.
2. **Search for `sandbox_mode` evidence under `CODEX_HOME`.** With
   `CODEX_HOME` defaulting to `~/.codex` (substitute your override
   if any — see A2), run the following, treating them as starting
   points (A3 / D4):
   - `rg "sandbox_mode" ~/.codex/`
   - `rg "read-only" ~/.codex/`
   - `rg "reviewer" ~/.codex/`
   - `jq 'select(.agent == "reviewer")' ~/.codex/session_index.jsonl`
     (or a substantively equivalent filter against whichever
     index file the installed Codex version writes)

   Likely artifact paths to inspect: `~/.codex/history.jsonl`,
   `~/.codex/sessions/<date-folder>/`, and
   `~/.codex/session_index.jsonl`. Exact filenames and layout can
   drift across Codex versions.
3. **Classify the result as strong or weak/inconclusive evidence.**
   See Evidence Classification below. Only strong evidence
   satisfies the Phase 3 sign-off checkbox.
4. **Capture the relevant log excerpt into
   `.scratch/reviewer-calibration.md` only.** Do not paste it into
   the PR body, a commit message, an issue, or any tracked file.
   `.scratch/` is git-ignored; this is the structural protection
   against accidental disclosure of agent reasoning traces or local
   paths.

### Evidence Classification

- **Strong evidence.** A literal `sandbox_mode = "read-only"` (or
  the equivalent JSON encoding, e.g. `"sandbox_mode":"read-only"`)
  appears in a session artifact that is unambiguously associated
  with the Reviewer invocation from step 1 — for example, in a
  record that also carries the Reviewer's agent name, the
  invocation's session ID, or the PR identifier. This is the only
  bar that satisfies the Phase 3 sign-off checkbox.
- **Weak/inconclusive evidence.** Any of: a proximity match where
  `sandbox_mode` appears in the same file but is not bound to the
  Reviewer invocation; an ambient config echo printed at Codex
  startup unrelated to a specific agent; absence of write-attempt
  errors in the session log (absence of evidence is not evidence
  of absence); a `read-only` string that turns out to be from
  documentation or help text rather than the runtime's own state.
  None of these satisfy the sign-off checkbox. If only weak
  evidence is found, rerun step 1 with a scoped identifier and
  search again, or escalate.

## Done When

- [ ] R1–R8 all satisfied.
- [ ] D1–D5 preserved or any deviation noted in the PR.
- [ ] T1–T8 executed with the documented expected outcomes.
- [ ] Validation Contract satisfied: every `R*` maps to a passing
  validator.
- [ ] `just lint-spec docs/specs/codex-reviewer-readonly-sandbox-verification.md`
  exits 0.
- [ ] `uv run pre-commit run markdownlint-cli2 --files docs/specs/codex-reviewer-readonly-sandbox-verification.md docs/specs/reviewer-calibration-workflow.md`
  exits 0.
- [ ] `just check` green locally.
- [ ] CI green on the PR branch.
- [ ] Invariants INV1–INV7 hold.
- [ ] Branch name begins with `spec/` per AGENTS.md branch-name
  rules; the PR is opened from
  `spec/codex-reviewer-readonly-sandbox-verification`.
- [ ] PR description links this spec.
- [ ] PR body contains a
  `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block.
- [ ] The sibling spec at
  `docs/specs/reviewer-calibration-workflow.md` carries a single
  one-sentence cross-link to this spec in its Done When section
  (per R7); no other lines in that file change.
- [ ] Maintainers extending or revising the broader Phase 3
  calibration workflow consult this spec for the sandbox-verification
  half; see `docs/specs/reviewer-calibration-workflow.md` for the
  full workflow.
