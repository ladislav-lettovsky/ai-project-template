# Phase 6 D1 — dispatch transport spike

Authorizing spec:
[`docs/archive/template-specs/phase6-scheduled-executor.md`](../archive/template-specs/phase6-scheduled-executor.md).

## Candidates evaluated

| Option | Verdict |
| --- | --- |
| (a) Codex async/cloud API via `actions/github-script` | Rejected for v1 — no stable template contract; org-specific endpoints. |
| (b) `codex exec` in GitHub-hosted Actions | **Deferred** — requires `CODEX_API_KEY` (or equivalent) repo secret, network egress, and non-deterministic CI without a pinned fixture harness. Documented for Phase 6.1 when secrets are configured. |
| (c) Self-hosted runner + Docker-isolated Codex | Rejected for v1 — operational cost exceeds template scope. |

## Chosen transport (v1)

**`pr` — branch + empty seed commit + `gh pr create`.**

- Satisfies D3 (stop at open PR) using only `GITHUB_TOKEN` scopes already granted to `scheduled-executor.yml`.
- `scripts/dispatch_spec.py --transport pr` is the workflow default.
- PR body includes spec link, `dispatch-source: scheduled`, and schema-valid `REVIEWER_JSON` stub.
- Executor implementation and Reviewer population remain human- or locally-invoked Codex (Phase 6.1).

## Legacy rollback

`--transport issue` opens a `phase6-queue` tracking issue instead of a PR (Slices 1–3 behavior). Keep for debugging; not used by the scheduled workflow after Slice 4.

## Enabling `codex exec` later

1. Add `CODEX_API_KEY` (or org-standard name) to repo secrets.
2. Add an isolated workflow job (separate from `GITHUB_TOKEN` push steps) that runs `codex exec` with the spec path prompt.
3. Amend D1 in the authorizing spec and switch `scheduled-executor.yml` dispatch step.
