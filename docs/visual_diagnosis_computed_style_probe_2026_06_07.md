# Visual Diagnosis Computed Style Probe - 2026-06-07

## Verdict

Computed-style snapshots are useful as a Context.dev replacement primitive, but
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

Recommended next step:

1. Change Visual Diagnosis Lab from source priority to source fusion.
2. Preserve `web_payload`, `computed_style_snapshot`, screenshot vision and Magnetism evidence together.
3. Add source-specific anti-pattern provenance.
4. Re-run the same four brands plus two visual-heavy brands.
5. Only consider promotion if anti-pattern changes become explainable instead of source-order dependent.

## Verification

```bash
./.venv/bin/python -m pytest \
  tests/test_visual_diagnosis.py \
  tests/test_visual_diagnosis_style_capture.py \
  -q
```

Result:

- `24 passed`
