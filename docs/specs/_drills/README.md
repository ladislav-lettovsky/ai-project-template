# Scheduler drill fixtures (optional)

Place **active** exit-drill specs here while the drill runs (`status: drafted`,
T0/low, all red-zone `no`). `scripts/queue_specs.py` and the scheduled executor scan
this subdirectory together with top-level `docs/specs/*.md`.

When a drill finishes, move the fixture to `docs/archive/exit-drills/<kit>/` and
set `status: complete` so cron does not re-open it. The scheduled-executor hello-world fixture
lives at [`docs/archive/exit-drills/phase6/phase6-hello-world.md`](../../archive/exit-drills/phase6/phase6-hello-world.md).
