# Phase 4 Router CI E2E Smoke

## Metadata

- spec_id: SPEC-20260515-phase4-route-codex-e2e
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T0
- repo: ai-project-template
- branch: spec/phase4-route-codex-e2e

## Context

Phase 4 has an in-process router smoke test, but that does not prove the live
GitHub Actions surface works: checkout, `build_pr_context.py`, `route_pr.py`,
`gh pr edit --add-label`, and `gh pr comment`.

This spec validates the happy path by using the PR that lands this spec as the
live smoke. A same-repo PR with only this non-red-zone spec file and a
schema-valid, threshold-clearing `REVIEWER_JSON` block must receive the
`review:codex` label and a router reasons comment from `.github/workflows/route-pr.yml`.

## Assumptions

- A1: `.github/workflows/route-pr.yml` triggers on pull requests to `main`.
- A2: `.routing-policy.json` v1 allows T0/low, at most three changed files, at
  most 150 diff lines, and `min_reviewer_confidence: 60`.
- A3: The PR head is from this repository, not a fork, so the workflow can
  apply labels and comments with `GITHUB_TOKEN`.
- A4: `tests/test_router_smoke.py` already covers in-process routing logic.

## Decisions

- D1: Validate by observing a real PR, because local tests cannot exercise
  GitHub label and comment application.
- D2: Add no source or test files; the only repository diff is this spec.
- D3: Keep this spec compact so the validating PR remains below the router's
  `max_diff_lines: 150` policy cap.

## Problem Statement

A workflow regression, permissions drift, `gh` CLI breakage, context-building
bug, or label typo can escape `just check` even when router unit tests pass.
This spec establishes a documented positive observation of the CI happy path.

## Requirements (STRICT)

- [ ] R1: A same-repo PR to `main` with only this non-red-zone spec file and a
  PR body containing a `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->`
  block that validates against `.reviewer-schema.json`, reports
  `requirements_covered == requirements_total`, and reports `confidence >= 60`
  results in the `route-pr` workflow completing green, applying the
  `review:codex` label, and posting a reasons comment.

## Non-Goals

- [ ] NG1: Adding or modifying deterministic router tests.
- [ ] NG2: Exercising `review:human`, `blocked`, fork-head PRs, or invalid
  reviewer JSON.
- [ ] NG3: Modifying `.github/workflows/route-pr.yml`, `.routing-policy.json`,
  `.reviewer-schema.json`, `scripts/route_pr.py`, or `scripts/build_pr_context.py`.
- [ ] NG4: Adding source or test files.

## Interfaces

Only one file is added: `docs/specs/phase4-route-codex-e2e.md`. The PR body is
the artifact under test for reviewer JSON extraction.

## Invariants to Preserve

- [ ] INV1: `just check` passes.
- [ ] INV2: No red-zone file is touched.
- [ ] INV3: `.routing-policy.json` and `.reviewer-schema.json` are unchanged.
- [ ] INV4: The PR body's `REVIEWER_JSON` block validates via `just validate-reviewer`.

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

- [ ] T1 -> covers R1. Open the same-repo validating PR, run
  `just validate-reviewer` on its body, and confirm the workflow success,
  `review:codex` label, and router reasons comment.

## Validation Contract

- R1 -> Manual CI observation on the validating PR: reviewer JSON validates,
  `gh run list --workflow route-pr.yml --branch spec/phase4-route-codex-e2e`
  shows the latest run as `completed success`, `gh pr view <pr> --json labels`
  includes `review:codex`, and `gh pr view <pr> --json comments` contains a
  comment beginning with `Router decision: review:codex` plus `Reasons:`.

## Edge Cases

- EC1: Fork PRs skip label/comment application; out of scope.
- EC2: Missing or invalid reviewer JSON routes away from `review:codex`; out
  of scope.
- EC3: Low confidence or incomplete requirement coverage routes away from
  `review:codex`; out of scope.
- EC4: If workflow concurrency cancels an earlier run, observe the latest
  completed run.

## Security / Prompt-Injection Review

- source: the PR body reviewer JSON is hand-authored for this validation.
- risk: low
- mitigation: schema validation and deterministic parsing by existing scripts.

## Observability

The existing workflow uploads `pr.json` and `route.json`, applies the label,
and posts the reasons comment. No additional telemetry is needed.

## Rollback / Recovery

Revert the commit. Removing this single additive Markdown file leaves router
code, workflow, policy, and schema unchanged.

## Implementation Slices

1. Slice 1: Add this spec, open the validating PR with threshold-clearing
   reviewer JSON, and record that workflow success, label, and comment were
   observed.

## Done When

- [ ] All requirement IDs satisfied
- [ ] Decision IDs preserved or explicitly deferred
- [ ] Tests mapped and passing
- [ ] Validation Contract satisfied
- [ ] `just check` green
- [ ] CI green
- [ ] No invariant violations
- [ ] Branch name starts with `spec/phase4-route-codex-e2e`
- [ ] PR description links this spec
- [ ] PR body contains a valid `REVIEWER_JSON` block
- [ ] The `route-pr` workflow completes green on that PR
- [ ] The `review:codex` label is applied by the workflow
- [ ] The workflow posts a router reasons comment
