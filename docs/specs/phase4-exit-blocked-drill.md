# Phase 4 exit drill C — blocked

## Metadata

- spec_id: SPEC-20260516-phase4-exit-blocked-drill
- owner: template
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/phase4-exit-blocked-drill

## Context

Exit drill for blueprint Phase 4: observe `blocked` when Reviewer JSON contains
a `critical` finding. PR body uses `docs/phase4-exit-drills/blocked-pr-body.md`.

## Assumptions

- A1: `route-pr` workflow is enabled on PRs to `main`.

## Decisions

- D1: Close PR after observing `blocked` label; do not merge.

## Problem Statement

Need one recorded `blocked` routing outcome on a real PR.

## Requirements (STRICT)

- [ ] R1: Same-repo PR with valid Reviewer JSON including a `critical` finding
  receives label `blocked` and a router reasons comment.

## Non-Goals

- [ ] NG1: Merging this drill PR.

## Interfaces

- `docs/specs/phase4-exit-blocked-drill.md` (this file)

## Invariants to Preserve

- [ ] INV1: `just check` passes on branches that only add docs.

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

- R1 -> manual: PR label `blocked` and router comment on GitHub

## Edge Cases

- EC1: Spec lint on branch must pass so router reaches critical-finding gate.

## Security / Prompt-Injection Review

- source: hand-authored drill PR body
- risk: low
- mitigation: not required

## Observability

Record in `docs/phase4-exit-drills/STATUS.md`.

## Rollback / Recovery

Close PR without merge.

## Implementation Slices

1. Open PR with `blocked-pr-body.md` as description.

## Done When

- [ ] R1 observed on GitHub
