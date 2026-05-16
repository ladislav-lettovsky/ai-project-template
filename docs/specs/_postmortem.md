<!-- markdownlint-disable MD033 -->
<!-- Angle-bracket placeholders are fillable template tokens, not HTML. -->

# Post-mortem: <incident title>

## Metadata

- incident_id: PM-<YYYYMMDD>-<slug>
- date: <YYYY-MM-DD>
- owner: <name>
- severity: low | medium | high | critical
- status: open | closed

## Summary

One paragraph: what happened, user impact, duration.

## Timeline

- <time> — <event>

## Root cause

What actually broke (not symptoms).

## Contributing factors

- <factor>

## What went well / poorly

- Good: …
- Poor: …

## Corrective actions

| Action | Owner | Due | Type |
| --- | --- | --- | --- |
| <action> | <name> | <date> | invariant \| prompt \| code \| process |

## Invariant or prompt update (required)

Every post-mortem must produce **one** of:

1. A new or revised numbered invariant in `AGENTS.md` (human-authored, red-zone), or
2. A concrete edit to Planner / Executor / Reviewer instructions or a skill under `.claude/skills/`.

Record the change here with a link to the PR that landed it.

## Links

- Spec / PR: …
- Dashboard row: `docs/telemetry/events.jsonl` (if applicable)
