# 🚀 Scaffold to Jump-Start New AI Project

![CI](https://github.com/ladislav-lettovsky/ai-project-template/actions/workflows/ci.yml/badge.svg)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ladislav-lettovsky/ai-project-template)

A GitHub template repository for modern Python / AI projects. Click the
green **"Use this template"** button at the top of this page to bootstrap
a new project with zero hygiene debt — `uv`, `ruff`, `ty`, pre-commit,
`just`, GitHub Actions CI, Cursor rules, and a multi-agent AI governance
system all preconfigured.

This template goes beyond hygiene: it ships an **AI-native development
environment** that separates planning, execution, and review across
constrained subagents, with lint-enforced specs and defense-in-depth
hooks. The full design is documented in
[`docs/blueprint.md`](./docs/blueprint.md).

---

## What you get

### Tooling
- `pyproject.toml` — project metadata, dependencies, `ruff` + `ty` + `jsonschema` configuration
- `justfile` — canonical task runner (`just check` is the full quality gate)
- `.pre-commit-config.yaml` — branch protection + hygiene + ruff + ty
- `.github/workflows/ci.yml` — thin CI wrapper that runs `just check`
- `.python-version` — pinned to Python 3.12

### Multi-agent governance

Three roles, each running under a different runtime with its own sandbox
and contract. Boundaries are enforced by the runtime, not by prompts.

- **Planner** — Claude Code subagent (`.claude/agents/planner.md`).
  Read-only Plan Mode. Drafts specs at `docs/specs/<slug>.md` per the
  §5.1 structure. Sets `risk_tier` and `complexity` on every spec.
- **Executor** — Codex subagent (`.codex/config.toml [agents.executor]`).
  `sandbox_mode = "workspace-write"`, `approval_policy = "on-request"`.
  Implements one spec per branch in its own git worktree. Runs
  `just check` before declaring done.
- **Reviewer** — Codex subagent (`.codex/config.toml [agents.reviewer]`).
  `sandbox_mode = "read-only"`, `model_reasoning_effort = "high"`.
  Produces schema-valid JSON code review fenced in
  `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` markers.
  Currently in calibration; see
  `.claude/skills/calibrate-reviewer/SKILL.md`.

### Spec-driven flow

- `docs/specs/` — per-feature specs, lint-enforced
- `docs/specs/README.md` — spec format documentation
- `docs/specs/_template.md` — fillable spec skeleton
- `scripts/lint_spec.py` — structural linter (gates `just check`)
- `.reviewer-schema.json` + `scripts/validate_reviewer.py` — JSON Schema
  contract for Reviewer output, with a validator script

### Defense-in-depth hooks

Tripwires fire at the earliest layer they can. Hook scripts live under
`scripts/hooks/`:

- `check_red_zone.py` — PreToolUse hook; blocks edits to invariant-protected
  files (AGENTS.md, justfile, agent configs, etc.)
- `check_branch_name.py` — UserPromptSubmit hook; rejects work on
  branches not starting with `spec/<slug>` or `fix/<slug>`
- `require_just_check.py` — Stop hook; refuses session completion if a
  touched spec fails `lint_spec.py`

### Skills (progressive disclosure)

Agent Skills load detailed playbooks on demand without bloating the
agent's eager context.

- `.claude/skills/write-spec/SKILL.md` — spec-writing walkthrough,
  loaded by the Planner
- `.claude/skills/calibrate-reviewer/SKILL.md` — Reviewer calibration
  procedure (3-PR / 6-of-10 scoring)

### Prompt-injection defense

- `scripts/scan_injection.py` — string-match scanner over LLM-input
  surfaces (specs, agent definitions, skills, Cursor rules, AGENTS.md,
  persisted MCP/web outputs). Runs as part of `just check`.

### Cursor rules

- `.cursor/rules/00-always.mdc` — always-on project conventions
- `.cursor/rules/tests.mdc` — pytest conventions (auto-attached to `tests/**`)
- `.cursor/rules/writing-rules.mdc` — meta-guide for authoring new rules

### Source layout

- `src/your_package/__init__.py` — placeholder to rename on fork
- `tests/` — pytest test suite (smoke test + tests for the spec/scan/validator scripts)
- `.scratch/.gitkeep` — sanctioned ephemeral-work directory

### Documentation

- `README.md` — this file (rewrite after forking)
- `CONTRIBUTING.md` — generic contribution guide, ready to extend
- `docs/blueprint.md` — full architecture: agent roles, invariants,
  red-zone files, phased plan
- `docs/post-fork-checklist.md` — the first-hour ritual after forking
- `LICENSE` — MIT (edit the copyright line)

---

## How to use

### Option 1 — GitHub "Use this template" button (recommended)

1. Click **"Use this template"** at the top of this page → **"Create a new repository"**
2. Name your new repo (e.g., `ai-my-new-project`)
3. Clone it locally and follow [docs/post-fork-checklist.md](./docs/post-fork-checklist.md)

### Option 2 — Manual clone

```bash
git clone --depth 1 https://github.com/ladislav-lettovsky/ai-project-template.git my-project
cd my-project
rm -rf .git
git init
# then follow docs/post-fork-checklist.md
```

---

## Actions after forking

```bash
# 1. Install dependencies
uv sync --extra dev

# 2. Install pre-commit hooks (one-time)
just install-hooks

# 3. Verify everything works
just check
```

If `just check` is green, your fork is healthy. Read
[docs/post-fork-checklist.md](./docs/post-fork-checklist.md) for the
full bootstrap process (renaming the placeholder package, filling in
AGENTS.md, adding a domain-specific Cursor rule, deciding what to do
with the example specs).

For the architectural picture — why three agents, what the invariants
mean, what gets enforced at edit-time vs commit-time vs CI-time — read
[docs/blueprint.md](./docs/blueprint.md).

---

## What's planned (not yet shipped)

The blueprint defines additional phases beyond what currently ships:

- **Router** (Phase 4) — deterministic Python script labels each PR as
  `review:codex` / `review:human` / `blocked`; auto-merge on the first
  outcome when CI is green and the Reviewer's JSON validates.
- **Telemetry + adaptive thresholds** (Phase 5) — `events.jsonl` per
  PR, dashboard, MCP integration for Reviewer context, bounded
  threshold tuning from real data.
- **Scheduled executor** (Phase 6) — semi-autonomous endgame: a spec
  in `docs/specs/` without a corresponding PR is dispatched to Codex
  on a schedule.

Each future phase has an exit criterion in `docs/blueprint.md` §4.

---

## Why this exists

Modern AI-assisted development needs more than hygiene — it needs a
governance system that enforces role boundaries (planning vs. executing
vs. reviewing) at the runtime layer rather than relying on prompt
discipline. This template provides scaffolding that gives you both:
the gold-standard hygiene tooling (`uv` + `ty` + pre-commit + CI) AND
the multi-agent governance layer (subagents + sandboxes + hooks +
specs + structured review). Forks inherit the full system.

---

## Philosophy

- **Local-first execution** — no cloud services required to develop
- **`just check` is the contract** — same command local and CI
- **Sandboxes over prompts** — role boundaries enforced by the runtime
  (Plan Mode, workspace-write, read-only), not by "please don't" instructions
- **Tooling over guidelines** — if a lint rule exists, don't also put it
  in AGENTS.md; if ruff catches it, a prose rule is noise
- **Invariants over style** — AGENTS.md is for rules linters cannot catch
- **Specs are documentation, not metadata** — every spec is plain
  Markdown a human can read, with structure enforced by `lint_spec.py`
- **Hooks are tripwires, not vibes** — every tripwire that can fire at
  edit-time is a hook, not a prompt instruction
- **Minimal placeholders** — no fake content that might ship unchanged;
  placeholders are flagged with `TODO:` or `your_package` so they can't
  be accidentally committed as-is

---

## License

MIT License — see [LICENSE](./LICENSE).
