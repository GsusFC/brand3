# Brand3 Offline Narrative Composition Architecture Review

Date: 2026-05-17

Scope: architecture review only. No code, prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, fixtures, audits, or runtime wiring were changed.

## Executive Assessment

The offline narrative composition system is coherent, but close to the point where more additions would create conceptual sprawl.

The current architecture has a useful separation:

- payload diagnostics measure stored narrative risk,
- render-aware diagnostics measure visible report risk,
- rendering hides only a narrow generic `Decision space` surface,
- `EntityNarrativeState` compiles offline composition state from existing diagnostics,
- `entity_resolution.related_surfaces` supplies explicit review metadata without entity inference, with `observed_related_surfaces` retained only as legacy compatibility.

The system is not yet overgrown, but it should now enter a controlled hardening/freeze phase. The next phase should not add more conceptual layers. It should stabilize contracts, reduce duplication, and protect invariants.

Recommended next phase:

```text
builder hardening
```

Specifically: harden the offline builder and its input contracts, then pause before prompt refinement or runtime integration.

## Architecture Map

Current flow:

```text
report_narrative payload
        |
        v
payload-level Narrative Harness
        |
        +--> payload diagnostics
        |
rendered report HTML/text
        |
        v
render-aware Narrative Harness
        |
        +--> visible-render diagnostics
        |
payload + diagnostics + optional snapshot/base dossier metadata
        |
        v
offline EntityNarrativeState builder v0
        |
        +--> entity_narrative_state.v0 JSON outputs
```

Separate visible report flow:

```text
report_narrative payload
        |
        v
ReportRenderer / Jinja template
        |
        +--> structured finding display
        +--> conditional Decision Space visibility
```

The important point: the `EntityNarrativeState` builder does not feed back into report rendering, prompts, scoring, Visual Signature, or runtime generation.

## Components Now Existing

### Narrative Harness

Location:

```text
src/reports/narrative_harness.py
tests/test_reports_narrative_harness.py
```

Role:

- offline diagnostic instrument,
- reads persisted `report_narrative`-shaped payloads,
- emits warning metrics and checks,
- does not mutate inputs,
- does not call LLMs,
- does not affect scoring, prompts, rendering, or runtime.

Measures:

- repeated openings,
- generic strategic filler,
- unsupported prescription language,
- missing evidence URLs,
- unsafe self-description validation,
- safe attribution overuse,
- observation repetition families,
- synthesis/tension lexical mismatch.

### Render-Aware Diagnostics

Location:

```text
src/reports/narrative_harness.py
tests/test_reports_narrative_harness.py
```

Role:

- offline diagnostic instrument,
- compares stored payload risk against visible rendered HTML/text risk,
- distinguishes suppressed generic material from still-visible risks.

Measures:

- visible repeated openings,
- visible safe attribution,
- visible generic filler,
- visible evidence link/chip count,
- visible `Decision space` count,
- visible `Teams in this position typically` count,
- visible `The brand...` count.

### Observation Repetition Families

Location:

```text
src/reports/narrative_harness.py
```

Role:

- payload/render diagnostic vocabulary,
- groups repeated language into families rather than one-off phrases.

Families:

- safe attribution repetition,
- fallback evidence-opening repetition,
- external corroboration caveat repetition.

This is one of the most useful pieces because it turns individual phrases into measured narrative-risk patterns.

### Conditional Decision Space Rendering

Location:

```text
src/reports/renderer.py
src/reports/templates/report.html.j2
tests/test_reports_renderer.py
```

Role:

- visible report output behavior,
- separates `observation + implication` from `typical_decision`,
- hides clearly generic `Decision space` text,
- keeps `Finding.prose` and persisted payloads unchanged.

This is the only piece in the current architecture that affects user-visible reports.

### EntityNarrativeState Builder v0

Location:

```text
src/reports/entity_narrative_state.py
tests/test_entity_narrative_state.py
```

Role:

- offline-only state compiler,
- consumes payloads, diagnostics, and optional snapshot/base dossier metadata,
- emits deterministic `entity_narrative_state.v0` dictionaries,
- does not generate prose,
- does not infer strategy,
- does not integrate with runtime.

Compiles:

- primary entity signal,
- entity aliases/observed related surfaces,
- owned-claim density,
- repeated opener budget,
- fallback language budget,
- evidence URL coverage,
- advisory decision-space mode,
- source ownership summary when explicit metadata exists,
- attribution/corroboration budgets,
- review-gated primary tension when payload text exists,
- empty contradiction candidates unless explicit future support exists,
- suggested-only compression candidates.

### Related Surfaces Input Contract

Location:

```text
docs/brand3_observed_related_surfaces_input_contract.md
examples/reports/narrative_harness/entity_state/inputs/*.observed_related_surfaces.input.json
```

Role:

- explicit input contract for entity/surface ambiguity,
- prevents unsafe inference from evidence URLs or name similarity,
- now writes the canonical packet field `entity_resolution.related_surfaces`,
- preserves relation type, confidence, source, evidence, and human-review flags,
- keeps `observed_related_surfaces` only as a compatibility alias for older snapshots.

Current manual inputs:

- Watermelon: ecosystem/adjacent-surface ambiguity.
- Iris: name-collision ambiguity.

### Builder Outputs

Location:

```text
examples/reports/narrative_harness/entity_state/*.entity_narrative_state.v0.json
```

Role:

- experimental generated artifacts,
- builder-output candidates,
- not official records,
- not runtime data,
- not report payloads.

## Component Classification

| Component | Classification | Affects visible reports? | Runtime? |
|---|---|---:|---:|
| Narrative Harness payload audit | Diagnostic instrument | No | No |
| Render-aware harness | Diagnostic instrument | No | No |
| Observation repetition families | Diagnostic vocabulary | No | No |
| Conditional Decision Space rendering | Report rendering behavior | Yes | Yes, but narrow |
| EntityNarrativeState builder v0 | Offline state compiler | No | No |
| Observed related surfaces contract | Offline input contract | No | No |
| Manual observed related surface inputs | Experimental artifact | No | No |
| `.entity_narrative_state.v0.json` outputs | Experimental artifact | No | No |
| Phase/review memos | Methodology artifacts | No | No |

## Separation Review

### Payload Diagnostics vs Visible-Render Diagnostics

Still clean.

Payload diagnostics read stored narrative structure. Render-aware diagnostics read rendered HTML/text and compare what remains visible. The render-aware layer calls the payload audit internally, but it does not mutate payloads or render anything itself.

Risk:

The same phrase families appear in both payload and visible metrics. This is fine now, but thresholds and phrase lists could drift if future code duplicates them elsewhere.

### Diagnostics vs Entity Composition State

Mostly clean.

The builder consumes diagnostic metrics and compiles state. It does not re-run semantic analysis or introduce a second opinion about prose quality.

Risk:

`compression_candidates` starts to sound operational. It is currently `suggested_only`, but it could become a hidden rewrite plan if not frozen.

### Report Rendering vs Entity State

Clean.

Rendering has no dependency on `EntityNarrativeState`. The builder has no dependency on `ReportRenderer`.

The only rendering change is the display-only `should_show_decision_space` filter.

Risk:

Future work may be tempted to use builder state to drive rendering. That should not happen before a separate opt-in lab display phase.

### Runtime Generation vs Offline Builder

Clean.

`src/reports/entity_narrative_state.py` is not wired into `build_brand_dossier(...)`, `ReportRenderer`, prompts, or generation.

Risk:

The builder now looks useful enough that premature runtime integration is tempting. It should remain offline until false-positive behavior is reviewed across more persisted reports.

### Visual Signature vs Narrative Composition

Clean.

The narrative system references Visual Signature only in documents as a pressure area. Code does not import or call Visual Signature modules.

Risk:

Iris has visual/perceptual pressure. The architecture must not treat visual strength as evidentiary confidence.

## Coupling Analysis

### Scoring Coupling

No unsafe coupling detected.

Harness and builder do not write scores or consume score as a narrative truth. Snapshot metadata may carry score summaries, but the builder does not convert score into narrative quality.

Protective invariant:

Entity state must never include a narrative quality score or modify dimension scores.

### Prompt Coupling

No runtime prompt coupling detected.

Diagnostics identify prompt-level patterns, but no prompt text is changed and no builder state is passed into prompts.

Risk:

Prompt refinement could become too broad if attempted before builder hardening.

Protective invariant:

Builder output must not be used as prompt context until an explicit opt-in experiment exists.

### Visual Signature Coupling

No code coupling detected.

Risk:

Documents discuss Visual Signature pressure. That is useful context, but the current builder cannot safely distinguish visual confidence from evidentiary confidence.

Protective invariant:

No imports from Visual Signature modules in narrative harness or entity-state builder.

### Runtime Coupling

No runtime coupling detected for harness or builder.

The conditional Decision Space renderer is runtime-visible, but it is separate from the offline composition system and narrow in scope.

Protective invariant:

`build_entity_narrative_state(...)` remains absent from dossier building, rendering, scoring, and web routes unless explicitly added in a future goal.

### Report Rendering Coupling

One deliberate coupling exists:

- `ReportRenderer` uses `should_show_decision_space`.
- The template renders structured fields and conditionally displays `Decision space`.

This is acceptable because it was a rendering experiment with tests and does not mutate payloads.

Risk:

Renderer heuristics can hide content and make payload diagnostics look worse than visible output. That is why render-aware diagnostics must remain separate.

### Evidence URL Coupling

Mostly clean.

Harness and builder both read finding-level `evidence_urls`. The builder turns missing URLs into coverage state, not failure.

Risk:

Evidence URL coverage may be over-weighted because `coherencia` and `diferenciacion` repeatedly lack URLs even when global evidence exists. This should be treated as a data-contract issue, not a final judgment.

### Entity-Discovery Coupling

Now deliberately minimal.

The builder accepts explicit `observed_related_surfaces` from snapshot/base dossier metadata. It does not infer surfaces from `related_domains`, `discovered_domains`, evidence URLs, or name similarity.

This is safe but conservative.

Risk:

Manual inputs and builder outputs may diverge if excluded/noisy surfaces become analytically important. For now, excluded surfaces remain fixture context, not state.

## Complexity Risks

### 1. Too Many Artifacts

There are now many docs, JSON fixtures, diagnostics, builder outputs, and review memos.

Risk:

Future contributors may not know which artifacts are authoritative.

Recommendation:

Keep a short index or phase boundary if work continues. Do not add more memos unless they replace or summarize older decisions.

### 2. Vocabulary Duplication

Terms like `safe attribution`, `fallback language`, `corroboration caveat`, `Decision space`, and `observed related surfaces` now appear in docs, harness metrics, builder fields, and reviews.

Risk:

The same concept can drift across code and documents.

Recommendation:

Freeze vocabulary for v0. Any new family should require a contract update and tests.

### 3. Builder Becoming A Policy Engine

The builder already emits:

- budgets,
- modes,
- candidates,
- review flags.

Risk:

Those can become operational decisions if reused too early.

Recommendation:

Keep builder outputs diagnostic. Do not use them to rewrite, suppress, score, or block report content.

### 4. Manual Inputs Becoming Hidden Truth

Manual `observed_related_surfaces` fixtures are useful, but they are manually curated.

Risk:

Manual review artifacts may be mistaken for verified entity metadata.

Recommendation:

Keep `requires_human_review` visible and preserve low confidence for ambiguous name matches.

### 5. Render Fix Masking Payload Problems

Conditional Decision Space rendering improved visible output, but payloads still contain generic material.

Risk:

The product may look better while the stored narrative remains structurally repetitive.

Recommendation:

Always compare payload-level and render-aware diagnostics before judging improvement.

## Keep / Freeze / Simplify / Delete

### Keep

Keep these as active offline tools:

- payload-level Narrative Harness,
- render-aware diagnostics,
- observation repetition family metrics,
- `EntityNarrativeState` builder v0,
- `observed_related_surfaces` explicit input contract,
- tests protecting offline/no-runtime behavior.

### Freeze

Freeze these areas for now:

- phrase families and thresholds,
- `compression_candidates`,
- `primary_tension` automation,
- contradiction candidates,
- conditional Decision Space rendering heuristic.

Freezing means no expansion until there is a clear measured need.

### Simplify

Simplify later:

- consolidate docs into a phase index,
- reduce repeated explanations of "no runtime / no scoring / no prompts",
- centralize shared phrase-family vocabulary if code begins to duplicate it beyond harness and builder.

Do not simplify by deleting provenance. The current audit trail is useful.

### Delete Or Merge Later

Candidates for future deletion/merge if they stop being useful:

- older intermediate memos once a phase index exists,
- manual entity-state fixtures that are superseded by builder outputs,
- redundant output review docs once builder behavior stabilizes,
- `compression_candidates` if no future lab display uses them.

Do not delete yet. The exploration is still young, and the provenance is useful.

## Invariants To Protect With Tests

### Harness Invariants

- Payload audit returns stable shape.
- Render-aware audit distinguishes payload metrics from visible metrics.
- Missing evidence URLs warn but do not error.
- Safe attribution overuse is warning-only.
- Observation repetition families are grouped consistently.
- Clean control payloads can pass.
- Harness never calls LLMs.
- Harness never mutates payloads.

### Rendering Invariants

- `Finding.prose` remains backward-compatible.
- Observation and implication render visibly.
- Specific `Decision space` remains visible.
- Generic `Decision space` is hidden without changing payload or `Finding.prose`.
- Evidence chips remain visible when evidence URLs exist.

### EntityNarrativeState Invariants

- Output shape remains stable.
- `status.runtime_enabled` is always false.
- `used_by_scoring`, `used_by_prompts`, `used_by_rendering` are always false.
- No strategic claims are invented.
- Good-evidence cases do not force false tensions.
- Missing evidence URLs become coverage metrics, not editorial failures.
- Inactive budgets remain inactive or absent.
- Review-gated fields are not promoted to facts.
- Arbitrary evidence URLs are ignored as related surfaces.
- Name similarity alone is ignored.
- Explicit `observed_related_surfaces` are copied through with metadata.
- `needs_review` becomes true when any related surface requires review.
- Related surfaces do not create contradiction candidates.

### Coupling Invariants

- Narrative harness imports no scoring, renderer, prompt, runtime, or Visual Signature modules.
- Entity-state builder imports no scoring, renderer, prompt, runtime, or Visual Signature modules.
- Report renderer imports no entity-state builder.
- Dossier generation does not call entity-state builder.
- Persisted `report_narrative` format remains unchanged.

## Recommended Next Phase

Choose:

```text
builder hardening
```

Rationale:

- The harness is useful enough.
- The builder now compiles meaningful state.
- `observed_related_surfaces` works across Watermelon and Iris.
- Runtime integration is premature.
- Prompt refinement is still premature.
- More corpus collection would add signal, but the current risk is not lack of cases; it is contract stability.

Builder hardening should mean:

1. Freeze v0 output shape.
2. Add import/coupling tests if practical.
3. Add small tests around generated Watermelon/Iris-style inputs.
4. Decide whether excluded/noisy surfaces should remain fixture-only or become a separate optional state field.
5. Create a short artifact index so the research layer is navigable.

Builder hardening should not mean:

- adding new semantic fields,
- generating prose,
- feeding prompts,
- changing report rendering,
- scoring narrative quality.

## Explicit Non-Goals

Do not do these next:

- no runtime integration,
- no prompt rewrite,
- no scoring changes,
- no Visual Signature integration,
- no report payload migration,
- no broad report renderer redesign,
- no automatic contradiction detection,
- no automatic entity resolution,
- no LLM-based narrative judge,
- no narrative quality score,
- no production persistence of reviewer decisions,
- no use of related surfaces as verified aliases,
- no use of evidence URLs as entity surfaces.

## Final Recommendation

The architecture is coherent enough to keep.

It is not ready for product/runtime rollout.

It is ready for a short hardening phase whose main goal is to prevent drift:

```text
stabilize contracts,
protect invariants,
stop adding new concepts,
and keep all entity composition work offline.
```
