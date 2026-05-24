# Brand3 Builder Hardening Phase Close

Date: 2026-05-17

Scope: phase-close memo only. No code, prompts, scoring, rendering, payload format, Visual Signature code, fixtures, audits, builder changes, or runtime behavior were changed.

## Status

The builder-hardening phase is closed.

Current state:

```text
offline narrative composition is coherent,
contracts are documented,
boundaries are protected by tests,
and the system should pause before adding new concepts.
```

## What Was Hardened

The phase hardened the offline narrative composition layer around:

- payload-level Narrative Harness diagnostics,
- render-aware diagnostics,
- observation repetition family checks,
- offline `EntityNarrativeState` builder v0,
- explicit `observed_related_surfaces` input contract,
- manual Iris and Watermelon related-surface inputs,
- generated `.entity_narrative_state.v0.json` outputs,
- artifact navigation/indexing.

The most important hardening outcome is separation:

```text
diagnostics measure,
builder compiles state,
renderer controls visible display,
runtime generation remains untouched.
```

## Boundaries Protected By Tests

Protected by:

```text
tests/test_offline_narrative_composition_boundaries.py
```

Current boundaries:

- Narrative Harness must not import scoring, renderer, dossier, narrative generation, EntityNarrativeState, experimental perceptual narrative, runtime, or Visual Signature modules.
- EntityNarrativeState builder must not import scoring, renderer, dossier, narrative generation, Narrative Harness, experimental perceptual narrative, runtime, or Visual Signature modules.
- Report renderer must not import or call `build_entity_narrative_state`.
- Dossier generation must not import or call `build_entity_narrative_state`.

Protected by:

```text
tests/test_entity_narrative_state.py
```

Current builder invariants:

- stable output shape,
- offline flags stay false for runtime, scoring, prompts, and rendering,
- no strategic claims are invented,
- good-evidence cases do not force false tensions,
- missing evidence URLs become coverage metrics,
- inactive budgets remain inactive or absent,
- review-gated fields are not promoted to facts,
- arbitrary evidence URLs are ignored as related surfaces,
- name similarity alone is ignored,
- explicit `observed_related_surfaces` are copied with metadata,
- `needs_review` is true when any surface requires review,
- related surfaces do not create contradiction candidates.

Protected by:

```text
tests/test_reports_narrative_harness.py
tests/test_reports_renderer.py
```

Current diagnostic/render invariants:

- payload diagnostics are warning-only,
- render-aware diagnostics distinguish stored risk from visible risk,
- generic Decision Space can be hidden without mutating `Finding.prose`,
- structured findings still render observation, implication, decision space when specific, and evidence chips.

## Authoritative Contracts

Current authoritative contracts:

- `docs/brand3_entity_narrative_state_builder_v0_contract.md`
- `docs/brand3_entity_narrative_state_builder_v0_contract.json`
- `docs/brand3_observed_related_surfaces_input_contract.md`
- `docs/brand3_offline_narrative_composition_architecture_review.md`
- `docs/brand3_narrative_composition_artifact_index.md`

These should be treated as the source of truth for the offline narrative composition layer.

## Offline-Only Artifacts

These remain offline-only:

- `src/reports/narrative_harness.py`
- `src/reports/entity_narrative_state.py`
- `examples/reports/narrative_harness/*.diagnostic.json`
- `examples/reports/narrative_harness/*.render_aware.diagnostic.json`
- `examples/reports/narrative_harness/entity_state/*.entity_narrative_state.v0.json`
- `examples/reports/narrative_harness/entity_state/inputs/*.observed_related_surfaces.input.json`
- manual non-`.v0` entity-state fixtures.

They must not be treated as production records, report payloads, prompt inputs, scoring inputs, or Visual Signature inputs.

## What Must Stay Frozen

Freeze these until a new phase is explicitly opened:

- new narrative diagnostic families,
- new EntityNarrativeState fields,
- `compression_candidates` behavior,
- automatic contradiction candidates,
- automatic `primary_tension` synthesis,
- related-surface inference,
- Decision Space rendering heuristic,
- prompt refinement based on builder outputs,
- runtime use of builder outputs.

The current value is in stability, not expansion.

## Explicitly Not Ready

### Runtime Integration

Not ready.

The builder is diagnostic and offline. It has not been tested as a runtime dependency and must not participate in public report reads.

### Prompt Refinement

Not ready.

The harness identifies prompt-level symptoms, but prompt changes should wait until the offline state contracts remain stable over time.

### Scoring Changes

Not ready.

No narrative composition artifact should affect scores. Evidence URL coverage, repetition budgets, and related-surface ambiguity are diagnostic state, not scoring inputs.

### Visual Signature Integration

Not ready.

Visual/perceptual pressure is discussed in the research layer, but the builder does not consume Visual Signature outputs and should not treat visual confidence as evidentiary confidence.

## Recommended Pause Criteria

Pause now if:

- core tests remain green,
- no immediate production bug depends on this layer,
- no partner-facing need requires lab display,
- no new evidence suggests the current contracts are wrong,
- the next proposed task would add another concept rather than harden an existing boundary.

During the pause:

- keep artifacts indexed,
- keep tests green,
- avoid drift in terminology,
- do not delete provenance docs yet.

## Future Restart Criteria

Restart only when one of these conditions is true:

1. A concrete product need appears for a lab-only display of entity composition state.
2. More persisted reports show the same failure families and need comparison.
3. The team decides to design an explicit entity-discovery related-surface source.
4. Prompt refinement is scoped to one measured pattern and can be tested without weakening evidence caution.
5. Runtime integration is explicitly framed as opt-in, diagnostic-only, and non-scoring.

If restarted, the next phase should begin with a short goal that names which boundary is being opened.

## Final Close

The builder-hardening phase achieved its purpose:

```text
contracts exist,
outputs exist,
tests protect boundaries,
manual related-surface ambiguity is representable,
and runtime remains untouched.
```

The correct next action is a pause unless a specific lab-display, entity-discovery, or narrowly scoped prompt experiment is deliberately opened.
