# Scheduler smoke — hello world drill

## Metadata

- spec_id: SPEC-20260519-test-hello-world
- owner: template
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/test-hello-world

## Context

Standing T0/low fixture so **Scheduled Executor** runs have an eligible spec when
operators trigger `workflow_dispatch` or weekday cron fires. No production code
changes are intended — only branch + PR initiation (and optional Codex agents when
`OPENAI_API_KEY` is configured). Historical exit-drill notes remain under
`docs/archive/exit-drills/scheduled-executor/` (archived fixture name `phase6-hello-world`).

## Assumptions

- A1: Fixture stays `status: drafted` while used for scheduler smoke; set `complete` or
  move to archive when retiring from the queue.

## Decisions

- D1: No implementation beyond an empty seed commit on `spec/test-hello-world`.

## Problem Statement

Provide an always-eligible (when no competing drafted T0/low specs) target so the
scheduler queue is non-empty for manual verification of dispatch and optional
`codex_agents`.

## Requirements (STRICT)

- [ ] R1: `queue_specs.py` reports this spec as eligible when no `spec/test-hello-world`
  branch exists and no open/merged PR cites `docs/specs/_drills/test-hello-world.md`.
- [ ] R2: `dispatch_spec.py` can open a PR linking this spec with a schema-valid
  `REVIEWER_JSON` stub.

## Non-Goals

- [ ] NG1: Land application code in `src/`.
- [ ] NG2: Require auto-merge (`SCHEDULER_AUTO_MERGE` remains optional).

## Interfaces

- `docs/specs/_drills/test-hello-world.md` — this file only.

## Invariants to Preserve

- [ ] INV1: Drill PR diff must not touch red-zone paths (seed commit only).

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no

## Test Plan

- [ ] T1 -> covers R1
- [ ] T2 -> covers R2

## Validation Contract

- R1 -> `uv run scripts/queue_specs.py --json` includes eligible `test-hello-world`
- R2 -> `uv run scripts/dispatch_spec.py --spec docs/specs/_drills/test-hello-world.md --dry-run --transport pr`

## Edge Cases

- EC1: Another eligible drafted spec sorts before this path lexicographically — only one
  spec dispatches per run; temporarily set the other to `complete` or remove it for smoke.
- EC2: Leftover `spec/test-hello-world` or legacy `spec/phase6-hello-world` branch or open
  PR — spec is ineligible until branch/PR is closed and deleted.

## Security / Prompt-Injection Review

- source: none (fixture spec only)
- risk: low
- mitigation: not required

## Observability

Manual runs: workflow summary on **Scheduled Executor**. Merged drill PRs append
`dispatch_source: scheduled` via existing telemetry.

## Rollback / Recovery

Close smoke PR; delete remote `spec/test-hello-world`. Set `status: complete` or move
this file to `docs/archive/exit-drills/scheduled-executor/` to stop cron from re-queuing.

## Implementation Slices

1. Slice 1: Keep fixture on `main` under `_drills/`; operators run workflow manually.

## Done When

- [ ] `just lint-spec docs/specs/_drills/test-hello-world.md` passes
- [ ] At least one successful `workflow_dispatch` selects this spec (or documents skip_reason in run log)
