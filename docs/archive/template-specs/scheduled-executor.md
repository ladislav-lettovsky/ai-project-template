# Phase 6 — scheduled Executor for queued specs

## Metadata

- spec_id: SPEC-20260518-scheduled-executor
- owner: template
- status: complete
- complexity: high
- risk_tier: T2
- repo: ai-project-template
- branch: spec/scheduled-executor

## Context

Phase 5 shipped telemetry, MCP, and bounded adaptive thresholds. The
remaining endgame is Phase 6: a scheduled workflow that picks up specs
sitting in `docs/specs/` without a corresponding `spec/<slug>` branch or
PR and dispatches the Executor to implement them — closing the loop from
"spec authored" to "PR opened, reviewed, routed, merged" without a human
having to invoke the Executor by hand.

Today, a Planner-authored spec sits idle on `main` until someone runs
the Executor from a worktree. The scheduler removes that step for the
narrow lane already trusted by Phase 4 routing (T0 + low complexity) and
leaves higher tiers untouched. Phase 6 is the first time this repo
delegates *initiation* (not just review) to automation; the spec deliberately
narrows scope so that any failure is auditable, recoverable, and incapable
of merging consequential work without human eyes.

## Assumptions

- A1: Codex exposes a dispatch path callable from a GitHub Actions runner
  (async API, `codex exec` invoked in CI, or a self-hosted runner with the
  Codex CLI installed). The exact transport is selected by D1; the spec
  is structured so the rest of Phase 6 is transport-agnostic.
- A2: `record-telemetry.yml` (Phase 5) continues to write `events.jsonl`
  on every merge to `main`; the scheduler does not duplicate telemetry.
- A3: Branch protection on `main` already requires `route-pr` plus CI;
  auto-merge is gated by label `review:codex` per `CONTRIBUTING.md`.
- A4: `GITHUB_TOKEN` available to the workflow has `contents:write`,
  `pull-requests:write`, and `issues:write` — same scope the existing
  `route-pr.yml` and `record-telemetry.yml` already require.

## Decisions

- D1: **Dispatch transport (amended Slice 4).** v1 production path:
  `scripts/dispatch_spec.py --transport pr` — create `spec/<slug>` from
  `origin/main`, seed an empty commit when the branch still matches `main`,
  and open a PR via `gh pr create` with spec link + `dispatch-source:
  scheduled` + schema-valid `REVIEWER_JSON` stub. Spike notes:
  [`docs/archive/spikes/scheduled-executor-d1/NOTES.md`](../spikes/scheduled-executor-d1/NOTES.md). `codex exec`
  in Actions is **deferred** (needs `CODEX_API_KEY` + isolation); `--transport
  issue` remains a legacy fallback. Phase 6.1 may add Codex-in-CI after secrets
  exist.
- D2: **Eligibility = T0 + low only in v1.** Every spec the scheduler
  picks up must declare `risk_tier: T0` and `complexity: low`. T1+ is
  out of scope for v1; the workflow logs and skips them.
- D3: **v1 stops at "open PR".** Confirmed flow: Scheduler creates the
  branch, opens a PR whose body (a) links the authorizing spec and (b)
  contains an empty `<!-- REVIEWER_JSON --> <!-- /REVIEWER_JSON -->` fence
  so `validate_reviewer.py` and `route-pr.yml` see a well-formed (not yet
  populated) block and route correctly. From there the existing flow takes
  over: `route-pr.yml` labels the PR; a human or a locally-invoked Codex
  session runs the Reviewer and fills the fence. No Reviewer dispatch in
  this spec. Phase 6.1 scope (out of scope here): scheduled or
  PR-triggered Reviewer invocation, plus optional auto-merge when the
  PR carries `review:codex` and all CI checks pass.
- D4: **Queue discovery is filesystem-only.** A spec is "queued" when
  (i) `docs/specs/<slug>.md` exists on `main`, (ii) its metadata
  `status` is `drafted`, (iii) no branch named `spec/<slug>` and no open
  or merged PR cites the spec. Discovery is a pure Python script — no
  LLM, no heuristic — symmetric with Invariant 2.
- D5: **One spec per run, single concurrent execution per repo.** The
  workflow uses GitHub Actions `concurrency:` with `cancel-in-progress:
  false` and a fixed group name; the scheduler picks the
  lexicographically-first eligible spec and stops. Parallel execution
  is a Phase 6.1 concern; bounded throughput trades against simplicity.
- D6: **Failure is visible, not silent.** Any error (queue parse failure,
  ineligibility, dispatch failure, PR open failure) writes to the
  workflow summary AND opens or comments on a tracking issue tagged
  `scheduler-failure`. The blueprint's anti-pattern #1 (`|| true`) is
  explicitly forbidden in this workflow.

## Problem Statement

A spec at `docs/specs/<slug>.md` with `status: drafted` and no
corresponding `spec/<slug>` branch/PR remains idle until a human
invokes the Executor. There is no automated path from "Planner
committed a spec" to "Executor opens a PR" — every spec, including
trivially-T0/low ones, requires manual initiation. Phase 6's endgame
is to close that loop for the narrow lane already trusted by the
Router, while leaving the rest of the policy unchanged.

## Requirements (STRICT)

- [ ] R1: Add `scripts/queue_specs.py` that scans `docs/specs/*.md`
  (excluding `_template.md`, `_postmortem.md`, `README.md`) on `main`,
  parses each spec's Metadata block, and emits a JSON list of "queued"
  spec descriptors. A spec is queued when `status` is `drafted` AND no
  branch named `spec/<slug>` exists on the remote AND no open or merged
  PR references the spec path in its body.
- [ ] R2: `queue_specs.py` filters the queue by eligibility: only
  `risk_tier: T0` AND `complexity: low` AND every Red-Zone Assessment
  axis `no` are returned as eligible. Ineligible specs are reported with
  a `skip_reason` field but never dispatched.
- [ ] R3: Add `scripts/dispatch_spec.py` that, given a single eligible
  spec descriptor, performs the v1 dispatch action: (a) create a remote
  branch `spec/<slug>` off the current `main` tip if it does not exist,
  (b) per D1, either invoke the chosen Codex transport OR open a
  tracking issue tagged `scheduler-queue` documenting the queued spec.
  When opening a PR, the body MUST (i) link the authorizing spec path
  and (ii) include an empty `<!-- REVIEWER_JSON --> <!-- /REVIEWER_JSON -->`
  fence so `validate_reviewer.py` and `route-pr.yml` treat it as
  well-formed. The script never writes to red-zone files and never
  executes Codex in the same job as the workflow's own GITHUB_TOKEN-scoped
  steps without an isolation boundary (separate job or container).
- [ ] R4: Add `.github/workflows/scheduled-executor.yml`. Triggers:
  `schedule:` cron (weekdays 09:00 UTC) and `workflow_dispatch:`. Steps:
  checkout `main`, `uv sync`, run `queue_specs.py`, select the
  lexicographically-first eligible spec, call `dispatch_spec.py`, write
  a summary, and (on failure) open or comment on a `scheduler-failure`
  tracking issue. Concurrency group `scheduled-executor` with
  `cancel-in-progress: false`. The workflow MUST NOT run on PRs from
  forks (event-trigger restriction).
- [ ] R5: Add a `dispatch_source` field to `docs/telemetry/events.jsonl`
  schema (documented in `docs/telemetry/README.md`) with values
  `manual` (default) and `scheduled`. The existing `append_event.py`
  reads the dispatching branch's commit trailer or PR body marker
  `dispatch-source: scheduled` to set the field; absence means
  `manual`. No backfill of historical rows.
- [ ] R6: Update `CONTRIBUTING.md` with a scheduled-executor section explaining
  the scheduler's eligibility gate (D2), the v1 stop-at-open-PR
  behavior (D3), the failure-visibility contract (D6), and how to
  disable the workflow (rollback).
- [ ] R7: Update `docs/blueprint.md` to mark scheduled-executor status (still
  in-progress until D1 spike resolves; `[implemented]` after the
  exit drill in R10 lands a dry-run PR).
- [ ] R8: Add deterministic tests covering: queue discovery (fixture
  specs with varying status / risk_tier / complexity / red-zone
  values), eligibility filtering (only T0+low+all-no eligible),
  dispatcher dry-run mode (no remote calls; asserts intended payload),
  and the events.jsonl schema extension (round-trip with
  `dispatch_source` present and absent).
- [ ] R9: The new workflow YAML passes `actionlint` (if installed
  pre-commit) and explicitly never contains `|| true`, `continue-on-error:
  true`, or any other failure-swallowing pattern. CI gates that already
  reject `|| true` continue to apply.
- [ ] R10: **Exit drill.** One T0+low fixture spec is queued, picked
  up by the scheduler (via `workflow_dispatch:` to avoid waiting on
  cron), dispatched via the chosen D1 transport, and a PR opens. The
  existing Router labels it `review:codex` (or `review:human` if the
  drill spec triggers a gate, which is informative — log the result).
  The drill outcome is recorded in `docs/archive/exit-drills/scheduled-executor/STATUS.md`
  with the PR link.

## Non-Goals

- [ ] NG1: Parallel execution of multiple specs in a single workflow
  run. Single-spec-per-run is the v1 contract.
- [ ] NG2: Planner auto-drafting specs from issues. The Planner remains
  human-invoked; the spec file must already exist on `main` to be
  queued.
- [ ] NG3: Auto-dispatch for `risk_tier: T1`, `T2`, or `T3`, or for
  any spec with a `yes` in Red-Zone Assessment.
- [ ] NG4: Auto-merge for any PR opened by the scheduler. Merge remains
  governed by Phase 4 routing + branch protection; this spec changes
  nothing in `route_pr.py` or `.routing-policy.json`.
- [ ] NG5: Reviewer dispatch or auto-merge. v1 leaves the PR open for
  a human or locally-invoked Codex session to populate the Reviewer
  fence and merge. Phase 6.1 scope (deferred): scheduled or
  PR-triggered Reviewer invocation, and optional auto-merge when the
  PR carries `review:codex` and all CI checks pass.
- [ ] NG6: Replacing or extending `scan_injection.py`. The scheduler
  consumes already-scanned spec content; no new injection surface is
  introduced beyond what specs and PR bodies already represent.

## Interfaces

New files:

- `scripts/queue_specs.py` — CLI: `uv run scripts/queue_specs.py
  [--remote origin] [--json]`. Exits 0 with JSON list on stdout.
- `scripts/dispatch_spec.py` — CLI: `uv run scripts/dispatch_spec.py
  --spec <path> [--dry-run] [--transport issue|codex]`. Exits 0 on
  successful dispatch.
- `.github/workflows/scheduled-executor.yml` — scheduled + dispatch
  workflow.
- `tests/test_queue_specs.py`, `tests/test_dispatch_spec.py`,
  `tests/test_events_schema_dispatch_source.py`,
  `tests/test_scheduled_executor_yaml.py` (smoke-parses the YAML).
- `docs/archive/exit-drills/scheduled-executor/README.md` and `docs/archive/exit-drills/scheduled-executor/STATUS.md`
  — drill kit and observation log, modelled on `docs/archive/exit-drills/router/`.

Modified files:

- `docs/telemetry/README.md` — `dispatch_source` field documented.
- `scripts/append_event.py` — populate `dispatch_source` when the
  source PR carries the trailer.
- `CONTRIBUTING.md` — scheduled-executor section.
- `docs/blueprint.md` — scheduled-executor / Codex-in-CI status pointer.

No modifications to: `scripts/route_pr.py`, `.routing-policy.json`,
`.reviewer-schema.json`, `scripts/lint_spec.py`,
`scripts/scan_injection.py`, `.codex/config.toml`.

## Invariants to Preserve

- [ ] INV1: Invariant 1 — every PR opened by the scheduler carries a
  branch name `spec/<slug>` matching the spec file, and the PR body
  links the spec path. Validates against Invariant 9 (path matches
  slug).
- [ ] INV2: Invariant 2 — routing remains deterministic Python; this
  spec adds no LLM call to the Router and no policy change.
- [ ] INV3: Invariant 4 — `uv`, `ty`, `just`, `pytest`, pre-commit, and
  strict CI remain unchanged. The new workflow uses the same `uv sync`
  and `just check` pattern as existing workflows.
- [ ] INV4: Invariant 6 — only T0+low specs are auto-dispatched;
  higher tiers always require human initiation, mirroring auto-review
  eligibility.
- [ ] INV5: Invariant 7 — the new workflow YAML lives under
  `.github/workflows/`, a red-zone path. The hook continues to block
  Edit/Write from agent sessions; human terminal edits only.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: yes — new scheduled workflow file under `.github/workflows/`
- migrations: no
- secrets: yes — workflow may consume new `CODEX_*` or PAT secrets per D1
- infra: yes — introduces a recurring scheduled job that mutates branches and opens PRs
- invariant-protected files: yes — `.github/workflows/`, `CONTRIBUTING.md`, and `docs/blueprint.md`

> Multiple `yes` axes. `risk_tier` is T2 in Metadata. Implementation
> Slices call out the human-edit boundary for the workflow YAML and
> any secrets documentation.

## Test Plan

- [ ] T1 -> covers R1
- [ ] T2 -> covers R2
- [ ] T3 -> covers R3
- [ ] T4 -> covers R4, R9
- [ ] T5 -> covers R5
- [ ] T6 -> covers R6
- [ ] T7 -> covers R7
- [ ] T8 -> covers R8
- [ ] T9 -> covers R10

## Validation Contract

- R1 -> `uv run pytest tests/test_queue_specs.py -q`
- R2 -> `uv run pytest tests/test_queue_specs.py::test_eligibility_filter -q`
- R3 -> `uv run pytest tests/test_dispatch_spec.py -q`
- R4 -> `uv run pytest tests/test_scheduled_executor_yaml.py -q` AND
  `test -f .github/workflows/scheduled-executor.yml`
- R5 -> `uv run pytest tests/test_events_schema_dispatch_source.py -q`
- R6 -> `grep -qi 'scheduled executor' CONTRIBUTING.md`
- R7 -> `grep -qiE 'scheduled executor.*implemented|codex in ci.*implemented' docs/blueprint.md`
- R8 -> `uv run pytest tests/test_queue_specs.py tests/test_dispatch_spec.py tests/test_events_schema_dispatch_source.py tests/test_scheduled_executor_yaml.py -q`
- R9 -> `! grep -E '\|\| true|continue-on-error: true' .github/workflows/scheduled-executor.yml`
- R10 -> `test -f docs/archive/exit-drills/scheduled-executor/STATUS.md` AND drill PR linked in `STATUS.md`
- FULL -> `just check`

## Edge Cases

- EC1: Empty queue (no `drafted` specs on `main`) — workflow exits 0,
  writes "no eligible specs" to summary, opens no issue.
- EC2: Eligible spec found but a `spec/<slug>` branch already exists
  on remote — workflow treats the spec as in-flight and skips it; no
  duplicate dispatch.
- EC3: Spec status is `drafted` but `risk_tier: T1` — skipped with
  `skip_reason: risk_tier_ineligible`; ineligibility is reported, not
  failed.
- EC4: Spec metadata is malformed (lint would fail) — `queue_specs.py`
  skips the spec with `skip_reason: metadata_invalid` and surfaces it
  in the workflow summary; the spec is never silently dispatched.
- EC5: GitHub API rate limit or transient error in `dispatch_spec.py`
  — workflow fails loudly, opens a `scheduler-failure` issue, and does
  not retry within the same run. Cron picks up the next attempt.
- EC6: Two T0+low specs eligible in the same run — only the
  lexicographically-first one is dispatched (D5); the second waits for
  the next cron tick.
- EC7: `workflow_dispatch:` triggered while a previous run is in flight
  — concurrency group with `cancel-in-progress: false` queues the new
  invocation rather than racing.

## Security / Prompt-Injection Review

- source: spec files on `main` (already scanned by
  `scripts/scan_injection.py` as part of `just check`); GitHub PR/issue
  bodies consulted by `queue_specs.py` to detect existing PRs (read
  via the GitHub REST API, never passed to an LLM by this spec's
  code); Codex prompt content per D1 (only the spec file path and
  the spec body — both already scanned).
- risk: medium
- mitigation: queue discovery and dispatch are pure Python with no
  LLM calls. PR/issue body content from the GitHub API is only used
  to detect *presence* (string match on the spec path); body text is
  never echoed into the dispatched Codex prompt. The Executor's prompt
  is the spec file itself, which has already passed
  `scripts/scan_injection.py` at spec-commit time. Any new injection
  surface introduced by D1's chosen transport must be re-evaluated
  in the spike note that amends D1 before the workflow merges.

## Observability

- Workflow summary on every run lists: queue size, eligible count,
  selected spec slug (or "none"), dispatch outcome, and a link to any
  opened PR or tracking issue.
- Failures open or comment on a `scheduler-failure` issue with the
  workflow run URL and a short excerpt of the failing step.
- Telemetry: `events.jsonl` gains a `dispatch_source` field (R5);
  merged scheduler-dispatched PRs are distinguishable from manual
  ones in `docs/telemetry/dashboard.md` after `telemetry_dashboard.py`
  is taught to bucket by source (deferred to a Phase 6.1 spec — this
  spec only ships the schema field, per NG-scope discipline).
- No new logs in `src/`. No new metric exporter. No new traces.

## Rollback / Recovery

- Disable the workflow: rename `.github/workflows/scheduled-executor.yml`
  to `.github/workflows/scheduled-executor.yml.disabled` (GitHub stops
  scheduling) or delete the file entirely.
- Revert telemetry-schema change: revert the commit that added
  `dispatch_source` to `docs/telemetry/README.md` and
  `scripts/append_event.py`. `events.jsonl` rows that include the
  field remain readable (forward-compatible per the same logic in
  blueprint §5.4 for the Reviewer schema).
- Revert documentation: revert the `CONTRIBUTING.md` and
  `docs/blueprint.md` edits.
- If the scheduler opens an unwanted PR: close it; the PR's branch can
  be deleted. No data outside Git is mutated by this spec.

## Implementation Slices

1. **Slice 1 — queue and dispatcher (R1, R2, R3, R8).** Land
   `scripts/queue_specs.py`, `scripts/dispatch_spec.py`, and their
   tests. No workflow yet; both scripts have a `--dry-run` mode for
   local exercise. Pure-Python, no red-zone files touched.
2. **Slice 2 — telemetry schema (R5, R8).** Add `dispatch_source` to
   `docs/telemetry/README.md` and `scripts/append_event.py`. New
   test. Still no workflow.
3. **Slice 3 — workflow + docs (R4, R6, R7, R9).** Add
   `.github/workflows/scheduled-executor.yml`, update
   `CONTRIBUTING.md`, update `docs/blueprint.md`. This slice touches
   red-zone files — human terminal session, not an agent edit. PR
   will route `review:human`.
4. **Slice 4 — D1 spike + amendment.** Land the dispatch-transport
   spike notes; amend D1 in this spec with the chosen path; replace
   the v1 "open tracking issue" fallback in `dispatch_spec.py` with
   the chosen transport.
5. **Slice 5 — exit drill (R10).** Author a trivial T0+low fixture
   spec (e.g., a `docs/specs/_drills/hello-world.md`), commit it on
   `main`, trigger the scheduler via `workflow_dispatch:`, observe
   the PR open and route, and record the outcome in
   `docs/archive/exit-drills/scheduled-executor/STATUS.md`. Mark scheduled executor implemented in
   `docs/blueprint.md`.

## Done When

- [ ] All requirement IDs R1–R10 satisfied
- [ ] Decision IDs D1–D6 preserved or explicitly amended (D1 in particular)
- [ ] Tests mapped and passing (T1–T9)
- [ ] Validation Contract satisfied
- [ ] `just check` passes
- [ ] CI green
- [ ] No invariant violations (INV1–INV5)
- [ ] Branch name starts with `spec/scheduled-executor` (Invariant 1)
- [ ] PR description links this spec (Invariant 9)
- [ ] PR body contains `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block
- [ ] Exit drill PR recorded in `docs/archive/exit-drills/scheduled-executor/STATUS.md`
- [ ] Blueprint scheduled-executor status updated from "in-progress" to "implemented"
