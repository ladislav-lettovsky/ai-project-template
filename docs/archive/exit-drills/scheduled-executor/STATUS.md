# Scheduled executor exit drill — observation log

> Historical paths below cite `docs/specs/…` as at drill time. Shipped template specs
> now live under `docs/archive/template-specs/` (see `docs/archive/README.md`).

| Step | Signal | Result |
| --- | --- | --- |
| Fixture on `main` | `docs/specs/_drills/hello-world-fixture.md` drafted T0/low (later archived) | OK (merged #55) |
| Scheduler run | `workflow_dispatch` on `scheduled-executor.yml` | See run 1 below |
| Dispatch | PR opened for drill spec | OK via local dispatch → PR #56 |
| Router | Label on drill PR | `review:human` (see notes) |

## Run 1 — GitHub Actions (2026-05-19)

- **Workflow run:** [actions/runs/26080008734](https://github.com/ladislav-lettovsky/ai-project-template/actions/runs/26080008734)
- **Outcome:** Job green, but dispatch step failed silently (`pipefail` off). Selected
  `docs/archive/template-specs/router-smoke.md` (lexicographically before `_drills/`) and hit a
  relative-path bug in `dispatch_spec.py` when loading the spec from the workflow cwd.
- **Follow-up:** `fix/scheduled-executor-exit-drill-dispatch` — resolve spec paths against `--repo-root`,
  prefer `_drills/` eligible specs in the workflow `jq` sort, enable `set -o pipefail` on dispatch.

## Drill PR (exit criterion)

- **Drill PR:** [#56](https://github.com/ladislav-lettovsky/ai-project-template/pull/56)
- **Branch:** `spec/hello-world-fixture` (empty seed commit + stub PR body; later drills use
  `spec/test-hello-world`)
- **Body checks:** Links `docs/specs/_drills/hello-world-fixture.md` (since moved to archive); contains
  `dispatch-source: scheduled`; schema-valid `REVIEWER_JSON` stub.
- **Router label:** `review:human` — expected for placeholder Reviewer JSON (`confidence: 0`,
  `invariant_risk: high` in stub per policy). Not `review:codex`; drill still validates
  scheduler → open PR → Router handoff.
- **Dispatch path:** Local `uv run scripts/dispatch_spec.py --transport pr` after path fix
  (same code path CI uses post-fix). Re-run Actions after merging the fix PR to confirm
  end-to-end in CI.

## Notes

- Drill PR #56: **closed** without merge (2026-05-19).
- Spec housekeeping (2026-05-19): shipped specs set to `status: complete` so cron no
  longer treats them as queued; see `docs/specs/README.md` § Status lifecycle.

## Run 2 — GitHub Actions post-fix (2026-05-19)

- **Workflow run:** [actions/runs/26080166522](https://github.com/ladislav-lettovsky/ai-project-template/actions/runs/26080166522)
- **Outcome:** Failed (dispatch step exit 2; `pipefail` now surfaces errors). Drill spec skipped
  (`pr_exists` — PR #56 already open). Selected `docs/archive/template-specs/router-smoke.md`; empty seed
  commit failed (`git commit` exit 128 — missing `user.name` / `user.email` on runner checkout).
- **Follow-up:** Set git author in `seed_dispatch_branch` or workflow before dispatch.
