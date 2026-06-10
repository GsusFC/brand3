# Brand3 Scoring Replay Audit

This document defines the replay integrity check for persisted Brand3 runs.

## Purpose

The replay audit recomputes a run's score from the persisted feature rows and the current scoring configuration, then compares:

- persisted features
- persisted dimension scores
- persisted composite score
- recomputed dimension scores
- recomputed composite score
- persisted scoring fingerprint
- current scoring fingerprint
- persisted result artifact JSON vs DB snapshot

The audit does not change scoring logic, phase behavior, or persisted schema.

## Report format

```json
{
  "run_id": 123,
  "score_integrity": "valid",
  "persisted_composite": 72,
  "recomputed_composite": 72,
  "difference": 0,
  "fingerprint_status": "match",
  "issues": [],
  "recommended_action": "none"
}
```

Additional diagnostic fields are returned by the helper for review and debugging:

- `persisted_scoring_state_fingerprint`
- `current_scoring_state_fingerprint`
- `persisted_features`
- `persisted_dimension_scores`
- `artifact_dimension_scores`
- `recomputed_dimension_scores`
- `dimensions`

## Score integrity statuses

- `valid`
  - persisted and recomputed scores match
  - the persisted fingerprint matches the current scoring configuration
  - the result artifact matches the DB snapshot

- `drift_detected`
  - persisted features changed without a matching score update
  - persisted composite differs from recomputed composite
  - artifact JSON differs from the DB snapshot
  - scoring fingerprint is stale

- `unverifiable`
  - snapshot cannot be loaded
  - result artifact is missing or invalid
  - fingerprint is missing
  - the run cannot be replayed safely from persisted data alone

## Fingerprint statuses

- `match`
  - the persisted fingerprint matches the current scoring configuration

- `mismatch`
  - the persisted fingerprint no longer matches the current code/config

- `missing`
  - no persisted fingerprint was available

## Issue types

Common issue codes produced by the replay audit:

- `persisted_composite_mismatch`
- `persisted_vs_recomputed_dimension_mismatch`
- `artifact_composite_mismatch`
- `artifact_vs_db_dimension_mismatch`
- `fingerprint_mismatch`
- `fingerprint_missing`
- `result_artifact_missing`
- `result_artifact_invalid_json`
- `neutral_fallback_dimension`

`neutral_fallback_dimension` is informational, not a drift error. It is emitted when a dimension score is `50.0` and the replay sees no persisted features for that dimension.

## Recommended action

- `none`
  - replay is valid and no interpretive warnings were produced

- `rerun`
  - score drift was detected but the current fingerprint still matches

- `config_check`
  - the fingerprint is missing, stale, or the artifact cannot be verified

- `human_review`
  - replay is valid, but one or more neutral-fallback dimensions were observed

## Drift classification

`build_score_replay_audit()` also classifies drift more precisely so fingerprint-only legacy mismatches do not get confused with score/data drift:

- `none`
  - persisted scores, recomputed scores, and the fingerprint all agree

- `fingerprint_only_mismatch`
  - persisted scores still match replayed scores, but the stored scoring fingerprint no longer matches the current config
  - this is a config provenance issue, not score drift

- `feature_score_mismatch`
  - one or more persisted dimension scores differ from recomputed scores
  - this is real score drift

- `artifact_mismatch`
  - the persisted result artifact differs from the DB snapshot, but persisted score values still match replay
  - this is an artifact/output consistency issue, not necessarily a scoring error

- `score_data_mismatch`
  - persisted score values differ from replayed scores
  - this is real score drift and should be treated as a rerun candidate

- `unverifiable`
  - the run cannot be replayed safely from persisted data alone

## How to use it

Call `build_score_replay_audit(store, run_id)` from `src/scoring/replay.py`.

Example:

```python
from src.scoring.replay import build_score_replay_audit
from src.storage.sqlite_store import SQLiteStore

store = SQLiteStore("data/brand3.sqlite3")
report = build_score_replay_audit(store, run_id=42)
```

## What this check does not do

- It does not redesign scoring.
- It does not mutate persisted data.
- It does not change Phase Zero, Phase One, or Phase Two.
- It does not replace the report renderer.
