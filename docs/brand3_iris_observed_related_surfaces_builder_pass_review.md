# Brand3 Iris Observed Related Surfaces Builder Pass Review

Date: 2026-05-17

Scope: offline builder-output review only. No runtime integration, prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, or LLM calls were changed.

## What Changed

The Iris `EntityNarrativeState` v0 output was regenerated using the reviewed manual input:

```text
examples/reports/narrative_harness/entity_state/inputs/iris.observed_related_surfaces.input.json
```

The regenerated output is:

```text
examples/reports/narrative_harness/entity_state/iris.entity_narrative_state.v0.json
```

## Iris Output Result

Iris is now classified as:

```text
case_family: multi_surface_or_entity_review
```

The state carries six observed related surfaces:

- `irisdesign.in`
- `irisdigital.design`
- `byiris.io`
- `heyiris.ai`
- `iris-ai.dev`
- `irisdesigncollaborative.com`

All six are marked:

```text
relation_type: ambiguous_name_match
confidence: low
requires_human_review: true
source: manual_review
```

The builder also preserves the notes explaining that these are name-collision/entity-composition pressure signals, not verified aliases or owned surfaces.

## Explicit Safety Checks

The regenerated Iris state preserves the intended boundaries:

- no ownership inference,
- no entity equivalence inference,
- no alias assertion,
- no contradiction candidates created from ambiguous surfaces,
- `entity_aliases.needs_review: true`,
- primary tension remains review-gated when present,
- runtime/scoring/prompt/rendering flags remain false.

The output keeps:

```text
contradiction_candidates: []
```

That is important. Ambiguous surfaces create composition pressure, but they are not sufficient evidence for a contradiction.

## Iris vs Watermelon

### Watermelon ambiguity pressure

Watermelon is ecosystem ambiguity.

Its reviewed surfaces include a mixture of:

- adjacent domains,
- developer surface,
- repository surfaces,
- marketplace profile.

The surface set suggests a broader product/ecosystem hierarchy question:

```text
Which surfaces belong to the same ecosystem, and which are adjacent or noisy?
```

Watermelon therefore tests whether the builder can carry mixed relation types without collapsing them into aliases.

### Iris ambiguity pressure

Iris is name-collision ambiguity.

All reviewed surfaces are:

```text
ambiguous_name_match
```

The surface set suggests a different question:

```text
How much of the discovered evidence is actually about this Iris?
```

Iris therefore tests whether the builder can represent ambiguity without pretending that similarly named design/AI surfaces are related.

## `ambiguous_name_match` vs `adjacent_domain`

`adjacent_domain` means the surface is plausibly close to the audited entity but still unverified.

Example from Watermelon:

```text
watermelon.ai
```

`ambiguous_name_match` is weaker. It means the surface appeared in the same discovery neighborhood because of naming overlap, but relation is not established.

Examples from Iris:

```text
heyiris.ai
iris-ai.dev
irisdesigncollaborative.com
```

The builder preserves this distinction because it passes through `relation_type` instead of flattening all entries into strings.

## How The Builder Behaves Differently

For Watermelon, the builder receives mixed relation types and sets the case family to `multi_surface_or_entity_review`.

For Iris, the builder receives only low-confidence ambiguous name matches and still sets the same case family, but without increasing confidence or creating stronger state claims.

This is the desired behavior:

- both cases require entity review,
- Watermelon looks like ecosystem ambiguity,
- Iris looks like name-collision ambiguity,
- neither becomes verified aliasing.

## What Remains Intentionally Unknown

The builder does not know:

- whether any Iris surface is owned by `irisdesign.dev`,
- whether `heyiris.ai` or `iris-ai.dev` are part of the audited entity,
- whether `irisdesign.in` or `irisdigital.design` are competitors, aliases, unrelated projects, or search noise,
- whether visual/perceptual identity belongs to the same entity across surfaces,
- whether the ambiguity should change scoring or recommendations.

Those remain review questions, not builder facts.

## Does The Same Contract Represent Both Cases Safely?

Yes.

The same `observed_related_surfaces` contract represents:

- Watermelon ecosystem ambiguity,
- Iris name-collision ambiguity.

It does so safely because relation type, confidence, source and review flags travel with each surface. The builder does not infer ownership, equivalence or contradiction from the existence of related surfaces.

## Remaining Limit

The builder currently passes through the observed surface list but does not preserve the `excluded_surfaces` section from the manual input fixture.

That is acceptable for v0 because excluded surfaces are review context, not current state. If excluded/noisy surfaces become important for future entity diagnostics, they should be added through a separate field rather than mixed into `observed_related_surfaces`.

## Recommendation

The contract is now validated across two different ambiguity shapes:

- Watermelon: ecosystem / adjacent-surface ambiguity.
- Iris: name-collision / search-discovery ambiguity.

No runtime integration should follow yet.

The next useful step is a small offline review of whether `EntityNarrativeState` should preserve excluded/noisy surfaces as a separate diagnostic field, or leave that context in the manual input fixtures only.
