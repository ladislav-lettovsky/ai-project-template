# Contributing

This file is the day-to-day operational guide. The architecture lives in
[`docs/blueprint.md`](./docs/blueprint.md); the agent-facing rules live in
[`AGENTS.md`](./AGENTS.md). Read those two for the *why*. Read this one
for the *how* and the *gotchas*.

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
doing any other work, read the prompt, decide whether it describes a new
capability (→ `spec/<slug>`) or a bug fix (→ `fix/<slug>`), and rename
the parking branch in place:

```bash
git branch -m scratch spec/<slug>   # or fix/<slug>
```

The `check_branch_name.py` UserPromptSubmit hook (Invariant 1) rejects
prompts on any branch other than `main`, `spec/*`, or `fix/*`, so a
session that stays on `scratch` will be blocked at the next prompt.
Recreate `scratch` from `main` only after the work merges.

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
Phase 4 Router can recognize them.

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
codex --profile executor --cd ../template-<slug>
codex --profile reviewer
```

Switching profiles mid-session via slash command does not change the
sandbox mode — the sandbox is set when the process starts. If you want
a read-only Reviewer session, you must launch it that way.

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

## Before saying "done"

A short pre-PR checklist that mirrors the one in `AGENTS.md`:

1. `just check` passes locally.
2. Any new public function has a test and a type-annotated signature.
3. No new `print()` calls in production code — use `logging.getLogger(__name__)`.
4. If behavior changed, README and CONTRIBUTING reviewed.
5. Diff against `main` looks like what you'd want in a PR review.
6. PR description links the authorizing spec (Invariant 1).
7. PR description notes any red-zone touch and which authoring path was taken.
8. PR body contains an empty `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->`
   block (the Reviewer fills it in Phase 3+).

## See also

- [`AGENTS.md`](./AGENTS.md) — agent-facing rules and invariants.
- [`docs/blueprint.md`](./docs/blueprint.md) — full architecture and phased roadmap.
- [`docs/specs/README.md`](./docs/specs/README.md) — spec format reference.
