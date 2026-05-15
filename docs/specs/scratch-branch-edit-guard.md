# Scratch branch edit guard (bootstrap deadlock fix)

## Metadata

- spec_id: SPEC-20260514-scratch-branch-edit-guard
- owner: TBD
- status: drafted
- complexity: low
- risk_tier: T1
- repo: ai-project-template
- branch: spec/scratch-branch-edit-guard

## Context

Agents often start on an ephemeral **parking** branch named `scratch` so the working copy is not left on `main` after a fast-forward. `AGENTS.md` instructs the first step on a new implementation prompt to **read the prompt**, pick a real branch name (`spec/<slug>` or `fix/<slug>`), and **`git branch -m scratch …`** before doing work.

Today, `scripts/hooks/check_branch_name.py` (wired to **UserPromptSubmit** in `.claude/settings.json`) rejects every branch that is not `main` and does not start with `spec/` or `fix/`. That set excludes `scratch`, so the agent **cannot submit a prompt** while parked on `scratch`—before it can run the rename the workflow already blocks. This is a bootstrap deadlock.

The fix splits concerns: allow **prompt intake** on `scratch`, but block **file mutations** on `scratch` until the branch is renamed to a valid working branch.

## Assumptions

- A1: Claude Code runs **UserPromptSubmit** before the turn proceeds and **PreToolUse** before each Edit/Write/MultiEdit; the same hook patterns are mirrored in `.codex/hooks.json` for Codex CLI parity.
- A2: The current branch for hooks is reliably available via `git rev-parse --abbrev-ref HEAD` in the repo root, matching `check_branch_name.py` behavior (including fail-open when git is unavailable).
- A3: “Exactly `scratch`” means the branch name is the literal string `scratch`, not `scratch/foo` or other variants.

## Decisions

- D1: **Allow list at prompt time** — Extend `check_branch_name.py` to treat `scratch` like `main`: permitted for **UserPromptSubmit**, still not a substitute for `spec/<slug>` or `fix/<slug>` when opening a PR.
- D2: **Block edits on `scratch` via PreToolUse** — Add `scripts/hooks/check_no_edits_on_scratch.py` on the same **Edit|Write|MultiEdit** matcher as `check_red_zone.py`, ordered after the red-zone hook so red-zone protection stays first.
- D3: **Documentation** — Update `AGENTS.md` and `docs/blueprint.md` so they no longer imply that `scratch` must fail the branch-name hook at prompt submission; Invariant 1 (PR branch naming) remains unchanged for merge workflow.

## Problem Statement

- **Symptom:** With `HEAD` == `scratch`, **UserPromptSubmit** exits non-zero and the user sees “BLOCKED by branch-name hook”, so the agent cannot execute the documented first step (`git branch -m scratch spec/<slug>`).
- **Root cause:** `check_branch_name.py` permits only `main`, `spec/*`, and `fix/*`; `scratch` is excluded.
- **Desired state:** Prompts on `scratch` succeed; file edits on `scratch` fail fast with actionable copy; invalid branches that are not `scratch` remain blocked at prompt time; `spec/<slug>` and `fix/<slug>` continue to pass both hooks.

## Requirements (STRICT)

- [ ] R1: **`check_branch_name.py` allows `scratch`.** When the current branch is exactly `scratch`, the hook exits `0` (same as `main`, `spec/*`, `fix/*`).
- [ ] R2: **Invalid branches remain blocked at prompt time.** Branches that are not `main`, not exactly `scratch`, and do not start with `spec/` or `fix/` still cause **UserPromptSubmit** to exit non-zero with existing Invariant 1 guidance (unchanged intent).
- [ ] R3: **New PreToolUse hook blocks writes on `scratch`.** `scripts/hooks/check_no_edits_on_scratch.py` runs on edit/write paths; when `HEAD` is exactly `scratch`, it exits non-zero and writes to stderr a **clear** message instructing the agent to rename with `git branch -m scratch spec/<slug>` or `git branch -m scratch fix/<slug>` before editing.
- [ ] R4: **Edits allowed off `scratch`.** When `HEAD` is `main`, or starts with `spec/` or `fix/`, the new hook exits `0` (no blocking solely because the parking branch was used earlier in the session).
- [ ] R5: **Claude Code registration.** `.claude/settings.json` **PreToolUse** matcher `Edit|Write|MultiEdit` invokes the new hook (in addition to `check_red_zone.py`), preserving the existing hook list behavior.
- [ ] R6: **`AGENTS.md` clarity.** The parking-branch section states explicitly that `scratch` is only for **prompt intake and branch selection**, and that the agent **must** rename off `scratch` before **creating or editing files** (the new hook enforces the latter).
- [ ] R7: **`docs/blueprint.md` alignment.** Every normative statement that currently suggests **UserPromptSubmit** rejects any branch outside `main` + `spec/*` + `fix/*` without mentioning the **`scratch` parking exception** is updated (including Invariant 7’s hook summary and Phase 1 checklist items that describe **UserPromptSubmit** behavior, and the §5.8-style hook examples if they repeat the same implication).
- [ ] R8: **Automated tests.** Deterministic tests (no live Claude runtime) cover `check_branch_name.py` and `check_no_edits_on_scratch.py` for: allow on `scratch` / `main` / `spec/x` / `fix/x`; block prompt on invalid branch; block edit on `scratch` with message containing the required `git branch -m` guidance; allow edit when not on `scratch` (using the same subprocess / mocking patterns as existing hook tests, e.g. `tests/test_require_just_check.py`).
- [ ] R9: **Codex parity.** `.codex/hooks.json` registers the same **PreToolUse** hook sequence as `.claude/settings.json` so Codex sessions behave consistently.

## Non-Goals

- [ ] NG1: Changing **Invariant 1** for PRs: merged work still uses `spec/<slug>` or `fix/<slug>`; `scratch` is not a delivery branch.
- [ ] NG2: Replacing or weakening pre-commit **`no-commit-to-branch`**, CI branch rules, or human push conventions.
- [ ] NG3: Blocking **`git branch -m`** or other non-edit tools on `scratch` (only **Edit|Write|MultiEdit** per Claude hook matcher; document if Codex differs).
- [ ] NG4: Special-casing branch names other than exact `scratch` (e.g. `parking`, `wip`).

## Interfaces

| Surface | Change |
| --- | --- |
| `scripts/hooks/check_branch_name.py` | Allow `scratch` in `main()`. |
| `scripts/hooks/check_no_edits_on_scratch.py` | **New** — exit `2` on `scratch` + stderr message; exit `0` otherwise; fail-open if git branch unknown (consistent with `check_branch_name.py`). |
| `.claude/settings.json` | Add second command under **PreToolUse** for the same `Edit` / `Write` / `MultiEdit` matcher as the red-zone hook. |
| `.codex/hooks.json` | Same PreToolUse addition as Claude. |
| `AGENTS.md` | Clarify `scratch` lifecycle vs edits. |
| `docs/blueprint.md` | Update hook / UserPromptSubmit descriptions per R7. |
| `tests/test_check_branch_name.py` | **New** — subprocess tests for `check_branch_name.py`. |
| `tests/test_check_no_edits_on_scratch.py` | **New** — subprocess tests for `check_no_edits_on_scratch.py`. |
| `tests/test_hook_registration_scratch_guard.py` | **New** — JSON + docs substring tests for R5, R6, R7, R9. |

## Invariants to Preserve

- [ ] INV1: **PR traceability (Invariant 1).** PRs still require spec link, reviewer JSON block, and branch prefix `spec/<slug>` or `fix/<slug>`; `scratch` is never the merge target.
- [ ] INV2: **Red-zone PreToolUse.** `check_red_zone.py` remains on the same matcher and continues to block edits to enumerated paths.
- [ ] INV3: **Fail-open on git failure** for branch-detection hooks where that is already the established behavior for `check_branch_name.py` (do not make PromptSubmit stricter for offline sandboxes without an explicit decision).

## Red-Zone Assessment

- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: yes

> Touches `AGENTS.md` and `.claude/settings.json` (red-zone paths per `AGENTS.md`). Implementation should follow the repo’s red-zone edit process (human terminal or explicitly authorized change); not eligible for `risk_tier: T0`.

## Test Plan

- [ ] T1 -> covers R1, R2, R8
- [ ] T2 -> covers R3, R4, R8
- [ ] T3 -> covers R5, R9
- [ ] T4 -> covers R6, R7

**Mapping:** T1 runs subprocess tests against `check_branch_name.py`. T2 runs subprocess tests against `check_no_edits_on_scratch.py`. Together, T1 and T2 satisfy the dual-hook coverage in R8. T3 loads `.claude/settings.json` and `.codex/hooks.json` and asserts the scratch edit hook is listed on the same PreToolUse matcher as the red-zone hook. T4 asserts stable substrings exist in `AGENTS.md` and `docs/blueprint.md` so R6/R7 do not drift without CI failure.

## Validation Contract

- R1 -> `uv run pytest tests/test_check_branch_name.py -q` and `just check`
- R2 -> `uv run pytest tests/test_check_branch_name.py -q` and `just check`
- R3 -> `uv run pytest tests/test_check_no_edits_on_scratch.py -q` and `just check`
- R4 -> `uv run pytest tests/test_check_no_edits_on_scratch.py -q` and `just check`
- R5 -> `uv run pytest tests/test_hook_registration_scratch_guard.py -q` and `just check`
- R6 -> `uv run pytest tests/test_hook_registration_scratch_guard.py -q` and `just check`
- R7 -> `uv run pytest tests/test_hook_registration_scratch_guard.py -q` and `just check`
- R8 -> `uv run pytest tests/test_check_branch_name.py tests/test_check_no_edits_on_scratch.py -q` and `just check`
- R9 -> `uv run pytest tests/test_hook_registration_scratch_guard.py -q` and `just check`

## Edge Cases

- EC1: **Git unavailable or `rev-parse` fails** — Match `check_branch_name.py`: fail **open** for prompt hook; the new edit hook should follow the same policy unless a documented exception is needed (avoid bricking sandboxes).
- EC2: **Detached HEAD** — Branch name may be `HEAD` or a hash depending on git; treat as not `scratch` unless `rev-parse` returns exactly `scratch` (document behavior in hook docstring).
- EC3: **Subdirectory execution** — Hooks should resolve repo root consistently if other hooks do (follow `check_red_zone.py` / existing patterns).

## Security / Prompt-Injection Review

- source: Git branch name only (local `git` output), not user chat content.
- risk: low
- mitigation: not required.

## Observability

Hook stderr messages are the operator signal; no new logging files required. Optional: one-line comment in each hook module pointing to this spec ID.

## Rollback / Recovery

Revert the implementing commit(s). If the new PreToolUse hook causes false positives, remove or adjust `check_no_edits_on_scratch.py` registration first (fastest), then revert branch-name logic if needed.

## Implementation Slices

1. Implement and test `check_branch_name.py` change + `check_no_edits_on_scratch.py` with pytest.
2. Register PreToolUse in `.claude/settings.json` and `.codex/hooks.json`.
3. Update `AGENTS.md` and `docs/blueprint.md`.
4. Run `just check` and fix any spec-lint or injection-scan findings.

## Done When

- [ ] All requirement IDs R1–R9 satisfied
- [ ] Decision IDs D1–D3 preserved or explicitly superseded in an amendment
- [ ] Tests mapped and passing per Test Plan
- [ ] Validation Contract satisfied
- [ ] `just check` green
- [ ] CI green
- [ ] No invariant violations (Invariant 1 unchanged for PRs)
- [ ] Branch name starts with `spec/<slug>` (Invariant 1)
- [ ] PR description links this spec
- [ ] PR body contains `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block
