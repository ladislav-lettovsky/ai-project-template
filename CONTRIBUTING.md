# Contributing

This file is the day-to-day operational guide. The architecture lives in
[`docs/blueprint.md`](./docs/blueprint.md); the agent-facing rules live in
[`AGENTS.md`](./AGENTS.md). Read those two for the *why*. Read this one
for the *how* and the *gotchas*.

**Legend (same as [README.md](./README.md)):** **Keep** = valid after fork;
**Customize** = update placeholders; **Replace** = template-only, delete on fork.
This file is mostly **Keep** except where noted.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/<you>/<your-project>.git
cd <your-project>

# One-shot rehydrate: syncs dev deps and installs pre-commit hooks
just refresh
```

`just refresh` is the canonical setup command. Run it after a fresh
clone, after `git worktree add`, or after pulling a branch that changed
`pyproject.toml` or `uv.lock`. Under the hood it is just
`uv sync --extra dev` + `uv run pre-commit install`.

## Per-checkout virtual environments

The `.venv` directory is git-ignored and lives inside each checkout. A
new `git worktree add ../<repo>-<slug>` produces a worktree with **no**
`.venv` — running `just check` there will fail with cryptic
`Cannot resolve imported module` errors until you run `just refresh`
inside the new worktree. The same applies after merging a dependency
change into `main`: the old `.venv` is now stale, and `ty check` will
flag the missing imports until the next `just refresh`.

Rule of thumb: if a brand-new error is "module X not resolvable" or
"no such command", the answer is almost always `just refresh`.

## Branch hygiene

`main` is checkout-only. Every commit lives on a topic branch.

The recommended workflow after `git pull`:

```bash
git checkout main
git pull
git switch -c scratch         # parking branch — never push, never commit real work to it
```

Treat `scratch` as ephemeral: when work has a name, rename it
(`git branch -m scratch fix/<slug>`) or branch off it
(`git switch -c spec/<slug>`). This pattern eliminates the most common
foot-gun in this repo: editing files while sitting on `main`.

**First step on a new implementation prompt while on `scratch`:** before
**creating or editing files**, read the prompt, decide whether it describes a new
capability (→ `spec/<slug>`) or a bug fix (→ `fix/<slug>`), and rename
the parking branch in place:

```bash
git branch -m scratch spec/<slug>   # or fix/<slug>
```

The **UserPromptSubmit** hook (`check_branch_name.py`) allows `main`, `scratch`,
and branch names starting with `chore/`, `docs/`, `feat/`, `fix/`, `refactor/`,
`spec/`, or `test/`. Branch `scratch` is for prompt intake only; the
**PreToolUse** hook (`check_no_edits_on_scratch.py`) blocks file edits until you
rename off `scratch`. Recreate `scratch` from `main` only after the work merges.

The `no-commit-to-branch` pre-commit hook will reject commits to
`main` regardless, but it can't catch *edits* — only commits. Sitting
on `scratch` by default means edits land somewhere safe.

### Branch name conventions

| Branch | Purpose |
| --- | --- |
| `main` | Production-ready code; CI must pass before merge. |
| `spec/<slug>` | Implementing an authorized spec. |
| `fix/<slug>` | Bug fix, with or without a spec. |
| `scratch` | Ephemeral parking branch (do not push). |
| `feat/`, `refactor/`, `chore/`, `docs/`, `test/` | Conventional prefixes for ad-hoc work. |

Specs of any non-trivial size should land on `spec/<slug>` so the
The Router can recognize them.

## Project Layout

This project uses the [src layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) —
all production code lives under `src/<your_package>/`.

| Directory             | Purpose                                                          |
| :-------------------- | :--------------------------------------------------------------- |
| `src/<your_package>/` | Production Python package                                        |
| `tests/`              | Pytest test suite                                                |
| `docs/`               | Project documentation                                            |
| `docs/specs/`         | One Markdown spec per feature; lint-enforced (see Spec Workflow) |
| `.scratch/`           | Ephemeral scratchpad for exploratory work (git-ignored contents) |
| `scripts/hooks/`      | Claude Code lifecycle hooks (red-zone)                           |

Describe any subdirectories of `src/<your_package>/` here once you have them.

## Running Tests

```bash
just test                                 # all tests
uv run pytest tests/test_smoke.py -v      # specific file
uv run pytest -m "not integration"        # skip live-API tests
```

## Quality Gate

`just check` is the canonical gate. It runs the same checks CI runs,
in the same order:

```bash
just check
```

Under the hood:

1. All pre-commit hooks (branch guard, hygiene, ruff, ty)
2. `uv run ty check` — full type check
3. `uv run pytest` — all tests
4. `just lint-changed-specs` — spec structure linter on touched specs
5. `just scan-injection` — prompt-injection scan on LLM-input artifacts

## Common gotchas

A short list of things that have bitten contributors. None are bugs;
each is a design choice with a sharp edge.

### `just check` always fails on `main`

Because `pre-commit run --all-files` runs unconditionally inside
`just check`, the `no-commit-to-branch` hook fires whether or not you
intended to commit. If `just check` failed with `no-commit-to-branch`,
you're sitting on `main` — switch to a topic branch first
(`git switch -c fix/<slug>`) and re-run.

### Spec files need the `.md` extension

`scripts/lint_spec.py` and `just lint-changed-specs` both filter on
`docs/specs/*.md`. A file saved as `docs/specs/my-feature` (no
extension — easy to do in editor "New File" dialogs) will be silently
ignored by the linter and the Stop hook. If you draft a spec and the
hook is suspiciously quiet, check the extension.

### Codex profile selection

The Executor and Reviewer roles are Codex *profiles*. Select them at
session start:

```bash
codex --profile executor --cd ../<repo>-<slug>   # sibling worktree; name to taste
codex --profile reviewer
```

Switching profiles mid-session via slash command does not change the
sandbox mode — the sandbox is set when the process starts. If you want
a read-only Reviewer session, you must launch it that way.

### GitHub MCP for Reviewer (optional)

Not required for `just check` or CI. Enable only when you want the Reviewer to
fetch linked GitHub issues (e.g. `Fixes #N` in the PR body) and cite them in
`evidence` fields.

1. **Secrets** — copy [`.env.example`](.env.example) to `.env` (gitignored).
   Set `GITHUB_PERSONAL_ACCESS_TOKEN` to a fine-scoped PAT. Do not commit `.env`.

2. **Load env before Codex** — Codex forwards `env_vars` from your **shell**, not
   from `.env` on disk unless you source it:

   ```bash
   set -a && source .env && set +a
   codex
   ```

   Then spawn the Reviewer subagent (read-only) per `[agents.reviewer]` — see
   blueprint §5.12. `--profile reviewer` only works if you define
   `[profiles.reviewer]` in `~/.codex/config.toml` (profiles are user-level).

3. **Config** — `[mcp_servers.github]` in `.codex/config.toml` (red-zone;
   human-authored). Start the server in **read-only** mode so write tools are not
   advertised to the model — `sandbox_mode = "read-only"` on the Reviewer does not
   constrain MCP-side tools. Official shape: [Codex MCP](https://developers.openai.com/codex/mcp),
   [github-mcp-server configuration](https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md).

   ```toml
   [mcp_servers.github]
   command = "docker"
   args = [
     "run", "-i", "--rm",
     "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
     "-e", "GITHUB_READ_ONLY=1",
     "ghcr.io/github/github-mcp-server",
     "stdio", "--read-only",
     "--toolsets=issues,pull_requests",
   ]
   env_vars = ["GITHUB_PERSONAL_ACCESS_TOKEN"]
   ```

4. **Injection** — do not paste raw MCP tool output into `docs/specs/*.md`. If you
   paraphrase issue text into a spec, run `just scan-injection`.

### GitHub MCP for Planner (optional)

The Planner subagent (`.claude/agents/planner.md`) declares `mcpServers: [github]` so
Claude Code can pull linked issue/PR context while drafting specs in Plan Mode. Same PAT
and read-only Docker server as the Reviewer; see steps 1–4 above.

1. Copy [`.mcp.json.example`](.mcp.json.example) to `.mcp.json` (gitignored) or merge
   the `github` entry into your Claude project MCP config.
2. Export `GITHUB_PERSONAL_ACCESS_TOKEN` in the shell before starting Claude Code.
3. Do not paste raw MCP tool output into committed specs — paraphrase and run
   `just scan-injection` when issue text influences Requirements.

**Post-mortems** — template `docs/specs/_postmortem.md`; playbook
`.claude/skills/postmortem/SKILL.md` (one incident → one invariant or prompt change).

### Worktree cleanup

`.claude/worktrees/` accumulates over time. A weekly hygiene pass:

```bash
git worktree prune
git worktree list
# remove any stale .claude/worktrees/spec-* directories whose branches are merged
```

### Editing red-zone files

Files listed in `AGENTS.md` under "Red-zone files" are blocked at
edit-time by `scripts/hooks/check_red_zone.py` for any Claude Code
agent session. Two ways to author intentional red-zone edits:

- **Path A (preferred):** edit in your editor (Cursor) directly. The
  hook only fires for Claude Code's `Edit`/`Write`/`MultiEdit` tools.
- **Path B (fallback):** instruct the Codex Executor explicitly. The
  Codex sandbox does not honor the Claude Code hook layer; document
  the deliberate red-zone touch in the PR body so future readers
  see it was intentional.

In either case: the PR description must call out the red-zone touch,
and risk_tier in the spec should reflect it (typically T1+).

## Spec Workflow

Specs live in `docs/specs/<slug>.md` and follow the §5.1 structure
documented in `docs/blueprint.md`. The structure is enforced by
`scripts/lint_spec.py` (run by `just check` and the `Stop` hook).

When does work need a spec? Use these consequence-based criteria
(time on the clock is *not* a reliable signal — see `.claude/agents/planner.md`):

- The change touches a red-zone file (per AGENTS.md).
- The change touches multiple unrelated files (co-located tests don't count).
- The change alters a public interface or behavior contract.
- A future reader will need context this PR diff cannot provide.

If any of those is true, write the spec first. If none are, an ad-hoc
prompt is fine.

The `write-spec` Agent Skill (`.claude/skills/write-spec/SKILL.md`)
walks you through the format step by step. The Planner subagent
loads it automatically.

## CI

GitHub Actions runs `just check` on every push to `main` and on every
pull request. The workflow is intentionally a thin wrapper — same
command as local, no rule duplication. See `.github/workflows/ci.yml`.

### `route-pr` workflow (Router)

`.github/workflows/route-pr.yml` runs on pull requests to `main`. It:

1. Runs `uv run scripts/build_pr_context.py` to assemble `pr.json` (changed
   files, diff size, authorizing-spec lint, Reviewer JSON validation).
2. Runs `uv run scripts/route_pr.py` against `.routing-policy.json` to assign
   one of `review:codex`, `review:human`, or `blocked`, then posts a PR
   comment with machine-readable reasons.

The job **succeeds** when those steps complete — a `review:human` label is not a
failed check. Humans merge once review is done. If you use Codex or another
bot to auto-merge, gate that path on `review:codex` plus green `CI`; branch
protection required checks alone cannot express "only automerge when label
X" without additional rules or bots.

Fork-head PRs receive a comment with the router’s recommendation; automated
label application applies to same-repo head branches (see workflow `if:`).

### Scheduled executor

`.github/workflows/scheduled-executor.yml` runs on weekdays at 09:00 UTC and via
`workflow_dispatch:`. It never runs on fork repositories (`if:
github.event.repository.fork == false`).

**Eligibility (D2):** Only specs with `risk_tier: T0`, `complexity: low`, every
Red-Zone Assessment axis `no`, and `status: drafted` are candidates. T1+ specs,
red-zone `yes` rows, or malformed metadata are logged with `skip_reason` and never
dispatched. One spec per run: lexicographically first eligible slug (D5).

**Dispatch (D3):** The workflow calls `scripts/dispatch_spec.py`, which creates
`spec/<slug>` from `origin/main`, seeds an empty commit when needed, and opens a GitHub
PR whose body links the spec and carries a schema-valid `REVIEWER_JSON` stub. PR bodies
include `dispatch-source: scheduled` for telemetry (Slice 2). Legacy `--transport issue`
opens a `scheduler-queue` tracking issue only (rollback).

**Without `OPENAI_API_KEY`:** transport stays `pr` — stop at open PR; a human or local
Codex session runs Executor and Reviewer; `route-pr.yml` labels the PR.

**With `OPENAI_API_KEY` (Codex-in-CI):** transport is `codex`; the `codex_executor` and
`codex_reviewer` jobs run
`openai/codex-action@v1` for Executor (workspace-write) and Reviewer (read-only), applies
Reviewer JSON via `scripts/codex_ci.py apply-reviewer`, and validates with
`scripts/validate_reviewer.py`. Optional squash-merge when repository variable
`SCHEDULER_AUTO_MERGE=true` and the PR is labeled `review:codex` with a clean merge state
(`scripts/try_auto_merge.py`). Local replay: `uv run scripts/codex_ci.py write-prompt`
and `uv run scripts/codex_ci.py exec` (requires `codex` CLI + API key).

**Failure visibility (D6):** Any failing step fails the job (no `|| true`). A
`scheduler-failure` issue is opened with the workflow run URL.

**GitHub Actions permissions (required for dispatch):** In the repo **Settings →
Actions → General → Workflow permissions**, choose **Read and write permissions** and
enable **Allow GitHub Actions to create and approve pull requests**. Without this,
`gh pr create` in the dispatch step fails after the branch is pushed (you may see a
leftover `spec/<slug>` branch with no PR). Re-run the workflow after enabling; if the
branch already exists, dispatch reuses it or opens the PR on retry.

**Disable / rollback:** Rename or delete `.github/workflows/scheduled-executor.yml`
(e.g. `scheduled-executor.yml.disabled`) to stop cron and manual runs. Revert
`CONTRIBUTING.md` / blueprint notes if you remove the feature entirely.

Authorizing spec:
[`docs/archive/template-specs/scheduled-executor.md`](docs/archive/template-specs/scheduled-executor.md).

### Branch protection (Router)

Configure in GitHub **Settings → Branches → Branch protection rules** for
`main` (not in-repo YAML):

1. **Require status checks:** `CI — Quality Checks` (or your `just check` job)
   and **`Router — Label PR`** / `route` job from `route-pr.yml`.
2. **Do not** fail the `route-pr` check when the label is `review:human` — the
   workflow succeeds after labeling; humans merge when review is complete.
3. **Automerge / bots:** If you use GitHub auto-merge, Mergify, or Codex merge
   automation, add a rule so only PRs labeled **`review:codex`** may auto-merge
   (and still require green CI). PRs labeled **`blocked`** or **`review:human`**
   must not auto-merge.

## Before saying "done"

A short pre-PR checklist that mirrors the one in `AGENTS.md`:

1. `just check` passes locally.
2. Any new public function has a test and a type-annotated signature.
3. No new `print()` calls in production code — use `logging.getLogger(__name__)`.
4. If behavior changed, README and CONTRIBUTING reviewed.
5. Diff against `main` looks like what you'd want in a PR review.
6. PR description links the authorizing spec (Invariant 1).
7. PR description notes any red-zone touch and which authoring path was taken.
8. PR body contains a `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->`
   block (schema-valid JSON from the Reviewer, or a stub until Reviewer runs).

Saving a PR description locally for `just validate-reviewer <file>` often lands in
`.scratch/`. That directory is gitignored throwaway content; PR-body stubs usually
start with `<!-- REVIEWER_JSON -->`, which triggers MD041 if linted as a normal doc.
To avoid repeating that noise: **vscode-markdownlint** reads the repo-root
`.markdownlint-cli2.jsonc`, which ignores `.scratch/**` (workspace `markdownlint.ignore`
is deprecated in recent extension releases). `just lint-md-fix` also excludes
`.scratch/` via negated globs. Tracked Markdown (including specs under `docs/specs/`)
still follows markdownlint normally.

## See also

- [`AGENTS.md`](./AGENTS.md) — agent-facing rules and invariants.
- [`docs/blueprint.md`](./docs/blueprint.md) — full architecture and blueprint roadmap.
- [`docs/specs/README.md`](./docs/specs/README.md) — spec format reference.

### Template exit-drill logs *(forks may delete)*

Drill kits and spikes live under [`docs/archive/`](./docs/archive/) (`exit-drills/`,
`spikes/`, `template-specs/`). Forks can `rm -rf docs/archive`; see
`docs/post-fork-checklist.md` §9.
