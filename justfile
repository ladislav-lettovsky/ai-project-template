# Install pre-commit hooks into .git/hooks/ (run once after cloning)
install-hooks:
    uv run pre-commit install

# Re-hydrate this checkout: sync dev dependencies and (re-)install pre-commit hooks.
# Run after a fresh clone, after `git worktree add`, or after pulling a branch
# that changed pyproject.toml / uv.lock. The .venv is per-checkout (git-ignored),
# so every worktree needs its own sync.
refresh:
    uv sync --extra dev
    uv run pre-commit install

# Run all pre-commit hooks against every file in the repo
pre-commit:
    uv run pre-commit run --all-files

fmt:  # format code
    uv run ruff format .

lint:
    uv run ruff check .

lint-fix:
    uv run ruff check --fix .

# Lint Markdown (.md + .mdc). Uses the version pinned in .pre-commit-config.yaml.
lint-md:
    uv run pre-commit run markdownlint-cli2 --all-files

# Auto-fix Markdown lint violations. Version inline-pinned to match
# .pre-commit-config.yaml -- bump both together.
lint-md-fix:
    npx --yes markdownlint-cli2@0.22.1 --fix "**/*.md" "**/*.mdc" "!.scratch/**"

type:
    uv run ty check

test:
    uv run pytest

# Lint a spec file (or files) against the §5.1 structure.
# Usage: `just lint-spec docs/specs/<slug>.md [<other>.md ...]`
lint-spec *paths:
    uv run scripts/lint_spec.py {{paths}}

# Lint every spec touched on the current branch (relative to origin/main).
# Used by `just check`. Quietly does nothing if no specs were touched.
lint-changed-specs:
    #!/usr/bin/env bash
    set -euo pipefail
    base=$(git merge-base HEAD origin/main 2>/dev/null || echo "")
    if [ -z "$base" ]; then
        # Detached, no upstream, or fresh repo — fall back to working-tree changes.
        changed=$(git diff --name-only HEAD -- 'docs/specs/*.md' 2>/dev/null | grep -v '^docs/specs/_template\.md$' | grep -v '^docs/specs/README\.md$' | grep -v '^docs/specs/_postmortem\.md$' || true)
    else
        changed=$(git diff --name-only "$base"..HEAD -- 'docs/specs/*.md' 2>/dev/null | grep -v '^docs/specs/_template\.md$' | grep -v '^docs/specs/README\.md$' | grep -v '^docs/specs/_postmortem\.md$' || true)
    fi
    if [ -z "$changed" ]; then
        echo "lint-changed-specs: no spec files modified on this branch."
        exit 0
    fi
    echo "lint-changed-specs: $changed"
    uv run scripts/lint_spec.py $changed

# Scan LLM-input-bearing files for known prompt-injection patterns.
scan-injection:
    uv run scripts/scan_injection.py

# Validate the Reviewer's structured-JSON block in a PR body file.
# Usage: `just validate-reviewer <pr-body-file>` (or `-` for stdin)
validate-reviewer pr_body:
    uv run scripts/validate_reviewer.py {{pr_body}}

# Full quality gate: all pre-commit hooks + type check + tests + spec hygiene.
# This is the same command CI runs.
check: pre-commit
    uv run ty check && uv run pytest && just lint-changed-specs && just scan-injection
