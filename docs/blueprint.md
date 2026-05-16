# AI-Native Development Environment Blueprint

**Author:** Ladislav Lettovsky
**Target:** Semi-autonomous software factory where specs in → reviewed PRs out, with human judgment reserved for irreversible or architectural decisions

---

## Document hygiene

**AGENTS.md describes the present; this blueprint describes the trajectory.** When a phase ships, the corresponding capability gets promoted in `AGENTS.md` from a forward-looking marker (`*(Phase N)*`) to live full text, and the marker is deleted. Backward markers like "added in Phase N" are noise — by the time someone reads `AGENTS.md`, they care what's true today, not what shipped when. The blueprint, by contrast, *does* keep historical markers (Phase numbers, "added in v2") because its purpose is to explain how the system arrived at its present state. Two documents, two audiences, one source of truth per claim.

**Bootstrap exception for phase-implementation PRs.** Invariant 1 requires every PR to link an authorizing spec, and §5.1 requires every spec to pass `lint_spec.py`. Phase-implementation PRs are recursive: the PR that *introduces* `lint_spec.py` cannot itself be linted by `lint_spec.py`, and the PR that introduces the Reviewer schema cannot itself produce a Reviewer JSON validating against that schema. Acknowledge the recursion explicitly in the PR body ("bootstrap PR — introduces the gate it would otherwise be subject to") rather than pretending the invariant was satisfied. Future-you will need this note when grepping the spec history for the first lint-clean spec.

**Optional session complements (non-normative).** Teams may adopt lightweight habits alongside specs: an ephemeral **lessons** log under `.scratch/` and an explicit **re-plan** rule when adhoc work goes sideways. These artifacts sit **outside** the merge gate—they reduce repeated mistakes and wasted trials but must **not** compete with `docs/specs/` as the authorizing plan for delivery work. Cursor may encode host-specific guidance under `.cursor/rules/` (agent-requested rules); other hosts rely on the portable subset in `AGENTS.md`.

---

## Purpose of this document

This blueprint defines the target state of a modern AI-native development environment and a phased path to reach it. It preserves the standards `ai-project-template` already ships — `uv`, `just`, `ty`, strict CI, and the invariants discipline from AGENTS.md — and extends them into a governed multi-agent system that exploits the native primitives of Claude Code and Codex (subagents, hooks, plan mode, worktrees, skills, MCP).

**Scope of applicability:**

- `ai-project-template` is the **living repo** — every phase of this blueprint evolves it first. All future projects forked from the template inherit whatever phase is live.

**Phased implementation:**

- Execute Phase 1 against `ai-project-template` first.
- Each subsequent phase is gated by its predecessor's exit criterion.

**What this document is not:**

- A copy-paste setup guide. Every code sample is illustrative; the real implementation will earn its own review per your standards.
- A timeline. Phases are ordered by dependency, not by calendar.

---

## 1. North Star — the endgame system

```text
               ┌──────────────────────────────────────────────┐
               │            Author (Human)                    │
               │     (product direction + irreversible gate)  │
               └──────────────────┬───────────────────────────┘
                                  │
                    defines feature / fixes bug /
                    sets architectural constraint
                                  │
                                  ▼
               ┌──────────────────────────────────────────────┐
               │     Planner  (Claude Code subagent)          │
               │  permissionMode: plan  (read-only)           │
               │  Writes docs/specs/<feature>.md              │
               │  Assigns risk_tier (T0..T3) + complexity     │
               │  Names invariants + test plan                │
               │  Spec must pass `lint_spec.py` before merge  │
               └──────────────────┬───────────────────────────┘
                                  │  (worktree spawned)
                                  ▼
               ┌──────────────────────────────────────────────┐
               │     Executor  (Codex [agents.executor])      │
               │  sandbox_mode: workspace-write               │
               │  approval_policy: on-request                 │
               │  Implements one spec per branch / worktree   │
               │  `just check` must pass locally              │
               │  Opens PR with spec link + reviewer payload  │
               └──────────────────┬───────────────────────────┘
                                  │
                                  ▼
               ┌──────────────────────────────────────────────┐
               │   Reviewer  (Codex [agents.reviewer])        │
               │  sandbox_mode: read-only                     │
               │  model_reasoning_effort: high                │
               │  Outputs schema-valid JSON, not prose        │
               │  Includes findings[], coverage, confidence   │
               │  Bias: false positives over false negatives  │
               └──────────────────┬───────────────────────────┘
                                  │
                                  ▼
               ┌──────────────────────────────────────────────┐
               │     Router (GitHub Action, Python, no LLM)   │
               │  Inspects PR context + reviewer JSON         │
               │  Three outcomes: review:codex / human /      │
               │                  blocked                     │
               └────────┬────────────────┬────────────────────┘
                        │                │
             review:codex    review:human     blocked
                        │                │         │
                        ▼                ▼         ▼
               ┌─────────────┐    ┌─────────┐  ┌───────────────┐
               │ CI green    │    │ Author  │  │ Dead until    │
               │ + auto-merge│    │ review  │  │ critical      │
               └──────┬──────┘    └────┬────┘  │ finding fixed │
                      │                │       └───────────────┘
                      └────────┬───────┘
                               ▼
                  ┌─────────────────────────────────────────┐
                  │    Telemetry + feedback                 │
                  │  docs/telemetry/events.jsonl            │
                  │  + optional OTel exporter (Codex)       │
                  │  → adaptive thresholds                  │
                  │  → prompt + skill improvements          │
                  └─────────────────────────────────────────┘
```

### Division of labor

**Claude plans (in Plan Mode) with risk tiers. Codex executes bounded work in a workspace-write sandbox. A second Codex (read-only sandbox) reviews with structured JSON. A deterministic Router decides human vs. agent vs. blocked. Hooks enforce tripwires at edit-time before any of this matters.**

### Role of the Planner (Claude Code subagent)

The Planner is a Claude Code subagent (`.claude/agents/planner.md`) with `permissionMode: plan` and `tools: [Read, Grep, Glob]` — read-only by construction. It owns both the *what* and the *how-it-will-be-tested* — the spec includes a Test Plan section with T1→R1 mappings. The Planner cannot write files; the spec is committed by the human after Plan Mode approval.

### Roles of the Executor and Reviewer (Codex subagents)

Both are defined in `.codex/config.toml` under `[agents.executor]` and `[agents.reviewer]`. The Executor has `sandbox_mode = "workspace-write"`, `approval_policy = "on-request"`. The Reviewer has `sandbox_mode = "read-only"`, `model_reasoning_effort = "high"`. The split is enforced by Codex's sandbox layer, not by prompt discipline alone.

### Deterministic Router

The Router is a deterministic Python script that decides — before any LLM is involved — whether a diff is safe for agent review. **The gate must be mechanical where it matters most.**

A PR with a **critical finding from the Reviewer** is not "a PR a human should look at" — it is **dead code until the finding is addressed**. A `blocked` outcome creates a distinct queue with different UX: the author must respond to the finding before the PR moves at all.

### Defense-in-depth ordering

Every tripwire in this system fires at the earliest possible layer. The layers, in firing order:

1. **Claude Code hooks** — PreToolUse / UserPromptSubmit / Stop. Block disallowed actions *before they happen*. Edit-time.
2. **pre-commit** — `no-commit-to-branch`, format, basic lint. Commit-time.
3. **`just check`** — full local validation: `ty`, `pytest`, `lint_spec.py`, `scan_injection.py`. Pre-push time.
4. **CI** — re-runs `just check` on the runner, plus the Router. Post-push time.
5. **Router + branch protection** — final gate; auto-merge only when all preceding layers passed and Router emits `review:codex`. Merge-time.

Layer N is not redundant with layer N-1; layer N catches what layer N-1 cannot. Hooks specifically catch the agent's intent before any state changes — a PreToolUse hook rejecting an `Edit` on `AGENTS.md` is qualitatively different from CI failing on the same change after the diff has been pushed.

---

## 2. Invariants of this system

These are the rules that stay true across all phases. If a proposed change violates one, either the change is wrong or the invariant needs a deliberate version bump.

### Invariant 1 — The role split is observable in every PR

**Subject:** Any PR opened against a repo that has adopted this system.

**Rule:** The PR description must link the spec that authorized the work, and the PR branch name must start with `spec/<slug>` or `fix/<slug>`. The PR body must include a reviewer-JSON block fenced with `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->`.

**Why (picturable):** Six months from now you'll review a PR and ask "why was this written?" The three artifacts — spec, branch name, reviewer JSON — turn every PR into a verifiable trace.

**Tripwire:** If you find yourself opening a PR that cannot cite a spec, stop. Either write the spec first, or acknowledge you're working outside the system (and that's fine sometimes — this blueprint is not a cage).

### Invariant 2 — The Router is code, not vibes

**Subject:** The PR routing logic that decides Codex review vs. Author review vs. blocked.

**Rule:** Routing is a GitHub Actions workflow that inspects diff + spec metadata + reviewer JSON and applies explicit rules (see §5.3). It emits one of three labels. It does not consult an LLM. The routing policy is a checked-in JSON file (`.routing-policy.json`), not a hard-coded constant.

**Why (picturable):** An LLM router is a gate that can be prompted around. A Python script checking `if "AGENTS.md" in changed_files: label = "review:human"` is a gate that can be audited by reading 20 lines of code. You want to sleep soundly when Codex is merging its own work — the Router is the reason you can. Putting the thresholds in a JSON file (not inline constants) means you can tune them without editing code, and the tuning history is a simple git log.

**Tripwire:** If you find yourself writing "let Claude decide whether this needs human review", stop. Write the deterministic rule instead. If you find yourself changing a threshold by editing the Python source, stop. Change the JSON policy file.

### Invariant 3 — Specs are documentation, not metadata

**Subject:** Feature specifications that drive Codex execution.

**Rule:** Specs live in `docs/specs/` as plain Markdown, readable by any human opening the repo. Each spec has a well-defined structure (see §5.1) including risk_tier, complexity, requirements with stable IDs, test plan with T→R mappings, and a done-when checklist. A spec that fails `scripts/lint_spec.py` is not valid and cannot be used to authorize a PR.

**Why (picturable):** `README.md` describes what this repo does. `AGENTS.md` defines how agents work in it. `docs/specs/` captures *the history of what was built and why*. Specs-as-docs are reviewable, diffable, searchable. Lint-enforced structure means a spec can't silently degrade into a vague prompt — the CI rejects it.

**Tripwire — consequence-based, not time-based.** If any of the following is true, the work needs a spec before code lands:

- The change touches a red-zone file (per the canonical list in §5.5 / AGENTS.md).
- The change touches multiple unrelated files (a file plus its co-located tests does not count as multi-file).
- The change alters a public interface or behavior contract.
- A future reader will need context the PR diff cannot provide on its own.

### Invariant 4 — No regression of the existing gold-standard

**Subject:** The tooling contract established by `ai-project-template`.

**Rule:** Every phase of this blueprint must preserve: `uv` as package manager, `ty` as type checker, `just` as task runner, `pytest` as test runner, pre-commit with `no-commit-to-branch`, and strict CI (no `|| true`, no swallowed failures). Codex may not "simplify" any of these away.

**Why (picturable):** Every tool in the current contract was chosen deliberately and must be adhered to.

**Tripwire:** If you find yourself reviewing a PR that replaces `uv` with `pip`, `just` with `make`, or adds `|| true` to any CI step, reject it without negotiation. If an agent proposes "simplifying" by removing `ty` from `just check`, reject it. These tools are the contract; changes to the contract require a deliberate version bump and a corresponding invariant revision, not an in-PR argument.

### Invariant 5 — Reviewer output is structured data, not prose

**Subject:** Output from the Reviewer role.

**Rule:** The Reviewer produces a JSON document conforming to the schema in §5.4. The JSON includes `findings[]` (each with severity, type, requirement IDs, description, evidence, suggested action), `coverage`, `risk_assessment`, `summary`, and `confidence` (0–100). Any Reviewer output that fails schema validation routes the PR to `review:human` automatically.

**Why (picturable):** A free-form review comment like "looks good, maybe add a test" is unparseable. The Router cannot branch on it. You cannot measure reviewer quality over 50 PRs if each review is narrative. Structured JSON means `reviewer.confidence < 60` is a boolean the Router evaluates in microseconds. It also means reviewer *quality itself* becomes measurable — you can compute "how often does confidence ≥ 80 correlate with merges that later needed fixes?" That question doesn't exist in a prose-review world.

**Tripwire:** If the Reviewer emits prose instead of JSON (because the prompt failed or the model refused the format), the Router must route to `review:human` by default. Never attempt to LLM-extract structure from prose reviews — that's building an LLM gate in front of the LLM gate.

### Invariant 6 — Risk tier is a first-class routing input

**Subject:** How the Router decides whether a PR is eligible for agent review.

**Rule:** Every spec declares a `risk_tier` (T0/T1/T2/T3) and a `complexity` (low/medium/high). Only T0 + low-complexity specs are eligible for `review:codex` by default. The eligibility set can be expanded over time via adaptive thresholds but must always be a subset explicitly listed in the routing policy.

**Why (picturable):** Diff size is a proxy. A 1-file 10-line PR that changes an auth check is higher risk than a 5-file 200-line PR that renames a variable. Risk tier is the signal; diff size is a fallback. Declaring risk tier at the **spec** stage (not the PR stage) means the Planner — the role with the most context — sets it, not the Executor who just wants to land the change.

**Tripwire:** If you find yourself wanting to auto-merge a T1 or higher PR "because it's small", stop. The tier exists because someone with full context said this work is consequential. Expand the eligibility set with a policy-file change, not an in-PR override.

### Invariant 7 — Hooks are tripwires, not vibes (NEW in v2)

**Subject:** Lifecycle hooks installed in `.claude/settings.json` and Codex's command-rules / `[shell_environment_policy]`.

**Rule:** Every tripwire that can be enforced at edit-time MUST be implemented as a hook, not only as a prompt instruction in AGENTS.md. Specifically: PreToolUse hooks reject edits to red-zone paths and reject Edit/Write/MultiEdit on the parking branch `scratch` (exact name; rename to `spec/<slug>` or `fix/<slug>` before mutating files); UserPromptSubmit hooks reject branch names that are not `main`, not exactly `scratch`, and whose names do not start with one of `chore/`, `docs/`, `feat/`, `fix/`, `refactor/`, `spec/`, or `test/`; Stop hooks refuse to declare a session done if `just check` has not run green; SessionStart hooks inject the active spec (if any). The hook scripts live under `scripts/hooks/` and are checked into the repo.

**Why (picturable):** A prompt that says "do not edit AGENTS.md" relies on the model interpreting and obeying. A PreToolUse hook that exits non-zero on `Edit AGENTS.md` is enforced by the Claude Code runtime itself — the model never gets the chance to disobey. Hooks turn the strongest tripwires from social contracts into mechanical ones, and they fail earlier (edit-time) than CI ever can (post-push). They also work for Codex via the equivalent layer: command rules + `[shell_environment_policy]` + protected paths.

**Tripwire:** If you find yourself adding a "MUST NOT" rule to AGENTS.md that *could* be expressed as a hook, you've left a gap. Add the hook. Use AGENTS.md for the *rationale* that the hook enforces, not as the enforcement itself.

### Invariant 8 — AGENTS.md is canonical; CLAUDE.md is a symlink (NEW in v2)

**Subject:** The agent-instruction file at the repo root.

**Rule:** The repo ships exactly one canonical instruction file: `AGENTS.md`. `CLAUDE.md` is a symbolic link to `AGENTS.md` (`ln -s AGENTS.md CLAUDE.md`). No content lives only in CLAUDE.md. Tool-specific guidance — Claude-only or Codex-only — lives in subagent definitions (`.claude/agents/*.md`, `.codex/config.toml [agents.*]`), NOT in the canonical instruction file.

**Why (picturable):** Codex CLI, Cursor, Copilot, Gemini, and Windsurf read AGENTS.md natively. Claude Code reads CLAUDE.md natively but follows the symlink to AGENTS.md transparently. With the symlink pattern, the two files cannot drift. With duplicated files, they always do — within three months you'll have two slightly different versions of "always run `just check`" and the agent will be reading whichever one happens to be loaded first. One file, no drift.

**Tripwire:** If you find yourself adding content to CLAUDE.md that's not also in AGENTS.md, stop. Either you're using the wrong file (symlink should make this impossible) or the content belongs in a subagent definition, not in the canonical instructions.

---

## 3. Anti-patterns to avoid

### 3.1 Tooling regressions

1. **`|| true` in CI steps.** Swallows failures. Makes CI green when code is broken.
2. **`Makefile` as task runner.** Using `just` with justfile templates is mandatory.
3. **`pip install -e .` over `uv`.** Loses lockfile guarantees and parallel install performance.
4. **Removing `ty` from `just check`.** The type checker catches a class of bugs unit tests do not.

### 3.2 Agent-config smells

5. **Generic agent prompts** (*"You are a senior software architect. Design clean, scalable systems."*). AGENTS.md invariants must be specific, tripwire-shaped, picturable.
2. **One-sentence subagent files.** A subagent definition like *"Read the spec, implement requirements, run just check"* is less useful than the full tripwire-shaped discipline in §5.2. Short is not the same as crisp.
3. **Duplicated agent instructions across CLAUDE.md and AGENTS.md.** See Invariant 8 — symlink, don't copy.
4. **Tool-specific instructions in the canonical AGENTS.md.** Anything that begins "if you are Claude Code…" or "if you are Codex…" belongs in the subagent definition, not in AGENTS.md.

### 3.3 Ceremony that doesn't pay for itself

9. **Role handoff files generated per-spec** (e.g., `docs/orchestration/<spec>/01-planner.md`, `02-test-designer.md`, ...). The spec *is* the handoff. The reviewer JSON *is* the evidence.
2. **Orchestration YAML listing role names in order.** Roles are defined in AGENTS.md and concretized in subagent definitions. Repeating them in a YAML file is duplication with no single-source-of-truth.
3. **Codebase-map scan scripts.** Generating a markdown list of top-level directories is trivial and doesn't need to be versioned. If you want one, run `ls -d */` — don't write a script for it.
4. **Drift-hint scripts that overlap with routing rules.** If the Router already blocks PRs touching >3 files, a separate "warn when touching 3+ source directories" script is noise.
5. **Decision-coverage checks parsing D1/D2 IDs from spec text.** The PR description will cite D1 whether or not the implementation actually honors it. Revisit only if telemetry shows decisions drifting in practice.

### 3.4 Metrics/claims without measurement

14. **Speed claims without measurement** ("teams typically see 2–5x faster implementation"). This blueprint measures effects with Phase 5 telemetry; if the speed gain is real, the data will show it.

### 3.5 Parallel agents without isolation

15. **"Agent 1 → backend, Agent 2 → frontend, Agent 3 → tests, then merge"** *in a shared working tree*. Glosses over the hardest problem (file conflicts, semantic conflicts, duplicate work). Per-task git worktrees solve the file-conflict half (Phase 1 — see §5.9). The semantic-conflict half is what Phase 5 telemetry is for: do not run multiple feature agents in parallel until the Router and Reviewer are battle-tested.

### 3.6 Generous budgets that signal the wrong thing

16. **Context budgets that are never tight** (e.g., "AGENTS.md ≤ 1600 lines"). A budget that never fires teaches agents that AGENTS.md can grow unbounded. If you set a budget, set it *tight* (≤ 200 lines for AGENTS.md per 2026 cross-tool consensus, ≤ 80 lines per subagent file, ≤ 60 lines per skill body before progressive-disclosure breakdown). A budget that bites 4 times a year is doing its job.

### 3.7 Prompt-only enforcement of safety properties (NEW in v2)

17. **"Never edit AGENTS.md" as a prompt rule with no hook.** If you can express a tripwire as a hook (PreToolUse, UserPromptSubmit, Stop), you must. Prompt-only enforcement is the weakest layer.
2. **Trusting MCP outputs and web-search results as if they were spec content.** Both are user-controlled and reach the agent's context window. They are an injection surface. Run `scan_injection.py` against MCP responses and web fetches that get persisted into specs (see §5.6).

---

## 4. Phased execution plan

Each phase has a **deliverable**, an **exit criterion** (a testable "done"), and a **one-sentence why**. Do not advance to phase N+1 until phase N's exit criterion is met.

### Phase 0 — Baseline (implemented)

**Deliverable:** Cursor + Claude Code across the portfolio + `ai-project-template` with AGENTS.md invariants, CLAUDE.md pointer (to be converted to symlink in Phase 1), `.cursor/rules/`, and `.claude/settings.json`.
**Exit criterion:** `ai-project-template` shows `just check` green on every push; AGENTS.md contains tripwire-shaped invariants.

**Why:** Phase 0 is documented so later phases can reference "the Phase 0 baseline."

### Phase 1 (implemented) — Roles as native subagents + worktrees + first hooks

**Deliverable, applied to `ai-project-template`:**

1. Convert `CLAUDE.md` to a symlink targeting `AGENTS.md`. Move any Claude-only content into `.claude/agents/planner.md`. (Invariant 8.)
2. Extend `AGENTS.md` with a new **Agent Roles** section that names Planner (Claude Code subagent), Executor (Codex subagent), and Reviewer. Each role gets a responsibility boundary and a pointer to its definition file.
3. Create `.claude/agents/planner.md` — Planner subagent (full template in §5.10): `permissionMode: plan`, `tools: [Read, Grep, Glob]`, `model: opus`. Read-only by construction.
4. Create `.codex/config.toml` with `[agents.executor]`: `sandbox_mode = "workspace-write"`, `approval_policy = "on-request"`, `developer_instructions` referencing the Executor discipline (see §5.2).
5. Add `.claude/settings.json` hooks (Phase-1 minimum set, full template in §5.8):
   - **PreToolUse on Edit|Write|MultiEdit** — block changes to red-zone paths (AGENTS.md, justfile, .pre-commit-config.yaml, etc.).
   - **UserPromptSubmit** — allow `main`, parking branch `scratch`, and branches whose names start with `chore/`, `docs/`, `feat/`, `fix/`, `refactor/`, `spec/`, or `test/`; block prompts on other branches.
   - **PreToolUse (second hook, same matcher)** — block Edit/Write/MultiEdit on `scratch` until renamed (`check_no_edits_on_scratch.py`).
6. Add `scripts/hooks/check_red_zone.py`, `scripts/hooks/check_branch_name.py`, and `scripts/hooks/check_no_edits_on_scratch.py`.
7. Add red-zone file list to AGENTS.md (canonical set from §5.5).
8. Add one new AGENTS.md invariant: *"The Executor never modifies files enumerated as red-zone without explicit human instruction."* (already enforced by hook in step 5.)
9. Document the worktree workflow: every non-trivial spec is implemented in `claude -w spec-<slug>` (Claude) or `codex --cd ../<repo>-<slug>` (Codex). One spec, one worktree, one branch.

**Exit criterion:** Take a small feature from a test project, ask the Planner subagent (Plan Mode) to write a draft spec (no lint yet), spawn a worktree, ask the Executor subagent to implement against that spec, and the resulting PR passes `just check`. The PR description links the spec. The PreToolUse red-zone hook has fired at least once during development (test it deliberately by trying to edit AGENTS.md — it must reject). You did not touch the code yourself.

**Why (picturable):** Today, asking an AI to "add a test" means one agent doing planning and execution in one shot, with no artifact documenting what it was supposed to do. Phase 1 separates *deciding what* from *writing the code*, encodes that split into native subagent definitions (so it's enforced by the runtime, not by hope), and isolates each task in its own worktree so parallel work cannot collide. The hooks layer makes the single most important tripwires mechanical rather than rhetorical. That separation + isolation + enforcement is what makes every later phase possible.

### Phase 2 (implemented) — Spec-driven flow + spec-writing skill

**Deliverable:**

1. Add `docs/specs/README.md` documenting the spec format.
2. Add `docs/specs/_template.md` — a fill-in-the-blanks skeleton with all required sections (see §5.1).
3. Add `scripts/lint_spec.py` — fails if a spec is missing required sections, has un-mapped requirements (no T→R mapping), or has un-validated requirements.
4. Add `just lint-spec <path>` recipe.
5. Extend `just check` to lint any spec modified in the current branch (`git diff --name-only` filtered to `docs/specs/`).
6. Add prompt-injection scan at `scripts/scan_injection.py` — string-match for known injection patterns in spec files AND in any persisted output from web search or MCP tools (see §5.6). Runs as part of `just check`.
7. Update Planner subagent definition to state: *"Specs for work >30 minutes of effort must lint clean before the Executor begins."*
8. Add `.claude/skills/write-spec/SKILL.md` — the spec-writing playbook as an Agent Skill, loaded via progressive disclosure when the Planner needs to draft a new spec (see §5.11).
9. Add a Stop hook that refuses session completion if the active branch has uncommitted spec changes that fail `lint_spec.py`.
10. Add to `post-fork-checklist.md`: step 9 — *"Delete example specs in `docs/specs/` or keep as references."*

**Exit criterion:** Three specs have been written and executed end-to-end. Each passes `lint_spec.py` and the injection scan. Each has a corresponding merged PR. You can read any spec and understand the feature without opening the code. The `write-spec` skill has been invoked and loaded at least once.

**Why (picturable):** Specs-as-files turn "what was this Codex session about?" into a link you can click. Enforcing structure via lint turns the spec from a vibe into an artifact with guarantees — every spec has a Test Plan, every requirement maps to a test, every requirement has a validation contract. The injection scan recognizes that specs are an attack surface: they are user input that flows to an LLM, so they deserve input validation. The skill lets the Planner load detailed spec-writing guidance only when needed, keeping AGENTS.md tight.

### Phase 3 (implemented) — Add the Reviewer subagent (structured-JSON output, read-only sandbox)

**Deliverable:**

1. Add to AGENTS.md: **Reviewer** role with adversarial responsibilities.
2. Add `[agents.reviewer]` to `.codex/config.toml` with `sandbox_mode = "read-only"`, `model_reasoning_effort = "high"`, `developer_instructions` containing the prompt template that commands schema-valid JSON output fenced by `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` markers (see §5.10).
3. Add `.reviewer-schema.json` — JSON Schema 2020-12 (see §5.4 for full schema).
4. Add `scripts/validate_reviewer.py` — extracts the fenced JSON from a PR body and validates it against the schema. Exit 0 = valid, Exit 1 = invalid (with specific error).
5. Add `just validate-reviewer <pr-body-file>` recipe.
6. Add Invariant 5 to AGENTS.md (already drafted above).
7. **Human still reviews every PR at this phase.** The Codex Reviewer's JSON is evidence, not a merge gate.

**Exit criterion:** On 10 consecutive PRs, the Codex Reviewer's JSON has been evaluated by human with scoring: *"useful / noise / missed a real issue I caught."* At least 6 of 10 PRs should produce at least one useful finding. If not, the prompt needs revision before Phase 4. In parallel, 10/10 reviewer outputs must pass schema validation — if any fail, fix the prompt template before proceeding. Confirm via `codex` session logs that the Reviewer agent ran with `sandbox_mode = read-only` (the sandbox is the guarantee, not the prompt).

**Why (picturable):** We have added the reviewer but deliberately keep the human as the real gate. The purpose is to *calibrate* the Codex Reviewer before trusting it. The structured JSON format is what makes Phase 4's automation possible. The read-only sandbox means even a misprompted Reviewer cannot accidentally edit code — the worst it can do is emit a bad finding, which fails schema validation and routes to human anyway.

### Phase 4 (roadmap) — The Router (deterministic PR labeling with three outcomes)

**Deliverable:**

1. `.routing-policy.json` — declarative thresholds (see §5.3).
2. `scripts/route_pr.py` — takes a PR context JSON, returns one of `review:codex` / `review:human` / `blocked` plus human-readable reasons.
3. `.github/workflows/route-pr.yml` — runs on every PR, builds the context, calls the router, applies a label, writes a comment explaining the routing decision (illustrative skeleton in §5.7).
4. Branch protection on `main`: PRs labeled `review:human` or `blocked` cannot auto-merge. PRs labeled `review:codex` can auto-merge when CI is green AND reviewer JSON validates AND no critical findings.
5. Update AGENTS.md with Invariants 2 and 6 (already drafted).

**Exit criterion:** All three routing outcomes observed in real usage — at least one `review:codex` PR auto-merged, at least one `review:human` PR correctly blocked from auto-merge because it touched AGENTS.md, and at least one `blocked` PR held because of a critical reviewer finding. Every routing decision is accompanied by a PR comment explaining *why* it was routed that way.

**Why (picturable):** Phase 4 is the moment the development environment becomes **asynchronous**. Before Phase 4, Codex opens a PR and waits for human. After Phase 4, Codex opens a PR, the Router labels it, and if the label is `review:codex` the system continues. Human is no longer in the loop for routine work. Human is, importantly, still in the loop for everything the Router decided human should be in the loop for.

### Phase 5 (roadmap) — Observability (events.jsonl + optional OTel), MCP integration, adaptive thresholds

**Deliverable:**

1. Telemetry file at `docs/telemetry/events.jsonl` — one JSON line per PR: spec_id, risk_tier, complexity, changed_files_count, diff_lines, reviewer_validation_status, reviewer_confidence, findings_count_by_severity, route_decision, ci_outcome, merge_outcome. (Kept under `docs/` — visible, not hidden per Invariant 3.)
2. **OPTIONAL:** OTel exporter for Codex via `[otel] exporter = { otlp-http = { endpoint = "..." } }` in `.codex/config.toml`. Useful when you want tool-call traces and per-PR cost beyond what `events.jsonl` captures (Open Question #2 in §6). `events.jsonl` remains the routing-decision source of truth.
3. `scripts/telemetry_dashboard.py` — reads the events file, writes a Markdown dashboard at `docs/telemetry/dashboard.md` summarizing route distribution, risk distribution, average confidence, and the last 20 PRs.
4. `scripts/adapt_thresholds.py` — bounded mechanical policy updates (see §5.13). Always bounded, always logged, never unbounded.
5. **MCP integration (NEW in v2):** add `[mcp_servers.github]` to the Reviewer agent's config so Reviewer findings can cite the linked issue, prior similar diffs, or runtime errors (see §5.12). Add the same MCP server to the Planner subagent's `mcpServers` field for spec-writing context.
6. Monthly ritual: read the dashboard, run `adapt_thresholds.py`, review the three worst-performing specs/PRs, update Planner/Executor/Reviewer prompts AND the relevant skills if patterns emerge.
7. Post-mortem template at `docs/specs/_postmortem.md` for production issues — each post-mortem produces one invariant addition or one prompt update. Also expressed as a `.claude/skills/postmortem/SKILL.md` skill.

**Exit criterion:** Run at least one adapt-thresholds cycle based on real telemetry (policy file changes committed). At least one AGENTS.md invariant was added or revised as a direct result of a post-mortem or dashboard pattern. At least one Reviewer finding cited MCP-sourced context (e.g., a Sentry error or linked issue).

**Why (picturable):** Without Phase 5, the system cannot improve. Prompts rot because the world changes (new dependency versions, new patterns, new edge cases). A static prompt library is a garden that nobody weeds. Telemetry + bounded adaptive thresholds turns prompt and policy quality into a **measurable engineering metric**, not a vibe. MCP brings in the context that lives outside the repo — the issue tracker, the error monitor, the design doc — so the Reviewer can cite evidence beyond the diff itself. The bounds on adaptation (floors and ceilings in the policy) are what make this safe to run on a schedule rather than by hand.

### Phase 6 — Endgame: semi-autonomous factory

**Deliverable:**

1. All repos in scope running the full system (starting with `ai-project-template`, then propagating to any new project forked from it).
2. A scheduled workflow at `.github/workflows/scheduled-executor.yml` that picks up any spec in `docs/specs/` without a corresponding PR and dispatches it to Codex for execution (contingent on a usable async Codex API or equivalent — see Open Question #1 in §6).
3. Portfolio-level status documentation updated to reflect the system's operational state.

**Exit criterion:** A submitted spec is executed (Executor subagent in its own worktree), reviewed (Reviewer subagent, structured JSON), routed (policy), CI-validated, and auto-merged — or blocked with a clear reason. Upon completion, read the dashboard, and spend time on specs rather than on code.

**Why (picturable):** Phase 6 is the semi-autonomous endgame done right with five verified phases, each with a tripwire, each tested on `ai-project-template` before propagating.

---

## 5. Design details

### 5.1 Spec structure (enforced by `lint_spec.py`)

Required sections — a spec that omits any of these fails the lint:

```markdown
# <Feature Title>

## Metadata
- spec_id: SPEC-<YYYYMMDD>-<slug>
- owner: <name>
- status: drafted | in-progress | complete | archived
- complexity: low | medium | high
- risk_tier: T0 | T1 | T2 | T3
- repo: <repo-name>

## Context
Why this work exists now.

## Assumptions
- A1: <what we're assuming>

## Decisions
- D1: <architectural decision with rationale>

## Problem Statement
Exact failure, missing capability, or constraint.

## Requirements (STRICT)
- [ ] R1: <specific, testable requirement>

## Non-Goals
- [ ] NG1: <explicitly out of scope>

## Interfaces
Affected entrypoints, APIs, CLI commands, models, schemas, UI surfaces, or files.

## Invariants to Preserve
- [ ] INV1: <invariant that must remain true after this change>

## Red-Zone Assessment
- auth: yes|no
- billing: yes|no
- dependencies: yes|no
- CI: yes|no
- migrations: yes|no
- secrets: yes|no
- infra: yes|no
- invariant-protected files: yes|no

## Test Plan
- [ ] T1 -> covers R1

## Validation Contract
- R1 -> `just check` (or specific command/assertion)

## Edge Cases
- EC1: <boundary condition>

## Security / Prompt-Injection Review
- source: <where does any LLM-input data come from? include MCP tools and web search if used>
- risk: low|medium|high
- mitigation: <if non-low, how is it mitigated?>

## Observability
Logs, metrics, assertions, traces, or telemetry updates needed.

## Rollback / Recovery
How to revert, disable, or mitigate if it fails.

## Implementation Slices
1. Slice 1: <smallest useful commit>

## Done When
- [ ] All requirement IDs satisfied
- [ ] Decision IDs preserved or explicitly deferred
- [ ] Tests mapped and passing
- [ ] Validation Contract satisfied
- [ ] `just check` green
- [ ] CI green
- [ ] No invariant violations
```

The linter checks:

1. All required section headings are present.
2. Every `R*` requirement has a matching `T* -> covers R*` entry in Test Plan.
3. Every `R*` requirement has a matching `R* ->` entry in Validation Contract.
4. Metadata section includes valid `risk_tier` and `complexity` values.

### 5.2 The Codex Executor discipline (in `.codex/config.toml`)

```toml
[agents.executor]
description = "Implements one spec per branch in a workspace-write sandbox."
model_reasoning_effort = "medium"
sandbox_mode = "workspace-write"
approval_policy = "on-request"
developer_instructions = """
You are the Executor role in this repo's three-agent system. The Planner (Claude Code) has written a spec at `docs/specs/<slug>.md` that has passed `just lint-spec`. Your job is to implement it — nothing more, nothing less.

Hard rules (tripwires):
1. Read the entire spec before writing any code. If the spec is ambiguous, STOP and ask.
2. Never modify files enumerated as red-zone in AGENTS.md without explicit instruction. (The PreToolUse hook should reject this anyway; if you find a way around the hook, that's a bug to report, not an opening to use.)
3. Never add features the spec did not request. If you find yourself writing helpful extras, STOP.
4. Run `just check` before declaring the task complete. If it fails, you are not done.
5. The PR description MUST include: (a) spec filepath link, (b) reviewer JSON block fenced by `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` (may be empty at Executor stage; Reviewer fills it).
6. Traceable PRs (Invariant 1): branch MUST start with `spec/<slug>` or `fix/<slug>`. UserPromptSubmit also allows `main`, `scratch`, and branches starting with `chore/`, `docs/`, `feat/`, `fix/`, `refactor/`, or `test/` — use `spec/` or `fix/` before opening a PR that must satisfy Invariant 1.

Discipline:
- Minimal diffs. No drive-by refactors.
- One logical concern per commit.
- Type hints on all new functions.
- Tests for happy path AND at least one failure path.
- Tests must be mapped to requirement IDs — the test docstring cites `R1, R2`.

What to do when stuck:
Do NOT invent. If the spec does not cover a case, add a `# TODO(spec):` comment and surface the gap in the PR description under a "Spec gaps" heading. The Planner will either amend the spec or the Router will block the PR.
"""
```

### 5.3 The routing policy (`.routing-policy.json` + `scripts/route_pr.py`)

Policy file:

```json
{
  "version": 1,
  "max_changed_files": 3,
  "max_diff_lines": 150,
  "min_reviewer_confidence": 60,
  "auto_review_allowed_risk_tiers": ["T0"],
  "auto_review_allowed_complexity": ["low"],
  "adaptive": {
    "enabled": true,
    "floor_max_changed_files": 1,
    "floor_max_diff_lines": 50,
    "ceiling_min_reviewer_confidence": 85
  }
}
```

Router (illustrative — final version will have tests):

```python
# scripts/route_pr.py
from __future__ import annotations
import json, sys
from pathlib import Path

RED_ZONE_PATHS = {
    "AGENTS.md", "CLAUDE.md", ".claude/settings.json", ".codex/config.toml",
    "pyproject.toml", "uv.lock", ".pre-commit-config.yaml", "justfile",
    ".routing-policy.json", ".reviewer-schema.json",
}
RED_ZONE_PREFIXES = (
    ".cursor/rules/", ".claude/agents/", ".claude/skills/",
    ".github/workflows/", "scripts/hooks/",
    "auth/", "billing/", "migrations/", "infra/",
)

def touches_red_zone(files: list[str]) -> bool:
    return any(
        f in RED_ZONE_PATHS or f.startswith(RED_ZONE_PREFIXES)
        for f in files
    )

def route(pr: dict, policy: dict) -> tuple[str, list[str]]:
    """Return ('review:codex'|'review:human'|'blocked', reasons)."""
    reviewer = pr.get("reviewer", {})
    spec = pr.get("spec", {})

    # Hard gates: invalid artifacts → human
    if pr.get("reviewer_validation", {}).get("status") != "valid":
        return "review:human", ["Reviewer JSON did not validate against schema."]
    if pr.get("spec_validation", {}).get("status") != "valid":
        return "review:human", ["Spec did not pass lint."]

    # Red zones
    if touches_red_zone(pr.get("changed_files", [])):
        return "review:human", ["PR touches red-zone or invariant-protected files."]

    # Critical finding → blocked (not human review — blocked)
    if any(f.get("severity") == "critical" for f in reviewer.get("findings", [])):
        return "blocked", ["Reviewer reported at least one critical finding."]

    # Risk and complexity eligibility
    if spec.get("risk_tier") not in set(policy["auto_review_allowed_risk_tiers"]):
        return "review:human", [f"Risk tier {spec.get('risk_tier')} not auto-review eligible."]
    if spec.get("complexity") not in set(policy["auto_review_allowed_complexity"]):
        return "review:human", [f"Complexity {spec.get('complexity')} not auto-review eligible."]

    # Size gates
    if len(pr.get("changed_files", [])) > policy["max_changed_files"]:
        return "review:human", [f"Changed files > {policy['max_changed_files']}."]
    if int(pr.get("diff_lines", 0)) > policy["max_diff_lines"]:
        return "review:human", [f"Diff lines > {policy['max_diff_lines']}."]

    # Confidence gate
    if int(reviewer.get("confidence", 0)) < policy["min_reviewer_confidence"]:
        return "review:human", [f"Reviewer confidence < {policy['min_reviewer_confidence']}."]

    # Coverage gate
    coverage = reviewer.get("coverage", {})
    if coverage.get("requirements_covered", 0) < coverage.get("requirements_total", 0):
        return "review:human", ["Reviewer reports incomplete requirement coverage."]

    return "review:codex", ["All policy thresholds satisfied."]

def main():
    pr = json.loads(Path(sys.argv[1]).read_text())
    policy = json.loads(Path(".routing-policy.json").read_text())
    route_label, reasons = route(pr, policy)
    print(json.dumps({"route": route_label, "reasons": reasons}, indent=2))

if __name__ == "__main__":
    raise SystemExit(main())
```

**Calibration warning:** The thresholds are version 1. Expect to revise after 20 real PRs. Every routing decision writes a telemetry event so you can audit false positives and false negatives.

### 5.4 Reviewer JSON Schema (`.reviewer-schema.json`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Reviewer Output",
  "type": "object",
  "required": ["summary", "findings", "coverage", "risk_assessment", "confidence"],
  "properties": {
    "summary": { "type": "string" },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type", "severity", "requirement_ids",
                     "description", "evidence", "suggested_action"],
        "properties": {
          "id": { "type": "string" },
          "type": {
            "type": "string",
            "enum": [
              "missing_requirement", "missing_decision", "extra_scope",
              "invariant_risk", "weak_test", "hidden_side_effect",
              "unclear_behavior", "observability_gap", "rollback_gap",
              "validation_gap", "prompt_injection_risk"
            ]
          },
          "severity": { "type": "string", "enum": ["critical", "warning", "nit"] },
          "requirement_ids": { "type": "array", "items": { "type": "string" } },
          "description": { "type": "string" },
          "evidence": { "type": "string" },
          "suggested_action": { "type": "string" }
        }
      }
    },
    "coverage": {
      "type": "object",
      "required": ["requirements_total", "requirements_covered",
                   "tests_expected", "tests_present"],
      "properties": {
        "requirements_total": { "type": "integer", "minimum": 0 },
        "requirements_covered": { "type": "integer", "minimum": 0 },
        "tests_expected": { "type": "integer", "minimum": 0 },
        "tests_present": { "type": "integer", "minimum": 0 }
      }
    },
    "risk_assessment": {
      "type": "object",
      "required": ["scope_fit", "invariant_risk", "production_risk"],
      "properties": {
        "scope_fit": { "type": "string", "enum": ["correct", "over_scope", "under_scope"] },
        "invariant_risk": { "type": "string", "enum": ["low", "medium", "high"] },
        "production_risk": { "type": "string", "enum": ["low", "medium", "high"] }
      }
    },
    "confidence": { "type": "integer", "minimum": 0, "maximum": 100 }
  }
}
```

**Asymmetric strictness.** The schema deliberately omits
`additionalProperties: false` at the top level and on every nested
object. The contract is "reject malformed output, tolerate unknown
fields." A future Reviewer iteration may want to emit an extra hint
field (e.g., `cited_issue_ids`, `mcp_provenance`) before the schema
is updated; a strict schema would reject that PR and the Reviewer's
extra signal would be lost. Lesson from reviewer calibration: schema
strictness is a one-way door — easy to tighten later, painful to
loosen once tools downstream depend on a strict contract. Bias toward
forward-compatibility, validate the required fields exhaustively.

The schema also omits `$id`. The schema is template-local and is
expected to ship with each fork; a hard-coded `$id` URL would be a
copy-paste hazard for downstream repos.

### 5.5 Red-zone file list (canonical)

Files/paths that trigger `review:human` regardless of other signals AND are blocked at edit-time by the PreToolUse hook (see §5.8):

```text
AGENTS.md
CLAUDE.md (symlink to AGENTS.md)
.claude/settings.json
.claude/agents/**
.claude/skills/**
.codex/config.toml
.cursor/rules/**
.github/workflows/**
scripts/hooks/**
pyproject.toml           (dependency sections)
uv.lock
.pre-commit-config.yaml
justfile
.routing-policy.json
.reviewer-schema.json
auth/**
billing/**
migrations/**
infra/**
```

Rationale: the first block protects the agent-governance surface itself (including the new subagents, skills, hooks, and Codex config layers added in v2). The second block protects production-critical code paths that should never be silently modified by an agent.

### 5.6 Prompt-injection scan (`scripts/scan_injection.py`)

Extended in v2 to cover MCP-tool outputs and persisted web-search results, not only spec files.

```python
# scripts/scan_injection.py
import sys
from pathlib import Path

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore the above",
    "system prompt",
    "developer message",
    "you are now",
    "bypass",
    "override instructions",
    "<system>",
    "###INSTRUCTION",
    "### instructions:",
    # MCP / web-source patterns added in v2:
    "tool_call_override",
    "skip approval",
    "disregard safety",
]

# Scan widened to MCP responses and web-source artifacts persisted into the repo.
SCAN_EXTENSIONS = {".md", ".mdc", ".txt", ".json"}
SCAN_DIRS = ["docs/specs", ".cursor/rules", ".claude/agents",
             ".claude/skills", "docs/external", "AGENTS.md"]

def scan_file(p: Path) -> list[str]:
    text = p.read_text(encoding="utf-8", errors="ignore").lower()
    return [pattern for pattern in INJECTION_PATTERNS if pattern in text]

def main():
    paths = sys.argv[1:] or SCAN_DIRS
    hits = []
    for arg in paths:
        p = Path(arg)
        if p.is_file():
            hits += [f"{p}: {h}" for h in scan_file(p)]
        elif p.exists():
            for child in p.rglob("*"):
                if child.is_file() and child.suffix in SCAN_EXTENSIONS:
                    hits += [f"{child}: {h}" for h in scan_file(child)]
    for h in hits:
        print(f"ERROR: {h}")
    return 1 if hits else 0

if __name__ == "__main__":
    raise SystemExit(main())
```

This is version 2. It catches obvious attacks across a wider surface than v1. A future version (Phase 5+ territory) could use a small classifier model. Do not over-engineer this before you see a real attack in the wild.

### 5.7 Routing workflow (`.github/workflows/route-pr.yml`) — illustrative skeleton

```yaml
name: route-pr
on:
  pull_request:
    types: [opened, synchronize, edited]

permissions:
  pull-requests: write
  contents: read

jobs:
  route:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up uv + Python
        uses: astral-sh/setup-uv@v3

      - name: Build PR context
        id: ctx
        run: |
          # Construct pr.json: changed_files, diff_lines, spec metadata,
          # reviewer JSON extracted from PR body, validation results.
          uv run scripts/build_pr_context.py \
            --pr "${{ github.event.pull_request.number }}" \
            --out pr.json

      - name: Validate spec
        run: uv run scripts/lint_spec.py --pr-context pr.json

      - name: Validate reviewer JSON
        run: uv run scripts/validate_reviewer.py --pr-context pr.json

      - name: Route
        id: route
        run: uv run scripts/route_pr.py pr.json > route.json

      - name: Apply label + comment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          LABEL=$(jq -r '.route' route.json)
          REASONS=$(jq -r '.reasons | join("\n- ")' route.json)
          gh pr edit "${{ github.event.pull_request.number }}" --add-label "$LABEL"
          gh pr comment "${{ github.event.pull_request.number }}" \
            --body "Router decision: \`$LABEL\`\n\nReasons:\n- $REASONS"

      - name: Append telemetry event
        run: uv run scripts/append_event.py --pr pr.json --route route.json
```

The accompanying branch protection rule (configured in repo settings, not in YAML) requires the `route-pr` check to succeed and the label to be `review:codex` for auto-merge.

### 5.8 Hooks (`.claude/settings.json` + `scripts/hooks/`)

The hooks configuration in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command", "command": "uv run scripts/hooks/check_red_zone.py" },
          { "type": "command", "command": "uv run scripts/hooks/check_no_edits_on_scratch.py" }
        ]
      }
    ],
    "UserPromptSubmit": [
      { "type": "command", "command": "uv run scripts/hooks/check_branch_name.py" }
    ],
    "Stop": [
      { "type": "command", "command": "uv run scripts/hooks/require_just_check.py" }
    ],
    "SessionStart": [
      { "type": "command", "command": "uv run scripts/hooks/inject_active_spec.py" }
    ]
  }
}
```

Example: `scripts/hooks/check_red_zone.py` (illustrative):

```python
# scripts/hooks/check_red_zone.py
"""PreToolUse hook: reject Edit/Write/MultiEdit on red-zone paths."""
from __future__ import annotations
import json
import sys
from pathlib import Path

RED_ZONE_PATHS = {
    "AGENTS.md", "CLAUDE.md", ".claude/settings.json", ".codex/config.toml",
    "pyproject.toml", "uv.lock", ".pre-commit-config.yaml", "justfile",
    ".routing-policy.json", ".reviewer-schema.json",
}
RED_ZONE_PREFIXES = (
    ".cursor/rules/", ".claude/agents/", ".claude/skills/",
    ".github/workflows/", "scripts/hooks/",
    "auth/", "billing/", "migrations/", "infra/",
)

def main() -> int:
    payload = json.load(sys.stdin)
    target = payload.get("tool_input", {}).get("file_path", "")
    rel = str(Path(target).resolve().relative_to(Path.cwd().resolve())) \
        if target else ""
    if rel in RED_ZONE_PATHS or any(rel.startswith(p) for p in RED_ZONE_PREFIXES):
        print(f"BLOCKED: {rel} is red-zone. Edit requires explicit human "
              f"instruction outside of agent context.", file=sys.stderr)
        return 2  # Claude Code: exit 2 blocks the tool call and surfaces stderr.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

**Codex equivalent layer:** Codex enforces analogous protections via `[shell_environment_policy]` (controls subprocess env), command rules (`pattern` + `decision` to forbid command prefixes), and the `sandbox_mode` itself (writable_roots + read-only paths). The Reviewer subagent's `read-only` sandbox is itself a hook-equivalent: it makes "Reviewer cannot edit code" a runtime guarantee.

Hooks block Claude Code: the model cannot move to the next step until the hook completes (default 10-minute timeout, configurable per hook). Exit code 2 specifically blocks the tool call and feeds stderr back to the model — the model sees the rejection and can react, but cannot bypass it.

### 5.9 Worktrees as the Phase 1 isolation primitive

Every non-trivial spec is implemented in its own git worktree. This is non-negotiable from Phase 1 onward.

```bash
# Claude Code (native flag, Claude Code v2.1.50+)
claude -w spec-add-cache-warmup
# Creates .claude/worktrees/spec-add-cache-warmup/
# on a fresh branch worktree-spec-add-cache-warmup.

# Codex (use git worktree directly, then --cd into it)
git worktree add ../template-spec-add-cache-warmup -b spec/add-cache-warmup
codex --cd ../template-spec-add-cache-warmup
```

Subagents that write code declare `isolation: "worktree"` in their frontmatter so they spawn into their own sandbox automatically. Read-only subagents (Planner, Reviewer) do not need worktrees — they share the parent checkout.

Cleanup: a weekly `git worktree prune` plus a SubagentStop hook that warns about idle worktrees keeps the directory list manageable. Empirical ceiling: 4–8 concurrent worktrees per developer before review becomes the bottleneck rather than implementation.

**What worktrees do not solve:** semantic conflicts across parallel feature branches (two specs that both modify the same data model in incompatible ways). That remains a human-judgment problem and is the reason multi-feature parallelism is deferred until Phase 5 telemetry exists. Single-task worktrees are still independently valuable from Phase 1 (fast bug-fix-during-feature-work, no `git stash` juggling).

### 5.10 Subagent definitions (canonical templates)

**Planner (`.claude/agents/planner.md`):**

```md
---
name: planner
description: USE PROACTIVELY for any request that mentions drafting, writing, or revising a spec under docs/specs/. Invoke this subagent BEFORE loading the write-spec skill — the skill is loaded by this subagent, not by the main agent. Read-only by construction (Plan Mode); produces plans that the human commits.
tools: [Read, Grep, Glob]
disallowedTools: [Edit, Write, MultiEdit, Bash]
permissionMode: plan
model: opus
memory: project
---

You are the Planner role in this repo's three-agent system.

Your job is to produce a spec at `docs/specs/<slug>.md` that conforms to the structure in §5.1 of `docs/blueprint.md`. You operate in Plan Mode — you cannot edit files. You produce a plan that the human approves; the human commits the spec.

**Scratch / branch before writes:** Tell the human first: if `HEAD` is `scratch`, run `git branch -m scratch spec/<slug>` (or `fix/<slug>`) *before* any Edit/Write to `docs/specs/` — `check_no_edits_on_scratch.py` blocks file mutations on `scratch`.

Hard rules:
1. The spec MUST pass `just lint-spec docs/specs/<slug>.md` before the Executor begins. If your draft would fail the lint, fix it in the plan.
2. You MUST set `risk_tier` and `complexity`. T0 + low is the only combination eligible for `review:codex` by default. Setting T0/low when the work is consequential is a tripwire — when in doubt, escalate.
3. Every requirement R* MUST have a matching test T* and a Validation Contract entry.
4. If the spec sources data from MCP tools or web search, the Security / Prompt-Injection Review section MUST identify the source and the risk level.

When does work need a spec? Use these consequence-based criteria — *not* a wall-clock time threshold:

- The change touches a red-zone file (per AGENTS.md / §5.5).
- The change touches multiple unrelated files (a file plus its co-located tests does not count as multi-file).
- The change alters a public interface or behavior contract.
- A future reader will need context the PR diff cannot provide on its own.

If none of the above is true, an ad-hoc prompt is fine.

Use the `write-spec` skill (`.claude/skills/write-spec/SKILL.md`) for the canonical workflow.
```

**Routing-primacy lesson.** Claude Code routes between subagents and skills based on `description:` text matching the user's prompt. In the Phase 2 demo, the `write-spec` skill's description matched the user's "draft a spec" prompt more literally than the Planner subagent's, so the skill loaded into the *main* agent (which has Edit/Write tools) instead of the constrained Planner subagent. The mitigation is belt-and-suspenders:

- The Planner subagent description claims primacy explicitly ("USE PROACTIVELY ... invoke this BEFORE loading the write-spec skill").
- The skill description scopes itself as Planner-loaded (see §5.11), not as a generally-callable spec-drafting playbook.

This is a fragility worth knowing: any future skill whose description matches a user prompt more literally than its parent subagent will exhibit the same routing race. If you add a new skill scoped to a subagent, sharpen both descriptions in the same PR.

**Codex Executor + Reviewer (`.codex/config.toml`):**

````toml
# Phase 1: Executor
[agents.executor]
description = "Implements one spec per branch in a workspace-write sandbox."
model_reasoning_effort = "medium"
sandbox_mode = "workspace-write"
approval_policy = "on-request"
developer_instructions = """
# (full Executor discipline from §5.2)
"""

# Phase 3: Reviewer
[agents.reviewer]
description = "Adversarial PR reviewer. Read-only sandbox. Outputs schema-valid JSON only."
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = """
You are the Reviewer role. Read the PR diff, the spec it cites, and (if available) the MCP-sourced context (linked issue, runtime errors). Output a JSON document validating against `.reviewer-schema.json`. Wrap it in a fenced block:

<!-- REVIEWER_JSON -->
```json
{ ... }
```
<!-- /REVIEWER_JSON -->

Default bias: produce findings. False positives are preferred to false negatives. If a requirement has no corresponding implementation, emit a `missing_requirement` finding with severity `critical`. If the diff touches code the spec did not authorize, emit an `extra_scope` finding.

NEVER emit prose instead of JSON. If you cannot produce schema-valid JSON, emit `{"summary": "Reviewer error: <reason>", "findings": [], "coverage": {"requirements_total": 0, "requirements_covered": 0, "tests_expected": 0, "tests_present": 0}, "risk_assessment": {"scope_fit": "correct", "invariant_risk": "high", "production_risk": "high"}, "confidence": 0}` — this guarantees `review:human` routing.
"""

# Phase 5: MCP integration (Reviewer reaches GitHub)

[agents.reviewer.mcp_servers.github]
url = "<http://localhost:7301/mcp>"
startup_timeout_sec = 20

````

### 5.11 The skills layer (`.claude/skills/`)

Skills (SKILL.md) are progressive-disclosure playbooks. Frontmatter (`name`, `description`) is loaded eagerly; the body is loaded only when the agent decides the skill applies. This is how we keep AGENTS.md tight without losing detail.

Phase 2 skill: `.claude/skills/write-spec/SKILL.md`

```md
---
name: write-spec
description: Loaded by the Planner subagent when drafting a new spec under docs/specs/ or when revising one. NOT a generally-callable spec-drafting playbook — invoke the Planner subagent instead, which loads this skill. Walks through the §5.1 structure step by step and verifies the result will pass lint_spec.py.
---

# Writing a spec

Step 1: Confirm the work needs a spec. Use these consequence-based criteria — *not* a time threshold:
  - touches a red-zone file (per AGENTS.md), OR
  - touches multiple unrelated files (co-located tests don't count), OR
  - alters a public interface or behavior contract, OR
  - a future reader will need context the PR diff cannot provide.
  If none apply, an ad-hoc prompt is fine — do not draft a spec.
Step 2: Pick a slug. Filename is `docs/specs/<slug>.md` (the `.md` extension is mandatory; `lint_spec.py` filters on it).
Step 3: Fill the Metadata block. Choose risk_tier honestly — T0 is "could not break anything important if wrong."
Step 4: Decompose: Context → Problem Statement → Requirements (with stable IDs).
Step 5: For every R*, write a T* in Test Plan and an entry in Validation Contract.
Step 6: Red-Zone Assessment — if any "yes", you cannot ship as risk_tier T0.
Step 7: Run `just lint-spec docs/specs/<slug>.md` mentally — would it pass?
Step 8: Hand to human for commit (you cannot edit files in Plan Mode).
```

Phase 5 skills: `.claude/skills/postmortem/SKILL.md` (one-postmortem-one-invariant discipline), `.claude/skills/calibrate-reviewer/SKILL.md` (the 6-of-10 evaluation procedure from Phase 3).

Skills also work in Codex via `[[skills.config]]` blocks pointing to the same SKILL.md files — the format is portable across tools (Agent Skills open standard).

### 5.12 MCP servers (`.codex/config.toml` + `.claude/agents/*.md`)

Phase 5 enhancement. Adds external context to the Reviewer (and optionally the Planner) without inflating the diff itself.

```toml
# .codex/config.toml — Reviewer reaches GitHub PR data, Sentry runtime errors
[agents.reviewer.mcp_servers.github]
url = "http://localhost:7301/mcp"

[agents.reviewer.mcp_servers.sentry]
url = "http://localhost:7401/mcp"
```

```md
# .claude/agents/planner.md frontmatter excerpt
mcpServers:
  - github
  - linear
```

What MCP buys: the Reviewer can cite "this fix to `auth.py` also resolves Sentry issue PROJ-1234" — evidence that lives outside the diff. The Planner can pull issue context directly into the spec rather than the human pasting it.

What MCP doesn't change: the sandbox boundary. A Reviewer with MCP access still runs in `sandbox_mode = "read-only"` — MCP only widens *read* surface, not write surface. Web-search results and MCP tool outputs are run through `scan_injection.py` before being persisted to specs (Anti-pattern #18).

### 5.13 Adaptive thresholds (`scripts/adapt_thresholds.py`)

Bounded, conservative mechanical updates — never unbounded.

```python
# scripts/adapt_thresholds.py
from __future__ import annotations
import json, sys
from pathlib import Path

def adapt(events: list[dict], policy: dict) -> tuple[dict, list[str]]:
    new = json.loads(json.dumps(policy))  # deep copy
    notes = []
    adaptive = new.get("adaptive", {})

    blocked_count = sum(1 for e in events if e.get("route") == "blocked")
    invalid_reviewer_count = sum(
        1 for e in events
        if e.get("reviewer_validation", {}).get("status") not in {None, "valid"}
    )

    # Blocked PRs → tighten diff-size gate
    if blocked_count > 0:
        floor = adaptive.get("floor_max_diff_lines", 50)
        old = new["max_diff_lines"]
        new["max_diff_lines"] = max(floor, old - 25)
        if new["max_diff_lines"] != old:
            notes.append(f"max_diff_lines {old} → {new['max_diff_lines']}")

    # Invalid reviewer JSON → raise confidence bar
    if invalid_reviewer_count > 0:
        ceiling = adaptive.get("ceiling_min_reviewer_confidence", 85)
        old = new["min_reviewer_confidence"]
        new["min_reviewer_confidence"] = min(ceiling, old + 5)
        if new["min_reviewer_confidence"] != old:
            notes.append(f"min_reviewer_confidence {old} → {new['min_reviewer_confidence']}")

    if not notes:
        notes.append("No threshold changes suggested.")
    return new, notes
```

Key properties:

1. Every adjustment is bounded by a floor or ceiling (the adaptation cannot run away).
2. Every adjustment is small (25 lines, 5 confidence points) — the system nudges, doesn't lurch.
3. Every adjustment is logged (`notes`) for commit messages and audits.
4. No adjustment is taken from a single event — the signal is *count* of blocked/invalid events, not individual cases.

### 5.14 Directory contract (portfolio-wide, end-state)

```text
<repo>/
├── AGENTS.md                       # canonical agent instructions
├── CLAUDE.md                       # symlink → AGENTS.md
├── .routing-policy.json            (Phase 4)
├── .reviewer-schema.json           (Phase 3)
├── .cursor/
│   └── rules/
│       ├── 00-always.mdc
│       └── <domain>.mdc            (existing, per-repo)
├── .claude/
│   ├── settings.json               (hooks config)
│   ├── agents/                     (Phase 1+)
│   │   └── planner.md
│   ├── skills/                     (Phase 2+)
│   │   ├── write-spec/SKILL.md
│   │   ├── postmortem/SKILL.md     (Phase 5)
│   │   └── calibrate-reviewer/SKILL.md (Phase 3+)
│   └── worktrees/                  (auto-managed, gitignored)
├── .codex/
│   └── config.toml                 (Phase 1: Executor; Phase 3: Reviewer; Phase 5: MCP, OTel)
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── route-pr.yml             (Phase 4)
│       └── scheduled-executor.yml   (Phase 6)
├── docs/
│   ├── specs/                       (Phase 2)
│   │   ├── README.md
│   │   ├── _template.md
│   │   ├── _postmortem.md           (Phase 5)
│   │   └── <feature>.md
│   └── telemetry/                   (Phase 5)
│       ├── events.jsonl
│       └── dashboard.md             (generated)
├── scripts/
│   ├── lint_spec.py                 (Phase 2)
│   ├── scan_injection.py            (Phase 2; extended in v2)
│   ├── validate_reviewer.py         (Phase 3)
│   ├── route_pr.py                  (Phase 4)
│   ├── build_pr_context.py          (Phase 4)
│   ├── append_event.py              (Phase 5)
│   ├── telemetry_dashboard.py       (Phase 5)
│   ├── adapt_thresholds.py          (Phase 5)
│   └── hooks/                       (Phase 1+)
│       ├── check_red_zone.py
│       ├── check_branch_name.py
│       ├── check_no_edits_on_scratch.py
│       ├── require_just_check.py
│       └── inject_active_spec.py
└── [existing repo contents]
```

Notice what is NOT here:

- No branded `.<name>/` directory beyond the tool-native ones (`.claude/`, `.codex/`, `.cursor/`, `.github/`).
- No `.codex/prompts/` directory. Codex prompts live in `[agents.*].developer_instructions` inside `.codex/config.toml` — the tool's native config layer.
- No orchestration YAML or per-role handoff files. The spec is the handoff; the reviewer JSON is the evidence.
- No `scripts/ai_pr.sh` wrapper. The GitHub CLI (`gh pr create`) is sufficient.

---

## 6. Open questions

1. **Codex async API maturity.** Phase 6's scheduled-executor workflow assumes an API that can be invoked from GitHub Actions on a cron. If the right API doesn't exist when you get there, Phase 6 may need to run on Claude Code's background agents or a third-party orchestrator. The rest of the blueprint is API-agnostic.

2. **Cost of two-Codex per PR.** Phase 3 runs Codex twice per PR (Executor + Reviewer). At low volume this is trivial; at 100 PRs/week it matters. Phase 5 telemetry should include per-PR cost so you can make this call with data rather than opinion. Codex's OTel exporter (§5 Phase 5 deliverable #2) gives per-tool-call cost natively if `events.jsonl` ends up under-instrumented.

3. **Routing rule calibration loop.** The `max_changed_files: 3` and `max_diff_lines: 150` thresholds in §5.3 are gut-feel. The first 20 PRs through the Router will probably produce several "the Router routed this wrong" events. The adaptive mechanism in §5.13 handles *mechanical* tightening; big directional changes (e.g., "we need a `max_diff_lines` of 500 for this repo") are human calls made by editing the policy file directly.

4. **Reviewer-prompt calibration is the hardest prompt engineering in the system.** The Reviewer must be adversarial without being noisy, must produce schema-valid JSON reliably, and must cite evidence from the diff. Expect 3–5 iterations of `developer_instructions` before the 6-of-10 useful-finding bar in reviewer calibration exit criterion is met. The `calibrate-reviewer` skill codifies the iteration procedure.

   **Goodhart-aware framing.** The 6-of-10 bar is a heuristic, not an SLA. The right response to a borderline calibration window (say 5 of 10) is to read the noise and the misses, then revise the Reviewer's `developer_instructions` accordingly — *not* to torque the threshold up or down. Treating the metric as a target rather than a signal is exactly the failure mode Goodhart's Law warns about: the moment "useful finding rate" becomes the optimization target, the Reviewer learns to produce verbose, technically-true findings that score well and inform little. Use the metric to find Reviewer drift; use human judgment to fix it.

5. **Fenced-block parsing is fragile.** Extracting JSON between `<!-- REVIEWER_JSON -->` markers assumes the Reviewer puts exactly one such block in the PR body. The fallback "emit minimum-confidence JSON on error" pattern in the Reviewer's `developer_instructions` is the mitigation. Expect at least one post-mortem about a malformed output.

6. **Hook performance on large repos.** PreToolUse hooks add latency to every Edit. On `ai-project-template` this is invisible; on a 100k-file monorepo, the red-zone check needs to be O(1) (path-prefix lookup) rather than O(n) (path traversal). The `check_red_zone.py` template uses a prefix tuple — fast — but watch this if the repo grows.

7. **MCP server trust.** Phase 5's MCP integration assumes the configured servers are trusted (locally hosted, or on a private endpoint). A compromised MCP server is an injection vector that bypasses `scan_injection.py` (the scan only sees persisted artifacts, not in-flight tool responses). For now, only run MCP servers you control. If you need third-party MCP, gate it behind the same approval policy Codex uses for live web search.

---

## 7. Limitations of this blueprint

1. **This is design, not implementation.** Every phase has ways to go wrong that cannot be fully anticipated. Exit criteria define whether a phase is completed.
2. **The multi-agent orchestration patterns are industry-young.** Much of this will be obsolete in 18 months. The blueprint's durable value is in the *decomposition* and *discipline*, not in any specific tool choice.
3. **Personal calibration matters more than this document.** This blueprint is scaffolding for *human* judgment, not a replacement for it.
4. **`ai-project-template` is a living repo.** Every phase changes it. What counts as "gold-standard" today is the completed Phase 3.
5. **Native primitives churn.** Hooks, subagents, skills, plan mode, and MCP all matured visibly between phases of this blueprint. Expect another wave of primitive evolution before Phase 6 lands. Track the official docs (Claude Code docs map, Codex developer docs) before each phase advance.

---
