# Visual Signature Technical Checkpoint

Last updated: 2026-05-08

This document records the current state of the Visual Signature module so
future changes stay controlled. It is an evidence system, not a scoring
system.

## Current Architecture

Visual Signature is a Python-native evidence layer under `src/visual_signature/`.
It ingests Brand3 capture output and optional local screenshot evidence, then
returns structured JSON for inspection, calibration, and comparison.

For the architectural boundary and interaction policy, see
[reliable_visual_perception.md](./reliable_visual_perception.md).

Current flow:

1. Brand3 runs the normal acquisition and extraction pipeline.
2. Visual Signature extracts DOM/CSS evidence from the payload.
3. Optional screenshot evidence is added locally through Vision Enrichment.
4. Optional full-page capture can be analyzed as secondary evidence.
5. DOM-vs-viewport agreement is computed as a comparison layer.
6. Viewport obstruction evidence detects banners, modals, overlays, and other
   first-impression capture interference.
7. Optional shadow runs can persist Visual Signature evidence during Brand3
   runs without exposing it in scoring, reports, or the web UI.
8. Category Baselines can compare saved Visual Signature payloads within the
   same expected category.
9. Calibration and inspection tools save and summarize the resulting payloads.

For the official Visual Signature capability governance map, see
[capability_registry.md](./governance/capability_registry.md). Capability
presence does not imply production approval. Readiness is scope-dependent, and
the registry is evidence-only governance metadata that does not modify scoring,
rubric dimensions, runtime behavior, reports, or UI.

For the scope-based execution companion, see
[runtime_policy_matrix.md](./governance/runtime_policy_matrix.md). Capability
existence does not imply runtime approval, runtime policy is scope-dependent,
`production_runtime` blocks runtime mutation, and the matrix is governance
metadata only. It does not change scoring, rubric dimensions, capture
behavior, production UI/reports, taxonomy, or runtime behavior.

## Implemented Evidence Layers

### DOM/CSS

This is the original Visual Signature evidence base. It includes:

- colors
- typography
- logo
- layout
- components
- assets
- consistency

This layer is still the main input when screenshot evidence is unavailable.

### Viewport Vision

Viewport vision is the primary screenshot strategy. It analyzes the first
impression at a 1440x900 viewport and produces:

- screenshot availability and quality
- screenshot palette
- viewport palette
- viewport whitespace ratio
- viewport visual density
- viewport composition
- viewport confidence

This is the preferred visual read for first-impression behavior.

### Optional Full-Page Vision

Full-page capture is secondary evidence. It is useful when page rhythm,
scroll depth, or long-form layout structure matters beyond the fold.

It remains evidence only and does not influence scoring.

### DOM-vs-Viewport Agreement

The agreement layer compares DOM/CSS interpretation against viewport evidence.
It reports:

- `agreement_level`
- `disagreement_flags`
- `summary_notes`

It is meant to detect material disagreement, such as:

- DOM says dense, viewport is spacious
- DOM palette looks noisy, viewport is minimal
- DOM complexity is likely hidden below the fold

### Viewport Obstruction

Viewport obstruction analysis is an evidence-quality layer. It combines DOM
heuristics and local viewport pixels to detect likely:

- cookie banners and consent modals
- newsletter or promo modals
- login walls
- unknown overlays
- non-blocking sticky bars

It reports `present`, `type`, `severity`, `coverage_ratio`,
`first_impression_valid`, `confidence`, `signals`, and `limitations`.

It never clicks, accepts, dismisses, modifies the DOM, bypasses protections, or
changes scoring. Calibration runs write `obstruction_audit.json` and
`obstruction_audit.md` so obstructed first impressions can be reviewed before
category baselines are trusted.

### Shadow-Run Persistence

Brand3 has an opt-in `enable_visual_signature_shadow_run` execution path.
When enabled, a normal Brand3 run can:

- extract Visual Signature evidence from already-collected Brand3 web data
- enrich it with existing screenshot evidence when available
- compute DOM-vs-viewport agreement when viewport evidence exists
- persist the result as raw Visual Signature evidence

The shadow path logs `started`, `completed`, `skipped`,
`acquisition_failed`, and `persisted` states. Failures in acquisition,
screenshot enrichment, or persistence are degraded so the Brand3 run
continues.

### Category Baselines

Category Baselines live under `src/visual_signature/baselines/`. They are an
offline calibration layer that groups saved Visual Signature payloads by
expected category, excludes `not_interpretable` payloads from averages, and
counts those failures in category coverage.

The baseline MVP produces:

- category averages
- viewport density and composition distributions
- DOM-vs-viewport agreement distributions
- category-relative outlier flags
- confidence and coverage notes

Baseline outputs are written by `scripts/visual_signature_build_baselines.py`
as local JSON and Markdown artifacts for inspection.

## What Is Evidence-Only

The following are evidence-only and may be used for calibration, inspection,
and future research:

- DOM/CSS extraction results
- viewport vision results
- full-page vision results
- DOM-vs-viewport agreement results
- shadow-run raw Visual Signature persistence
- category baseline summaries and brand comparisons
- viewport obstruction evidence and obstruction audit reports
- extraction confidence
- signal coverage
- weak signal counts
- calibration summaries and manifests

These layers are explicitly not scoring inputs today.

## What Is Explicitly Not Scoring

Visual Signature does not currently affect:

- scoring weights
- rubric dimensions
- production reports
- web UI behavior
- Brand3 output ranking
- category scores

Shadow-run persistence is also excluded from those surfaces. It stores raw
evidence for inspection and traceability only.

Category Baselines are also excluded from those surfaces. They compare evidence
within categories but do not create scoring adjustments or category scores.

The module is intentionally isolated so evidence can be reviewed before any
future rubric integration is considered.

## Known Limitations

Current limitations are practical, not semantic:

- DOM/CSS can overstate complexity when hidden or below-the-fold content is
  present.
- Screenshot palettes are still coarse and background-heavy.
- Vision confidence mostly reflects capture readability, not brand quality.
- Full-page capture can dilute first-impression signals.
- Cookie banners, consent modals, login walls, and overlays can invalidate a
  first-impression capture; obstruction detection is heuristic and may require
  human review for ambiguous cases.
- DOM extraction still mixes useful structure with noisy heuristics.
- Typography and CTA extraction remain imperfect.
- Logo and asset signals are still weak without stronger vision.
- No multimodal interpretation is in place yet.

Interpretation remains limited to evidence quality. It should not be used to
claim premium quality, distinctiveness, template-likeness, or category fit.

## Safe Next Phases

### 1. Multimodal Vision

Add a multimodal adapter for richer visual semantics:

- logo prominence
- imagery style
- product presence
- editorial tone
- template-likeness
- visual distinctiveness

### 2. Multi-Page System Analysis

Compare homepages, docs, pricing, product pages, and lower-funnel pages to
understand a brand system across page types rather than from one surface only.

### 3. Category Baseline Calibration

Expand category-specific calibration baselines with larger sample sizes so the
same signal can be compared relative to SaaS, editorial, ecommerce, wellness,
developer-first, and luxury expectations.

### 4. Possible Future Rubric Integration

Only after repeated calibration should Visual Signature be considered for any
future rubric work. If that ever happens, it should be introduced as a
carefully bounded, test-backed change.

## Operating Rule

Keep Visual Signature as evidence-only until the capture stack, agreement
analysis, and category calibration are stable enough to justify any wider use.
