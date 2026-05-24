# Visual Signature Inspection Fixtures

These payloads are local examples for evaluating Visual Signature signal quality
before the evidence layer influences Brand3 scoring.

- `strong_visual_system.json` — broad coverage, high confidence, consistent system.
- `weak_visual_system.json` — sparse rendered evidence and many missing signals.
- `inconsistent_system.json` — enough evidence, but mixed color/type/asset behavior.
- `template_saas_system.json` — internally consistent SaaS-like system for category comparison.

Use:

```bash
./.venv/bin/python scripts/visual_signature_inspect.py inspect examples/visual_signature/strong_visual_system.json
./.venv/bin/python scripts/visual_signature_inspect.py compare examples/visual_signature/*.json
```

The inspector reads saved JSON only. It does not call Firecrawl and does not
modify scoring.

## Calibration Batches

`calibration_brands.json` contains a curated set of real websites for manual
Visual Signature evaluation across luxury, SaaS, AI-native, editorial/media,
ecommerce, small business, developer-first, wellness/lifestyle, and
template-like SaaS examples.

Visual Signature screenshot analysis is viewport-first by default. The
viewport capture is the primary evidence for first-impression behavior, and
full-page capture is secondary evidence for deeper review. Neither capture type
influences scoring yet.

Run a batch:

```bash
./.venv/bin/python scripts/visual_signature_calibrate.py \
  --input examples/visual_signature/calibration_brands.json \
  --output-dir examples/visual_signature/calibration_outputs
```

Add `--with-vision` to enrich payloads with local screenshot evidence when
`screenshot_path` or `screenshot_payload` is present in the input rows. The
input rows can also carry `capture_type` to make viewport capture explicit.
If the screenshot metadata includes `capture_type: viewport`, the calibrator
also computes viewport-normalized palette and composition evidence from the
above-the-fold slice.

Why viewport-first:

- useful for first-impression density, spacing, and color balance
- useful for comparing visible hero treatment across brands
- can avoid DOM/CSS overcounting of hidden sections or below-the-fold blocks

Why full-page:

- useful for longer editorial, commerce, or docs pages where layout rhythm
  matters beyond the fold
- useful for comparing the total rendered system once viewport behavior is
  understood

DOM/CSS can misread visual density because the HTML tree often includes hidden
sections, deferred modules, repeated components, and below-the-fold structure
that are not visible in the first impression.

For screenshot-backed calibration, use
`examples/visual_signature/vision_calibration_brands.json` together with local
PNG files stored under `examples/visual_signature/screenshots/`.

The screenshot-backed set is intentionally kept separate from the main real
website batch so large image files do not need to live in the repo.

The calibrator saves:

- one Visual Signature payload JSON per brand
- one compact text summary per brand under `calibration_outputs/summaries/`
- `manifest.json` with status, confidence, coverage, and per-brand errors
- `batch_summary.md` for quick manual review

After running calibration, review `signal_quality_framework.md` for the first
documented keep/improve/downgrade framework based on interpretable captures.

CSV inputs are also accepted with columns:

```csv
brand_name,website_url,expected_category,notes
```

This workflow may call the live Visual Signature extractor and therefore
Firecrawl when no fixture/mocked extractor is provided. Tests use mocks only.
The output is for evidence calibration; it does not modify scoring, dimensions,
reports, or the web UI.
