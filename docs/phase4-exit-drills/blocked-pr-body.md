# Phase 4 exit drill C — expect `blocked`

Authorizing observation only. PR diff may be trivial; routing is driven by Reviewer JSON below.

Spec: [docs/specs/phase4-exit-drills.md](../specs/phase4-exit-drills.md)

<!-- REVIEWER_JSON -->
```json
{
  "summary": "Exit drill: synthetic critical finding to exercise the blocked routing lane.",
  "findings": [
    {
      "id": "F1",
      "type": "invariant_risk",
      "severity": "critical",
      "requirement_ids": [],
      "description": "Drill-only critical finding; do not merge this PR.",
      "evidence": "docs/phase4-exit-drills/README.md — Drill C",
      "suggested_action": "Close PR after confirming blocked label; no code change required."
    }
  ],
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
  "confidence": 90
}
```
<!-- /REVIEWER_JSON -->
