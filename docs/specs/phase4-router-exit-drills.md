# Phase 4 Router — exit criteria closure

## Metadata

- spec_id: SPEC-20260516-phase4-router-exit-drills
- owner: template
- status: in-progress
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/phase4-exit-drills

## Context

Phase 4 Router shipped in #37. Smoke PRs proved `review:codex` (#39) and
`review:human` via invalid JSON (#38). Blueprint exit criteria still require
documented observation of **`review:human` for a red-zone touch** (e.g.
`AGENTS.md`) and **`blocked` for a critical Reviewer finding**, plus repo
docs marking Phase 4 complete.

## Assumptions

- A1: `route-pr` workflow remains enabled on PRs to `main`.
- A2: Drill PRs are opened from same-repo branches so labels are applied.

## Decisions

- D1: Drill kit lives under `docs/phase4-exit-drills/` with copy-paste PR bodies
  and a `STATUS.md` observation log — not under `.scratch/` (durable traceability).
- D2: Red-zone `AGENTS.md` edit for drill B is human-authored (Invariant 7).

## Problem Statement

Without a recorded observation log and drill templates, Phase 4 exit criteria
are ambiguous and easy to declare “done” without exercising `blocked` or
red-zone `review:human` on GitHub.

## Requirements (STRICT)

- [ ] R1: Add `docs/phase4-exit-drills/` with `README.md`, `STATUS.md`, and
  schema-valid PR body templates for drills B (`human-redzone`) and C (`blocked`).
- [ ] R2: Update `docs/blueprint.md` to mark Phase 4 **implemented** and list
  exit-criteria status with links to `STATUS.md`.
- [ ] R3: Extend `CONTRIBUTING.md` with GitHub **branch protection** guidance
  for `route-pr` + automerge vs label semantics (deliverable #4).
- [ ] R4: Complete drills B and C on GitHub; update `STATUS.md` with PR numbers,
  labels, and confirmation of router comments.

## Non-Goals

- [ ] NG1: Phase 5 telemetry (`append_event.py`, `events.jsonl`).
- [ ] NG2: Changing router code, policy, or workflow for drills.

## Interfaces

- `docs/phase4-exit-drills/**` (new)
- `docs/specs/phase4-router-exit-drills.md` (this file)
- `docs/blueprint.md`, `CONTRIBUTING.md` (docs only)

## Invariants to Preserve

- [ ] INV1: `just check` green after doc-only changes on this branch.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no on this branch; drill B touches `AGENTS.md` on a **separate** branch only

## Test Plan

- [ ] T1 -> covers R1, R2, R3
- [ ] T2 -> covers R4

## Validation Contract

- R1 -> `just validate-reviewer docs/phase4-exit-drills/blocked-pr-body.md` and `human-redzone-pr-body.md` exit 0
- R2 -> `grep -q 'Phase 4 (implemented)' docs/blueprint.md`
- R3 -> `grep -q 'Branch protection' CONTRIBUTING.md` (Phase 4 Router section)
- R4 -> `STATUS.md` lists PR links for all three outcome rows
- FULL -> `just check`

## Edge Cases

- EC1: Drill PRs closed without merge — acceptable; observation is the deliverable.

## Security / Prompt-Injection Review

- source: hand-authored drill PR bodies in-repo
- risk: low
- mitigation: not required

## Observability

`STATUS.md` is the observation log.

## Rollback / Recovery

Revert doc commits; close drill PRs without merge.

## Implementation Slices

1. Land drill kit + blueprint/CONTRIBUTING updates (R1–R3).
2. Run drills B and C; fill `STATUS.md` (R4).

## Done When

- [ ] R1–R4 satisfied; `just check` green; blueprint shows Phase 4 implemented.
