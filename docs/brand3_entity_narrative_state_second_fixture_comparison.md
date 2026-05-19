# Brand3 EntityNarrativeState Second Fixture Comparison

Date: 2026-05-16

Scope: offline fixture comparison only. No builder, prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, runtime wiring, or LLM calls were added.

## Executive Assessment

The Netlify fixture shows that the `EntityNarrativeState` shape can generalize beyond the Builtwith case, but only if several fields remain optional or explicitly inactive.

Builtwith tested a high-friction case:

- entity ambiguity between adjacent surfaces,
- high owned-claim density,
- repeated safe attribution,
- repeated corroboration caveats,
- generic Decision Space suppression.

Netlify tests a simpler fallback/control case:

- no meaningful entity ambiguity,
- no safe attribution overuse,
- no corroboration-caveat repetition,
- no `typical_decision` content,
- clear fallback evidence-opening repetition,
- partial evidence URL coverage.

That contrast is useful. It suggests that `EntityNarrativeState` should not be a fixed checklist where every field must be active. It should behave as a composition-risk state where some fields are required metadata and measured budgets, while others remain conditional.

## Fields That Generalized Well

`status` and `metadata` generalized cleanly.

They remain necessary because these fixtures can easily be mistaken for runtime logic. The Netlify fixture again needs explicit markers for offline, experimental, non-runtime, non-scoring, non-rendering, and non-prompt use.

`primary_entity_signal` generalized, with lower ambition.

In Builtwith, this field captured entity ambiguity. In Netlify, it captures a stable entity signal: Netlify as a serverless/builder platform with external coverage. The field is still useful, but it must allow different confidence levels and should not force tension or contradiction.

`entity_aliases` generalized after the naming adjustment.

The renamed `observed_related_surfaces` works better than `aliases_or_adjacent_surfaces`. In Netlify, the field records related surfaces without implying entity drift. That is the right semantic behavior.

`repeated_opener_budget` generalized strongly.

Builtwith and Netlify fail through different repetition families. Netlify confirms that repeated openings can remain visible even when rendering suppresses other repeated payload structures.

`fallback_language_budget` generalized strongly.

Netlify is the cleanest example so far of fallback evidence-opening repetition. The visible report repeats “the available sources” five times. This field is justified as a first-class budget.

`evidence_url_coverage` generalized strongly.

Both Builtwith and Netlify have findings without evidence URLs, even though the pattern manifests differently. This should remain a required diagnostic field.

`decision_space_mode` generalized as an advisory field, but not as an always-active field.

Netlify contains no `typical_decision` text, so the correct state is `not_applicable_empty`. That confirms the field should exist, but should support inactive modes.

## Fields That Felt Builtwith-Specific

`owned_claim_density` remains useful, but it is inactive in Netlify.

Netlify has zero safe attribution overuse. The field should stay, but the shape should allow a low or inactive state without implying a problem.

`attribution_budget` is Builtwith-specific in the current sample set.

It is justified for cases with repeated owned-claim framing, but should be conditional. In Netlify, it adds clarity only because it says the budget is not applicable.

`corroboration_caveat_budget` is also conditional.

Builtwith needs it. Netlify does not. The field should not be required unless the harness detects that repetition family.

`contradiction_candidates` did not activate.

Netlify does not provide a clear stated-claim-versus-observed-signal contradiction. Keeping an empty list plus a status note is better than manufacturing a contradiction.

## Fields That Became Optional

These should be optional or inactive unless supported by diagnostics:

- `attribution_budget`
- `corroboration_caveat_budget`
- `contradiction_candidates`
- `primary_tension`
- `compression_candidates`

`primary_tension` is the most delicate field. The Netlify payload says there is a tension around strong presence and limited differentiation, but there is no separate `tensions_prose`. The fixture marks it low confidence and requires human review. That should remain the standard for manually consolidated tensions.

## Shape Adjustments Applied

The second fixture applies the review recommendations:

- `aliases_or_adjacent_surfaces` is avoided in favor of `observed_related_surfaces`.
- `source_ownership_summary` includes `method: manual_estimate`.
- `findings_to_compress_or_demote` is represented as `compression_candidates`.
- every compression item is marked `suggested_only`.
- `primary_tension` includes `requires_human_review`.

These changes make the artifact less operational and more diagnostic.

## Is The Shape Stabilizing?

Partially.

The stable core appears to be:

- `status`
- `metadata`
- `primary_entity_signal`
- `entity_aliases.observed_related_surfaces`
- `owned_claim_density`
- `source_ownership_summary`
- `repeated_opener_budget`
- `fallback_language_budget`
- `evidence_url_coverage`
- `decision_space_mode`

The conditional layer appears to be:

- `attribution_budget`
- `corroboration_caveat_budget`
- `primary_tension`
- `contradiction_candidates`
- `compression_candidates`

The shape is still too expressive for automation. It is appropriate for offline fixtures and design exploration, not for a builder.

## What Changed Compared With Builtwith

Builtwith turned the state into a warning map for owned-claim dependency and entity ambiguity.

Netlify turns the state into a warning map for fallback repetition and partial evidence coverage.

That means the state can represent more than one failure mode, but the fixture author must keep inactive fields explicit. Otherwise, the shape risks making every report look like it has every possible narrative failure.

## What Should Not Be Automated Yet

Do not automate `primary_tension`.

The Netlify example shows why: the payload contains a tension-like sentence, but the evidence is too compact to promote it into a reliable entity-level state without review.

Do not automate `compression_candidates`.

The candidates are useful as editorial hypotheses, not rewrite instructions.

Do not automate source ownership counts from this fixture shape.

`source_ownership_summary.method` is still `manual_estimate`. A real source classifier would need a separate design step.

Do not convert inactive fields into failures.

The second fixture proves that absence is informative. A clean `attribution_budget` or empty `contradiction_candidates` field should not be treated as missing analysis.

## Recommended Next Step

Create one more fixture before implementing any builder.

The third fixture should be neither Builtwith-like nor Netlify-like. It should use a report with stronger evidence URL coverage and less fallback language, if available. That would test whether the shape can represent a relatively healthy narrative state without becoming a list of forced warnings.

Only after three fixtures should Brand3 define a minimal JSON contract for future `EntityNarrativeState` candidates.
