# Scheduler drill fixtures (optional)

Place **active** exit-drill specs here while they should be queueable (`status: drafted`,
T0/low, all red-zone `no`). `scripts/queue_specs.py` and the scheduled executor scan
this subdirectory together with top-level `docs/specs/*.md`.

## Standing smoke fixture

[`phase6-hello-world.md`](phase6-hello-world.md) — T0/low `drafted` spec for manual
**Scheduled Executor** runs and weekday cron when no other eligible specs exist.

Before re-running smoke, ensure:

- No open PR whose body cites `docs/specs/_drills/phase6-hello-world.md`
- No remote branch `spec/phase6-hello-world` (delete after closing the smoke PR)

When retiring the fixture from the queue, set `status: complete` or move the file to
[`docs/archive/exit-drills/phase6/`](../../archive/exit-drills/phase6/). Historical
exit-drill status: [`STATUS.md`](../../archive/exit-drills/phase6/STATUS.md).
