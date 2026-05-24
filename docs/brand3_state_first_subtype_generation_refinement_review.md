# Brand3 State-First Subtype Generation Refinement Review

Date: 2026-05-17

Scope: lab-only refinement review. No runtime integration, prompt rollout, scoring change, renderer change, report mutation or Visual Signature change.

## Purpose

The side-by-side comparison showed that the deterministic prose generator preserved epistemic structure, but Iris and Watermelon still read like protected templates. This pass refined only the two ambiguity-heavy pressure subtypes:

- `name_collision`
- `ecosystem_surface_pressure`

`stable_entity_evidence_binding` was intentionally left unchanged.

## What Changed

The generator now uses dimension-specific narrative moves for the two strong ambiguity subtypes.

For `name_collision`, the prose now separates:

- audited surface coherence,
- owned speed/value positioning,
- visibility and interpretation risk,
- footprint ambiguity,
- activity/vitality evidence that must not be imported from other Iris-named surfaces.

For `ecosystem_surface_pressure`, the prose now separates:

- owned story,
- owned differentiation claim,
- surface noise versus brand signal,
- relation-type footprint mapping,
- vitality signals that must not become roadmap, traction or growth.

## Iris

Previous generated output:

The earlier generator repeated the same frame across most dimensions:

```text
The [dimension] reading should start from https://irisdesign.dev and keep similarly named Iris surfaces separate...
```

Refined generated output:

The new output keeps the same safety boundary, but changes the dimension logic:

- `coherencia`: anchor the entity story to `irisdesign.dev`.
- `diferenciacion`: treat speed/value as owned positioning, not proven market position.
- `percepcion`: treat Iris-name overlap as visibility and interpretation risk.
- `presencia`: separate primary audited domain from unresolved Iris-like surfaces.
- `vitalidad`: do not import activity from AI, agency or collaborative Iris surfaces.

Assessment:

The refined output is closer to the manual state-first candidate. It still lacks the editorial compression and nuance of the manual version, but it no longer sounds like one repeated safety sentence.

## Watermelon

Previous generated output:

The earlier generator repeated the same broad ecosystem warning across most dimensions:

```text
The [dimension] reading should separate the owned promise on https://watermelon.sh from adjacent domains, repositories, and marketplace surfaces...
```

Refined generated output:

The new output makes each dimension do a different job:

- `coherencia`: owned story first; no verified ecosystem architecture.
- `diferenciacion`: infrastructure claim as owned claim; no verified category advantage from repository/marketplace context.
- `percepcion`: surface noise and brand signal are separated.
- `presencia`: surfaces are mapped by relation type.
- `vitalidad`: repository/listing/adjacent-domain activity does not prove momentum.

Assessment:

The refined output is materially better. It is still deterministic and cautious, but it now exposes the ecosystem ambiguity more clearly instead of repeating the same defensive clause.

## Comparison To Manual Candidates

The refined generator is not equal to the manual candidates.

Manual prose still wins on:

- editorial compression,
- case-specific judgment,
- cadence,
- cleaner transitions,
- avoiding mechanical dimension labels.

The refined generator now wins over the previous generator on:

- specificity,
- dimension differentiation,
- reduced middleware language,
- clearer subtype logic,
- preserving the same evidence discipline.

## Epistemic Discipline

The refinement preserved the core guardrails:

- no inferred ownership,
- no inferred aliases,
- no ecosystem architecture inference,
- no roadmap inference,
- no traction inference,
- no strategic duality language from name collision,
- strong ambiguity cases remain human-review gated.

The main remaining risk is not overreach. The main remaining risk is still prose quality: the generator is safer and more specific, but not yet a polished human-facing Brand3 reading.

## Recommendation

Keep the generator lab-only.

The refined subtype logic is now strong enough to continue testing as a Lab candidate, but not strong enough to replace manual state-first prose or official Brand Audit findings.

Next useful step:

```text
rerun the side-by-side comparator after refinement
```

That comparison should decide whether the refined generator is good enough to appear as a clearly marked Lab-applied reading candidate, or whether it should remain internal planning/prose scaffolding only.
