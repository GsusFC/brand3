# Deprecated Surfaces

This file records product and code surfaces that have been retired so they do
not reappear as parallel modules.

## Reverse Engineering

Status: deprecated and removed.

Replacement: Magnetism Scanner TLDR Brand3.

Reverse Engineering was an early approximation of the Magnetism Scanner. Its
useful role was to interpret observed brand signals through the Magenta Circle.
That responsibility now lives inside TLDR Brand3, where each block exposes the
source signal, claim type, mode, confidence, reasoning, evidence, and review
status.

Decision:

- Do not expose Reverse Engineering as a product route.
- Do not keep a separate Reverse Engineering service.
- Do not add new Reverse Engineering tests.
- Use Brand Audit as the canonical acquisition layer.
- Use Magnetism Scanner / TLDR Brand3 as the strategic interpretation layer.

Removed code:

- `src/features/reverse_engineering/`
- `src/services/reverse_engineering_service.py`
- `tests/test_reverse_engineering.py`
- `tests/test_reverse_engineering_service.py`

Reason:

Keeping Reverse Engineering as a separate module duplicated the strategic
interpretation now handled by Magnetism Scanner and increased the risk of
parallel, inconsistent outputs.

## Brand3 Lab

Status: deprecated and removed as a web/product surface.

Replacement: no replacement surface. Useful methodology was absorbed into product-side quality policy.

Brand3 Lab was a research UI for narrative comparison, per-audit cases, signal depth review, and shadow narrative trials. It duplicated product interpretation surfaces and created a parallel path beside Brand Audit and Magnetism Scanner.

Absorbed into product code:

- Signal-depth, overreach, and editorial discipline rules now live in `src/reports/editorial_policy.py`.

(The Narrative Harness and EntityNarrativeState modules retained here at Lab
deprecation were themselves later deleted — see "Narrative Harness / State-First
Phase-2 Family" below.)

Removed code and artifacts:

- `web/routes/brand3_lab.py`
- `web/brand3_lab_data.py`
- `web/templates/brand3_lab*.j2`
- `web/templates/perceptual_narrative_comparison.html.j2`
- `web/static/brand3_lab_review.js`
- `web/static/perceptual_narrative_comparison.js`
- `src/reports/narrative_shadow_adapter.py`
- `scripts/narrative_shadow_adapter_trial.py`
- `examples/brand3_lab/`
- `examples/perceptual_library/`
- `examples/reports/narrative_shadow_adapter_trial/`

Decision:

- Do not restore Brand3 Lab routes.
- Do not keep Lab pages as hidden/internal URLs.
- Do not add another comparison/cases product surface.
- Promote useful methodology only by moving it into Brand Audit or Magnetism Scanner contracts.

## Narrative Harness / State-First Phase-2 Family

Status: deprecated and removed (2026-06-14).

Replacement: no replacement. Prose/evidence discipline lives in the TLDR/SV9
path (`src/features/magnetism/`) and `src/reports/editorial_policy.py`.

This was an offline-only Phase-2 family for post-generation narrative
diagnostics: prose-quality heuristics (generic filler, repeated openings,
unsupported prescription language) plus a deterministic state/prose generator.
It self-declared `runtime_enabled: False` and had zero production callers. The
`unsupported_editorial_synthesis` readiness gate it was designed to feed never
received input — `_readiness_inputs_from_snapshot` never populated
`narrative_summary`, so the gate always saw `{}` and was structurally
unreachable in production. None of its checks crossed a claim against
`raw_inputs`, so it was never an anti-hallucination safeguard.

Removed code and artifacts:

- `src/reports/narrative_harness.py`
- `src/reports/entity_narrative_state.py`
- `src/reports/state_first_findings_generator.py`
- `src/reports/state_first_prose_generator.py`
- `tests/test_reports_narrative_harness.py`, `tests/test_entity_narrative_state.py`, `tests/test_state_first_findings_generator.py`, `tests/test_state_first_prose_generator.py`, `tests/test_offline_narrative_composition_boundaries.py`
- `examples/reports/narrative_harness/` (fixtures)
- `narrative_summary` parameter, `unsupported_editorial_synthesis` gate, and `_dimension_narrative_state` / `_unsupported_editorial_synthesis` helpers in `src/quality/report_readiness.py`; the dead blocker branch in `src/reports/derivation.py`

Decision:

- Do not reintroduce a post-generation prose-QC harness as a readiness gate.
- Prose quality is governed in the TLDR/SV9 interpretation path, not a parallel offline module.
- The Phase-2 research docs whose subject was this family (per-brand findings, builder contracts, v0 specs, generator output reviews, trial syntheses) were deleted with the code (~37 docs). Memos about *live* surfaces that merely referenced the family were kept: report rendering of `typical_decision`/`Finding.prose` (the 2026-05-16 rendering memos), the evidence-packet / evidence-reset pipeline work, the perceptual corpus notes, and `brand3_narrative_cohesion_diagnostic.md` (which also holds a still-valid `build_report_base` pipeline map).
