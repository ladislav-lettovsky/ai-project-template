# Phase 4 exit criteria — observation log

| Outcome | Required signal | PR | Label | Router comment |
| --- | --- | --- | --- | --- |
| `review:codex` | Policy-eligible PR + valid Reviewer JSON | [#39](https://github.com/ladislav-lettovsky/ai-project-template/pull/39) | `review:codex` | Yes |
| `review:human` | Red-zone file in diff (e.g. `AGENTS.md`) | [#42](https://github.com/ladislav-lettovsky/ai-project-template/pull/42) | `review:human` | Red-zone / invariant-protected files |
| `blocked` | Reviewer `critical` finding in valid JSON | [#41](https://github.com/ladislav-lettovsky/ai-project-template/pull/41) | `blocked` | Critical finding |

Also observed (not a separate exit row): [#38](https://github.com/ladislav-lettovsky/ai-project-template/pull/38)
→ `review:human` when Reviewer JSON missing/invalid.
