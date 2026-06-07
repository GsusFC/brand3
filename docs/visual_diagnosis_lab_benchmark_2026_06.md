# Visual Diagnosis Lab Benchmark - June 2026

## Verdict

The lab-only `VisualDiagnosis` prototype is useful enough to continue, but not ready for scoring or public report integration.

The strongest signal from this first benchmark is not the profile labels. It is the evidence boundary: the prototype correctly refuses to diagnose brands when no usable screenshot evidence is available.

That matters for Brand3 because it separates:

- weak visual identity;
- weak or missing visual evidence;
- unsupported visual inference.

## Scope

This benchmark uses only local fixtures and local calibration outputs. It does not call the network, LLMs, providers, Scanner, Brand Audit, or production storage.

Manifest:

- `examples/visual_diagnosis_lab/calibration_manifest.json`

Command:

```bash
./.venv/bin/python scripts/visual_diagnosis_lab.py \
  --manifest examples/visual_diagnosis_lab/calibration_manifest.json \
  --output-root /tmp/brand3_visual_diagnosis_lab
```

Latest run inspected:

- `/tmp/brand3_visual_diagnosis_lab/20260607T065417Z`

## Result Summary

| Brand | Status | Profile | Identity read | Confidence | Anti-patterns |
| --- | --- | --- | --- | --- | --- |
| Hermes | unavailable | unknown | not_evaluable | low | capture_not_evaluable |
| Linear | usable | developer_first | functionally_clear | high | - |
| OpenAI | limited | ai_native | coherent_but_generic | high | card_heavy_composition, flat_typographic_hierarchy |
| The Verge | usable | editorial_media | editorially_coherent | high | card_heavy_composition, flat_typographic_hierarchy |
| Allbirds | usable | ecommerce_mass_market | commerce_clear | high | card_heavy_composition |
| Joe's Plumbing NYC | unavailable | unknown | not_evaluable | low | capture_not_evaluable |
| Stripe Docs | usable | developer_first | functionally_clear | high | flat_typographic_hierarchy |
| Headspace | usable | wellness_lifestyle | emotionally_coherent | high | card_heavy_composition, flat_typographic_hierarchy |
| Notion | usable | template_saas | polished_but_undifferentiated | high | template_saas_layout, card_heavy_composition, flat_typographic_hierarchy, low_distinctiveness_hero |
| A24 | unavailable | unknown | not_evaluable | low | capture_not_evaluable |

## What Worked

### Evidence Gating

The prototype does not infer a visual diagnosis when screenshot evidence is missing.

This is correct for:

- Hermes;
- Joe's Plumbing NYC;
- A24.

Hermes now has a local screenshot reference, but the Visual Signature payload is still `not_interpretable`. The prototype correctly refuses to diagnose from screenshot presence alone because the deterministic mapper does not read pixels directly.

Joe's Plumbing NYC and A24 still lack usable screenshot-backed visual analysis in this benchmark. The output `not_evaluable` is safer than calling them weak.

### Source Reconciliation

The benchmark exposed and fixed a useful issue: Visual Signature calibration payloads can contain the limitation `screenshot_not_available` even when Brand3 separately provides `screenshot_capture`.

`VisualDiagnosis` now reconciles this:

- if Brand3 screenshot capture exists, stale `screenshot_not_available` from Visual Signature is suppressed;
- screenshot evidence can come from `raw_inputs:screenshot_capture`;
- Visual Signature remains an evidence source, not the only source.

### Category Token Matching

The first real run exposed a bad category heuristic: `retail` was classified as AI-native because it contains the character sequence `ai`.

The mapper now uses token-aware category matching. Regression coverage was added.

### Profile Labels

For the evaluable cases, profile assignment is directionally sensible:

- Linear -> `developer_first`
- OpenAI -> `ai_native`
- The Verge -> `editorial_media`
- Allbirds -> `ecommerce_mass_market`
- Headspace -> `wellness_lifestyle`
- Stripe Docs -> `developer_first`
- Notion -> `template_saas`

This is enough for lab exploration.

## What Still Needs Work

### Anti-pattern Precision

`card_heavy_composition` and `flat_typographic_hierarchy` are still coarse.

They are useful as early warning labels, but they need refinement before any report-facing use:

- editorial cards are not automatically a negative anti-pattern;
- ecommerce grids often need cards;
- unknown or sparse typography evidence should become a limitation, not a defect;
- category-specific thresholds are needed.

### Missing Screenshot Coverage

Three benchmark cases could not be visually diagnosed.

This is not a failure of the diagnosis contract. It shows that any future visual diagnosis depends first on reliable screenshot capture and interpretable visual analysis.

Priority cases to fix next:

- A24;
- one local service brand with a valid live domain.
- Hermes, but only after regenerating interpretable Visual Signature evidence from the existing viewport screenshot.

### No Human Judgment Yet

This benchmark does not include human review notes. Without human comparison, we can validate contract behavior but not claim improved design judgment.

### No Magnetism Comparison Yet

The original benchmark used placeholder/local `visual_identity` values in the manifest.

The lab runner now supports real Magnetism payloads through:

- inline `magnetism_payload`;
- `magnetism_payload_path`.

It can extract coherence evidence from known local shapes:

- Scanner methodology payloads: `methodology.score_breakdown.coherence.visual_identity`;
- normalized local/deploy comparison payloads: `scanner.score_coherence_breakdown.visual_identity`;
- batch rows with `coherence_score`, as a fallback labelled `coherence_score_fallback`.

The next useful comparison should use current local Scanner/Audit outputs, not historical batch fallbacks.

## Decision

Continue the lab, but keep it blocked from scoring and public reports.

Recommended next step:

1. Generate or attach reliable screenshots and interpretable visual evidence for the currently non-evaluable cases.
2. Run the same manifest again.
3. Add a short human note per brand.
4. Compare against real Magnetism `visual_identity` breakdowns by adding `magnetism_payload_path` per manifest row.
5. Only then decide whether `VisualDiagnosis` becomes report explanation, Scanner diagnostics, or remains lab-only.

## Current Technical Status

Implemented:

- `src/visual_diagnosis/models.py`
- `src/visual_diagnosis/mapper.py`
- `scripts/visual_diagnosis_lab.py`
- `examples/visual_diagnosis_lab/calibration_manifest.json`
- `tests/test_visual_diagnosis.py`

Supported lab manifest fields:

- `brand_name`
- `website_url`
- `category_hint`
- `visual_signature` or `visual_signature_path`
- `screenshot_capture` or `screenshot_capture_path`
- `coherence_breakdown` or `coherence_breakdown_path`
- `magnetism_payload` or `magnetism_payload_path`

Validated:

```bash
./.venv/bin/python -m pytest tests/test_visual_diagnosis.py -q
```

Result:

- `10 passed`

Broader related subset:

```bash
./.venv/bin/python -m pytest \
  tests/test_visual_diagnosis.py \
  tests/test_visual_signature.py \
  tests/test_visual_signature_vision.py \
  tests/test_visual_signature_multimodal.py \
  tests/test_visual_signature_phase_zero.py \
  tests/test_visual_signature_phase_one.py \
  tests/test_visual_signature_phase_two.py \
  tests/test_web_visual_signature_routes.py -q
```

Prior result after the first prototype:

- `70 passed, 5 subtests passed`

## Bottom Line

The prototype is already useful as a guardrail: it prevents Brand3 from confusing unavailable visual evidence with weak visual identity.

The next improvement is not more taste vocabulary. It is better visual evidence coverage and a real comparison against Magnetism outputs.
