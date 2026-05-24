# Brand3 State-First Generator v0 Pressure Profile Review

Date: 2026-05-17

Scope: review of lab-only pressure-profile output. No runtime integration, prompt rollout, scoring change, renderer change, report mutation, persisted payload change, Visual Signature change, UI change, new intervention mode, or LLM call was introduced.

## Purpose

The state-first generator originally used three intervention modes:

- `none`
- `light`
- `strong`

That remains useful as the executive decision, but it is too compressed to explain why cases differ.

The generator now adds:

- `generation_decision.intervention_reasons`
- `generation_decision.pressure_profile`

This keeps the mode simple while making the diagnostic basis explicit.

## Why Three Modes Still Work

The modes should not model case richness.

They answer only one operational question:

```text
how much state-first intervention is allowed?
```

- `none`: do not generate.
- `light`: improve evidence/caveat discipline without rewriting the entity reading.
- `strong`: govern findings through shared entity/evidence/uncertainty state.

That remains the right abstraction for v0.

## Why Pressure Profile Was Needed

Without pressure profile, `strong` hid important differences:

- Builtwith / Kit: entity boundary plus owned-claim/caveat pressure.
- Iris: name-collision/related-surface pressure plus visual/perceptual overreach risk.
- Watermelon: ecosystem/related-surface pressure.

Similarly, `light` needed to distinguish:

- LaunchDarkly: healthy entity with proof-distribution pressure.
- Netlify mock: fallback repetition with thin finding-level evidence.

The profile prevents `strong` and `light` from becoming vague buckets.

## Current Case Profiles

| Case | Mode | Key reasons | Profile summary |
|---|---|---|---|
| Builtwith / Kit | `strong` | `entity_boundary_risk`, `owned_claim_repetition`, `external_corroboration_caveat_inflation`, `missing_finding_level_evidence` | Entity boundary high, caveat/owned/fallback/generic pressure high, related-surface pressure inactive. |
| Iris | `strong` | `related_surface_review_required`, `owned_claim_repetition`, `visual_or_perceptual_overreach` | Related-surface pressure high, name-collision pressure high, visual/perceptual risk medium. |
| Watermelon | `strong` | `related_surface_review_required`, `external_corroboration_caveat_inflation`, `generic_decision_space` | Ecosystem/related-surface pressure high, evidence/caveat pressure high. |
| LaunchDarkly | `light` | `stable_entity_restraint`, `missing_finding_level_evidence`, `owned_claim_repetition` | Entity boundary inactive, restraint high, evidence/caveat pressure still high. |
| Netlify mock | `light` | `fallback_repetition`, `missing_finding_level_evidence`, `stable_entity_restraint` | Fallback repetition medium, evidence binding medium, entity boundary inactive. |

## What The Profile Reveals

### Builtwith / Kit

Builtwith / Kit is not just a generic `strong` case.

Its profile says:

- entity boundary is high,
- caveat inflation is high,
- owned-claim repetition is high,
- related-surface pressure is inactive.

That distinction matters. The issue is not a reviewed ecosystem of related surfaces. The issue is a collision between strong owned narratives and target identity.

### Iris

Iris has high related-surface pressure.

That separates it from Builtwith / Kit. The risk is name-collision inflation: similarly named surfaces can become false aliases or false brand architecture.

The profile also marks visual/perceptual overreach as medium, which is directionally useful, but still coarse.

### Watermelon

Watermelon also has high related-surface pressure, but its pressure is ecosystem-shaped rather than name-collision-only.

The profile correctly puts it in `strong`, but the current fields do not yet distinguish ecosystem ambiguity from name-collision ambiguity. That remains a limitation.

### LaunchDarkly

LaunchDarkly is the most important restraint case.

The profile shows:

- entity boundary inactive,
- related-surface pressure inactive,
- healthy-case restraint high,
- evidence/caveat pressure still high.

That explains why the mode is `light`, not `strong`. The generator sees narrative pressure, but not entity ambiguity.

### Netlify Mock

Netlify remains a fallback-control case.

The profile shows:

- fallback repetition medium,
- evidence binding medium,
- healthy-case restraint high,
- owned/caveat/generic decision pressure inactive.

That supports `light`. A stricter future version might choose `none` if the evidence map is too thin.

## Strong Generation Pressure

Profiles indicate strong generation pressure when:

- `entity_boundary` is high,
- or `related_surface_pressure` is medium/high,
- especially when combined with evidence binding and caveat inflation.

Current strong cases:

- Builtwith / Kit
- Iris
- Watermelon

## Restraint Pressure

Profiles indicate restraint when:

- `entity_boundary` is inactive,
- `related_surface_pressure` is inactive,
- `healthy_case_restraint` is high,
- and the remaining issues are evidence/caveat/fallback rather than entity collapse.

Current restraint cases:

- LaunchDarkly
- Netlify mock

## What Remains Too Coarse

### 1. Visual / Perceptual Overreach

The current detector is lexical. It can mark medium pressure when words like visual, perceptual, aesthetic, motion, or brand identity appear.

That is enough for v0 explanation, but not enough for serious perceptual gating.

It should not affect mode selection yet.

### 2. Ecosystem vs Name Collision

`related_surface_pressure` does not yet distinguish:

- ecosystem ambiguity,
- name collision,
- adjacent product surfaces,
- developer surfaces,
- repository surfaces.

The raw related-surface metadata contains this, but the profile compresses it.

### 3. Evidence Binding Severity

Evidence binding is currently based on missing finding-level URLs. That is useful, but incomplete.

It does not yet know whether the attached evidence is strong, owned, third-party, stale, ambiguous, or overused.

### 4. Healthy Case Restraint

`healthy_case_restraint` is useful, but should remain advisory. It prevents overstructuring, but it must not hide real evidence-binding issues.

## Recommendation

Keep the three modes.

Keep pressure profile as explanatory metadata.

Do not add more intervention modes yet.

The next useful improvement is not more levels. It is sharper pressure dimensions:

- separate `name_collision_pressure` from `ecosystem_pressure`,
- improve `visual_or_perceptual_overreach`,
- improve evidence-source quality beyond missing URLs.

But those should wait until the generator v0 proves useful as a planning layer.

