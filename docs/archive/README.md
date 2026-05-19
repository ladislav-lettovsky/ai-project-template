# Documentation archive

Historical material for the **ai-project-template** repo itself — not
authorizing specs for new product work on a fork.

## `template-specs/`

Completed (and superseded) specs that built the template through Phases 0–6:
Router, telemetry, scheduled executor, demo modules, lint gates, and similar.
They remain in git as an audit trail and as lint/regression examples.

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
