# Visual Diagnosis Calibration Probe - 2026-06-07

## Verdict

The second Visual Diagnosis probe confirms that the Lab can classify broad
brand/profile direction, but it is not ready for product scoring.

The main blocker is not vocabulary or provider depth. The blocker is capture
state: bot checks, cookie banners, location gates and campaign overlays can
pollute visual diagnosis unless they are represented as first-class evidence.

## Scope

This probe used 8 calibration brands with:

- existing Visual Signature payloads;
- local viewport screenshots from the calibration corpus;
- live computed-style snapshots captured on 2026-06-07;
- human review notes written as `human_review_path` fixtures.

Input manifest:

- `/tmp/brand3_visual_diagnosis_calibration_probe/manifest.with-human-review.json`

Output:

- `/tmp/brand3_visual_diagnosis_calibration_probe/lab_human_review/20260607T121021Z/comparison.json`

Computed-style capture:

- `/tmp/brand3_visual_diagnosis_calibration_probe/computed_styles/20260607T120453Z/capture_manifest.json`

The Lab run emitted the known local Python `hashlib` warnings for `blake2b` and
`blake2s`, but completed successfully.

## Brands

| Brand | Sources | Diagnosis read | Human verdict | Identity fit |
| --- | --- | --- | --- | --- |
| Linear | `visual_signature`, `computed_style`, `screenshot_vision` | `polished_but_undifferentiated` | `diagnosis_too_harsh` | partial |
| OpenAI | `visual_signature`, `computed_style`, `screenshot_vision` | `coherent_but_generic` | `capture_blocked` | no |
| The Verge | `visual_signature`, `computed_style`, `screenshot_vision` | `editorially_coherent` | `useful_but_obstructed` | yes |
| Allbirds | `visual_signature`, `computed_style`, `screenshot_vision` | `commerce_clear` | `useful_but_obstructed` | partial |
| Stripe Docs | `visual_signature`, `computed_style`, `screenshot_vision` | `functionally_clear` | `directionally_useful` | yes |
| Headspace | `visual_signature`, `computed_style`, `screenshot_vision` | `emotionally_coherent` | `directionally_useful_but_obstructed` | yes |
| Notion | `visual_signature`, `computed_style`, `screenshot_vision` | `polished_but_undifferentiated` | `partially_useful` | partial |
| Le Labo | `visual_signature`, `computed_style`, `screenshot_vision` | `coherent_but_generic` | `diagnosis_too_generic` | partial |

Aggregates:

- `profile_fit = yes`: 7/8
- `profile_fit = unknown`: 1/8
- `identity_read_fit = yes`: 3/8
- `identity_read_fit = partial`: 4/8
- `identity_read_fit = no`: 1/8
- all 8 rows had `visual_signature + computed_style + screenshot_vision`

## Findings

### Broad profile reads are useful

The Lab correctly points most rows toward a plausible broad read:

- The Verge as editorial;
- Allbirds as commerce;
- Stripe Docs as functional developer documentation;
- Headspace as emotional/wellness;
- Notion as template-like SaaS.

This is enough for Lab calibration and comparison charts.

### Identity reads are not robust enough

Only 3/8 rows were accepted as a clean identity read by human review. The failed
or partial rows are not random:

- OpenAI is a Cloudflare bot-check screenshot.
- Allbirds has a shipping selector and cookie banner.
- The Verge has a large privacy notice.
- Headspace has a cookie dialog.
- Notion has a cookie overlay and campaign-specific hero.
- Le Labo has a location gate and cookie banner.

This means the Lab needs explicit page-state evidence before any scoring
integration.

### Some anti-patterns are category-sensitive

`flat_typographic_hierarchy` is not automatically bad for documentation pages.
`card_heavy_composition` is not automatically bad for ecommerce or wellness
pages. `template_saas_layout` can describe a common pattern without proving weak
identity.

The current comparison rows are useful because `signal_provenance` shows where
these signals came from, but the severity still needs human-reviewed thresholds.

### Visual Signature remains canonical in this path

When a manifest includes an existing `visual_signature_path`, the bundle uses
that payload as canonical. Computed styles and screenshot vision appear as
available sources, but they do not override the canonical Visual Signature
payload.

That is acceptable for Lab comparison, but it means this probe should not be
interpreted as a fully fused multimodal read.

## Decision

Keep Visual Diagnosis Lab-only.

The next implementation should not tune taste heuristics directly. It should add
a Lab-only page-state/capture-quality layer that can mark rows as:

- clean viewport;
- cookie/privacy obstructed;
- location gated;
- bot-check blocked;
- modal obstructed;
- campaign/announcement overlay present.

Only after this layer exists should we compare anti-pattern severity across
categories.

## Review Fixtures

- `examples/visual_diagnosis_lab/reviews/calibration_probe/linear.json`
- `examples/visual_diagnosis_lab/reviews/calibration_probe/openai.json`
- `examples/visual_diagnosis_lab/reviews/calibration_probe/the-verge.json`
- `examples/visual_diagnosis_lab/reviews/calibration_probe/allbirds.json`
- `examples/visual_diagnosis_lab/reviews/calibration_probe/stripe-docs.json`
- `examples/visual_diagnosis_lab/reviews/calibration_probe/headspace.json`
- `examples/visual_diagnosis_lab/reviews/calibration_probe/notion.json`
- `examples/visual_diagnosis_lab/reviews/calibration_probe/le-labo.json`

## Validation

```bash
./.venv/bin/python -m pytest tests/test_visual_diagnosis.py tests/test_visual_diagnosis_style_capture.py -q
```

Result:

- `30 passed`
