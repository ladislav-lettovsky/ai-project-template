# Phase 5 — telemetry, dashboard, and adaptive thresholds

## Metadata

- spec_id: SPEC-20260516-phase5-telemetry
- owner: template
- status: in-progress
- complexity: medium
- risk_tier: T1
- repo: ai-project-template
- branch: spec/phase5-telemetry

## Context

Phase 4 shipped the deterministic Router (`route_pr.py`, `route-pr.yml`). Phase 5
adds **observability**: append-only `events.jsonl`, a Markdown dashboard, bounded
`adapt_thresholds.py`, and merge-time recording so routing decisions become a
measurable signal. MCP / OTel / post-mortem skill exit items are partially deferred
to human red-zone edits (`.codex/config.toml`, `AGENTS.md`).

## Assumptions

- A1: Phase 4 exit drills (#39, #41, #42, #43) supply seed telemetry rows.
- A2: One event per PR number; re-record replaces the prior row for that PR.

## Decisions

- D1: **Record on merge** via `record-telemetry.yml` (commits to `main`) — avoids
  push loops from recording on every PR synchronize.
- D2: **`route-pr.yml` unchanged** for append; merge workflow is the durable writer.
- D3: **`adapt_thresholds.py`** follows blueprint §5.13 verbatim (blocked → tighten
  diff cap; invalid reviewer → raise confidence floor).

## Problem Statement

Without `events.jsonl`, operators cannot audit false positives/negatives from the
Router or run bounded policy adaptation. Phase 5 exit criteria require at least one
adapt cycle committed from real telemetry.

## Requirements (STRICT)

- [ ] R1: Add `docs/telemetry/events.jsonl` with schema documented in `docs/telemetry/README.md`
  and seed rows from Phase 4 drill PRs.
- [ ] R2: Add `scripts/append_event.py` building events from `pr.json` + `route.json`.
- [ ] R3: Add `scripts/telemetry_dashboard.py` writing `docs/telemetry/dashboard.md`.
- [ ] R4: Add `scripts/adapt_thresholds.py` with bounded updates per §5.13.
- [ ] R5: Add `.github/workflows/record-telemetry.yml` on merged PRs: build context,
  route, append, regenerate dashboard, commit to `main`.
- [ ] R6: Add `just` recipes: `telemetry-dashboard`, `adapt-thresholds`, `adapt-thresholds-write`.
- [ ] R7: Add `docs/specs/_postmortem.md` template (excluded from authorizing-spec lint).
- [ ] R8: Run `adapt_thresholds.py --write` once against seed telemetry; commit policy nudge.
- [ ] R9: Deterministic tests for append, adapt, and dashboard scripts.

## Non-Goals

- [ ] NG1: OTel exporter in `.codex/config.toml` (optional; human red-zone).
- [ ] NG2: MCP servers on Planner/Reviewer (exit criterion; human red-zone).
- [ ] NG3: New `AGENTS.md` invariant from post-mortem (exit criterion; human red-zone).
- [ ] NG4: `.claude/skills/postmortem/SKILL.md` (human red-zone; template at `docs/specs/_postmortem.md` ships).

## Interfaces

- `docs/telemetry/events.jsonl`, `docs/telemetry/dashboard.md`, `docs/telemetry/README.md`
- `scripts/append_event.py`, `scripts/telemetry_dashboard.py`, `scripts/adapt_thresholds.py`
- `.github/workflows/record-telemetry.yml`
- `tests/test_append_event.py`, `tests/test_adapt_thresholds.py`, `tests/test_telemetry_dashboard.py`

## Invariants to Preserve

- [ ] INV1: `just check` remains strict; no `|| true` in workflows.
- [ ] INV2: Router gate order in `route_pr.py` unchanged.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: yes — new workflow on merge
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: yes — `.github/workflows/` (human/agent via shell only)

## Test Plan

- [ ] T1 -> covers R1
- [ ] T2 -> covers R2, R9
- [ ] T3 -> covers R3, R9
- [ ] T4 -> covers R4, R9
- [ ] T5 -> covers R5
- [ ] T6 -> covers R6
- [ ] T7 -> covers R7
- [ ] T8 -> covers R8

## Validation Contract

- R1 -> test -f docs/telemetry/events.jsonl
- R2 -> uv run scripts/append_event.py --help
- R3 -> just telemetry-dashboard
- R4 -> uv run scripts/adapt_thresholds.py
- R5 -> test -f .github/workflows/record-telemetry.yml
- R6 -> just adapt-thresholds
- R7 -> test -f docs/specs/_postmortem.md
- R8 -> jq -e '.max_diff_lines == 125' .routing-policy.json
- R9 -> uv run pytest tests/test_append_event.py tests/test_adapt_thresholds.py tests/test_telemetry_dashboard.py
- FULL -> just check

## Edge Cases

- Empty `events.jsonl` — dashboard renders placeholders; adapt suggests no changes.
- Duplicate PR append — replace existing row for same `pr_number`.

## Security / Prompt-Injection Review

Telemetry reads PR bodies already validated by Router; no new LLM calls.

## Observability

This spec **is** the observability layer for Phase 4 routing.

## Rollback / Recovery

Revert `events.jsonl` line and policy commit; disable `record-telemetry.yml`.

## Implementation Slices

1. Scripts + tests + seed events + dashboard
2. Workflow + just recipes + adapt write
3. Docs (README blueprint pointer)

## Done When

- [ ] All R* checked; `just check` green on `spec/phase5-telemetry`
- [ ] Seed telemetry + one adapt-thresholds write committed
