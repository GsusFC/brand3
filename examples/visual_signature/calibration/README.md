# Visual Signature Calibration

This folder contains evidence-only calibration artifacts that compare machine
perception claims against reviewed outcomes.

What it is:
- a join layer for Phase One / Phase Two records
- a calibration record set with explicit agreement and uncertainty states
- a summary of claim alignment by category and source
- a coherent bundle with `calibration_records.json`, `calibration_summary.json`,
  `calibration_summary.md`, and `calibration_manifest.json`

What it is not:
- scoring input
- rubric logic
- model training data
- production reporting
- UI behavior

Inputs:
- `examples/visual_signature/phase_one/`
- `examples/visual_signature/phase_two/reviews/review_records.json`
- `examples/visual_signature/screenshots/capture_manifest.json`
- `examples/visual_signature/screenshots/dismissal_audit.json`
- `examples/visual_signature/calibration_brands.json`

Generate:

```bash
./.venv/bin/python scripts/visual_signature_calibration.py
```

Validate:

```bash
./.venv/bin/python scripts/visual_signature_calibration_validate.py
```

Output files:
- `calibration_records.json`
- `calibration_summary.json`
- `calibration_summary.md`
- `calibration_manifest.json`

Readiness gate:

```bash
./.venv/bin/python scripts/visual_signature_calibration_readiness.py
```

Readiness outputs:
- `calibration_readiness.json`
- `calibration_readiness.md`
- `calibration_governance_checkpoint.md`

What the readiness gate does:
- reads the hardened calibration bundle
- reads the calibration corpus manifest when available
- returns `ready` or `not_ready`
- reports explicit block reasons for broader corpus use
- evaluates the `broader_corpus_use` scope by default

What it does not do:
- scoring
- rubric changes
- production UI
- production reports
- capture behavior
- taxonomy expansion

Bundle metadata:
- `calibration_run_id`
- `generated_at`
- `source_artifact_refs`
- `source_artifact_hashes`
- `record_count`
- `summary_count_consistency`
- `schema_versions`

Manifest metadata:
- generated files and file hashes
- source roots
- validation status

Rules:
- evidence-only
- no scoring impact
- no rubric impact
- no production UI/report impact
- missing review becomes `insufficient_review`
- unclear review becomes `unresolved`
- high-confidence contradiction is flagged `overconfident`
- low-confidence confirmation is flagged `underconfident`
- raw evidence and lineage are preserved in the records

Readiness rules:
- `ready` requires the bundle validation to pass
- `ready` requires enough claims, reviewed claims, category depth, and confidence spread
- `not_ready` is expected for the current small bundle
- `ready` / `not_ready` only describe the evaluated scope, which defaults to `broader_corpus_use`
- this does not imply production readiness, scoring readiness, runtime readiness, provider-pilot readiness, or model-training readiness
- unsupported scopes are not silently mapped to broader corpus thresholds

Scope options:
- `broader_corpus_use`
- `provider_pilot_use`
- `human_review_scaling`
- `production_runtime`
- `scoring_integration`
- `model_training`

Governance checkpoint:
- `calibration_governance_checkpoint.md` documents the validated bundle,
  the reliability report, and the current scope-aware readiness state.
