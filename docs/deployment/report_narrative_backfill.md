# Report Narrative Backfill

Brand3 public report reads must not call LLM. Rich report narrative is persisted
as a `raw_inputs` record with source `report_narrative`.

## Policy

- Backfill is explicit and operator-triggered.
- Backfill must target selected `run_id` values.
- No automatic mass LLM calls are allowed on public page load.
- Existing reports without `report_narrative` keep the deterministic fallback.

## Command

Dry run:

```bash
./.venv/bin/python scripts/backfill_report_narrative.py --dry-run 73
```

Persist:

```bash
./.venv/bin/python scripts/backfill_report_narrative.py 73
```

## Production

Run only for selected reports after confirming API credentials and expected
cost. The script writes one additional `raw_inputs` row per run.
