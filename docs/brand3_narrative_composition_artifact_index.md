# Brand3 Narrative Composition Artifact Index

Date: 2026-05-17

Scope: navigation index only. No code, prompts, scoring, rendering, payload format, Visual Signature code, fixtures, audits, or runtime behavior were changed.

## Current Phase Status

Current phase:

```text
Builder hardening
```

The offline narrative composition layer is coherent enough to keep, but not ready for runtime or prompt integration.

Current recommendation:

```text
stabilize contracts,
protect invariants,
avoid adding new concepts,
keep all entity composition work offline.
```

## Authoritative Docs

Read these first.

| Document | Role |
|---|---|
| `docs/brand3_offline_narrative_composition_architecture_review.md` | Current architecture review and recommended next phase. |
| `docs/brand3_narrative_harness_phase_1_boundary.md` | Closes Phase 1 diagnostic scope and explains payload/render diagnostics. |
| `docs/brand3_phase_2_synthesis_entity_state_readiness.md` | Explains why offline `EntityNarrativeState` became justified. |
| `docs/brand3_entity_narrative_state_builder_v0_contract.md` | Human-readable builder v0 contract. |
| `docs/brand3_entity_narrative_state_builder_v0_contract.json` | Machine-readable builder v0 contract. |
| `docs/brand3_entity_narrative_state_builder_v0_outputs_review.md` | Review of initial builder outputs across five cases. |
| `docs/brand3_observed_related_surfaces_input_contract.md` | Authoritative contract for related-surface metadata. |
| `docs/brand3_watermelon_observed_related_surfaces_builder_pass_review.md` | Review of ecosystem ambiguity passthrough. |
| `docs/brand3_iris_observed_related_surfaces_builder_pass_review.md` | Review of name-collision ambiguity passthrough. |

## Superseded Or Intermediate Docs

These are useful provenance, but not the current entry point.

| Document | Status |
|---|---|
| `docs/brand3_narrative_cohesion_diagnostic.md` | Early diagnosis of narrative fragmentation. |
| `docs/brand3_narrative_harness_next_step_memo.md` | Decision memo that led to the harness. |
| `docs/brand3_narrative_harness_v1_findings.md` | Early harness findings. |
| `docs/brand3_render_aware_narrative_harness_findings.md` | Early render-aware findings. |
| `docs/brand3_remaining_visible_narrative_repetition.md` | Intermediate rendering/repetition review. |
| `docs/brand3_entity_narrative_state_design_memo.md` | Early design memo for `EntityNarrativeState`. |
| `docs/brand3_entity_narrative_state_fixture_review.md` | Review of first manual fixture shape. |
| `docs/brand3_entity_narrative_state_second_fixture_comparison.md` | Comparison after second manual fixture. |

Do not delete these yet. They explain why the current contracts exist.

## Core Code Files

| File | Role |
|---|---|
| `src/reports/narrative_harness.py` | Offline payload and render-aware diagnostics. |
| `src/reports/entity_narrative_state.py` | Offline `EntityNarrativeState` builder v0. |
| `src/reports/renderer.py` | Runtime renderer; includes display-only `Decision space` heuristic. |
| `src/reports/templates/report.html.j2` | Report template rendering structured findings and conditional `Decision space`. |

## Core Tests

| File | Protects |
|---|---|
| `tests/test_reports_narrative_harness.py` | Payload/render-aware diagnostic behavior. |
| `tests/test_entity_narrative_state.py` | Builder shape, flags, uncertainty, related-surface passthrough. |
| `tests/test_offline_narrative_composition_boundaries.py` | Import/coupling boundaries. |
| `tests/test_reports_renderer.py` | Visible report behavior for structured findings and `Decision space`. |

## Example Diagnostics

Directory:

```text
examples/reports/narrative_harness/
```

Important files:

```text
builtwith_kit_com.diagnostic.json
builtwith_kit_com.render_aware.diagnostic.json
netlify_snapshot_mock.diagnostic.json
netlify_snapshot_mock.render_aware.diagnostic.json
clean_control.diagnostic.json
clean_control.render_aware.diagnostic.json
launchdarkly.diagnostic.json
launchdarkly.render_aware.diagnostic.json
iris.diagnostic.json
iris.render_aware.diagnostic.json
watermelon.diagnostic.json
watermelon.render_aware.diagnostic.json
```

Use these as example diagnostics only. They are not production records.

## EntityNarrativeState Builder Outputs

Directory:

```text
examples/reports/narrative_harness/entity_state/
```

Builder-generated outputs:

```text
builtwith_kit_com.entity_narrative_state.v0.json
netlify_snapshot_mock.entity_narrative_state.v0.json
launchdarkly.entity_narrative_state.v0.json
iris.entity_narrative_state.v0.json
watermelon.entity_narrative_state.v0.json
```

Manual older fixtures:

```text
builtwith_kit_com.entity_narrative_state.json
netlify_snapshot_mock.entity_narrative_state.json
```

Treat `.v0.json` files as builder outputs. Treat non-`.v0` files as manual design provenance.

## Manual Observed Related Surfaces Inputs

Directory:

```text
examples/reports/narrative_harness/entity_state/inputs/
```

Current inputs:

```text
watermelon.observed_related_surfaces.input.json
iris.observed_related_surfaces.input.json
```

Purpose:

- provide explicit reviewed related-surface metadata,
- test entity/surface ambiguity safely,
- avoid inference from evidence URLs or name similarity.

These are manual offline fixtures, not verified production entity metadata.

## Runtime-Visible

Currently runtime-visible:

- structured rendering of finding `observation` and `implication`,
- conditional display of `Decision space`,
- evidence chips in report output.

The runtime-visible code is in:

```text
src/reports/renderer.py
src/reports/templates/report.html.j2
```

## Offline-Only

Offline-only:

- `src/reports/narrative_harness.py`
- `src/reports/entity_narrative_state.py`
- diagnostics under `examples/reports/narrative_harness/`
- entity-state builder outputs under `examples/reports/narrative_harness/entity_state/`
- manual related-surface inputs under `examples/reports/narrative_harness/entity_state/inputs/`

These do not affect scoring, prompts, generation, rendering, Visual Signature, or runtime behavior.

## Must Not Be Used As Production Input

Do not use these as production input:

- `*.diagnostic.json`
- `*.render_aware.diagnostic.json`
- `*.entity_narrative_state.v0.json`
- manual `*.observed_related_surfaces.input.json`
- manual non-`.v0` entity-state fixtures
- review memos as machine-readable truth

They are research and diagnostic artifacts only.

## Recommended Next Action

Recommended next action:

```text
continue builder hardening, then pause
```

Concretely:

1. Keep current tests green.
2. Avoid new semantic fields.
3. Avoid runtime wiring.
4. Keep `observed_related_surfaces` explicit and review-gated.
5. Consider one small cleanup pass later to reduce duplicated docs, not now.

Do not move to prompt refinement, runtime integration, Visual Signature integration, or scoring changes from the current artifact set.
