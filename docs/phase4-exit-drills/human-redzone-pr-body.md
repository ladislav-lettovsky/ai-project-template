# Phase 4 exit drill B — expect `review:human` (red-zone)

This PR intentionally touches `AGENTS.md`. Router should route to human review.

Spec: [docs/specs/phase4-exit-drills.md](../specs/phase4-exit-drills.md)

<!-- REVIEWER_JSON -->
```json
{
  "summary": "Exit drill: red-zone touch with otherwise valid reviewer JSON.",
  "findings": [],
  "coverage": {
    "requirements_total": 1,
    "requirements_covered": 1,
    "tests_expected": 0,
    "tests_present": 0
  },
  "risk_assessment": {
    "scope_fit": "correct",
    "invariant_risk": "low",
    "production_risk": "low"
  },
  "confidence": 85
}
```
<!-- /REVIEWER_JSON -->
