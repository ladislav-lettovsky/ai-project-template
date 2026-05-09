---
name: calibrate-reviewer
description: |
  Loaded by the human when scoring a Codex Reviewer's JSON output during
  the Phase 3 calibration window. Walks through the useful/noise/missed
  three-bucket scoring procedure, tracks progress against the 6-of-10
  exit-criterion bar, and prescribes when to iterate the Reviewer's
  developer_instructions vs. continue collecting data. NOT for general
  PR review or spec work — only for Reviewer-output assessment.
---

# Calibrating the Codex Reviewer

The Phase 3 exit criterion (per `docs/blueprint.md` §4) is behavioral:

> *"On 3 consecutive PRs, the Codex Reviewer's JSON has been evaluated by
> human with scoring: useful / noise / missed real issue I caught. At
> least 2 of 3 PRs should produce at least one useful finding. All 3 must
> pass schema validation."*

This skill is how you make that judgment.

## When this skill applies

Use this skill when you have:
1. A merged or open PR with a Reviewer JSON in its body, AND
2. You've personally read the diff and formed your own opinion of what's
   good/bad about it, AND
3. You want to score the Reviewer's findings against your opinion.

Do NOT use this skill for:
- General PR review (just review the PR normally).
- Spec drafting (use `write-spec` instead).
- Code-quality assessment of the diff (the Reviewer reviews the diff;
  this skill reviews the Reviewer).

## Pre-flight: extract and validate the JSON

Before scoring:

1. Run `just validate-reviewer <pr-body-file>`. If it exits non-zero, the
   Reviewer failed at the structural level. Skip the per-finding scoring
   for this PR — it counts toward the "all 3 must pass schema validation"
   criterion as a fail. Note the schema error and move on.
2. If validation passes, extract the JSON. Read `summary` first to
   anchor on the Reviewer's overall framing.

## The three-bucket score (per finding)

For each finding in the JSON:

- **useful** — A real issue you would have flagged (or didn't notice
  but agree with on review). Doesn't matter if severity exactly matches
  yours; the categorical type and the underlying observation must be
  right.
- **noise** — A finding that's technically true but unimportant
  (over-eager nit), wrong about the code, or a misclassification (e.g.,
  marked `extra_scope` when the diff is actually in scope).
- **missed** — Something *you* caught that the Reviewer should have
  flagged but didn't. Track these even though they're not in the JSON;
  they're the most informative signal.

A PR with five findings might score: `[useful, useful, noise, noise, noise]`
plus one `missed`. The PR-level question is "did the Reviewer produce
at least one useful finding?" — yes here, even though most findings
were noise.

## The 6-of-10 bar (a reframing of the blueprint's 2-of-3)

The blueprint says 2-of-3 PRs must produce ≥1 useful finding. That's a
short window — useful for kickoff, but volatile (one bad day on the
prompt will fail it). Once you're past the initial 3, switch to a
rolling window: 6-of-10 most recent PRs producing ≥1 useful finding.

If the rolling 10 drops below 6 useful: stop, iterate the prompt,
restart the count.

## Scoring template (use this format in your notes / events.jsonl)

```text
PR #<N> — <slug>
schema_valid: yes|no
findings: [useful, useful, noise]
missed: [<one-line description per missed issue>]
prompt_iteration: vN  (the developer_instructions hash you were running)
notes: <one or two sentences>
```

Append to `docs/telemetry/reviewer-calibration.md` (Phase 5 will move
this to `events.jsonl`; for the 3-PR calibration window, plain
markdown is fine).

## When to iterate the developer_instructions

Iterate if you observe ANY of:

1. **Two consecutive PRs with zero useful findings.** The prompt isn't
   producing signal; tweak the bias toward findings or sharpen a
   specific finding type's guidance.
2. **A repeated finding-type confusion.** E.g., Reviewer keeps marking
   `extra_scope` when it should be `weak_test`. Add disambiguating
   examples to the relevant section of `developer_instructions`.
3. **All findings are nits.** Reviewer is too cautious about emitting
   `warning` or `critical`. Add language: "use warning when an issue
   would be uncomfortable to discover post-merge."
4. **Schema validation fails twice in 3 PRs.** Fence-extraction or
   field-set is unstable. Tighten the output format instructions and
   re-anchor the fallback stub.

Do NOT iterate for:
- A single bad PR (noise is normal).
- A finding you disagree with but can't quickly explain why.
- Stylistic preferences about how findings are worded.

## How to iterate

1. Open `.codex/config.toml`. Edit the `[agents.reviewer]
   developer_instructions` block (red-zone — Path A authorship in
   Cursor).
2. Make ONE specific change per iteration. Multi-change iterations make
   it impossible to attribute behavior shifts to specific edits.
3. Bump a comment-tracked iteration tag (e.g., `# Reviewer prompt vN`
   at the top of the developer_instructions string).
4. Restart the rolling-10 calibration tally — vN+1 measurements are
   not comparable to vN measurements.

## Exit-criterion checklist (Phase 3)

You can declare Phase 3 done when ALL of:

- [ ] 3 consecutive PRs scored.
- [ ] All 3 produced schema-valid Reviewer JSON.
- [ ] At least 2 of 3 produced ≥1 useful finding.
- [ ] You've confirmed via Codex session log that Reviewer ran with
  `sandbox_mode = "read-only"` (the runtime guarantee, not the prompt).
- [ ] At least one PR produced a `missing_*` or `invariant_risk`
  finding — proves the Reviewer can flag real bugs, not just nits.

If you hit 3-of-3 useful on the first attempt, that's suspect (the bar
is calibrated for ~67% useful). Look for:
- Is the bar too easy? Are you scoring "useful" generously?
- Are the demo PRs unrepresentative? Pick a harder one for PR #4.

## Common Reviewer failure modes (and the fix)

| Symptom | Likely cause | Iteration |
|---|---|---|
| Findings are all `nit` | Severity-bias too cautious | Add: "use `warning` when an issue would be uncomfortable post-merge" |
| Findings cite no evidence | Evidence rule under-emphasized | Move evidence rule earlier; add example |
| Findings are vague ("could improve X") | Output is drifting toward prose | Re-anchor the schema in instructions; add more enum examples |
| Reviewer writes paragraphs outside the fence | Format prohibition unclear | Strengthen "NEVER prose" with example of what NOT to do |
| Schema fails (missing field) | Fallback stub not memorized | Move fallback stub closer to top of prompt; tag as MUST USE WHEN UNSURE |
| `confidence` always 80-90 | No incentive to vary | Add: "if you're guessing on any finding, drop confidence by 10 per finding" |
