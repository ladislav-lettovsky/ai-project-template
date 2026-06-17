# Telemetry

Machine-readable routing history for the deterministic PR Router.

| File | Purpose |
| --- | --- |
| `events.jsonl` | One JSON object per line per PR (append-only log) |
| `dashboard.md` | Human summary — regenerate with `just telemetry-dashboard` |

## Event schema (`events.jsonl`)

Each line is one JSON object. Core routing fields are unchanged; scheduled dispatch adds:

| Field | Type | Values | Notes |
| --- | --- | --- | --- |
| `dispatch_source` | string | `manual`, `scheduled` | How the PR was opened. Default `manual` when absent on historical rows. Set to `scheduled` when the merged PR body or merge commit history contains a `dispatch-source: scheduled` marker (`dispatch_spec.py` scheduled transport). |

Historical rows without `dispatch_source` remain valid; readers should treat missing values as `manual`.

## Recording events

On each merged PR (except telemetry chore PRs), `.github/workflows/record-telemetry.yml`
rebuilds `pr.json`, runs `route_pr.py`, appends via `scripts/append_event.py`, and
opens a short-lived `chore/telemetry/pr-<N>` PR so branch protection checks run before
telemetry lands on `main`. See **Branch protection (Router)** in `CONTRIBUTING.md`.

Local replay:

```bash
uv run scripts/build_pr_context.py --repo OWNER/REPO --pr N --out pr.json
uv run scripts/route_pr.py pr.json | tee route.json
uv run scripts/append_event.py --pr pr.json --route route.json --pr-number N --merge-outcome merged
just telemetry-dashboard
```

## Adaptive thresholds

```bash
just adapt-thresholds          # dry-run JSON to stdout
just adapt-thresholds --write  # apply bounded updates to .routing-policy.json
```

See `docs/blueprint.md` and `scripts/adapt_thresholds.py`.
