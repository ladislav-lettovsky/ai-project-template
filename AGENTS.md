# {PROJECT_NAME} — AI Agent Memory

<!--
  HOW TO USE THIS FILE (delete this comment block after you've filled it in)

  AGENTS.md is the shared memory that Claude Code, Cursor, Codex CLI, and
  human contributors all read. Its job is to stop people (including AI
  agents) from making mistakes the code itself won't warn about.

  The sections below are required. Replace every {PLACEHOLDER} and every
  line that starts with "TODO:". Delete any section that genuinely does
  not apply to your project — but think twice before deleting "Architectural
  invariants."

  WRITING GOOD INVARIANTS (the hard section)

  An invariant earns its slot by being NON-OBVIOUS and causing SUBTLE,
  DELAYED damage when violated. Style rules belong in ruff; type rules
  belong in ty; only invariants go here.

  Use this shape for each invariant:

    N. **<Bold title sentence ending in a period.>**
       <One sentence of what/where, naming a concrete file or directory.>
       <One sentence of why violating it causes subtle damage — a
       picturable failure, not "breaks integrity".>
       If you find yourself <doing X>, stop and <do Y instead>.

  Three-question review test — for each invariant, ask:
    1. Does the title tell a reader what the rule is about?
    2. Does the "why" paint a specific failure I can picture
       (e.g., "400MB ships to every pipx user", not "breaks things")?
    3. Does the tripwire ("if you find yourself X, stop") catch a real
       keystroke a contributor might make?

  If any answer is "no" or "sort of", rewrite until all three are "yes".

  Good invariants are rare — aim for 3-5, not 10. A document with 10
  invariants has zero, because readers skim past them all.
-->

## What this is
TODO: One paragraph explaining what this project does and who uses it.
If it is a library, an application, a scaffolder, or a service, say so
explicitly — the shape of "what this is" determines the shape of
invariants that belong here.

## Stack
- Python 3.12+, `uv` for dependency management, `just` as the task runner
- TODO: list frameworks and libraries this project actually depends on
  (runtime only — dev tools are listed separately)
- Testing: pytest with optional `integration` marker for live-API tests
- Linting: ruff; Type checking: `ty` (Astral); Pre-commit hooks enabled

## Commands you can run without asking
- `just fmt` — format code
- `just lint` — ruff check
- `just lint-fix` — ruff check with --fix
- `just type` — ty check
- `just test` — full pytest run
- `just check` — pre-commit + type + test (the same command CI runs)
- `uv sync`, `uv sync --extra dev`
- TODO: add your project's entry points (e.g., `uv run python -m your_package`)
- Read-only git: `git status`, `git diff`, `git log`, `git branch`

## Commands with preconditions
- `git commit` is allowed on a non-`main` branch **only after `just check`
  passes with no errors**. On `main`, always ask first.

## Commands that need explicit approval
- `uv add`, `uv remove` (dependency changes)
- `git push`, `git reset --hard`
- `gh pr create`, `gh pr merge`
- Anything touching `.env`, `.github/workflows/`, or project-critical data dirs

## Architectural invariants (do not violate without explicit discussion)

<!--
  Draft 3-5 invariants specific to THIS project. Delete the example below
  once you have real ones. Do not ship placeholder invariants — an empty
  section is better than fake content.

  Good sources for invariants:
  - Boundaries between distinct layers (e.g., scaffolder vs. product code,
    agent vs. tool, model vs. view)
  - Places where a config change could silently break user code
  - Logic that is duplicated for good reasons but must stay in sync
  - Security boundaries (PII access, secret handling)
  - Testing constraints (e.g., "tests must run without network")
-->

1. **TODO: <Write your first invariant here.>**
   What/where — name a concrete file or directory this rule applies to.
   Why — describe a specific, picturable failure that happens when it's
   violated. If you find yourself <specific action>, stop and <correct
   redirect> instead.

## Where things live
- `src/{your_package}/` — production package (src layout)
  - TODO: describe each subdirectory's purpose
- `tests/` — pytest test suite
- `docs/` — project documentation
- `.scratch/` — sanctioned scratchpad for exploratory work (git-ignored contents)

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

## Before saying "done"
1. `just check` passes (ruff + ty + pytest)
2. Any new public function has a test and a type-annotated signature
3. No new `print()` calls in production code — use
   `logging.getLogger(__name__)`
4. If the change affects behavior, `README.md` and `CONTRIBUTING.md` reviewed
5. Diff against `main` looks like what you'd want in a PR review
