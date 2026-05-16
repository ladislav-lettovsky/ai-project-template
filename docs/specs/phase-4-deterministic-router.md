# Phase 4 — deterministic PR Router

## Metadata

- spec_id: SPEC-20260515-phase-4-deterministic-router
- owner: template
- status: in-progress
- complexity: medium
- risk_tier: T1
- repo: ai-project-template
- branch: spec/phase-4-deterministic-router

## Context

[`docs/blueprint.md`](../../blueprint.md) Phase 3 added the Codex Reviewer with schema-valid JSON in every PR body. Phase 4 adds the **Router**: deterministic Python that labels each PR `review:codex`, `review:human`, or `blocked` based on declarative policy, red-zone touches, reviewer findings, confidence, coverage, diff size, and spec risk metadata. Until this lands, merging remains a human bottleneck for routine lanes.

## Assumptions

- A1: GitHub-hosted runners expose `gh` and `GITHUB_TOKEN` for PRs opened from branches of **this** repository (fork PR behavior is degraded but explained in docs).
- A2: Authorizing specs use branch names `spec/<slug>` or `fix/<slug>` with `docs/specs/<slug>.md`.

## Decisions

- D1: **Red-zone path lists live in `scripts/red_zone_paths.py`** and are imported by the PreToolUse hook and the Router — no duplication.
- D2: **Telemetry `append_event.py` is deferred to Phase 5**; workflow does not write `events.jsonl` yet.
- D3: **More than one** non-excluded Markdown file under `docs/specs/` in the PR’s changed files forces `review:human` (narrow scope ambiguity).

## Problem Statement

The repo has reviewer validation (`scripts/validate_reviewer.py`), spec lint, and CI (`just check`) but **no automated routing label** tying them together at PR time. Phase 4 exit criteria require three routing outcomes observable in GitHub plus explanatory comments.

## Requirements (STRICT)

- [ ] R1: Add **`.routing-policy.json`** matching the knob shape in blueprint §5.3 (`max_changed_files`, `max_diff_lines`, `min_reviewer_confidence`, `auto_review_allowed_risk_tiers`, `auto_review_allowed_complexity`, version field, adaptive placeholder ignored by Router v1 unless documented).

- [ ] R2: Add **`scripts/red_zone_paths.py`** with the canonical path set aligned to AGENTS / blueprint §5.5 and use it from **`scripts/hooks/check_red_zone.py`** and **`scripts/route_pr.py`**.

- [ ] R3: Add **`scripts/build_pr_context.py`** that emits **`pr.json`** including at least: `changed_files`, `diff_lines`, `branch_name`, `fork_pr`, optional `multiple_authorizing_specs_changed` boolean, **`spec.slug` / `spec.path` / `spec.risk_tier` / `spec.complexity`** (nullable when unresolved), **`spec_validation`** `{status, errors}`, **`reviewer_validation`** `{status, errors}`, **`reviewer`** (parsed object or empty dict when invalid), **`pr_body`**.

- [ ] R4: Add **`scripts/route_pr.py`** that loads policy + `pr.json` and emits JSON `{route, reasons}` using this **deterministic gate order**: invalid reviewer/spec artifacts → human; multiple authorizing specs **or** unresolved branch/spec file → human; red zone → human; any `critical` finding → **blocked**; tier/complexity not allowed → human; changed-files / diff-lines caps → human; reviewer confidence floor → human; incomplete requirement coverage (`requirements_covered < requirements_total`) → human; else `review:codex`.

- [ ] R5: Refactor **`scripts/validate_reviewer.py`** so **`build_pr_context`** can reuse the same extraction/schema/coverage validation logic without spawning a subprocess (exported functions or shared internal API).

- [ ] R6: Add **`tests/test_route_pr.py`** covering at minimum: invalid reviewer JSON → human; invalid spec lint → human; critical finding → blocked; red-zone file in diff → human; disallowed tier → human; diff too large → human; confidence too low → human; incomplete coverage counts → human; happy-path T0/low within caps → codex.

- [ ] R7: Add **`.github/workflows/route-pr.yml`**: triggers on PR `opened` / `synchronize` / `edited`; checks out PR head; `uv sync`; runs `build_pr_context` → `route_pr`; creates routing labels if missing; removes stale routing labels; applies label + explanatory comment via `gh`; **concurrency group per PR**; **fork PRs** skip mutate steps and post an informational comment instead.

- [ ] R8: Update **`CONTRIBUTING.md`**, **`README.md`**, **`AGENTS.md`**: Phase 4 active wording for Invariants 2 and 6; branch protection vs auto-merge semantics; Router comment expectation.

## Non-Goals

- [ ] NG1: Implement **`scripts/append_event.py`** or **`docs/telemetry/events.jsonl`** (Phase 5).

- [ ] NG2: LLM-based routing.

## Interfaces

New: `.routing-policy.json`, `scripts/red_zone_paths.py`, `scripts/build_pr_context.py`, `scripts/route_pr.py`, `.github/workflows/route-pr.yml`, `tests/test_route_pr.py`, `tests/test_build_pr_context.py`, `tests/test_red_zone_paths.py`, `tests/test_router_docs_phase4.py`.

Modified: `scripts/hooks/check_red_zone.py`, `scripts/validate_reviewer.py`, `CONTRIBUTING.md`, `README.md`, `AGENTS.md`.

## Invariants to Preserve

- [ ] INV1: Do not weaken **`just check`** / CI parity or add `|| true` in workflows.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: yes — new workflow invokes Python on every PR (`route-pr`).
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: yes — edits to `.github/workflows/` from agent sessions remain human-only.

## Test Plan

- [ ] T1 -> covers R1, R2, R3, R4, R5, R6, R7, R8

## Validation Contract

- R1 -> `pytest tests/test_route_pr.py tests/test_validate_reviewer.py tests/test_build_pr_context.py tests/test_router_docs_phase4.py -q` and `.routing-policy.json` exists
- R2 -> `pytest tests/test_route_pr.py tests/test_red_zone_paths.py -q`
- R3 -> `pytest tests/test_build_pr_context.py -q`
- R4 -> `pytest tests/test_route_pr.py -q`
- R5 -> `pytest tests/test_validate_reviewer.py -q`
- R6 -> `pytest tests/test_route_pr.py -q`
- R7 -> `pytest tests/test_router_docs_phase4.py -q` and `.github/workflows/route-pr.yml` exists
- R8 -> `pytest tests/test_router_docs_phase4.py -q`
- FULL -> `just check`

## Edge Cases

- EC1: Branch `feat/foo` → human route (Invariant 1 branch convention).
- EC2: `docs/specs/<slug>.md` missing on disk → `spec_validation.invalid`.
- EC3: Fork PR → no label mutations; explanatory comment only.

## Security / Prompt-Injection Review

- source: GitHub PR body (public collaboration surface).
- risk: medium — body flows into JSON parsing only; Router does not send content to LLMs.
- mitigation: strict JSON-schema validation unchanged; malformed reviewer block yields `review:human`.

## Observability

Router workflow posts PR comment listing machine-generated `reasons[]`. Optionally upload `pr.json`/`route.json` as workflow artifacts for debugging.

## Rollback / Recovery

Disable **`route-pr`** required check in branch settings or delete/rename `.github/workflows/route-pr.yml`; remove labels from automation if noisy.

## Implementation Slices

1. Shared red-zone module + reviewer refactor + `.routing-policy.json`.
2. `build_pr_context.py` + `route_pr.py` + pytest.
3. `route-pr.yml` + documentation.

## Done When

- [ ] Requirements R1–R8 satisfied and **Validation Contract** commands green.
- [ ] Phase 4 blueprint exit drills documented in **CONTRIBUTING.md** (`review:codex` / `review:human` / `blocked`).
- [ ] No regression in `tests/test_validate_reviewer.py`.
