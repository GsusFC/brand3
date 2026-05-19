# Brand3 Watermelon Observed Related Surfaces Builder Pass Review

Date: 2026-05-17

Scope: offline builder passthrough review only. No runtime integration, prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, or LLM calls were changed.

## What Changed

The offline `EntityNarrativeState` builder v0 now accepts explicit structured `observed_related_surfaces` metadata from snapshot/base dossier input and copies it into:

```text
state.entity_aliases.observed_related_surfaces
```

The Watermelon `.v0` output was regenerated using the manual reviewed input:

```text
examples/reports/narrative_harness/entity_state/inputs/watermelon.observed_related_surfaces.input.json
```

## Watermelon Output Result

The regenerated state now classifies Watermelon as:

```text
case_family: multi_surface_or_entity_review
```

and carries reviewed surfaces including:

- `watermelon.ai`
- `watermelon.market`
- `watermelon.us`
- `developer.watermelon.ai`
- `github.com/watermelontools`
- `github.com/watermeloncorp/watermellon-registry`
- `producthunt.com/products/watermelon`

Each surface preserves:

- `relation_type`
- `evidence`
- `confidence`
- `requires_human_review`
- `source`
- `notes` when present

Because every manual surface requires review, the builder sets:

```text
entity_aliases.needs_review: true
```

## What Improved

The builder can now represent the Watermelon entity/surface ambiguity that the Phase 2 memo identified.

Before this pass, Watermelon had:

```text
observed_related_surfaces: []
case_family: owned_claim_repetition
```

After this pass, the state better reflects the case's actual composition pressure:

```text
observed_related_surfaces: populated from reviewed input
case_family: multi_surface_or_entity_review
```

This is a better fit for Watermelon because the core risk is not only safe attribution or evidence binding. It is also ecosystem hierarchy and adjacent-surface ambiguity.

## What Stayed Safe

The builder still does not infer related surfaces.

It ignores:

- arbitrary evidence URLs,
- `related_domains`,
- `discovered_domains`,
- name similarity alone,
- search co-occurrence,
- report prose speculation.

It also does not:

- infer ownership,
- treat related surfaces as aliases,
- create contradiction candidates from related surfaces alone,
- mutate payloads,
- affect rendering,
- affect scoring,
- affect prompts,
- affect runtime.

## Remaining Limits

The builder still depends on upstream explicit metadata.

If `observed_related_surfaces` is not provided, Iris/Watermelon-style ambiguity remains invisible to the state object. That is still preferable to unsafe inference.

The builder also does not yet distinguish:

- verified related surfaces,
- possible related surfaces,
- search noise,
- excluded surfaces.

That distinction exists in the manual input fixture, but the builder currently passes only the observed surface list into state.

## Recommendation

This passthrough behavior is safe enough for offline diagnostics.

The next step should be another manual input fixture, likely Iris, before expanding the builder further. That would test whether the same contract can represent a more ambiguous, name-collision-heavy surface set without producing false equivalence.
