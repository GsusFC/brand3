# Visual Signature Review Viewer

This folder contains offline human review tooling for Visual Signature
multimodal annotation calibration. It is evidence-only and does not affect
Brand3 scoring, rubric dimensions, production reports, or production UI.

## Inputs

- `review_sample.json`: sampled annotation cases for review.
- Annotation overlays from `../mock_first_pass/`.
- Viewport screenshots referenced by each annotation payload.

## Run The Local Viewer

From the project root:

```bash
./.venv/bin/python scripts/visual_signature_review_viewer.py
```

Then open:

```text
http://127.0.0.1:8765
```

The viewer defaults to English and includes an `en` / `es` selector. Open the
Spanish version directly with:

```text
http://127.0.0.1:8765/?lang=es
```

Optional paths:

```bash
./.venv/bin/python scripts/visual_signature_review_viewer.py \
  --sample examples/visual_signature/calibration_corpus/annotations/multimodal/review/review_sample.json \
  --records examples/visual_signature/calibration_corpus/annotations/multimodal/review/review_records.json \
  --port 8765
```

## Review Form

Each case shows:

- brand name
- website URL
- expected category
- sample reason
- viewport screenshot
- annotation targets and labels
- confidence per target
- evidence and limitations

The form records:

- `visually_supported`: `yes`, `partial`, `no`
- `useful`: `useful`, `neutral`, `not_useful`
- `hallucination_or_overreach`: `no`, `yes`
- `most_reliable_target`
- `most_confusing_target`
- `adds_value_beyond_heuristics`: `yes`, `no`, `unsure`
- `reviewer_notes`

Reviews are appended to:

```text
examples/visual_signature/calibration_corpus/annotations/multimodal/review/review_records.json
```

## Boundary

This viewer is a local calibration tool. Do not include it in the production
FastAPI app, public routes, scoring pipeline, rubric dimensions, reports, or UI.
