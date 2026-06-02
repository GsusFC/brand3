# Brand3 Owned Content Extraction Bake-off Sprint 0

Date: 2026-06-02
Status: experimental harness added

## Verdict

Brand3 should not assume Firecrawl, Exa, browser extraction, or the current fallback chain is the best way to produce owned content. The first Lab step is to compare extraction methods on the same captured HTML before comparing live providers.

## Why This Comes First

Provider quality and extraction quality are different questions:

- A provider may discover the right page but extract noisy text.
- A provider may extract clean text but miss important pages.
- A browser capture may see rendered content but include navigation, modals, and footer noise.
- A simple HTML parser may be cleaner but miss JavaScript-rendered copy.

The first bake-off isolates extraction quality by holding the HTML constant.

## What Was Added

- `src/quality/owned_content_extraction.py`
  - offline extraction evaluation utilities
  - baseline method: Brand3 current HTML fallback
  - alternative method: section-aware HTML extraction
  - alternative method: naive visible body text
  - scoring for expected evidence, rejected noise, strategic signals, length, and line diversity

- `scripts/owned_content_extraction_bakeoff.py`
  - CLI runner for JSON benchmark cases
  - Markdown and JSON output support

- `examples/benchmarks/owned_content_extraction/dataset.json`
  - initial synthetic benchmark cases
  - nav-heavy SaaS homepage
  - cookie-banner-before-product-copy case

- `tests/test_owned_content_extraction_lab.py`
  - offline regression tests for the Lab harness

## Initial Finding

On synthetic fixtures, `section_aware_html` beats the current Brand3 HTML fallback because it removes header/nav/footer/cookie containers before block extraction while preserving strategic product copy.

This is not enough evidence to replace production extraction. It is only enough to justify expanding the benchmark to real captured pages.

## Next Experiment

Add real saved HTML fixtures for 5-10 brands:

- one JS-heavy app
- one clean marketing site
- one local Spanish business
- one docs/product-led company
- one ecommerce or marketplace-like site

For each case, define:

- expected strategic terms
- rejected boilerplate terms
- required page intent
- known failure modes

Then compare:

- Brand3 current HTML fallback
- section-aware HTML
- browser body text
- Firecrawl markdown snapshot
- Playwright DOM segment extraction
- optional external libraries only after local baselines are measured
