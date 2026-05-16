# Phase 4 Router — exit drill kit

Observability checklist for [blueprint Phase 4 exit criteria](../blueprint.md)
(§4). Record outcomes in [`STATUS.md`](STATUS.md).

## Drill A — `review:codex` (done)

Observed on PR **#39** (`review:codex`, router comment *All policy thresholds satisfied*).

## Drill B — `review:human` (red-zone touch) — observed on [#42](https://github.com/ladislav-lettovsky/ai-project-template/pull/42)

1. Branch `spec/phase4-exit-human-redzone` from `main` (single spec + `AGENTS.md` only).
2. Make a **minimal** edit to `AGENTS.md` (human terminal — red-zone for agents).
3. Open PR with schema-valid JSON from [`human-redzone-pr-body.md`](human-redzone-pr-body.md).
4. Confirm label **`review:human`** and comment citing red-zone / policy.
5. **Do not merge** unless intentional; close after observation.
6. Update `STATUS.md` with PR number.

## Drill C — `blocked` (critical finding) — observed on [#41](https://github.com/ladislav-lettovsky/ai-project-template/pull/41)

1. Branch `spec/phase4-exit-blocked-drill` from `main` with **only**
   `docs/specs/phase4-exit-blocked-drill.md` (no second authorizing spec in diff)
   (e.g. one-line change under `docs/phase4-exit-drills/`).
2. Open PR; paste body from [`blocked-pr-body.md`](blocked-pr-body.md) (valid JSON + **critical** finding).
3. Confirm label **`blocked`** and router comment.
4. Close without merge; update `STATUS.md`.

Validate bodies locally:

```bash
just validate-reviewer docs/phase4-exit-drills/blocked-pr-body.md
just validate-reviewer docs/phase4-exit-drills/human-redzone-pr-body.md
```
