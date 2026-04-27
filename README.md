# 🚀 Scaffold to Jump-Start New AI Project

![CI](https://github.com/ladislav-lettovsky/ai-project-template/actions/workflows/ci.yml/badge.svg)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ladislav-lettovsky/ai-project-template)

A GitHub template repository for modern Python / AI projects. Click the
green **"Use this template"** button at the top of this page to bootstrap
a new project with zero hygiene debt — uv, ruff, ty, pre-commit, just,
GitHub Actions CI, Cursor rules, and a Claude Code config all preconfigured.

---

## What you get

### Tooling
- `pyproject.toml` — project metadata, dependencies, ruff + ty configuration
- `justfile` — canonical task runner (`just check` is the full quality gate)
- `.pre-commit-config.yaml` — 10-hook config (branch protection + hygiene + ruff + ty)
- `.github/workflows/ci.yml` — thin CI wrapper that runs `just check`
- `.python-version` — pinned to Python 3.12

### AI-native configuration
- `AGENTS.md` — shared memory for Claude Code, Cursor, and Codex CLI,
  with a `TODO:` skeleton and an embedded guide for writing good
  architectural invariants
- `CLAUDE.md` — Claude Code entry point (one-line `@AGENTS.md` pointer)
- `.claude/settings.json` — allow / ask / deny permissions with sensible
  defaults (allow `just check`, ask before `git commit`, deny `.env`
  edits)
- `.cursor/rules/` — three generic rules:
  - `00-always.mdc` — always-on project conventions
  - `tests.mdc` — pytest conventions (auto-attached to `tests/**`)
  - `writing-rules.mdc` — meta-guide for authoring new rules

### Source layout
- `src/your_package/__init__.py` — placeholder to rename on fork
- `tests/test_smoke.py` — one trivial test so `just check` passes immediately
- `.scratch/.gitkeep` — sanctioned ephemeral-work directory

### Documentation
- `README.md` — this file (rewrite after forking)
- `CONTRIBUTING.md` — generic contribution guide, ready to extend
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
AGENTS.md, adding a domain-specific Cursor rule).

---

## Why this exists

This GitHub template provides scaffolding, including ruff +
ty + pre-commit + just + CI + Cursor rules + Claude Code
settings + AGENTS.md structure.
 to umpstart future projects.

---

## Philosophy

- **Local-first execution** — no cloud services required to develop
- **`just check` is the contract** — same command local and CI
- **Tooling over guidelines** — if a lint rule exists, don't also put it
  in AGENTS.md; if ruff catches it, a prose rule is noise
- **Invariants over style** — AGENTS.md is for rules linters cannot catch
- **Minimal placeholders** — no fake content that might ship unchanged;
  placeholders are flagged with `TODO:` or `your_package` so they can't
  be accidentally committed as-is

---

## License

MIT License — see [LICENSE](./LICENSE).
