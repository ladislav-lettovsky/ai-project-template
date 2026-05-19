# Phase 6 exit drill — hello world

## Metadata

- spec_id: SPEC-20260519-hello-world-fixture
- owner: template
- status: complete
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/hello-world-fixture

## Context

Trivial T0/low fixture for Phase 6 exit drill (R10). The scheduled executor should
queue and dispatch this spec; no production code changes are intended. Archived under
`docs/archive/exit-drills/scheduled-executor/` after the drill completed so cron does not re-queue it.

## Assumptions

- A1: Drill runs only on the template repo with Phase 6 workflow enabled.

## Decisions

- D1: No implementation beyond an empty seed commit on `spec/hello-world-fixture` (legacy branch `spec/phase6-hello-world`).

## Problem Statement

Validate scheduler → open PR → Router handoff without touching red-zone files.

## Requirements (STRICT)

- [ ] R1: Scheduler selects this spec when it is the only eligible drafted T0/low fixture.

## Non-Goals

- [ ] NG1: Land application code.
- [ ] NG2: Auto-merge or automated Reviewer.

## Interfaces

- `docs/archive/exit-drills/scheduled-executor/hello-world-fixture.md` — this file only.

## Invariants to Preserve

- [ ] INV1: No red-zone paths in the drill PR diff (empty or seed commit only).

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

## Validation Contract

- R1 -> `workflow_dispatch` on `scheduled-executor.yml` with drill recorded in `docs/archive/exit-drills/scheduled-executor/STATUS.md`

## Edge Cases

- EC1: Another eligible spec sorts before `hello-world-fixture` lexicographically — drill waits or temporarily ineligible the other spec.

## Security / Prompt-Injection Review

- source: none (fixture spec only)
- risk: low
- mitigation: not required

## Observability

Exit drill log in `docs/archive/exit-drills/scheduled-executor/STATUS.md`.

## Rollback / Recovery

Close drill PR; delete the drill branch (`spec/test-hello-world` or legacy `spec/phase6-hello-world`). Fixture remains in this archive path.

## Implementation Slices

1. Slice 1: Merge fixture on `main`; run exit drill; update `STATUS.md`.

## Done When

- [ ] Exit drill recorded in `docs/archive/exit-drills/scheduled-executor/STATUS.md`
