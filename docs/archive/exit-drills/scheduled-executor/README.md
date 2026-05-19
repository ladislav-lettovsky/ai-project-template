# Phase 6 exit drill kit

Observability checklist for
[Phase 6 exit criterion](../../template-specs/scheduled-executor.md)
(R10). Record outcomes in [`STATUS.md`](STATUS.md).

## Drill — scheduled dispatch → open PR → Router label

1. For a **new** drill run, copy or draft a fixture under `docs/specs/_drills/` with
   `status: drafted`, `risk_tier: T0`, `complexity: low`, all red-zone `no`. The shipped
   hello-world example is archived at
   [`hello-world-fixture.md`](hello-world-fixture.md) (`status: complete` — not queued).
2. Confirm no `spec/<drill-slug>` branch and no open PR citing the active fixture path.
3. Run **Actions → Phase 6 — Scheduled Executor → Run workflow** (`workflow_dispatch`).
4. Expect workflow summary: eligible ≥ 1, selected `docs/specs/_drills/<slug>.md` (or the
   path you placed), dispatch `pr_url` in summary.
5. Open the PR; confirm body links the spec, `dispatch-source: scheduled`, and valid
   `REVIEWER_JSON` stub; confirm `route-pr` labels `review:codex` (or note `review:human` /
   `blocked` if a gate fires).
6. Update `STATUS.md` with PR link, label, and workflow run URL.
7. Close the drill PR without merge unless you intend to land drill-only noise on `main`.

Local dry-run (no GitHub writes):

```bash
uv run scripts/queue_specs.py --json | jq '[.[] | select(.slug=="test-hello-world")]'
uv run scripts/dispatch_spec.py --spec docs/archive/exit-drills/scheduled-executor/hello-world-fixture.md --dry-run
```
