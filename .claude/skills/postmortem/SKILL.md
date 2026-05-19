---
name: postmortem
description: |
  Loaded by humans when running a production or near-miss post-mortem. Walks
  through docs/specs/_postmortem.md and enforces exactly one invariant or one
  prompt/skill update per incident. NOT for Planner/Executor routine work or
  spec drafting — use write-spec via the Planner subagent instead.
---

# Post-mortem playbook

A post-mortem closes the loop: an incident or repeated telemetry pattern
becomes a **durable rule** (AGENTS.md invariant 9+) or a **single** prompt/skill
edit — not a one-off PR comment.

## When this skill applies

Use when:

- A production or staging incident occurred (preferred), or
- `docs/telemetry/dashboard.md` shows a repeated `route_reasons` pattern
  (monthly ritual in blueprint Phase 5), and process/policy alone is insufficient.

Do **not** use for feature specs, bug fixes without systemic root cause, or
Reviewer calibration (use `calibrate-reviewer` instead).

## Prerequisites

- Template: [`docs/specs/_postmortem.md`](../../../docs/specs/_postmortem.md)
- Invariant shape: [`docs/blueprint.md`](../../../docs/blueprint.md) §2
- Red-zone edits (`AGENTS.md`, `.codex/config.toml`, `.claude/**`) require a
  **human terminal** — hooks block agents.

## Steps

1. **Copy the template** to `.scratch/PM-<YYYYMMDD>-<slug>.md` (scratch is
   git-ignored). Fill every section; do not skip **Root cause** or
   **Invariant or prompt update (required)**.

2. **Choose one lever** for this incident:
   - **Invariant** (default for repo-wide rules) → edit `AGENTS.md` + full text
     in blueprint §2 if this repo maintains both.
   - **Prompt/skill** (Reviewer/Executor/Planner behavior) → one file in
     `.codex/config.toml` or `.claude/agents/` or `.claude/skills/`.
   - Not both in the same PR unless split for review clarity.

3. **Draft exactly one invariant** (if that lever) using Subject / Rule / Why /
   Tripwire. Example tripwires: `build_pr_context` → `spec_validation.invalid`,
   missing row in `events.jsonl` for a merged PR, invalid `reviewer_validation`.

4. **Human commit** on `chore/invariant-9-<slug>` or `fix/<slug>` as appropriate.
   Expect Router label `review:human` for `AGENTS.md` — that is correct.

5. **Link traceability** in the post-mortem: landing PR URL, issue id, optional
   telemetry PR number if the incident correlated with a merge.

6. **Injection hygiene** — if MCP or web text is pasted into `docs/specs/*.md`,
   run `just scan-injection` before merge.

## Done when

- [ ] Post-mortem file complete in `.scratch/` or promoted to `docs/` if the team
      keeps durable post-mortems in-repo.
- [ ] Exactly one invariant or prompt change merged.
- [ ] Post-mortem **Invariant or prompt update** section links the landing PR.
