# Visual Signature Screenshots

This directory is the local landing zone for screenshot-backed Visual Signature
calibration runs.

Do not commit large binary screenshots here.

Recommended workflow:

1. Capture local PNG screenshots for the brands listed in
   `../vision_calibration_brands.json`.
2. Viewport-first is the default strategy:
   - `viewport` uses a 1440x900 screenshot for above-the-fold analysis and is
     the primary evidence layer.
   - `full_page` keeps the older 1440x1200/full-page behavior and is secondary
     evidence for deeper review.
3. Save screenshots using the same filenames referenced in that JSON file, for example:
   `linear.png`, `openai.png`, `the-verge.png`.
4. Run calibration with `--with-vision`:

```bash
./.venv/bin/python scripts/visual_signature_calibrate.py \
  --input examples/visual_signature/vision_calibration_brands.json \
  --output-dir examples/visual_signature/calibration_outputs \
  --with-vision
```

The calibrator will read `capture_manifest.json` from this directory when
available and use its screenshot metadata to populate viewport evidence.
5. If you want both capture types for comparison, run the capture utility with
   `--capture-both`. It will keep the primary file at the requested path and
   write a secondary file with a derived suffix for the other capture type.

For test runs, generated screenshots can live in a temporary directory and the
input JSON can be copied or rewritten to point at those temporary paths.

If Playwright is not installed, install it with:

```bash
./.venv/bin/python -m pip install playwright
./.venv/bin/python -m playwright install chromium
```
