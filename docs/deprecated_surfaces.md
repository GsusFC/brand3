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

- Narrative Harness remains in `src/reports/narrative_harness.py`.
- EntityNarrativeState remains in `src/reports/entity_narrative_state.py`.
- Signal-depth, overreach, and editorial discipline rules now live in `src/reports/editorial_policy.py`.

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
