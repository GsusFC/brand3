# Phase One

Phase One connects real Visual Signature capture outputs to the Phase Zero contract.

## What Phase One does

- reads existing capture outputs from `examples/visual_signature/screenshots/`
- normalizes them into Phase Zero records
- writes validated records to `examples/visual_signature/phase_one/`
- preserves raw evidence, mutation lineage, and export eligibility boundaries

## What Phase One does not do

- it does not expand the taxonomy
- it does not add new perceptual concepts
- it does not train models
- it does not make perception smarter
- it does not change scoring behavior
- it does not mutate production UI or reports

## Input mapping

Phase One reads the capture manifest and dismissal audit, then maps the existing fields into Phase Zero records:

- `raw_screenshot_path` -> raw evidence refs
- `page_url` / `website_url` -> record URLs
- `brand_name` -> record brand identity
- `viewport_width` / `viewport_height` -> viewport metadata
- `captured_at` -> record timestamp
- `perceptual_transitions` -> transition records
- `mutation_audit` -> mutation audit records when present
- `before_obstruction` / `raw_viewport_metrics` -> observation values and confidence

Raw evidence remains primary. Clean attempts are supplemental only.

One real-run normalization is intentional:

- the capture flow may emit `low_confidence_obstruction`
- Phase Zero keeps the transition taxonomy small, so Phase One serializes that case as `human_review_required`
- the original source reason is preserved in transition notes

## Generate

```bash
./.venv/bin/python scripts/visual_signature_phase_one_generate.py
```

This writes:

- `examples/visual_signature/phase_one/records/`
- `examples/visual_signature/phase_one/manifests/`
- `examples/visual_signature/phase_one/exports/`

## Validate

```bash
./.venv/bin/python scripts/visual_signature_phase_one_validate.py
```

Validation checks:

- Phase Zero schema validity
- registry and record contract compliance
- append-only lineage preservation
- export eligibility gating

## Add a new observation safely

1. Add the smallest possible registry entry in Phase Zero.
2. Add a fixture record that uses only that registered key.
3. Run Phase Zero validation.
4. Run Phase One generation.
5. Confirm the new record passes validation before adding any export rule.

Do not add ad hoc keys in Phase One. Phase One only consumes the Phase Zero contract.

## Eligibility

Phase One uses Phase Zero eligibility rules.

A record is not exportable when:

- raw evidence is missing
- mutation lineage is missing
- unsupported inference is present
- reviewer required is true and review is incomplete
- confidence is below the threshold

`REVIEW_REQUIRED_STATE` is not exportable until reviewed.

`not_interpretable` is a valid result and is not treated as a weak brand judgment.
