# Phase 6 exit drill kit

Observability checklist for [Phase 6 exit criterion](../specs/phase6-scheduled-executor.md)
(R10). Record outcomes in [`STATUS.md`](STATUS.md).

## Drill — scheduled dispatch → open PR → Router label

1. Ensure [`docs/specs/_drills/phase6-hello-world.md`](../specs/_drills/phase6-hello-world.md)
   is on `main` with `status: drafted`, `risk_tier: T0`, `complexity: low`, all red-zone `no`.
2. Confirm no `spec/phase6-hello-world` branch and no open/merged PR citing that spec path.
3. Run **Actions → Phase 6 — Scheduled Executor → Run workflow** (`workflow_dispatch`).
4. Expect workflow summary: eligible ≥ 1, selected `docs/specs/_drills/phase6-hello-world.md`,
   dispatch `pr_url` in summary.
5. Open the PR; confirm body links the spec, `dispatch-source: scheduled`, and valid
   `REVIEWER_JSON` stub; confirm `route-pr` labels `review:codex` (or note `review:human` /
   `blocked` if a gate fires).
6. Update `STATUS.md` with PR link, label, and workflow run URL.
7. Close the drill PR without merge unless you intend to land drill-only noise on `main`.

Local dry-run (no GitHub writes):

```bash
uv run scripts/queue_specs.py --json | jq '[.[] | select(.slug=="phase6-hello-world")]'
uv run scripts/dispatch_spec.py --spec docs/specs/_drills/phase6-hello-world.md --dry-run
```
