# Visual Signature Calibration Corpus

This folder is the offline corpus scaffold for expanded Visual Signature
calibration. It is an evidence dataset, not a scoring dataset.

Visual Signature evidence collected here may be used for inspection,
calibration, baseline research, and future multimodal annotation work. It must
not affect Brand3 scoring, rubric dimensions, production reports, or production
UI.

## Purpose

The corpus is meant to compare Visual Signature evidence within stable brand
categories before any scoring integration is considered. It keeps raw evidence,
screenshots, category metadata, eligibility decisions, failures, and future
annotations in versioned local artifacts.

## Eligibility

A record is baseline-eligible only when all of these are true:

- DOM extraction is interpretable.
- Acquisition has no blocking errors.
- Viewport screenshot evidence is available.
- Viewport screenshot quality is usable, not missing, unreadable, or blank.
- Viewport composition exists.
- Viewport palette exists.
- Viewport confidence exists.
- DOM-vs-viewport agreement exists.
- Signal coverage is at least `0.70`.
- Viewport dimensions are at least `1200x750`.

Records that fail eligibility can stay in the corpus for acquisition and
quality diagnostics, but they must not be included in category averages.

## Screenshot Rules

Viewport screenshots are required for eligible records:

- preferred capture: `1440x900`
- minimum accepted dimensions: `1200x750`
- PNG preferred
- saved under `screenshots/viewport/<category>/`

Full-page screenshots are optional secondary evidence:

- saved under `screenshots/full_page/<category>/`
- useful for editorial, ecommerce, docs, and long-scroll systems
- never replaces viewport-first evidence for first-impression analysis

Large screenshot files should be added deliberately. The scaffold uses
`.gitkeep` files so the folder layout exists without requiring binary assets.

## Storage Layout

```text
calibration_corpus/
  corpus_manifest.json
  categories/
    saas.json
    ecommerce.json
  screenshots/
    viewport/
    full_page/
  payloads/
  baselines/
  failures/
  annotations/
    multimodal/
```

Category seed files define candidate brands. Payloads and screenshots are
created later by capture/calibration workflows.

## Metadata Versioning

The corpus separates:

- `schema_version`: shape of the JSON metadata.
- `corpus_version`: curated corpus release.
- `extractor_version`: Visual Signature extractor version expected by the run.
- `vision_version`: Vision Enrichment version expected by the run.
- `baseline_version`: baseline algorithm version used for generated summaries.

## Future Multimodal Annotations

Future annotation overlays should live under `annotations/multimodal/`. They
should reference existing screenshot and payload paths instead of mutating raw
evidence. Possible future fields include logo prominence, imagery style,
product presence, human presence, template-likeness, visual distinctiveness,
category fit, annotator ID, model ID, confidence, and timestamp.

## Boundary

This corpus is evidence-only. Do not wire it into scoring, rubric dimensions,
production reports, or production UI.
