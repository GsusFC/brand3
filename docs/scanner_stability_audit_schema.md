# Scanner Stability Audit Schema

Version: `scanner-stability-audit-v2`

Purpose: diagnose repeat scanner instability from a production SQLite dump without mutating data.

## CLI

```bash
./.venv/bin/python scripts/scanner_stability_audit.py \
  --db data/brand3.sqlite3 \
  --version SV9 \
  --format json \
  --output tmp/scanner_stability_audit_sv9.json
```

Use `--group-by-day` when the question is same-day stability. Leave it off when the sample size is small and the question is broader version stability.

## Group Key

Groups are built from:

- `normalized_brand_or_url`
- `scanner_version`
- `rubric_version`
- `model_versions`
- `lang`
- `visual_signature_version`
- `tldr_prompt_version`
- `research_pack_builder_version`
- `capture_strategy`
- `created_day_bucket` when `--group-by-day` is enabled; otherwise `all`

Missing fields are emitted as `unknown` so older dumps remain auditable.

## Diagnosis Stages

- `acquisition_drift`: persisted raw inputs differ.
- `evidence_pack_drift`: research pack/proof-point layer differs.
- `interpretation_drift`: TLDR/interpreter output differs.
- `scoring_drift`: score/component output differs while upstream hashes do not explain it.
- `presentation_drift`: quadrant/reliability presentation changes without upstream score drift.
- `persistence_drift`: `magnetism_scans` columns disagree with the saved `raw_payload`.
- `non_critical_payload_drift`: raw payload metadata changed but critical hashes and scores did not.
- `stable`: no material drift detected.

## Severity

Each group includes:

- `severity.rank`: numeric priority.
- `severity.label`: `critical`, `high`, `medium`, `low`, or `none`.
- `severity.reasons`: machine-readable reason codes.

Highest priority cases:

- same raw/research/TLDR but different score.
- same raw/research but different TLDR and score.
- same brand/version/lang with quadrant changes.
- any `persistence_drift`, because the stored columns no longer represent the scanner payload.

## Output Shape

Top-level:

- `schema_version`
- `generated_at`
- `db_path`
- `options`
- `sample_count`
- `repeated_group_count`
- `unstable_group_count`
- `groups`

Group:

- `group_key`
- `display_name`
- `sample_count`
- `group_dimensions`
- `created_days`
- `first_seen`
- `last_seen`
- `diagnosis_stage`
- `severity`
- `numeric_stats`
- `max_numeric_range`
- `changing_hashes`
- `changing_fields`
- `examples`

Example rows include stored scores, payload scores, quadrants, source run ids, and hashes for raw inputs, research pack, TLDR, SV9 components, and raw payload.
