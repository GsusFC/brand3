# Brand3 State-First Prose Candidates Review

Date: 2026-05-17

Scope: review only. No generator implementation, runtime integration, prompt rollout, scoring change, renderer change, report mutation or Visual Signature change.

## Reviewed Candidates

| Case | Mode | Pressure subtype | Result |
|---|---:|---|---|
| Iris | `strong` | `name_collision` | Better than baseline. Prevents similarly named Iris surfaces from becoming aliases or one implied strategy. |
| Watermelon | `strong` | `ecosystem_surface_pressure` | Better than baseline. Prevents ecosystem adjacency from becoming false brand architecture. |
| LaunchDarkly | `light` | `stable_entity_evidence_binding` | Moderately better. Preserves stable entity signal and improves proof distribution without inventing tension. |

## Core Answer

The improvements are not merely manual/editorial.

The writing is manual, but the improvement pattern is structural:

```text
audited surface
+ pressure subtype
+ evidence map
+ uncertainty model
+ dimension role
→ bounded finding candidate
```

The candidates repeatedly improve the baseline by:

- anchoring the audited surface first,
- separating related or ambiguous surfaces,
- centralizing the main caveat,
- binding each dimension to evidence,
- naming what remains uncertain,
- stating what was not inferred.

That is enough to justify a lab-only prose generator v0.

It is not enough to justify production runtime integration.

## Repeatable Prose Moves

### 1. Global Caveat

All three candidates use one governing caveat before dimension prose.

- Iris: name-collision surfaces are not aliases.
- Watermelon: ecosystem surfaces are not proof of shared ownership.
- LaunchDarkly: stable entity should not be overcomplicated.

This is highly automatable.

Risk: if templated poorly, it becomes another boilerplate paragraph.

### 2. Audited Surface Anchor

Each candidate names the audited surface and treats it as the primary evidence boundary:

- `irisdesign.dev`
- `watermelon.sh`
- `launchdarkly.com`

This is highly automatable if the target URL is reliable.

Risk: unsafe if target/entity metadata is missing or contaminated.

### 3. Related Surface Boundary

The strong cases separate adjacent surfaces from ownership:

- Iris: similar names create collision pressure.
- Watermelon: adjacent domains, GitHub and marketplace surfaces create ecosystem pressure.

This is automatable only when `entity_resolution.related_surfaces` metadata is explicit and reviewed.

It must not be inferred from arbitrary evidence URLs.

### 4. Owned Claim Boundary

All cases treat owned claims as positioning, not proof.

This is safe and repeatable.

Risk: repeated owned-claim caveats can create the same defensive cadence that started this work. The generator should state this once globally, then apply it locally only when needed.

### 5. Missing Evidence Boundary

The candidates do not turn missing evidence URLs into a negative strategic finding.

They mark them as coverage limits.

This is important. It prevents the system from punishing brands for extraction gaps or incomplete evidence maps.

### 6. Overreach Avoided

Each candidate explicitly names suppressed inference:

- no false aliases,
- no ecosystem ownership inference,
- no roadmap inference,
- no market-leadership leap,
- no visual confidence as evidentiary confidence.

This is useful for Lab output.

It should not be rendered directly as production report prose yet.

## Case-Specific Moves

### Iris

Structural move:

```text
similarly named Iris surfaces ≠ aliases
```

The candidate separates:

- audited design surface,
- agency-like Iris surfaces,
- AI/open-source Iris surfaces,
- collaborative Iris surfaces.

This prevents false strategic duality.

### Watermelon

Structural move:

```text
ecosystem evidence ≠ owned brand architecture
```

The candidate separates:

- owned surface,
- adjacent domains,
- GitHub repositories,
- marketplace listings,
- unrelated watermelon references.

This prevents false ecosystem coherence.

### LaunchDarkly

Structural move:

```text
stable entity + proof gaps ≠ hidden strategic problem
```

The candidate keeps the baseline stable and intervenes only on:

- owned-claim boundaries,
- missing finding-level evidence,
- activity evidence versus market outcome claims.

This is the most important restraint test.

## Are Pressure Subtypes Enough?

For three reviewed subtypes, yes:

- `name_collision`
- `ecosystem_surface_pressure`
- `stable_entity_evidence_binding`

They are enough to guide the shape of prose because each maps to a distinct protection rule:

- prevent false aliasing,
- prevent false ecosystem ownership,
- prevent false complexity.

Two subtypes still need prose trials before confidence:

- `entity_boundary_collision` for Builtwith / Kit,
- `fallback_compression` for Netlify mock.

## What A Generator Could Safely Write

### Safe

- global caveat,
- audited-surface boundary,
- evidence-used list,
- evidence-bound dimension candidate,
- uncertainty retained,
- overreach avoided,
- lab-only verdict.

### Conditional

Dimension finding prose is safe only if:

- it uses the pressure subtype,
- it cites evidence boundaries,
- it does not introduce new strategy,
- it stays compact when evidence is missing,
- it preserves human-review flags.

### Not Safe

The generator should not write:

- final production report prose,
- strategic recommendations,
- market position claims,
- intentional brand architecture claims,
- ownership conclusions,
- public reputation claims,
- Visual Signature interpretation beyond explicit signal boundaries.

## Where Automation Would Be Unsafe

Unsafe zones:

- inferring ownership from domain similarity,
- inferring roadmap from repository presence,
- inferring traction from marketplace listings,
- using visual confidence as evidence confidence,
- treating missing evidence as negative performance,
- applying strong mode to stable cases,
- replacing official report findings without review.

## Recommendation

Proceed to a lab-only prose generator v0.

Do not move to runtime.

Do not rewrite production prompts yet.

Do not treat this as report replacement.

The generator should create candidate findings in the same artifact shape as the manual candidates, and then compare generated output against these three manual references.

## Required Guardrails

The generator v0 must:

- abstain when audited surface is unknown,
- use explicit related-surface metadata only,
- keep strong-mode ambiguity cases review-gated,
- keep light-mode stable cases light,
- include `evidence_used` or `missing_evidence_note` for every dimension,
- include `uncertainty_retained`,
- include `overreach_avoided`,
- avoid generic Decision Space language,
- avoid using scores as evidence,
- mark all output as lab-only and not production-ready.

## Decision

```text
implement lab-only prose generator v0
```

The manual candidates show enough repeatable structure to justify implementation.

The next implementation should be small and reversible:

- one pure module,
- no runtime wiring,
- no prompt rollout,
- no renderer changes,
- no scoring changes,
- no Visual Signature changes.
