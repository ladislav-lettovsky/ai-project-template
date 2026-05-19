# Documentation archive

Historical material for the **ai-project-template** repo itself — not
authorizing specs for new product work on a fork.

**Naming:** paths and filenames use **capability slugs** only (for example
`router-smoke.md`, `exit-drills/router/`). Rollout order and “Phase N” labels
live in [`docs/blueprint.md`](../blueprint.md), not in archive paths.

## `template-specs/`

Completed (and superseded) specs that built the template through Phases 0–6:
Router, telemetry, scheduled executor, lint gates, planner-tightening backlog,
and similar. They remain in git as an audit trail and as lint/regression examples
(`add-greet-module.md` is one §5.1 regression target for `lint_spec.py` tests).
Demo Python modules were removed from `src/` — forks start with an empty package
shell (`__init__.py` only).

## `exit-drills/`

Router and scheduled-executor **exit drill kits** — `README.md`, `STATUS.md`, and PR
body templates used to verify Router and scheduler handoffs. Not authorizing work on a
fork; kept on the living template as observability history.

- [`exit-drills/router/`](exit-drills/router/) — Router `review:codex` / `review:human` / `blocked`
- [`exit-drills/scheduled-executor/`](exit-drills/scheduled-executor/) — scheduled executor drill log and
  [`hello-world-fixture.md`](exit-drills/scheduled-executor/hello-world-fixture.md) fixture (`status: complete`)

## `spikes/`

Time-boxed investigation notes (e.g. scheduled-executor D1 dispatch transport).

- [`spikes/scheduled-executor-d1/NOTES.md`](spikes/scheduled-executor-d1/NOTES.md)

**Active specs** live in [`docs/specs/`](../specs/) only (`_template.md`,
`_postmortem.md`, optional examples, and work in progress).

### Forking this template

If you start a new project from this repo, you usually do not need this history:

```bash
rm -rf docs/archive
```

Also see [`docs/post-fork-checklist.md`](../post-fork-checklist.md) §9 (trim specs,
disable scheduler if unused). Keep `docs/specs/_template.md` and `docs/specs/README.md`.

### Metadata note

Spec files may use `status: archived` in Metadata — that is per-spec lifecycle.
This **directory** is unrelated; it only means “stored template history.”
