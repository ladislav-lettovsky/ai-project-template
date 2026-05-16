# Phase 4 exit drill B — human (red-zone)

## Metadata

- spec_id: SPEC-20260516-phase4-exit-human-redzone
- owner: template
- status: drafted
- complexity: low
- risk_tier: T1
- repo: ai-project-template
- branch: spec/phase4-exit-human-redzone

## Context

Exit drill: `review:human` when the diff touches `AGENTS.md`. PR body uses
`docs/phase4-exit-drills/human-redzone-pr-body.md`.

## Assumptions

- A1: `AGENTS.md` is in the router red-zone list.

## Decisions

- D1: Revert or replace the AGENTS drill line before merge if undesired.

## Problem Statement

Blueprint requires observing human routing for a red-zone touch.

## Requirements (STRICT)

- [ ] R1: PR touching `AGENTS.md` with valid Reviewer JSON receives `review:human`
  citing red-zone and a router comment.

## Non-Goals

- [ ] NG1: Merging the AGENTS drill line to `main` unless intentional.

## Interfaces

- `AGENTS.md` (minimal drill edit)
- `docs/specs/phase4-exit-human-redzone.md`

## Invariants to Preserve

- [ ] INV1: Drill PR is observation-only.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: yes

## Test Plan

- [ ] T1 -> covers R1

## Validation Contract

- R1 -> manual: PR label `review:human` with red-zone reason on GitHub

## Edge Cases

- EC1: Invalid spec lint routes human before red-zone — branch must include this spec file.

## Security / Prompt-Injection Review

- source: hand-authored PR body
- risk: low
- mitigation: not required

## Observability

`docs/phase4-exit-drills/STATUS.md`

## Rollback / Recovery

Close PR; revert AGENTS drill line.

## Implementation Slices

1. Open PR with human-redzone body.

## Done When

- [ ] R1 observed on GitHub
