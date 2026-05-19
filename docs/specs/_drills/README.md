# Scheduler drill fixtures (optional)

Place **active** drill specs here while they should be queueable (`status: drafted`,
T0/low, all red-zone `no`). `scripts/queue_specs.py` and the scheduled executor scan
this subdirectory together with top-level `docs/specs/*.md`.

## Standing smoke fixture

[`test-hello-world.md`](test-hello-world.md) — T0/low `drafted` spec for manual
**Scheduled Executor** runs and weekday cron when no other eligible specs exist.
Dispatches to branch `spec/test-hello-world`.

Before re-running smoke, ensure:

- No open PR whose body cites `docs/specs/_drills/test-hello-world.md`
- No remote branch `spec/test-hello-world` (delete after closing the smoke PR)
- No stale drill branches besides the current smoke branch (delete leftover `spec/*` after closing drill PRs)

When retiring the fixture from the queue, set `status: complete` or move the file to
[`docs/archive/exit-drills/phase6/`](../../archive/exit-drills/phase6/). Historical
exit-drill status: [`STATUS.md`](../../archive/exit-drills/phase6/STATUS.md).
