# Brand3 State-First Generator v0 Planning Layer Review

Date: 2026-05-17

Scope: lab-only planning-layer refinement for the offline state-first findings generator. No runtime integration, prompt rollout, scoring change, renderer change, report mutation, persisted payload change, Visual Signature change, UI change, new intervention mode, or LLM call was introduced.

## Why This Change Exists

The v0 generator already selected the right executive mode for the five research cases:

- Builtwith / Kit: `strong`
- Iris: `strong`
- Watermelon: `strong`
- LaunchDarkly: `light`
- Netlify mock: `light`

But the generated planning layer was still too generic. Iris and Watermelon both appeared as related-surface cases, even though their risks are different:

- Iris: name-collision ambiguity.
- Watermelon: ecosystem and adjacent-surface ambiguity.

The generator now keeps the same mode system, but adds a planning subtype inside `state_first_finding_plan`.

## Added Planning Fields

Each output now includes:

- `state_first_finding_plan.pressure_subtype`
- `state_first_finding_plan.planning_focus`
- subtype-specific `coordination_rules`
- subtype-specific `caveat_strategy`
- subtype-specific `evidence_binding_strategy`
- subtype-specific overreach suppression rules

This does not add scoring and does not create a richer intervention mode. The subtype explains what the mode is trying to protect.

## Current Planning Subtypes

| Case | Mode | Planning subtype | Meaning |
|---|---:|---|---|
| Builtwith / Kit | `strong` | `entity_boundary_collision` | The main risk is a mixed entity frame, not a reviewed ecosystem. |
| Iris | `strong` | `name_collision` | Similarly named surfaces must not become aliases or shared strategy. |
| Watermelon | `strong` | `ecosystem_surface_pressure` | Product, developer, repository and marketplace surfaces must stay separated. |
| LaunchDarkly | `light` | `stable_entity_evidence_binding` | The entity is stable; state-first should only coordinate proof distribution. |
| Netlify mock | `light` | `fallback_compression` | The useful intervention is centralizing fallback evidence language. |

## What Improved

### Builtwith / Kit

The global caveat no longer says “related surfaces” generically. It now frames the issue as a mixed entity boundary:

```text
State-first reading keeps the mixed entity frame visible and does not merge adjacent brand surfaces into one strategy.
```

That is closer to the actual failure: false entity merge.

### Iris

Iris now receives a name-collision plan:

- do not convert name similarity into aliases,
- do not let visual/perceptual confidence become evidentiary confidence,
- bind claims to the audited domain unless a reviewed related surface supports local ambiguity.

This keeps the generator from turning multiple Iris-like domains into one implied architecture.

### Watermelon

Watermelon now receives an ecosystem-surface plan:

- separate product, developer, repository and marketplace surfaces,
- do not infer ecosystem ownership,
- bind each finding to its own surface before making ecosystem-level claims.

This is materially different from Iris.

### LaunchDarkly

LaunchDarkly stays light. The planning focus is proof distribution, not invented ambiguity:

```text
keep intervention light and use state only to coordinate proof distribution
```

This protects the restraint principle for healthy cases.

### Netlify Mock

Netlify stays light, but now clearly as fallback compression:

```text
centralize fallback evidence language and avoid repeating thin-source openings
```

That makes the candidate useful without pretending the case has richer entity state than it does.

## What This Still Does Not Solve

This is still a planning skeleton.

It does not:

- generate final Brand3 prose,
- decide production readiness,
- fix missing evidence URLs,
- classify evidence source quality beyond available diagnostics,
- perform real perceptual overreach gating,
- replace human review.

## Risk

The main risk is that subtypes start to look like editorial truth. They are not. They are deterministic planning labels derived from explicit state and diagnostics.

The safe use is:

```text
mode = how much intervention is allowed
pressure subtype = what the intervention must protect against
```

## Recommendation

Keep the three modes.

Keep the pressure profile.

Keep the new planning subtype.

The next meaningful test is not more taxonomy. It is whether a lab-only prose generator can use this planning layer to produce one real state-first finding set without:

- inventing confidence,
- deleting uncertainty,
- collapsing related surfaces,
- or overcomplicating healthy cases.
