# {PROJECT_NAME} — AI Agent Memory

> **AI-native development governance.** This repo follows the blueprint at
> [`docs/blueprint.md`](docs/blueprint.md) — a multi-agent system with a Planner
> (Claude Code), Executor (Codex), Reviewer (Codex),
> and a deterministic Router (Phase 4 — `.github/workflows/route-pr.yml`).
> Defense-in-depth via hooks → pre-commit → `just check` → CI → branch protection.
> **After forking:** replace `{PROJECT_NAME}` and every section marked **(Customize)**
> below. Keep agent roles, commands, invariants, and the red-zone list unless you
> deliberately change governance. See [docs/post-fork-checklist.md](docs/post-fork-checklist.md).

## What this is *(Customize)*

TODO: One paragraph explaining what this project does and who uses it.
If it is a library, an application, a scaffolder, or a service, say so
explicitly — the shape of "what this is" determines the shape of
invariants that belong here.

## Stack *(Customize)*

- Python 3.12+, `uv` for dependency management, `just` as the task runner
- TODO: list frameworks and libraries this project actually depends on
  (runtime only — dev tools are listed separately)
- Testing: pytest with optional `integration` marker for live-API tests
- Linting: ruff; Type checking: `ty` (Astral); Pre-commit hooks enabled

## Agent Roles

This repo runs a three-agent system. Each role is a subagent with constrained
permissions; the Claude Code / Codex runtime enforces the boundaries — the
prompt does not.

- **Planner — Claude Code subagent** (`.claude/agents/planner.md`)
  - Mode: read-only (Plan Mode). Cannot edit files; produces plans for human approval.
  - Drafts and revises specs at `docs/specs/<slug>.md`.
  - Sets `risk_tier` (T0/T1/T2/T3) and `complexity` (low/medium/high) on every spec.
  - Spec drafting playbook: `.claude/skills/write-spec/SKILL.md`.
- **Executor — Codex subagent** (`.codex/config.toml [agents.executor]`)
  - Mode: `sandbox_mode = "workspace-write"`, `approval_policy = "on-request"`.
  - Implements one spec per branch in its own git worktree.
  - Runs `just check` before declaring done.
- **Reviewer — Codex subagent** (`.codex/config.toml [agents.reviewer]`)
  - Mode: `sandbox_mode = "read-only"`, `model_reasoning_effort = "high"`.
  - Outputs schema-valid JSON (never prose) per `.reviewer-schema.json`.
  - Bias: false positives over false negatives.

## Commands you can run without asking

- `just fmt` — format code
- `just lint` — ruff check
- `just lint-fix` — ruff check with --fix
- `just type` — ty check
- `just test` — full pytest run
- `just check` — pre-commit + type + test + spec-lint + injection-scan (the same command CI runs)
- `just lint-spec <path>` — lint a spec under `docs/specs/`
- `just lint-changed-specs` — lint specs touched on the current branch
- `just scan-injection` — scan LLM-input artifacts for injection patterns
- `just validate-reviewer <pr-body-file>` — validate Reviewer JSON against `.reviewer-schema.json`
- `uv sync`, `uv sync --extra dev`
- TODO: add your project's entry points (e.g., `uv run python -m your_package`)
- Read-only git: `git status`, `git diff`, `git log`, `git branch`

## Commands with preconditions

- `git commit` is allowed on a non-`main` branch **only after `just check` passes with no errors**. On `main`, always ask first.
- After any update to local `main` (PR merge, `git pull`, fast-forward, etc.),
  immediately `git switch` to a parking branch — by convention `scratch`,
  forked from the new `main` tip. This keeps the working copy off `main`
  so no edits or commits land there by accident. Create real work
  branches from `main`, not from `scratch`. If `scratch` is missing or
  stale, recreate it with `git switch -c scratch` from the current `main`.
- **First step on a new implementation prompt while on `scratch`:** read the
  prompt, decide whether it describes a new capability (→ `spec/<slug>`) or a
  bug fix (→ `fix/<slug>`), and rename the parking branch *before* **creating
  or editing files**:
  `git branch -m scratch spec/<slug>` (or `fix/<slug>`). Branch `scratch` is
  only for **prompt intake and branch selection**: the **UserPromptSubmit**
  hook (`check_branch_name.py`) allows `main`, `scratch`, and any branch whose
  name starts with `chore/`, `docs/`, `feat/`, `fix/`, `refactor/`, `spec/`, or
  `test/`; the **PreToolUse** hook (`check_no_edits_on_scratch.py`) blocks
  Edit/Write/MultiEdit on `scratch` until you rename. If `scratch` is missing,
  branch directly from `main` with `git switch -c spec/<slug>` (or
  `fix/<slug>`) instead. Recreate `scratch` only after the work merges (see the
  parking rule above).

## Commands that need explicit approval

- `uv add`, `uv remove` (dependency changes)
- `git push`, `git reset --hard`
- `gh pr create`, `gh pr merge`
- Anything touching `.env`, `.github/workflows/`, or project-critical data dirs

## Architectural invariants

Numbered invariants below; full text (Subject / Rule / Why / Tripwire) lives in
[`docs/blueprint.md` §2](docs/blueprint.md). The compressed form here is
sufficient for day-to-day work.

1. **Role split observable in every PR.** Branch starts with `spec/<slug>` or
   `fix/<slug>`. PR description links the spec. PR body contains a
   `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block. *Why:* every PR
   is a verifiable trace.
2. **Router is deterministic Python, not an LLM.** Routing reads `.routing-policy.json`
   plus PR context (`scripts/build_pr_context.py` → `scripts/route_pr.py`).
3. **Specs are documentation in `docs/specs/`, lint-enforced.** `scripts/lint_spec.py`
   gates `just check`; the `Stop` hook refuses session completion if a touched
   spec fails the linter.
4. **No regression of gold-standard tooling.** Preserve `uv`, `ty`, `just`,
   `pytest`, pre-commit, strict CI (no `|| true`). Tool swaps require an
   invariant version bump, not an in-PR argument.
5. **Reviewer output is structured JSON, not prose.** The Codex Reviewer
   produces a JSON document conforming to `.reviewer-schema.json`, fenced
   inside `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` markers in
   the PR body. `scripts/validate_reviewer.py` (run via `just
   validate-reviewer <pr-body-file>`, and in the **`route-pr`** CI
   workflow) rejects unparseable or non-conforming output. Any review that
   fails schema validation routes the PR to `review:human` automatically.
6. **Risk tier is a first-class routing input.** Declared on every spec (`risk_tier`,
   `complexity`); `.routing-policy.json` constrains which tiers may receive `review:codex`.
7. **Hooks are tripwires, not vibes.** Every tripwire enforceable at edit-time
   MUST be a hook in `.claude/settings.json` (or Codex command rules), not
   only a prompt instruction. Hook scripts live under `scripts/hooks/`.
8. **AGENTS.md is canonical; CLAUDE.md is a symlink.** Do not add content to
   CLAUDE.md. Tool-specific guidance belongs in subagent definitions.

> **TODO (Customize — project-specific):** add invariants 9+ for *this* project's domain.
> Each entry: What/where (concrete file or directory) — Why (picturable
> failure when violated) — Tripwire (the rule's negation, in observable form).

Optional artifacts under `.scratch/` (including optional `lessons.md`) are **not**
part of merge traceability or CI—they complement specs and gates; they do not
replace them.

## Red-zone files

Paths blocked at edit-time by `scripts/hooks/check_red_zone.py` (see Invariant 7)
and routed to `review:human` by `scripts/route_pr.py`.

```text
AGENTS.md
CLAUDE.md                       (symlink → AGENTS.md)
.claude/settings.json
.claude/agents/**
.claude/skills/**
.codex/config.toml
.cursor/rules/**
.github/workflows/**
scripts/hooks/**
pyproject.toml                  (dependency sections)
uv.lock
.pre-commit-config.yaml
justfile
.routing-policy.json
.reviewer-schema.json
```

To intentionally edit a red-zone file, do so from a human terminal session
(not via an agent). Do not silently bypass the hook in committed code.

## Worktree workflow

Every non-trivial spec is implemented in its own git worktree to prevent
parallel agents from colliding on shared file state.

- Claude Code: `claude -w spec-<slug>` (creates `.claude/worktrees/spec-<slug>/`)
- Codex: `git worktree add ../<repo>-<slug> -b spec/<slug> && codex --cd ../<repo>-<slug>`
- Cleanup: weekly `git worktree prune` plus removal of stale `.claude/worktrees/` dirs.

Read-only sessions (Planner subagent, ad-hoc questions) do not need worktrees.

## Where things live

- `src/{your_package}/` — production package (src layout)
  - TODO: describe each subdirectory's purpose
- `tests/` — pytest test suite
- `docs/` — project documentation
  - `docs/blueprint.md` — the AI-native dev environment blueprint
  - `docs/specs/` — per-feature specs
    - `docs/specs/README.md` — spec format documentation
    - `docs/specs/_template.md` — fillable spec skeleton
  - `docs/telemetry/` — events.jsonl + dashboard (Phase 5+)
- `.scratch/` — sanctioned scratchpad for exploratory work (git-ignored contents)
- `.claude/agents/` — Claude Code subagent definitions
- `.claude/skills/` — Agent Skills (progressive disclosure playbooks)
  - `.claude/skills/write-spec/SKILL.md` — spec-writing playbook
- `.claude/settings.json` — Claude Code permissions + hook config
- `.codex/config.toml` — Codex agent definitions (Executor, Reviewer)
- `scripts/hooks/` — Claude Code lifecycle hook scripts
- `scripts/lint_spec.py` — spec structure linter
- `scripts/scan_injection.py` — prompt-injection scanner
- `scripts/validate_reviewer.py` — Reviewer JSON validator
- `.reviewer-schema.json` — Reviewer output JSON Schema

## Testing conventions

- Deterministic tests (no API) are the default
- LLM-integration tests should be marked `@pytest.mark.integration` and
  skippable via `-m "not integration"`
- New features require at least one deterministic test

## Ephemeral / scratch work

Use `.scratch/` at the repo root for any exploratory, diagnostic, or
throwaway work — quick Python snippets, draft queries, debug logs, or
scratch notes. Directory is git-ignored (contents only; the directory
itself is kept via `.gitkeep`).

- Create on demand: `mkdir -p .scratch`
- Preferred file names: `<topic>.py`, `<topic>.md`, `<topic>.sql`, etc.
- Do NOT place exploratory files at the repo root — always use `.scratch/`

## Interactive session habits

These complement specs and CI; they do not replace them.

- **No AI attribution in committed content.** Do not add attribution lines, AI-generated signatures, or "Generated by" comments anywhere.

- **Ambiguous or non-spec work:** sketch a short plan before multi-step edits; if
  the approach fails repeatedly, stop and re-plan.
- **Lessons:** optionally append corrections to `.scratch/lessons.md` (format and
  habits in `.cursor/rules/session-workflow.mdc`); treat as session notes unless
  promoted to `docs/` or a spec.
- **Change discipline:** smallest fix that addresses the cause; avoid unrelated
  refactors unless a spec requires them.

## Before saying "done"

1. `just check` passes (ruff + ty + pytest + lint-changed-specs + scan-injection)
2. Any new public function has a test and a type-annotated signature
3. No new `print()` calls in production code — use `logging.getLogger(__name__)`
4. If the change affects behavior, `README.md` and `CONTRIBUTING.md` reviewed
5. Diff against `main` looks like what you'd want in a PR review
6. PR description links the authorizing spec (Invariant 1)
7. Any spec touched on this branch lints clean (the `Stop` hook will block
   session completion otherwise)
