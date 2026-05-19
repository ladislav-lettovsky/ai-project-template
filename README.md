# 🚀 Scaffold to Jump-Start New AI Project

![CI](https://github.com/ladislav-lettovsky/ai-project-template/actions/workflows/ci.yml/badge.svg)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ladislav-lettovsky/ai-project-template)

**Legend (for forkers):**

| Tag | Meaning |
| --- | --- |
| **Keep** | Still valid after fork — content or workflow carries over |
| **Customize** | Keep the idea; update names, URLs, badges, or placeholders |
| **Replace** | Template-only — delete and write your project's version |

**You are here:**

- Browsing the **template** on GitHub → read [About this template](#about-this-template-replace-on-fork), then create a repo.
- Working in a **fork** → start at [Your project](#your-project-keep--customize); use
  [docs/post-fork-checklist.md](./docs/post-fork-checklist.md) for rename steps.

---

## About this template *(Replace on fork)*

A GitHub **template repository** for modern Python / AI projects. Click the green
**"Use this template"** button to bootstrap a new repo with `uv`, `ruff`, `ty`,
pre-commit, `just`, GitHub Actions CI, Cursor rules, and a multi-agent governance
system preconfigured.

The design — Planner / Executor / Reviewer, specs, hooks, Router — is in
[`docs/blueprint.md`](./docs/blueprint.md).

### How to create a repo from this template

1. Click **"Use this template"** → **"Create a new repository"**
2. Name your new repo (e.g. `ai-my-new-project`)
3. Clone locally and follow [docs/post-fork-checklist.md](./docs/post-fork-checklist.md)

Or mirror manually:

```bash
git clone --depth 1 https://github.com/ladislav-lettovsky/ai-project-template.git my-project
cd my-project
rm -rf .git && git init
# then docs/post-fork-checklist.md
```

---

## Your project *(Keep & customize)*

After forking, treat everything below as **your** project README. Replace the title,
badges, and [About this template](#about-this-template-replace-on-fork); keep the
workflows and doc links unless you remove features.

### Quick start *(Keep)*

```bash
uv sync --extra dev
just install-hooks    # one-time
just check
```

Green `just check` means the fork is healthy. Full bootstrap (rename package, fill
`AGENTS.md`, trim example specs): [docs/post-fork-checklist.md](./docs/post-fork-checklist.md).

Architecture and invariants: [docs/blueprint.md](./docs/blueprint.md). Day-to-day
contributing: [CONTRIBUTING.md](./CONTRIBUTING.md).

### What you get *(Keep — customize placeholders)*

#### Tooling

- `pyproject.toml` — metadata, dependencies, `ruff` + `ty` + `jsonschema`
- `justfile` — `just check` is the full quality gate (same as CI)
- `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.python-version`

#### Multi-agent governance

- **Planner** — Claude Code (`.claude/agents/planner.md`), Plan Mode, specs at
  `docs/specs/<slug>.md`
- **Executor** — Codex (`[agents.executor]`), workspace-write sandbox, one spec per
  worktree, `just check` before done
- **Reviewer** — Codex (`[agents.reviewer]`), read-only, schema-valid JSON in PR bodies

#### Spec-driven flow

- `docs/specs/`, `scripts/lint_spec.py`, `.reviewer-schema.json`,
  `scripts/validate_reviewer.py`

#### Hooks, skills, injection scan, Cursor rules

- `scripts/hooks/` — red-zone, branch name, scratch guard, spec lint on Stop
- `.claude/skills/` — `write-spec`, `calibrate-reviewer`
- `scripts/scan_injection.py` — part of `just check`
- `.cursor/rules/` — project conventions

#### Layout *(Customize)*

- `src/your_package/` — placeholder package (`__init__.py` only); rename per post-fork checklist
- `tests/`, `.scratch/`, `docs/blueprint.md`, `CONTRIBUTING.md`

### Optional: GitHub MCP (Codex Reviewer) *(Keep)*

Not required for `just check` or CI. Only if you enable GitHub MCP in
`.codex/config.toml` so Reviewer can read linked issues (`docs/blueprint.md` §4).

1. `cp .env.example .env` — set `GITHUB_PERSONAL_ACCESS_TOKEN` (never commit `.env`)
2. Load env before Codex (Codex does **not** read `.env` automatically):

   ```bash
   set -a && source .env && set +a
   codex --profile reviewer
   ```

3. Add `[mcp_servers.github]` in `.codex/config.toml` (red-zone; human edit). Details:
   [CONTRIBUTING.md](./CONTRIBUTING.md), blueprint §5.12.

### Shipped governance features *(Keep)*

**Router (Phase 4)** — `route-pr.yml` labels PRs `review:codex`, `review:human`, or
`blocked`. Automerge bots should gate on `review:codex` + green CI; see CONTRIBUTING.

**Telemetry (Phase 5)** — `docs/telemetry/events.jsonl`, `just telemetry-dashboard`,
`just adapt-thresholds` / `adapt-thresholds-write`, `record-telemetry.yml` on merge.

**Scheduled executor (Phase 6, v1)** — `scheduled-executor.yml` queues T0+low `drafted`
specs under `docs/specs/` and opens stub PRs via `dispatch_spec.py`. See
`docs/blueprint.md` §4 and CONTRIBUTING.md. Template spec history:
`docs/archive/template-specs/`.

### Why this exists *(Keep — optional trim)*

AI-assisted work needs governance at the runtime layer, not only in prompts. This
stack combines hygiene tooling (`uv`, `ty`, pre-commit, CI) with role-split agents,
lint-enforced specs, hooks, structured review, and deterministic PR routing.

### Philosophy *(Keep)*

- **Local-first** — no cloud required to develop
- **`just check` is the contract** — local and CI
- **Sandboxes over prompts** — Plan Mode, workspace-write, read-only Reviewer
- **Tooling over guidelines** — don't duplicate ruff rules in prose
- **Specs are documentation** — plain Markdown, `lint_spec.py` enforced
- **Hooks are tripwires** — edit-time enforcement where possible

### License *(Customize)*

MIT — see [LICENSE](./LICENSE) (update copyright on fork).
