# Visual Diagnosis Computed Style Probe - 2026-06-07

## Verdict

Computed-style snapshots are useful as a paid-provider replacement primitive, but
they are not enough to promote Visual Diagnosis beyond Lab.

The probe shows stable top-level diagnosis across four real local DB brands, but
anti-pattern attribution changes materially. This is useful evidence, not a
production-ready decision layer.

## Scope

Local DB:

- `data/brand3.sqlite3`

Audit runs selected:

- `217` - `www.netlify.com`
- `216` - `www.langchain.com`
- `215` - `elevenlabs.io`
- `212` - `www.sklum.com`

Local working directory:

- `/tmp/brand3_visual_diagnosis_db_probe`

Baseline manifest:

- `/tmp/brand3_visual_diagnosis_db_probe/manifest.before-computed.json`

Computed-style manifest:

- `/tmp/brand3_visual_diagnosis_db_probe/manifest.with-computed.json`

Commands:

```bash
./.venv/bin/python scripts/visual_diagnosis_lab.py \
  --manifest /tmp/brand3_visual_diagnosis_db_probe/manifest.before-computed.json \
  --output-root /tmp/brand3_visual_diagnosis_db_probe/lab_before

./.venv/bin/python scripts/visual_diagnosis_capture_computed_styles.py \
  --manifest /tmp/brand3_visual_diagnosis_db_probe/manifest.before-computed.json \
  --output-root /tmp/brand3_visual_diagnosis_db_probe/computed_styles

./.venv/bin/python scripts/visual_diagnosis_lab.py \
  --manifest /tmp/brand3_visual_diagnosis_db_probe/manifest.with-computed.json \
  --output-root /tmp/brand3_visual_diagnosis_db_probe/lab_with_computed_enriched
```

## Capture Result

Computed-style capture succeeded for all four brands.

| Brand | Elements | Colors | Snapshot |
| --- | ---: | ---: | --- |
| `www.netlify.com` | 80 | 12 | `/tmp/brand3_visual_diagnosis_db_probe/computed_styles/20260607T090109Z/www-netlify-com.computed-style.json` |
| `www.langchain.com` | 80 | 9 | `/tmp/brand3_visual_diagnosis_db_probe/computed_styles/20260607T090109Z/www-langchain-com.computed-style.json` |
| `elevenlabs.io` | 80 | 8 | `/tmp/brand3_visual_diagnosis_db_probe/computed_styles/20260607T090109Z/elevenlabs-io.computed-style.json` |
| `www.sklum.com` | 80 | 3 | `/tmp/brand3_visual_diagnosis_db_probe/computed_styles/20260607T090109Z/www-sklum-com.computed-style.json` |

## Diagnosis Comparison

| Brand | Visual identity | Baseline | Computed + screenshot | Anti-pattern change |
| --- | ---: | --- | --- | --- |
| `www.netlify.com` | 85 | `limited / developer_first / functionally_clear / high` | `limited / developer_first / functionally_clear / high` | `card_heavy_composition`, `flat_typographic_hierarchy`, `viewport_obstruction_login_wall` -> none |
| `www.langchain.com` | 95 | `limited / developer_first / functionally_clear / high` | `limited / developer_first / functionally_clear / high` | `card_heavy_composition`, `viewport_obstruction_modal` -> `card_heavy_composition`, `flat_typographic_hierarchy`, `viewport_obstruction_modal` |
| `elevenlabs.io` | 52 | `limited / ai_native / weak_or_inconsistent / high` | `limited / ai_native / weak_or_inconsistent / high` | `card_heavy_composition`, `generic_ai_aesthetic`, `visual_promise_mismatch`, `overused_gradient_palette`, `low_distinctiveness_hero`, `viewport_obstruction_modal` -> `visual_promise_mismatch`, `weak_cta_weight` |
| `www.sklum.com` | 95 | `limited / ecommerce_mass_market / commerce_clear / high` | `limited / ecommerce_mass_market / commerce_clear / high` | `card_heavy_composition`, `flat_typographic_hierarchy`, `viewport_obstruction_modal` -> `card_heavy_composition`, `weak_cta_weight`, `flat_typographic_hierarchy` |

## What This Proves

Computed-style evidence is strong enough to preserve:

- reference profile;
- identity read;
- confidence level;
- comparison with Magnetism `visual_identity`.

It also gives us a provider-free way to inspect:

- typography scale;
- colors;
- CTA presence;
- card/navigation/layout hints;
- rendered CSS rather than scraped HTML alone.

## What It Does Not Prove

It does not prove visual composition by itself.

The Netlify row is the warning case: the top-level read is stable, but the
obstruction anti-pattern disappears when computed styles become the primary
visual payload. This means computed styles should not replace screenshot vision
or obstruction diagnostics. They should be an additional evidence layer.

The ElevenLabs row is useful in the opposite direction: the weak identity read
survives the new evidence source because it is anchored by low Magnetism visual
identity and `visual_promise_mismatch`. That is the behavior we want.

## Decision

Keep computed-style capture in Lab.

Do not promote it to Brand Audit, Scanner, public reports, or scoring yet.

## Bundle Follow-up

After the first probe, the lab was changed from destructive source priority to
`visual-evidence-bundle-v1` fusion. The same four-brand manifest was rerun with
`web_payload`, `computed_style_snapshot` and screenshot evidence available.

Run inspected:

- `/tmp/brand3_visual_diagnosis_db_probe/lab_bundle_check/20260607T094301Z`

Generated chart-ready output:

- `/tmp/brand3_visual_diagnosis_db_probe/lab_bundle_check/20260607T094301Z/comparison.json`

Bundle result:

| Brand | Sources | Fusion notes | Identity read | Anti-patterns |
| --- | --- | --- | --- | --- |
| `www.netlify.com` | `computed_style`, `web_payload`, `screenshot_vision` | `computed_style_and_web_payload_fused`, `screenshot_vision_merged_into_fused_payload` | `functionally_clear` | `card_heavy_composition` |
| `www.langchain.com` | `computed_style`, `web_payload`, `screenshot_vision` | `computed_style_and_web_payload_fused`, `screenshot_vision_merged_into_fused_payload` | `functionally_clear` | `card_heavy_composition`, `flat_typographic_hierarchy`, `viewport_obstruction_modal` |
| `elevenlabs.io` | `computed_style`, `web_payload`, `screenshot_vision` | `computed_style_and_web_payload_fused`, `screenshot_vision_merged_into_fused_payload` | `weak_or_inconsistent` | `card_heavy_composition`, `visual_promise_mismatch` |
| `www.sklum.com` | `computed_style`, `web_payload`, `screenshot_vision` | `computed_style_and_web_payload_fused`, `screenshot_vision_merged_into_fused_payload` | `commerce_clear` | `card_heavy_composition`, `flat_typographic_hierarchy` |

This is a better operating model than source priority: the top-level reads stay
stable, and the source list/fusion notes are explicit enough for graphs and
human review. It still needs source-level anti-pattern provenance before any
promotion decision.

## Provenance Follow-up

The lab now emits `signal_provenance` in `summary.json` and `comparison.json`.
This explains each signal as `observed`, `inferred`, `conflicting` or
`weak_evidence`, with source attribution and confidence.

Run inspected:

- `/tmp/brand3_visual_diagnosis_db_probe/lab_provenance_check/20260607T095837Z`

Anti-pattern provenance from the four-brand probe:

| Brand | Signal | Sources | Evidence level | Confidence |
| --- | --- | --- | --- | --- |
| `www.netlify.com` | `card_heavy_composition` | `web_payload` | `observed` | `medium` |
| `www.langchain.com` | `card_heavy_composition` | `computed_style`, `web_payload` | `observed` | `high` |
| `www.langchain.com` | `flat_typographic_hierarchy` | `computed_style` | `observed` | `medium` |
| `www.langchain.com` | `viewport_obstruction_modal` | `screenshot_vision` | `observed` | `high` |
| `elevenlabs.io` | `card_heavy_composition` | `web_payload` | `observed` | `medium` |
| `elevenlabs.io` | `visual_promise_mismatch` | `magnetism` | `observed` | `high` |
| `www.sklum.com` | `card_heavy_composition` | `computed_style`, `web_payload` | `observed` | `high` |
| `www.sklum.com` | `flat_typographic_hierarchy` | `computed_style`, `web_payload` | `observed` | `high` |

This is the first result that is suitable for charting by source. It also shows
why provenance matters: `visual_promise_mismatch` is not a visual heuristic, it
comes from Magnetism; `viewport_obstruction_modal` is not a CSS/computed-style
finding, it comes from screenshot vision.

Recommended next step:

1. Re-run the same four brands plus two visual-heavy brands.
2. Add human review notes to `comparison.json`.
3. Only consider promotion if anti-pattern changes become explainable instead of source-order dependent.

## Verification

```bash
./.venv/bin/python -m pytest \
  tests/test_visual_diagnosis.py \
  tests/test_visual_diagnosis_style_capture.py \
  -q
```

Result:

- `68 passed, 5 subtests passed`
