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

- `/tmp/brand3_visual_diagnosis_lab/20260607T073853Z`

## Result Summary

| Brand | Status | Profile | Identity read | Visual identity | Brand fit | Confidence | Anti-patterns |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| Hermes | unavailable | unknown | not_evaluable | - | unknown | low | visual_analysis_not_interpretable |
| Linear | usable | developer_first | functionally_clear | 82 | medium | high | - |
| OpenAI | limited | ai_native | coherent_but_generic | 80 | medium | high | card_heavy_composition, flat_typographic_hierarchy |
| The Verge | usable | editorial_media | editorially_coherent | 90 | high | high | card_heavy_composition, flat_typographic_hierarchy |
| Allbirds | usable | ecommerce_mass_market | commerce_clear | 76 | medium | high | card_heavy_composition |
| Joe's Plumbing NYC | unavailable | unknown | not_evaluable | - | unknown | low | capture_not_evaluable |
| Stripe Docs | usable | developer_first | functionally_clear | 78 | medium | high | flat_typographic_hierarchy |
| Headspace | usable | wellness_lifestyle | emotionally_coherent | 84 | medium | high | card_heavy_composition, flat_typographic_hierarchy |
| Notion | usable | template_saas | polished_but_undifferentiated | 82 | medium | high | template_saas_layout, card_heavy_composition, flat_typographic_hierarchy, low_distinctiveness_hero |
| A24 | unavailable | unknown | not_evaluable | 88 | unknown | low | capture_not_evaluable |

## What Worked

### Evidence Gating

The prototype does not infer a visual diagnosis when screenshot evidence is missing.

This is correct for:

- Hermes;
- Joe's Plumbing NYC;
- A24.

Hermes now has a local screenshot reference, but the Visual Signature payload is still `not_interpretable`. The prototype correctly refuses to diagnose from screenshot presence alone because the deterministic mapper does not read pixels directly. It now labels this boundary as `visual_analysis_not_interpretable`, not as a capture failure.

Joe's Plumbing NYC and A24 still lack usable screenshot-backed visual analysis in this benchmark. The output `not_evaluable` is safer than calling them weak.

### Source Reconciliation

The benchmark exposed and fixed a useful issue: Visual Signature calibration payloads can contain the limitation `screenshot_not_available` even when Brand3 separately provides `screenshot_capture`.

`VisualDiagnosis` now reconciles this:

- if Brand3 screenshot capture exists, stale `screenshot_not_available` from Visual Signature is suppressed;
- screenshot evidence can come from `raw_inputs:screenshot_capture`;
- Visual Signature remains an evidence source, not the only source.

### Magnetism Comparison Surface

The lab summary now shows `visual_identity` and Brand3 `brand_fit` side by side.

This immediately exposes useful robustness questions. A24 has a placeholder/local `visual_identity` value in the manifest, but `VisualDiagnosis` returns `not_evaluable` because the visual evidence is unavailable. That is the correct tension to surface before any scoring integration.

### Real DB Smoke Test

A local DB smoke test used four recent Brand3 runs from `data/brand3.sqlite3`:

- LangChain: screenshot capture + historical external visual candidates + Magnetism payload.
- Netlify: raw web payload + screenshot capture + local screenshot vision + Magnetism payload.
- ElevenLabs: raw web payload + screenshot capture + local screenshot vision + Magnetism payload.
- Sklum: raw web payload + screenshot capture + local screenshot vision + Magnetism payload.

Latest run inspected:

- `/tmp/brand3_visual_diagnosis_real_runs/20260607T081444Z`

| Brand | Status | Profile | Identity read | Visual identity | Brand fit | Confidence | Anti-patterns |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| www.langchain.com | limited | developer_first | functionally_clear | 95 | high | high | card_heavy_composition |
| www.netlify.com | limited | developer_first | functionally_clear | 85 | high | high | card_heavy_composition, flat_typographic_hierarchy, viewport_obstruction_login_wall |
| elevenlabs.io | limited | ai_native | weak_or_inconsistent | 52 | low | high | card_heavy_composition, generic_ai_aesthetic, visual_promise_mismatch, overused_gradient_palette, low_distinctiveness_hero, viewport_obstruction_modal |
| www.sklum.com | limited | ecommerce_mass_market | commerce_clear | 95 | high | high | card_heavy_composition, flat_typographic_hierarchy, viewport_obstruction_modal |

This is the strongest result from the real-data pass: current Scanner/Audit screenshots prove capture availability, but they do not automatically provide semantic visual diagnosis. LangChain is informed by historical external visual candidates. Netlify, ElevenLabs and Sklum become limited diagnoses when the manifest combines `web_payload_path` with local screenshot vision via `derive_visual_signature_from_screenshot: true`.

The ElevenLabs row is the useful negative control: Magnetism `visual_identity` is low, and Visual Diagnosis surfaces that as `weak_or_inconsistent` through `visual_promise_mismatch`. Netlify and Sklum read as functionally or commercially coherent from raw web evidence, screenshot shape, category and Magnetism fit, but they remain `limited` because this is still deterministic evidence, not a full multimodal or human design review. Viewport obstruction labels are heuristics and should be treated as diagnostic flags, not final design judgments.

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

### Human Review Notes

The lab can now carry human review notes through the run outputs. This is
deliberately non-scoring metadata: human review helps benchmark judgment quality,
but it does not alter `VisualDiagnosis`.

Manifest rows can include:

- inline `human_review`;
- `human_review_path`.

Example files:

- `examples/visual_diagnosis_lab/human_review_manifest.example.json`
- `examples/visual_diagnosis_lab/reviews/example-review.json`

First six-brand review probe:

- `docs/visual_diagnosis_human_review_probe_2026_06_07.md`

Second eight-brand calibration probe:

- `docs/visual_diagnosis_calibration_probe_2026_06_07.md`

Clean-capture dismissal probe:

- `docs/visual_diagnosis_clean_capture_probe_2026_06_07.md`

Allowed review fields are `reviewer`, `reviewed_at`, `verdict`, `profile_fit`,
`identity_read_fit`, `notes`, `disagreements` and `recommended_changes`.
Unknown fields are ignored so review payloads do not become an accidental
execution contract.

### Page State Notes

The lab can also carry page-state notes through `summary.json` and
`comparison.json`. This is lab-only metadata for separating capture quality from
visual identity.

Manifest rows can include:

- inline `page_state`;
- `page_state_path`.

Allowed page-state fields are `status`, `obstructions`, `capture_quality`,
`confidence`, `source` and `notes`.

Recommended `status` values:

- `clean`
- `cookie_obstructed`
- `privacy_obstructed`
- `location_gated`
- `bot_check_blocked`
- `modal_obstructed`
- `campaign_overlay`
- `unknown`

Recommended obstruction values include `cookie_banner`, `privacy_notice`,
`location_gate`, `cloudflare_check`, `modal`, `announcement_bar` and
`campaign_overlay`.

The page-state contract exists because the first reviewed probes showed that
several rows were not bad visual systems; they were contaminated captures.

### Magnetism Comparison

The original benchmark used placeholder/local `visual_identity` values in the manifest. The current lab also supports real Magnetism payloads and historical external visual candidate summaries for local DB smoke tests.

The lab runner now supports real Magnetism payloads through:

- inline `magnetism_payload`;
- `magnetism_payload_path`.

The lab now writes two run-level outputs:

- `summary.json` and `summary.md` for review;
- `comparison.json` for charts, source comparison and longitudinal analysis.

`comparison.json` uses `visual-diagnosis-comparison-v1` and includes source
comparison rows per brand, available source types, fusion notes, anti-patterns,
limitations, evidence refs, `signal_provenance` and optional `human_review`
notes.

`signal_provenance` attributes anti-patterns, positives, negatives and
limitations to sources such as `computed_style`, `web_payload`,
`screenshot_vision` and `magnetism`. Historical
`external_candidate_summary_legacy` evidence is always low-confidence by
policy.

It can read historical external visual candidate evidence through:

- inline `external_candidate_summary_legacy`;
- `external_candidate_summary_legacy_path`.

`contextdev_candidate_summary` remains a deprecated manifest alias only for old
local DB fixtures. It is not an active provider path.

It can derive a lab-only visual payload from an existing local screenshot when a manifest row sets:

- `derive_visual_signature_from_screenshot: true`.

It can derive DOM/CSS visual evidence from existing local web inputs through:

- inline `web_payload`;
- `web_payload_path`.

It can also consume browser computed-style snapshots through:

- inline `computed_style_snapshot`;
- `computed_style_snapshot_path`.

Snapshots can be generated from a local browser pass with:

```bash
./.venv/bin/python scripts/visual_diagnosis_capture_computed_styles.py \
  --manifest examples/visual_diagnosis_lab/calibration_manifest.json \
  --output-root /tmp/brand3_visual_diagnosis_computed_styles
```

This is the first paid-provider replacement primitive: the lab can read local
browser-observed typography, colors, layout hints and component signals without
calling a visual enrichment provider or an LLM. The output remains `limited`
when no screenshot exists because computed styles explain the rendered system
but do not prove visual composition by themselves.

When a manifest row also includes `screenshot_capture` and sets
`derive_visual_signature_from_screenshot: true`, the lab enriches computed-style
evidence with local screenshot vision. This keeps the evidence boundary explicit:
computed styles explain CSS/DOM presentation, while screenshots contribute
viewport quality, palette/composition and obstruction evidence.

When `web_payload`, `computed_style_snapshot` and screenshot evidence are all
available, the lab builds a `visual-evidence-bundle-v1` and fuses the sources
instead of letting one source silently replace another. This is still lab-only:
the bundle is designed to expose source disagreement, not to become scoring.

It can extract coherence evidence from known local shapes:

- Scanner methodology payloads: `methodology.score_breakdown.coherence.visual_identity`;
- normalized local/deploy comparison payloads: `scanner.score_coherence_breakdown.visual_identity`;
- batch rows with `coherence_score`, as a fallback labelled `coherence_score_fallback`.

The current local DB smoke test confirms that Scanner/Audit outputs are useful, but screenshot capture and Magnetism scores are insufficient on their own. Visual Diagnosis needs interpretable visual evidence from Visual Signature, raw web DOM/CSS, local computed styles, local screenshot vision, or a future multimodal pass.

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
- `web_payload` or `web_payload_path`
- `computed_style_snapshot` or `computed_style_snapshot_path`
- `screenshot_capture` or `screenshot_capture_path`
- `coherence_breakdown` or `coherence_breakdown_path`
- `magnetism_payload` or `magnetism_payload_path`
- `external_candidate_summary_legacy` or `external_candidate_summary_legacy_path`
- `human_review` or `human_review_path`
- `page_state` or `page_state_path`
- deprecated legacy alias: `contextdev_candidate_summary` or `contextdev_candidate_summary_path`
- `derive_visual_signature_from_screenshot`

When a `screenshot_capture` row includes both raw and clean-attempt artifacts,
the Lab now writes a `clean_capture_decision` object into `summary.json` and
`comparison.json`.

Decision policy:

- `use_clean_attempt`: only when dismissal clearly succeeds or obstruction
  severity / coverage materially improves.
- `keep_raw_with_clean_supplement`: clean attempt improved some metrics but not
  enough to replace raw evidence.
- `keep_raw_clean_degraded`: clean attempt worsened obstruction or first
  impression metrics.
- `keep_raw_no_material_improvement`: clean attempt did not materially improve
  the capture.
- `raw_only`: no clean attempt exists or no safe mutation was available.

The raw screenshot remains the default evidence. A clean attempt is used for
diagnosis only when `clean_capture_decision.use_clean_for_diagnosis` is `true`.
The decision contract lives in `src/visual_diagnosis/clean_capture.py` and is
shared by the Lab and the capture-side dismissal audit to avoid policy drift.

Validated:

```bash
./.venv/bin/python -m pytest tests/test_visual_diagnosis.py -q
```

Result:

- `28 passed`

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

Current result:

- `70 passed, 5 subtests passed` for the current visual diagnosis/provenance subset.

## Bottom Line

The prototype is already useful as a guardrail: it prevents Brand3 from confusing unavailable visual evidence with weak visual identity.

The next improvement is not more taste vocabulary. It is better visual evidence
coverage and real human review notes on the comparison rows, so we can separate
diagnosis quality from source coverage.

The six-brand provenance probe confirms this: A24 and Hermes can be directionally
classified from computed styles, but they stay `limited` until screenshot vision
and Magnetism evidence are present.
