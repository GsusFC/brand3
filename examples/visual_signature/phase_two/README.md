# Phase Two

Phase Two is the minimum human review loop for Phase One captures.

It joins reviewer decisions to the Phase One eligibility records and recomputes dataset eligibility only when the human review gate is satisfied.

## What Phase Two does

- loads Phase One eligibility records
- loads explicit human review records
- joins them by `capture_id`
- recomputes dataset eligibility with review gates applied
- preserves the original Phase One eligibility record
- writes reviewed eligibility separately

## What Phase Two does not do

- it does not add new perceptual concepts
- it does not expand taxonomy
- it does not train models
- it does not infer reviewer intent
- it does not change scoring
- it does not override raw evidence

## How reviews affect eligibility

A reviewer-required record can become eligible only when:

- `review_status` is `approved`
- `visually_supported` is `yes` or `partial`
- `unsupported_inference_present` is `false`
- `uncertainty_accepted` is `true` when uncertainty exists

If a review is missing, rejected, needs more evidence, or fails any gate above, the reviewed eligibility remains blocked.

## Generate

```bash
./.venv/bin/python scripts/visual_signature_phase_two_generate.py
```

This writes:

- `examples/visual_signature/phase_two/reviews/review_records.json`
- `examples/visual_signature/phase_two/manifests/phase_two_manifest.json`
- `examples/visual_signature/phase_two/records/`
- `examples/visual_signature/phase_two/exports/phase_two_reviewed_dataset_eligibility.jsonl`

## Validate

```bash
./.venv/bin/python scripts/visual_signature_phase_two_validate.py
```

Validation checks:

- review record schema validity
- reviewed eligibility schema validity
- manifest counts
- export JSONL validity

## Review fixture

The checked-in review fixture covers the five current Phase One captures and includes:

- approved
- rejected
- needs_more_evidence
- partial support

That fixture exists so the loop can be exercised end to end without changing any production behavior.
