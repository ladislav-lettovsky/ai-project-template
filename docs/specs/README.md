# Specs

This directory holds the **authorizing specs** for non-trivial work in this
repo. Every PR for work that meets the Planner's consequence-based criteria
(red-zone touch, multi-file change, public-interface change,
future-reader-needs-context, or the >30-min-by-hand fallback) cites a spec
here; the spec is the contract the Executor (Codex) implements literally
and the Reviewer (Codex) checks against.

> Read first: `docs/blueprint.md` §5.1 (spec structure) and §2 (invariants).
> The Planner subagent definition at `.claude/agents/planner.md` and the
> `write-spec` skill at `.claude/skills/write-spec/SKILL.md` walk through
> the authoring procedure.

## What lives here

**Active authorizing specs** — only files in this directory (not
`docs/archive/`). Template build history lives in
[`docs/archive/template-specs/`](../archive/template-specs/); see
[`docs/archive/README.md`](../archive/README.md).

- `_template.md` — a fill-in-the-blanks skeleton. Copy it to
  `docs/specs/<slug>.md` to start a new spec.
- `_postmortem.md` — A separate template for production-issue
  postmortems (one postmortem produces one invariant addition or one
  prompt update). Procedure: `.claude/skills/postmortem/SKILL.md`.
- `<slug>.md` — one file per spec. Filename slug matches the branch name
  (`spec/<slug>`). Use **capability slugs only** — no `phaseN-` prefix (rollout
  order is in `docs/blueprint.md`, not in filenames).

## The structure (enforced)

Every spec must contain — and `scripts/lint_spec.py` rejects any spec that
omits — these sections, in this order:

1. `# <Feature Title>` (any title)
2. `## Metadata` — block of `- key: value` lines including:
   - `spec_id: SPEC-<YYYYMMDD>-<slug>`
   - `owner: <name>`
   - `status: drafted | in-progress | complete | archived`
   - `complexity: low | medium | high`
   - `risk_tier: T0 | T1 | T2 | T3`
   - `repo: <repo-name>`
3. `## Context` — why this work exists now.
4. `## Assumptions` — `A1`, `A2`, …
5. `## Decisions` — `D1`, `D2`, … (architectural decisions with rationale).
6. `## Problem Statement` — exact failure or missing capability.
7. `## Requirements (STRICT)` — `R*` or `REQ-*` IDs, each on a line, each
   testable.
8. `## Non-Goals` — `NG1`, … explicit out-of-scope.
9. `## Interfaces` — affected entrypoints, APIs, files.
10. `## Invariants to Preserve` — `INV1`, … invariants that must hold after.
11. `## Red-Zone Assessment` — yes/no answers for the canonical eight axes
    (auth, billing, dependencies, CI, migrations, secrets, infra,
    invariant-protected files).
12. `## Test Plan` — `T*` entries, each declaring `T<n> -> covers
    R<list>` (or `REQ-<list>`).
13. `## Validation Contract` — for every `R*`, a `R* -> <command-or-assertion>`
    line.
14. `## Edge Cases` — `EC1`, …
15. `## Security / Prompt-Injection Review` — `source`, `risk` (low/medium/
    high), `mitigation`. Mandatory for specs that source data from MCP
    tools, web search, or external docs.
16. `## Observability` — logs, metrics, telemetry updates.
17. `## Rollback / Recovery` — how to revert.
18. `## Implementation Slices` — numbered slices, smallest useful commits.
19. `## Done When` — checklist that includes the standard items (all R\*
    satisfied, tests passing, `just check` green, CI green, no invariant
    violations).

## What the linter checks

`scripts/lint_spec.py <path>` exits non-zero if:

- Any required section heading is missing or out of order.
- Any `R*` or `REQ-*` requirement is not covered by a `T<n> -> covers
  R<list>` entry in Test Plan.
- Any `R*` or `REQ-*` requirement is not addressed by a `R* -> ...` line in
  Validation Contract.
- The Metadata block is missing `risk_tier` or `complexity`, or the values
  are outside the allowed enums.
- The spec contains a known prompt-injection pattern (delegated to
  `scripts/scan_injection.py`).

Separately from `lint_spec.py`, **Markdown formatting** on spec files is
enforced by **markdownlint-cli2** (the same engine as repo pre-commit,
including under `just check`): fenced blocks need an info string (MD040),
lists need spacing where required (**MD032**), etc. Run
`uv run pre-commit run markdownlint-cli2 --files docs/specs/<slug>.md` or use
`just lint-md`. This gate complements — it does **not** replace —
`just lint-spec` / §5.1 structure checks.

The linter is intentionally strict. A spec that "looks fine but the linter
says no" is not a successful spec — fix the spec.

## Workflow

1. The Planner subagent (Plan Mode, read-only) drafts the spec content.
2. A human commits the file at `docs/specs/<slug>.md` on a `spec/<slug>`
   branch.
3. `just lint-spec docs/specs/<slug>.md` must pass.
4. The Executor (Codex, workspace-write sandbox) implements against the
   spec on the same branch.
5. The PR description links the spec; the branch is named `spec/<slug>`;
   the PR body contains a `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON
   -->` block (Reviewer JSON or a schema-valid stub until Reviewer runs).

Specs that authorize work touching red-zone files (per AGENTS.md "Red-zone
files") cannot ship as `risk_tier: T0` regardless of size — see
`Red-Zone Assessment` in the template.

## Status lifecycle and the scheduled executor

`status` is not decorative — `scripts/queue_specs.py` only queues specs with
`status: drafted`. The scheduled executor (`scheduled-executor.yml`) dispatches
**T0 + low** drafted specs that have no `spec/<slug>` branch and no open/merged PR
citing the spec path.

| Status | Meaning |
| --- | --- |
| `drafted` | Authorized, not started — **eligible for the scheduler** when T0/low |
| `in-progress` | Branch/PR in flight — not queued |
| `complete` | Shipped or drill finished — not queued; **keep the file** as history |
| `archived` | Abandoned or superseded — not queued |

**After merge:** set `status: complete` (or `archived` if abandoned). Keep the file
under `docs/specs/` for your project's specs. Template build specs that shipped before
the archive layout live under `docs/archive/template-specs/` — do not move them back.

**Forking:** remove template history with `rm -rf docs/archive` (see
`docs/post-fork-checklist.md` §9). Lint example specs live in the archive, not here.

Active scheduler drill fixtures may live under `docs/specs/_drills/` while a drill
runs; when finished, move them to `docs/archive/exit-drills/<kit>/` with
`status: complete` so cron does not re-queue them (see
[`docs/archive/exit-drills/scheduled-executor/`](../archive/exit-drills/scheduled-executor/)).
