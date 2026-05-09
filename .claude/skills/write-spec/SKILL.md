---
name: write-spec
description: |
  Draft a new spec under docs/specs/<slug>.md following the §5.1 structure
  enforced by scripts/lint_spec.py. Use whenever the user asks for a spec,
  feature plan, or implementation contract for work estimated >30 minutes.
  Walks through every required section in order, names common failure
  modes, and produces a draft the Planner can hand to the human for
  commit.
---

# Writing a spec

A spec is the contract the Executor implements literally and the Reviewer
checks against. Get it wrong here and the cost compounds — the Executor
will faithfully build the wrong thing.

## When this skill applies

Use this skill when the user asks for any of:

- "write a spec for…"
- "plan how we should add / change / remove …"
- "draft a feature for …"
- An implementation request estimated at more than 30 minutes of effort.

If the work is < 30 minutes — fix one typo, rename one variable, add one
log line — say so explicitly and offer to proceed without a spec. Specs
are for work substantial enough to benefit from the structure.

## When this skill does NOT apply

- Reviewing or revising an *existing* spec — read the existing spec
  first; this skill is for green-field drafting.
- Writing a postmortem — that's a different skill (Phase 5,
  `.claude/skills/postmortem/SKILL.md`).
- Writing tests, code, or documentation that doesn't authorize work.

## Pre-flight (before you write a single section)

1. **Read the request twice.** The spec is the contract; ambiguity here
   produces wrong code later. If after two reads the goal isn't clear,
   STOP and ask one clarifying question.
2. **Estimate effort honestly.** If it's <30 min, suggest skipping the
   spec. If it's >2 days, suggest splitting into multiple specs.
3. **Identify external inputs.** Does this work require reading from
   MCP tools, web search, external docs, user input, or untrusted files?
   If yes, the `## Security / Prompt-Injection Review` section is
   non-empty and the risk is at least medium.
4. **Pick the slug.** `<verb>-<noun>` or `<noun>-<scope>` style.
   Examples: `add-cache-warmup`, `fix-greet-unicode`, `migrate-pg-15`.
   The slug becomes:
   - the filename: `docs/specs/<slug>.md`
   - the branch name: `spec/<slug>`
   - the `spec_id`: `SPEC-<YYYYMMDD>-<slug>`

## Section-by-section walkthrough

Copy `docs/specs/_template.md` and fill it in. The walkthrough below
assumes you're working through that template top-to-bottom.

### Title (`# <Feature Title>`)
A noun phrase describing the *artifact*, not the *task*. Good:
"Cache warm-up on cold start." Bad: "Add cache warm-up."

### Metadata
- `spec_id`: `SPEC-<YYYYMMDD>-<slug>` — use today's UTC date.
- `owner`: real name, not a handle.
- `status`: `drafted` (you're drafting; the Executor flips it to
  `in-progress`, the human flips to `complete` post-merge).
- `complexity`: `low | medium | high`. Low = single file, well-known
  pattern. High = touches multiple subsystems or introduces a new
  concept.
- `risk_tier`: `T0 | T1 | T2 | T3`. T0 = "could not break anything
  important if wrong." This is the **only** tier that will be eligible
  for `review:codex` auto-merge in Phase 4. Marking consequential work
  T0 to dodge human review is the worst failure mode in this system —
  when in doubt, escalate.
- `repo`: the GitHub repo name.
- `branch`: `spec/<slug>` — must match the working branch.

### Context
Why this work exists *now*. Two paragraphs at most. The reader six
months from now should understand motivation from this section alone.

### Assumptions (`A1`, `A2`, …)
List the things you're taking for granted that, if false, would
invalidate the spec. "Python 3.12 is available." "The package layout
is src/." Don't list things that are obvious from the codebase ("the
repo uses git").

### Decisions (`D1`, `D2`, …)
Architectural choices with rationale. Each `D*` is a sentence-or-two
"we chose X over Y because Z." Decisions are referenced from PR
descriptions and from the Reviewer JSON in Phase 3.

### Problem Statement
Concrete: name the file, the function, the error, the user-visible
symptom. "We have no canonical example of a minimal public function" is
a concrete-enough problem; "the codebase is hard to navigate" is not.

### Requirements (STRICT)
Bullet-form. Stable IDs (`R1`, `R2`, … or `REQ-<DOMAIN>-<NN>`). Each
requirement is **specific** (one observable behavior) and **testable**
(you can write a unit/integration test for it).

Bad: `R1: greet should be nice.`
Good: `R1: greet(name) returns "Hello, <name>!" when name is a non-empty
str.`

### Non-Goals (`NG1`, `NG2`, …)
Explicitly out-of-scope. Prevents the Executor from "helpfully"
expanding the work.

### Interfaces
New files, new public APIs, modified entrypoints. A behavioural-contract
table is helpful (input → output / effect).

### Invariants to Preserve (`INV1`, `INV2`, …)
What must remain true after this change. "`just check` stays green."
"No new runtime dependencies." "Red-zone files are not touched."
Reference the AGENTS.md invariants by number where applicable.

### Red-Zone Assessment
Eight axes, each `yes` or `no`:
- auth, billing, dependencies, CI, migrations, secrets, infra,
  invariant-protected files

Any `yes` ⇒ this spec **cannot** ship as `risk_tier: T0`. Adjust the
metadata above. Note the red-zone touch in Implementation Slices so
the Reviewer can confirm the touch is intentional.

### Test Plan (`T1`, `T2`, …)
For every `R*`, write `T<n> -> covers R<list>`. Tests can cover
multiple requirements; that's fine. Requirements without test coverage
are rejected by `lint_spec.py`.

Each `T*` includes the test name (the function the Executor will
write) and a one-line description of what it asserts.

### Validation Contract
For every `R*`, write `R* -> <validator>`. The validator is the exact
command (or test name) that demonstrates the requirement is satisfied.
`just check` is acceptable for requirements covered by the standard
gate; for `ty`-only requirements (e.g., a typed signature), cite
`just type`.

This section can be a list **or** a Markdown table; the linter accepts
both.

### Edge Cases (`EC1`, `EC2`, …)
Boundary conditions, unusual inputs, failure modes you considered but
that don't rise to the level of a separate requirement.

### Security / Prompt-Injection Review
- `source`: where does any LLM-input data come from? Specs that source
  data from MCP tools, web search, external docs, or user input must
  identify the source.
- `risk`: `low | medium | high`.
- `mitigation`: required if risk is non-low.

A pure in-process function with no external input is `risk: low`,
`mitigation: not required`.

### Observability
What logs / metrics / traces / assertions does this work add or rely
on? "None required" is acceptable for purely additive, in-process
changes.

### Rollback / Recovery
How to revert, disable, or mitigate if the change fails in
production.
- Purely additive code change: "revert the commit."
- Migration: name the down-script.
- Feature flag: name the flag and the safe-default value.

### Implementation Slices
Numbered, each a smallest-useful commit. One slice per logical
concern. If the work needs to ship across multiple PRs, the slices
document the order.

### Done When
Checklist that includes the standard items (all `R*` satisfied, tests
passing, `just check` green, CI green, no invariant violations,
branch named `spec/<slug>`, PR description links the spec, PR body
contains the `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->`
block — empty until Phase 3).

## Pre-handoff checklist (before presenting the plan to the human)

Mentally run through these — they are exactly what `lint_spec.py`
will check at commit time:

- [ ] Every required section is present and in canonical order.
- [ ] `risk_tier` and `complexity` are set, and the values are honest.
- [ ] Every `R*` appears in Test Plan as `T<n> -> covers R*`.
- [ ] Every `R*` appears in Validation Contract as `R* -> <validator>`.
- [ ] Red-Zone Assessment is yes/no, not "maybe." If any `yes`, the
      `risk_tier` is at least T1.
- [ ] Security review is non-empty if external data flows in.

Then present the plan in Plan Mode for human approval. **You cannot
edit files** — the human commits the spec, runs `just lint-spec`, and
hands the branch to the Executor.

## Common failure modes to flag, not paper over

If any of the following arise during drafting, surface them as a
clarifying question rather than guessing:

- The user describes *what they want done* but not *what success looks
  like*. You cannot write `R*` without knowing what success means.
- The user's request implies touching red-zone files but doesn't
  acknowledge it.
- Two requirements contradict each other.
- A requirement has no obvious test (e.g., "must be performant" with
  no threshold).
- The work spans multiple unrelated subsystems and would be better
  split into two specs.

A clarifying question costs minutes; a wrong spec costs a PR cycle.
