# Post-Fork Checklist

The first hour after forking `ai-project-template`. Ordered by dependency —
earlier steps unblock later ones. Expect ~30-60 minutes depending on how
much project-specific content you have ready.

## 0. Before anything else

- [ ] Give your repo a real name on GitHub (Settings → General → Rename).
  The template's name was `ai-project-template`; yours should be
  `ai-<your-thing>` or similar.
- [ ] Update the repo description and topics on GitHub.
- [ ] **Unset "Template repository"** in Settings unless you intend
  *your* fork to also be a template for others.

## 1. Rename the Python package (breaks `just check` until done)

The template ships with a placeholder package named `your_package`. Rename
it consistently across four locations:

- [ ] `src/your_package/` → `src/<your_package>/` (directory rename)
- [ ] `pyproject.toml` — `[project] name = "your-project-name"` → your slug
- [ ] `pyproject.toml` — `[tool.hatch.build.targets.wheel] packages =
      ["src/your_package"]` → `["src/<your_package>"]`
- [ ] `tests/test_smoke.py` — `import your_package` → `import <your_package>`

After this step, `uv sync --extra dev && just check` should pass.

## 2. Update LICENSE and project metadata

- [ ] `LICENSE` — replace `TODO: Your Name` with your real name
- [ ] `pyproject.toml` — `description = "TODO: ..."` with one real sentence
- [ ] `README.md` — rewrite from scratch using the template as scaffolding;
      the template's README is about *the template*, not your project

## 3. Write AGENTS.md

This is the most valuable and the hardest step. AGENTS.md is what makes
your project AI-ready. See the comment block at the top of the file for
the invariant-writing discipline.

- [ ] Fill in the `## What this is` section (one paragraph)
- [ ] Fill in the `## Stack` section with your actual dependencies
- [ ] Draft 3-5 `## Architectural invariants` specific to your project.
      Use the three-question test in the AGENTS.md comment block.
      Aim for non-obvious, high-consequence rules — not style rules.
- [ ] Fill in `## Where things live` with your actual directory structure
- [ ] Delete all the `<!-- HOW TO USE THIS FILE -->` comments when done

**Do not ship placeholder invariants.** An empty "Architectural invariants"
section with a note like `<!-- TBD after first milestone -->` is better
than fake rules.

## 4. Add a domain-specific Cursor rule

The template ships with three generic rules: `00-always.mdc`, `tests.mdc`,
and `writing-rules.mdc`. Most projects benefit from a fourth, domain-scoped
rule. Examples from the portfolio:

- `langgraph.mdc` — for LangGraph multi-agent projects
- `rag.mdc` — for retrieval-augmented generation projects
- `scaffolder.mdc` — for code generators / CLI scaffolders

Naming: use the domain, not the tech (good: `rag.mdc`; bad: `chromadb.mdc`).

- [ ] Create `.cursor/rules/<domain>.mdc` with `globs:` frontmatter scoping
      it to the relevant files — see `writing-rules.mdc` for the authoring
      workflow

## 5. Wire up secrets (only if you need them)

The template assumes no runtime secrets — `just check` passes without
network or API keys. If your project needs them:

- [ ] Create `.env.example` listing every required variable with placeholder
      values. Commit this file.
- [ ] Add `.env` to `.gitignore` (the template already does this)
- [ ] Document required variables in README under `## Setup`
- [ ] If tests need an API key, mark them `@pytest.mark.integration`, not
      `@pytest.mark.skipif` — gives users explicit control over what runs

## 6. First commit and push

- [ ] On a feature branch (never `main`): make your first real commit
- [ ] `just check` must pass before the commit (the `no-commit-to-branch`
      hook will block you on `main`; ruff/ty/pytest will block any commit
      that breaks the gate)
- [ ] Open a PR against `main` and merge. CI should turn green in under 60
      seconds on the first run.

## 7. Update `.claude/settings.json` if you have domain-specific paths

- [ ] If your project has product data or generated files that should never
      be edited by AI agents (e.g., `data/`, `templates/`), add them to
      the `deny` list under `permissions.deny`. The template ships with
      reasonable defaults but cannot know your project's layout.

## 8. Optional — add a `.scratch/.gitkeep` note

- [ ] If your team has conventions for `.scratch/` use (naming,
      retention), add a `.scratch/README.md` explaining them. The template
      ships with a `.gitkeep` and convention pointers in `AGENTS.md` and
      the Cursor `00-always.mdc` rule.

## 9. Decide what to do with the example specs

The template ships with one or more example specs under `docs/specs/`
(currently `add-greet-module.md`). They demonstrate the §5.1 structure
end-to-end and serve as a regression target for `lint_spec.py`. You have
two reasonable options:

- [ ] **Delete them.** A fresh project should not carry example specs
      that aren't authorizing real work. Run
      `rm docs/specs/add-greet-module.md` (and any other
      example-named files). Confirm `just check` still passes.
- [ ] **Keep them as references.** Move them under
      `docs/specs/_examples/` so they don't appear alongside your real
      specs but remain discoverable. Update `docs/specs/README.md` to
      mention the references directory.

Either way, do this before opening your first real spec PR — otherwise
the example will appear in `just lint-changed-specs` outputs and create
confusion.

## Done state

After this checklist, your project should:
- Pass `just check` from a fresh clone with `uv sync --extra dev`
- Have a meaningful `AGENTS.md` with 3-5 real invariants
- Have at least one domain-specific Cursor rule
- Be at roughly 32-34/40 on the portfolio modernization rubric — the
  remaining 6-8 points come from project-specific work (coverage,
  ADRs, deployment) that no template can provide.
