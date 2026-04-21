# Contributing

## Development Setup

```bash
# Clone the repository
git clone https://github.com/<you>/<your-project>.git
cd <your-project>

# Install with dev dependencies
uv sync --extra dev

# Install pre-commit hooks (runs ruff, ty, and hygiene checks on every commit)
just install-hooks
```

## Project Layout

This project uses the [src layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) —
all production code lives under `src/<your_package>/`.

| Directory | Purpose |
|:---|:---|
| `src/<your_package>/` | Production Python package |
| `tests/` | Pytest test suite |
| `docs/` | Project documentation |
| `.scratch/` | Ephemeral scratchpad for exploratory work (git-ignored contents) |

Describe any subdirectories of `src/<your_package>/` here once you have them.

## Branch Conventions

| Branch | Purpose |
|:---|:---|
| `main` | Production-ready code. All CI must pass before merging. |
| `feat/<name>` | New features (e.g., `feat/escalation-rules`) |
| `fix/<name>` | Bug fixes (e.g., `fix/off-by-one-pagination`) |
| `refactor/<name>` | Internal restructuring with no behavior change |
| `chore/<name>` | Tooling, config, dependencies — no runtime behavior change |
| `docs/<name>` | Documentation-only updates |
| `test/<name>` | Test additions or fixes |

Use [Conventional Commits](https://www.conventionalcommits.org/) for
commit messages; one logical change per commit.

## Running Tests

```bash
# Run all tests
just test

# Or equivalently
uv run pytest

# Run a specific test file
uv run pytest tests/test_smoke.py -v

# Skip integration tests (if you have any)
uv run pytest -m "not integration"
```

## Quality Gate

`just check` is the canonical command. It runs the same set of checks that
CI runs, in the same order:

```bash
just check
```

Under the hood:
1. All pre-commit hooks (branch guard, hygiene, ruff, ty)
2. `uv run ty check` — full type check
3. `uv run pytest` — all tests

Commits on non-`main` branches are allowed only after `just check` passes.
Never commit directly to `main` (the `no-commit-to-branch` pre-commit hook
will block you).

## Key Architectural Invariants

See [AGENTS.md](./AGENTS.md) for the full list with rationale.

## CI

GitHub Actions runs on every push to `main` and on pull requests. The
workflow is a thin wrapper that runs `just check` — same command as local,
no rule duplication. See `.github/workflows/ci.yml`.
