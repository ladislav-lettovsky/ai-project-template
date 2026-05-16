# Phase 4 Router E2E Smoke

## Metadata

- spec_id: SPEC-20260515-phase4-router-smoke
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/phase4-router-smoke

## Context

Phase 4 introduced a deterministic PR router (`scripts/route_pr.py`) and its CI workflow (`.github/workflows/route-pr.yml`). The router has been deployed but has no dedicated in-process smoke test: the only way to confirm the `build_pr_context → route_decision` pipeline works end-to-end is to open a real PR and watch the GitHub Actions job. That loop is too slow for regression detection.

This spec adds the smallest possible test that exercises the happy path: a synthetic PR context dict (T0/low, matching `.routing-policy.json`) flows through `route_decision()` and the router emits `review:codex`, confirming the in-process Phase 4 routing path under current policy.

## Assumptions

- A1: `scripts/route_pr.py` exposes `route_decision(pr: dict, policy: dict) -> tuple[str, list[str]]` as a stable, importable callable (confirmed — no refactor required).
- A2: `.routing-policy.json` is present at the repo root and its allow-list includes `risk_tier: T0` / `complexity: low` (v1 policy; T1+ are human-review by default).
- A3: A synthetic PR context with `risk_tier=T0`, `complexity=low`, zero red-zone files, valid reviewer/spec validation flags, and full requirement coverage routes to `review:codex` under current policy.

## Decisions

- D1: The test imports `route_decision` directly from `scripts/route_pr.py` rather than shelling out, keeping it deterministic and fast with no subprocess or network dependency.

## Problem Statement

`scripts/route_pr.py` has no dedicated E2E smoke test. A regression — a broken import, a renamed policy key, a logic inversion — would be invisible to `just check` until a live PR is opened.

## Requirements (STRICT)

- [ ] R1: A single deterministic pytest test in `tests/test_router_smoke.py` calls `route_decision()` with a synthetic T0/low/no-red-zone PR context (reading the real `.routing-policy.json`) and asserts the routing decision equals `"review:codex"`.

## Non-Goals

- [ ] NG1: Testing non-happy-path routing outcomes (T2/T3 tiers, red-zone paths, blocked decisions) — out of scope; only the `review:codex` path is exercised.
- [ ] NG2: Replacing `.routing-policy.json` with a mock — the test reads the real policy file from the repo root.
- [ ] NG3: Touching any red-zone file.

## Interfaces

Files added or modified (≤ 2):

- `tests/test_router_smoke.py` — new file; contains a single pytest test calling `route_decision()` with a synthetic context.

No existing production file requires modification.

## Invariants to Preserve

- [ ] INV1: `just check` passes with no errors after this change.
- [ ] INV2: No red-zone file is touched.
- [ ] INV3: The new test makes no network calls and requires no GitHub credentials.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: no

## Test Plan

- [ ] T1 -> covers R1

## Validation Contract

- R1 -> `pytest tests/test_router_smoke.py` (also covered by `just check`)

## Edge Cases

- EC1: If `.routing-policy.json` is absent or malformed the test fails with a clear `FileNotFoundError` or `json.JSONDecodeError` — no silent pass.
- EC2: If the policy allow-list changes to exclude T0/low the test fails with an assertion error, which is the intended tripwire.

## Security / Prompt-Injection Review

- source: none — the test constructs a fully synthetic in-process dict; no external input flows to an LLM
- risk: low
- mitigation: not required

## Observability

None required — standard pytest output is sufficient.

## Rollback / Recovery

Revert the commit. The new test file is additive; removing it leaves the router and all production code unchanged.

## Implementation Slices

1. Slice 1: Add `tests/test_router_smoke.py` with a single assertion against `route_decision()`; confirm `just check` is green.

## Done When

- [ ] All requirement IDs satisfied
- [ ] Decision IDs preserved or explicitly deferred
- [ ] Tests mapped and passing
- [ ] Validation Contract satisfied
- [ ] `just check` green
- [ ] CI green
- [ ] No invariant violations
- [ ] Branch name starts with `spec/phase4-router-smoke` (Invariant 1)
- [ ] PR description links this spec
- [ ] PR body contains `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block
