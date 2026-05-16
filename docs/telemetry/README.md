# Telemetry (Phase 5)

Machine-readable routing history for the deterministic PR Router.

| File | Purpose |
| --- | --- |
| `events.jsonl` | One JSON object per line per PR (append-only log) |
| `dashboard.md` | Human summary — regenerate with `just telemetry-dashboard` |

## Recording events

On each merged PR, `.github/workflows/record-telemetry.yml` rebuilds `pr.json`,
runs `route_pr.py`, and appends via `scripts/append_event.py`.

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

See `docs/blueprint.md` Phase 5 and `scripts/adapt_thresholds.py`.
