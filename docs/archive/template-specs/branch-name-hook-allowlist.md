# Branch-name hook allowlist (conventional prefixes)

## Metadata

- spec_id: SPEC-20260514-branch-name-hook-allowlist
- owner: TBD
- status: complete
- complexity: low
- risk_tier: T1
- repo: ai-project-template
- branch: spec/branch-name-hook-allowlist

## Context

`.cursor/rules/00-always.mdc` recommends conventional branch prefixes (`feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/`) for everyday work. Before this change, the **UserPromptSubmit** hook `scripts/hooks/check_branch_name.py` allowed only `main`, `scratch`, and branches whose names start with `spec/` or `fix/`. Contributors who followed the Cursor rule and created e.g. `feat/login` saw prompts blocked before any rename, which contradicted published branch-guidance tables in `CONTRIBUTING.md`.

This change widens the hook allowlist so prompt submission succeeds on those conventional prefixes **without** relaxing Invariant 1 for mergeable PRs (`spec/<slug>` or `fix/<slug>` remains the traceability contract).

## Assumptions

- A1: Broadening prompt-time acceptance does not weaken pre-commit, CI, or branch protection that already enforce `main` protections.
- A2: Operators still use `spec/<slug>` or `fix/<slug>` when opening PRs that must satisfy Invariant 1; the hook is aligned with Cursor rules, not replacing the merge contract.

## Decisions

- D1: **Extend prefix allowlist** — Treat `feat/`, `chore/`, `docs/`, `refactor/`, and `test/` like `spec/` and `fix/` for **UserPromptSubmit** only (exit `0` when `HEAD` matches).
- D2: **stderr copy** — On block, list the accepted shape (including new prefixes) and restate that PRs still require `spec/<slug>` or `fix/<slug>` per Invariant 1.
- D3: **Red-zone** — `scripts/hooks/` edits require human care; this work is **not** `risk_tier: T0`.

## Problem Statement

- **Symptom:** Creating a branch such as `feat/foo` or `chore/deps` and running the agent yields `BLOCKED by branch-name hook` even though repo docs recommend those prefixes alongside `spec/` and `fix/`.
- **Root cause:** `check_branch_name.py` only whitelists `spec/` and `fix/` (plus `main` and `scratch`).
- **Desired state:** The hook accepts the same conventional prefixes documented in Cursor rules and `CONTRIBUTING.md`, while invalid branches remain blocked and Invariant 1 stays unchanged for PRs.

## Requirements (STRICT)

- [x] R1: **`check_branch_name.py` allows conventional prefixes.** When `HEAD` starts with `feat/`, `chore/`, `docs/`, `refactor/`, or `test/`, the hook exits `0` (same as existing `spec/` and `fix/` behavior).
- [x] R2: **`main`, `scratch`, `spec/`, and `fix/` unchanged.** Existing allow rules continue to pass.
- [x] R3: **Invalid branches remain blocked.** Branches that do not match any allowed pattern still exit non-zero (`2`).
- [x] R4: **User-facing stderr stays actionable.** Blocked runs mention the expanded allowed prefixes (or equivalent summary) and remind that mergeable PRs still use `spec/<slug>` or `fix/<slug>` under Invariant 1.
- [x] R5: **Deterministic tests.** `tests/test_check_branch_name.py` covers each new prefix plus at least one rejected branch and the prior cases (`main`, `scratch`, `spec/*`, `fix/*`).

## Non-Goals

- [x] NG1: Changing Invariant 1 or the requirement that traceable PRs use `spec/<slug>` or `fix/<slug>`.
- [x] NG2: Modifying `check_no_edits_on_scratch.py`, pre-commit `no-commit-to-branch`, or CI branch rules.
- [x] NG3: Allowing arbitrary branch names (only the listed prefixes plus `main` / `scratch`).

## Interfaces

| Surface | Change |
| --- | --- |
| `scripts/hooks/check_branch_name.py` | Extend allowed-prefix logic; update module docstring and blocked stderr. |
| `tests/test_check_branch_name.py` | Parametrize allowed branches; add/adjust assertions for stderr guidance if tested. |
| `CONTRIBUTING.md` | UserPromptSubmit bullet: list new prefixes consistent with the hook. |
| `README.md` | Defense-in-depth hooks blurb: describe allowlist accurately. |

## Invariants to Preserve

- [x] INV1: **Invariant 1 (PR traceability).** Spec still documents that merged work uses `spec/<slug>` or `fix/<slug>`; this hook broadens **prompt** acceptance only.
- [x] INV2: **Fail-open on git failure** — Keep returning `0` when git cannot determine the branch.
- [x] INV3: **`scratch` parking semantics** — Unchanged: exact `scratch` remains allowed for prompt intake; `check_no_edits_on_scratch.py` remains the edit gate.

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: yes

> The implementation edits `scripts/hooks/` (red-zone). Use human-authored review and the repo’s red-zone process; do **not** classify this change as `risk_tier: T0`.

## Test Plan

- [x] T1 -> covers R1, R2, R3, R5
- [x] T2 -> covers R4

## Validation Contract

- R1 -> `uv run pytest tests/test_check_branch_name.py -q` and `just check`
- R2 -> `uv run pytest tests/test_check_branch_name.py -q` and `just check`
- R3 -> `uv run pytest tests/test_check_branch_name.py -q` and `just check`
- R4 -> `uv run pytest tests/test_check_branch_name.py -q` and `just check`
- R5 -> `uv run pytest tests/test_check_branch_name.py -q` and `just check`

## Edge Cases

- EC1: **Prefix boundary** — `feat` without a slash remains invalid; `feat/x` is valid.
- EC2: **Git unavailable** — Unchanged: fail open (`0`).

## Security / Prompt-Injection Review

- source: Git branch name via local `git rev-parse` only.
- risk: low
- mitigation: not required.

## Observability

Stderr from the hook on block; docstring references this spec ID.

## Rollback / Recovery

Revert the implementing commit(s) to restore the narrower allowlist.

## Implementation Slices

1. Update `check_branch_name.py` and tests; refresh `CONTRIBUTING.md` and `README.md` hook descriptions.

## Done When

- [x] All requirement IDs R1–R5 satisfied
- [x] Decision IDs D1–D3 preserved or explicitly superseded
- [x] Tests mapped and passing per Test Plan
- [x] Validation Contract satisfied
- [x] `just check` green
- [ ] CI green
- [x] No invariant violations (Invariant 1 unchanged for PRs)
- [x] Branch name starts with `spec/<slug>` (Invariant 1)
- [ ] PR description links this spec
- [ ] PR body contains `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block
