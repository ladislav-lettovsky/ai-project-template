# Tighten Planner spec-drafting routing and trigger criteria

## Metadata
- spec_id: SPEC-20260508-tighten-planner-spec-drafting
- owner: Ladislav Lettovsky
- status: drafted
- complexity: low
- risk_tier: T1
- repo: ai-project-template
- branch: spec/tighten-planner-spec-drafting

## Context

Phase 2's first end-to-end exercise (the `farewell` module, PR #5)
surfaced two weaknesses in the Planner+`write-spec` interaction that
were noted during Stage D review:

1. **Routing race.** When the user said "draft a spec," Claude Code
   routed directly to the `write-spec` skill from the main session
   and bypassed the Planner subagent entirely. The Planner's
   `permissionMode: plan` constraint (read-only by construction) never
   engaged. The skill's description matched the user's prompt more
   literally than the Planner's role description, so the skill won the
   routing race. The spec was produced by the main agent — which has
   Edit/Write tools — not by the constrained Planner role.

2. **Time-based trigger is the wrong unit.** Both `planner.md` and
   `SKILL.md` gate spec-drafting on "more than 30 minutes of effort."
   Time is a poor proxy for "this work needs a spec":
   - Codex's wall-clock is much shorter than a human's by-hand time.
   - Some 5-minute tasks are radioactive (auth changes); many 2-hour
     tasks are safe (typo fixes across files).
   - Arbitrary thresholds invite gaming ("this will only take 28 min").
   The signals that actually drive review burden — red-zone touch,
   file count, public-interface change, future-reader-needs-context —
   are already first-class in the spec format itself. The trigger
   criterion should reflect those signals directly.

This spec fixes both in one PR because they share a surface (the
Planner subagent definition and the `write-spec` skill, especially
their `description:` frontmatter and trigger language).

## Assumptions
- A1: `.claude/agents/planner.md` and `.claude/skills/write-spec/SKILL.md`
  are the only locations referencing the 30-minute threshold or the
  Planner-vs-skill routing surface. (`grep -r "30 min" .` should
  confirm.)
- A2: Claude Code routes between subagents and skills based on
  `description:` text matching against the user's prompt. Sharpening
  descriptions is therefore sufficient to bias the routing. If proven
  false in practice, a follow-up spec is needed (this spec does not
  add telemetry to detect it; see NG3).

## Decisions
- D1: Sharpen `.claude/agents/planner.md`'s `description:` frontmatter
  to claim primacy over the `write-spec` skill — language like
  "USE PROACTIVELY ... invoke this BEFORE loading the write-spec skill."
  Rationale: the description is what Claude Code's routing logic sees;
  the model picks the most specific description match.
- D2: Sharpen `.claude/skills/write-spec/SKILL.md`'s `description:` to
  scope the skill as "loaded by the Planner subagent when drafting a
  new spec," rather than a generally-callable spec-drafting playbook.
  Rationale: belt-and-suspenders — both ends of the routing race get
  tightened.
- D3: Replace the "30-minute threshold" language in both files with a
  consequence-based test. The 30-min item remains as a final fallback
  bullet, not the primary criterion. Rationale: align the trigger with
  the signals that actually drive review burden.
- D4: Do NOT modify `AGENTS.md` or `docs/post-fork-checklist.md` in this
  spec. Neither cites the 30-min number. Keeping the change tight to
  the two files that actually contain the criterion limits blast radius.

## Problem Statement

`.claude/agents/planner.md` and `.claude/skills/write-spec/SKILL.md`
contain (a) descriptions that allow the `write-spec` skill to be loaded
by the main agent without engaging the Planner subagent, and (b) trigger
language ("more than 30 minutes of effort") that is a weak proxy for
"this work needs a spec." The first weakness was observed in the
Phase 2 demo on `spec/add-farewell-module`; the second was identified
as a follow-up during Stage D review of Phase 2. Both should be
addressed in one PR because they share the same surface.

## Requirements (STRICT)

- [ ] R1: `.claude/agents/planner.md`'s `description:` frontmatter
  includes language that explicitly claims primacy over the
  `write-spec` skill, instructing Claude Code to invoke the Planner
  subagent before loading the skill.
- [ ] R2: `.claude/skills/write-spec/SKILL.md`'s `description:`
  frontmatter explicitly scopes the skill as "loaded by the Planner
  subagent when drafting a new spec," not as a generally-callable
  spec-drafting playbook.
- [ ] R3: `.claude/agents/planner.md` replaces every reference to the
  30-minute time threshold with a consequence-based criteria block.
  The criteria block lists at minimum: (a) red-zone touch, (b)
  multi-file change (excluding co-located tests), (c) public-interface
  or behavior-contract change, (d) future-reader-needs-context.
  The 30-min threshold may remain as a final fallback bullet.
- [ ] R4: `.claude/skills/write-spec/SKILL.md` mirrors R3 — every
  reference to the 30-minute threshold replaced by the same
  consequence-based criteria block. Wording may differ but the
  criteria set must match.
- [ ] R5: After both files are edited, `just check` (which includes
  `lint-changed-specs` and `scan-injection`) passes green.

## Non-Goals
- [ ] NG1: No edits to `AGENTS.md`, `docs/post-fork-checklist.md`,
  `docs/blueprint.md`, or any other file outside the two named
  red-zone files.
- [ ] NG2: No changes to `lint_spec.py` or `scan_injection.py`.
  The linter contract is unchanged.
- [ ] NG3: No measurement / telemetry to prove the routing fix worked.
  Verification is by behavioral observation in the next real
  spec-drafting request (out of scope; will be confirmed when Phase 3
  begins or the next non-trivial work requires a spec).
- [ ] NG4: No new skill or subagent files are created.
- [ ] NG5: No model-side or Claude-Code-side configuration changes.
  The fix is purely in description text.

## Interfaces

**Modified files:**
- `.claude/agents/planner.md` — frontmatter `description:` field
  (R1, D1); body sections "Operating notes" and any other 30-min
  reference (R3, D3).
- `.claude/skills/write-spec/SKILL.md` — frontmatter `description:`
  field (R2, D2); body sections "When this skill applies," "When this
  skill does NOT apply," and "Pre-flight" (R4, D3).

**Public API surface:** none. These are agent-instruction documents,
not code interfaces.

**Behavioural contract:**

| User says | Pre-change behavior | Post-change behavior |
|---|---|---|
| "Draft a spec for X" | Main agent loads write-spec, writes the file directly | Planner subagent invoked, drafts plan, human commits |
| "Add a one-line print statement" (sub-30-min, single file) | Planner suggests skipping spec (time-based) | Planner suggests skipping spec (consequence-based: trivial, no red-zone, no interface change) |
| "Refactor src/widget.py and update its tests" (multi-file but trivially time-quick) | Planner may skip spec if estimated <30 min | Planner skips spec because co-located test edits do not count as multi-file |
| "Refactor src/widget.py and src/helper.py" (genuine multi-file) | Planner may skip spec if estimated <30 min | Planner requires spec (multi-file trigger) |
| "Touch AGENTS.md to add an invariant" | Planner requires spec | Planner requires spec (red-zone trigger; equivalent) |

## Invariants to Preserve
- [ ] INV1: `just check` stays green (Invariant 4 from AGENTS.md).
- [ ] INV2: No new runtime dependencies in `pyproject.toml`.
- [ ] INV3: The Planner subagent remains read-only — `tools:`,
  `disallowedTools:`, and `permissionMode:` fields unchanged.
- [ ] INV4: The `write-spec` skill remains a single SKILL.md file
  under `.claude/skills/write-spec/` — no scope change beyond
  frontmatter description and body wording.
- [ ] INV5: Spec format §5.1 (the structure `lint_spec.py` enforces)
  is unchanged.

## Red-Zone Assessment
- auth: no
- billing: no
- dependencies: no
- CI: no
- migrations: no
- secrets: no
- infra: no
- invariant-protected files: yes

Risk tier is **T1**, not T0, because of the red-zone touch. T1 makes
this PR ineligible for Phase 4's `review:codex` auto-merge — human
review required. Implementation Slices documents how the red-zone
edit is authorized.

## Test Plan

The work is purely text changes to documentation. There is no Python
function to test. Validation is by manual diff review plus the
existing `just check` gate.

- [ ] T1 -> covers R1, R2, R3, R4, R5
  Manual diff review of the PR confirms each requirement is met:
  - R1: planner.md `description:` mentions write-spec primacy.
  - R2: SKILL.md `description:` names the Planner subagent and
    scopes itself as Planner-loaded.
  - R3: planner.md no longer leads with "30 minutes" — the new
    consequence-based criteria block is present and contains all four
    required items.
  - R4: SKILL.md mirrors R3.
  - R5: `just check` runs green locally before push, and CI is green.

No automated tests are added because:
- Description routing is enforced by Claude Code's runtime, not by
  repo-side code.
- Documentation language is best validated by human read.

## Validation Contract

| Requirement | Validator |
|---|---|
| R1 | Manual diff review: planner.md `description:` frontmatter |
| R2 | Manual diff review: SKILL.md `description:` frontmatter |
| R3 | Manual diff review: planner.md body sections |
| R4 | Manual diff review: SKILL.md body sections |
| R5 | `just check` green locally and in CI |

## Edge Cases
- EC1: A user explicitly bypasses the Planner with `/agents write-spec`
  (or equivalent slash-command in their Claude Code version) — the
  skill still loads. This is intended (explicit user override). No
  change required.
- EC2: An older or differently-configured Claude Code version routes
  by something other than `description:` text. Out of scope per A2.
- EC3: The consequence-based criteria are themselves ambiguous in
  edge cases (e.g., "is editing one file plus its co-located test
  'multi-file'?"). Resolution: the criteria explicitly exclude
  co-located tests from the multi-file count, and the planner.md
  wording must say so.

## Security / Prompt-Injection Review
- source: in-process LLM input only. The Planner subagent reads its
  own description from `.claude/agents/planner.md`; the skill reads
  its own description from SKILL.md. No external data flows. No MCP
  tools. No web search.
- risk: low
- mitigation: not required. The text edits are not derived from any
  external source; they are authored by the human.

## Observability

None required. The change has no runtime behavior — it's text in
agent-instruction documents read by Claude Code at session start.
Behavioral verification happens in the next real spec-drafting
request (out of scope per NG3).

## Rollback / Recovery

Purely text changes in two files. To revert:
`git revert <merge-commit-sha>`. No data migrations, no feature
flags, no service restarts.

## Implementation Slices

1. **Slice 1 (single PR, two commits):** edit both red-zone files as
   described in Requirements R1-R4. Run `just check` locally to
   satisfy R5. Open PR with linked spec and empty REVIEWER_JSON block.

   **Red-zone authorization:** Path A — the human authors the edits
   in their editor (Cursor) directly. The PreToolUse `check_red_zone.py`
   hook only fires for Claude Code agent edits, not for human editor
   saves. The Codex Executor is NOT used for this slice. The PR
   description states this explicitly so a future reader knows
   red-zone was touched intentionally and by which path.

## Done When
- [ ] R1 through R5 satisfied
- [ ] Decisions D1-D4 preserved or explicitly deferred
- [ ] Test T1 (manual review checklist) passes
- [ ] `just check` green locally
- [ ] CI green
- [ ] No invariant violations (INV1-INV5)
- [ ] Branch name starts with `spec/tighten-planner-spec-drafting`
- [ ] PR description links this spec
- [ ] PR description explicitly notes the red-zone touch and Path A
- [ ] PR body contains `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block
