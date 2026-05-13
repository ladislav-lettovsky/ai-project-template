<!--
Copy this file to docs/specs/<slug>.md and fill it in. The slug must match
your branch name (spec/<slug>). `scripts/lint_spec.py` enforces the
structure below; missing sections or unmapped requirements will fail the
lint and block `just check`.

Delete this comment block from your spec before committing.
-->

<!-- markdownlint-disable MD033 -->
<!-- Angle-bracket placeholders below (e.g., <slug>, <Feature Title>) are
     fillable template tokens, not inline HTML. -->

# <Feature Title>

## Metadata

- spec_id: SPEC-<YYYYMMDD>-<slug>
- owner: <your name>
- status: drafted
- complexity: low | medium | high
- risk_tier: T0 | T1 | T2 | T3
- repo: <repo-name>
- branch: spec/<slug>

## Context

Why this work exists now. One or two paragraphs. The reader six months
from now should be able to read just this section and understand
motivation.

## Assumptions

- A1: <what we're assuming>

## Decisions

- D1: <architectural decision with rationale>

## Problem Statement

Exact failure, missing capability, or constraint. Be concrete: name the
file, the function, the error, the user-visible symptom.

## Requirements (STRICT)

- [ ] R1: <specific, testable requirement>

> Each requirement gets a stable ID (`R1`, `R2`, … or `REQ-<DOMAIN>-<NN>`).
> The ID is referenced from Test Plan and Validation Contract — do not
> renumber after the spec is committed.

## Non-Goals

- [ ] NG1: <explicitly out of scope>

## Interfaces

Affected entrypoints, APIs, CLI commands, models, schemas, UI surfaces, or
files. New files added or existing files modified — list them.

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

> Any `yes` answer means this work cannot ship as `risk_tier: T0`,
> regardless of diff size. Adjust the `risk_tier` in Metadata above if
> needed.

## Test Plan

- [ ] T1 -> covers R1

> For every `R*` above, there MUST be a `T<n> -> covers R<list>` line
> here. Each test maps to one or more requirement IDs. Tests that don't
> cite a requirement are out of scope.

## Validation Contract

- R1 -> `just check` (or specific command/assertion that proves R1)

> For every `R*` above, there MUST be a `R* -> <validator>` line here.
> The validator is the exact command (or test name) that demonstrates
> the requirement is satisfied. `just check` is acceptable for
> requirements covered by the standard test gate.

## Edge Cases

- EC1: <boundary condition>

## Security / Prompt-Injection Review

- source: <where does any LLM-input data come from? include MCP tools,
  web search, external docs, user input>
- risk: low | medium | high
- mitigation: <if non-low, how is it mitigated?>

> Mandatory non-empty if the work sources content that flows to an LLM.
> A pure in-process function with no external input is `risk: low`,
> `mitigation: not required`.

## Observability

Logs, metrics, assertions, traces, or telemetry updates needed. "None
required" is acceptable for purely additive, in-process changes.

## Rollback / Recovery

How to revert, disable, or mitigate if it fails in production. For purely
additive changes: "revert the commit". For migrations: name the down
script. For feature flags: name the flag and the safe-default.

## Implementation Slices

1. Slice 1: <smallest useful commit>

> One spec, one branch. If it needs to be split into multiple PRs, the
> slices document the order.

## Done When

- [ ] All requirement IDs satisfied
- [ ] Decision IDs preserved or explicitly deferred
- [ ] Tests mapped and passing
- [ ] Validation Contract satisfied
- [ ] `just check` green
- [ ] CI green
- [ ] No invariant violations
- [ ] Branch name starts with `spec/<slug>` (Invariant 1)
- [ ] PR description links this spec
- [ ] PR body contains `<!-- REVIEWER_JSON --> ... <!-- /REVIEWER_JSON -->` block
