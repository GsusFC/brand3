# Brand3 EntityNarrativeState Fixture Review

Date: 2026-05-16

Scope: fixture-shape review only. No builder, prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, runtime wiring, or LLM calls were added.

## Executive Assessment

The first offline `EntityNarrativeState` fixture is useful as a bridge between diagnostics and future architecture.

It does the right thing conceptually:

- keeps the state offline and experimental,
- avoids scoring and runtime use,
- represents measured narrative/cohesion failures,
- marks entity ambiguity and strategic uncertainty,
- keeps dangerous strategic inference out of scope.

The shape can generalize, but not exactly as-is. Some fields are clearly diagnostic and reusable. Others are case-specific, too hand-authored, or need tighter semantics before a second fixture.

The fixture should not become a builder target yet.

## Clearly Justified Fields

These fields are strongly supported by measured diagnostics and should remain in the shape.

### `status`

Justified.

This is essential because the artifact must remain visibly non-runtime:

- `runtime_enabled: false`
- `used_by_scoring: false`
- `used_by_prompts: false`
- `used_by_rendering: false`
- `persisted_report_narrative: false`

This field should be required.

### `metadata`

Justified.

The `created_from` list is important because the fixture is manually derived. Without provenance, the state could be mistaken for generated truth.

This field should be required.

### `primary_entity_signal`

Justified, but needs stricter semantics.

Builtwith shows entity ambiguity between `builtwith.kit.com`, `kit.com`, and BuiltWith surfaces. Capturing that ambiguity is useful.

Required fields should be:

- `label`
- `confidence`
- `supporting_sources`
- `uncertainty`

Optional fields:

- `supporting_payload_findings`

### `entity_aliases`

Justified.

This is one of the most reusable fields because entity drift and adjacent domains are common in web audits.

It should be required, but the naming should change from `aliases_or_adjacent_surfaces` to something more cautious:

```text
observed_related_surfaces
```

Reason: "alias" can imply verified equivalence. The fixture correctly warns against that, but the field name should avoid overclaiming.

### `owned_claim_density`

Strongly justified.

Directly derived from:

- `safe_attribution_repetition: 11`
- visible safe attribution total: 11

This should be required.

### `repeated_opener_budget`

Strongly justified.

Builtwith and Netlify fail in different repeated opening families. This field should exist across cases.

This should be required, but it should remain budget/diagnostic only, not prose-control logic yet.

### `attribution_budget`

Strongly justified.

Builtwith repeats owned-claim attribution enough to justify a global caveat preference.

This should be required when owned-claim density is moderate or high, optional otherwise.

### `corroboration_caveat_budget`

Strongly justified.

Builtwith has 14 external corroboration caveat family matches.

This should be required when external corroboration caveat repetition exceeds the threshold, optional otherwise.

### `fallback_language_budget`

Justified.

Netlify shows this pattern clearly. Builtwith also shows evidence-pool phrase repetition, but not as a pure fallback case.

This field should be required, but it needs a `mode` distinction:

```text
fallback_mode: true | false
fallback_like_repetition: true | false
```

### `evidence_url_coverage`

Strongly justified.

Both warning cases have findings without evidence URLs. This is one of the cleanest measurable fields.

This should be required.

### `decision_space_mode`

Justified.

The conditional render experiment gives concrete evidence:

- 13 payload `typical_decision` values
- 9 generic `teams in this position typically`
- 0 visible `Decision space` after suppression

This field should be required, but only as advisory.

## Useful But Needs Narrower Semantics

### `source_ownership_summary`

Useful, but currently too hand-authored.

The count estimates are approximate and not produced by a real source classifier. That is acceptable in a fixture, but the field should not imply precision.

Recommended change before the next fixture:

```json
"source_ownership_summary": {
  "method": "manual_estimate",
  "owned_or_self_description": {},
  "third_party_or_external_assessment": {},
  "technical_or_configuration": {},
  "uncited_or_missing_evidence_url": {}
}
```

Each bucket should carry:

- `count_estimate`
- `confidence`
- `sources`
- `notes`

This field should be optional until source classification is more formal.

### `primary_tension`

Useful, but interpretive.

The current field is reasonable because it uses evidence-backed language and uncertainty. Still, it combines several concerns:

- owned positioning,
- external trust/safety signals,
- entity ambiguity.

Before a second fixture, the shape should allow multiple candidate tensions or mark whether the tension is consolidated manually.

Recommended structure:

```json
"primary_tension": {
  "summary": "...",
  "source": "manual_synthesis",
  "confidence": "medium",
  "requires_human_review": true
}
```

This field should be optional until more cases confirm it generalizes.

### `contradiction_candidates`

Useful, but must remain evidence-anchored.

This field is valuable because it separates stated claims from observed signals. It should remain, but every candidate should require:

- `stated_claim`
- `observed_signal`
- `supporting_sources`
- `confidence`
- `requires_human_review`

This field should be optional. Some cases may have no contradiction candidates.

### `findings_to_compress_or_demote`

Useful, but the most premature operational field.

It starts to sound like an action plan. That is not wrong, but it is closer to future composition behavior than diagnosis.

For now, rename conceptually to:

```text
compression_candidates
```

Each item should distinguish:

- measured reason,
- editorial reason,
- confidence,
- whether action is allowed or only suggested.

This should be optional and should always require review.

## Fields That Feel Too Interpretive Or Premature

No field is obviously dangerous if kept offline, but these are closest to overreach:

- `primary_tension`
- `contradiction_candidates`
- `findings_to_compress_or_demote`
- `source_ownership_summary.count_estimate`

Why:

- They require manual synthesis.
- They can imply entity resolution where only ambiguity is known.
- They may become automatic too early.

They should stay optional and review-gated.

## Redundant Fields

Some budgets overlap but should not be removed yet.

### `owned_claim_density` vs `attribution_budget`

Not redundant.

- `owned_claim_density` describes the evidence/narrative condition.
- `attribution_budget` describes the future composition constraint.

### `corroboration_caveat_budget` vs `attribution_budget`

Partially overlapping.

`based only on self-description` appears in both families. That is acceptable because it performs two jobs:

- owned-claim attribution,
- lack-of-corroboration caveat.

The fixture should keep both, but future docs should explain that phrase overlap is intentional.

### `repeated_opener_budget` vs family budgets

Not redundant.

Repeated opener budget catches syntax repetition. Family budgets catch semantic repetition.

Both are needed.

## Required vs Optional Fields

### Required For Every Fixture

- `version`
- `status`
- `metadata`
- `primary_entity_signal`
- `entity_aliases` or renamed `observed_related_surfaces`
- `owned_claim_density`
- `repeated_opener_budget`
- `fallback_language_budget`
- `evidence_url_coverage`
- `decision_space_mode`
- `explicit_non_goals`

### Conditional Required

- `attribution_budget`
  - required when owned-claim density is moderate/high.

- `corroboration_caveat_budget`
  - required when corroboration caveat family count exceeds threshold.

- `source_ownership_summary`
  - required only if source ownership was manually reviewed or classifier-backed.

### Optional

- `primary_tension`
- `contradiction_candidates`
- `findings_to_compress_or_demote` / `compression_candidates`

## Confidence And Review Flags

Every interpretive field should carry confidence.

Required confidence/review fields:

- `primary_entity_signal.confidence`
- `primary_entity_signal.uncertainty`
- `entity_aliases.needs_review`
- `owned_claim_density.confidence`
- `source_ownership_summary.*.confidence`
- `primary_tension.confidence`
- `primary_tension.requires_human_review`
- `contradiction_candidates[].confidence`
- `contradiction_candidates[].requires_human_review`
- `findings_to_compress_or_demote[].confidence`

Budgets should carry confidence only when derived from manual estimation. Pure counted fields do not need confidence, but they should include the observed count.

## Case-Specific Fields

These should remain case-specific values, not schema assumptions:

- Kit/BuiltWith ambiguity,
- ScamAdviser/Joe Sandbox trust scrutiny,
- creator/email positioning,
- BuiltWith intelligence positioning,
- robots.txt detail,
- API ecosystem detail,
- exact finding indices selected for compression.

The reusable part is not those claims. The reusable part is the structure:

- entity ambiguity,
- owned claim density,
- source ownership,
- repetition budgets,
- evidence coverage,
- contradiction candidates,
- compression candidates.

## What Must Change Before A Second Fixture

Before creating a second fixture, tighten the shape in four ways:

1. Rename `entity_aliases.aliases_or_adjacent_surfaces` to `observed_related_surfaces`.
2. Add `method: manual_estimate` to `source_ownership_summary`.
3. Rename `findings_to_compress_or_demote` to `compression_candidates`, or at least mark actions as `suggested_only`.
4. Add `requires_human_review` to `primary_tension`.

These are fixture-shape improvements, not runtime changes.

## What Should Still Not Be Automated

Do not automate yet:

- entity resolution,
- primary tension synthesis,
- contradiction candidate generation,
- source ownership classification,
- compression/demotion decisions,
- global caveat writing,
- prompt rewriting,
- scoring impact,
- report payload mutation,
- runtime gating.

The only safe automation later would be a read-only validator that checks fixture shape and counts obvious metrics. Even that should wait until at least one more fixture exists.

## Recommendation

Do not create a builder yet.

Create one more fixture only after applying the shape clarifications above. The second fixture should not be another Builtwith-like ambiguity case. It should be either:

- the Netlify fallback/control case, to test fallback language budget, or
- a new real persisted report with stronger evidence coverage, if available.

The current fixture shape is directionally correct, but it is still too manually expressive to automate.

## Bottom Line

The fixture works as a design artifact.

It should be treated as a manually authored composition-state sketch, not a schema-ready data model. Its core diagnostic fields are reusable; its interpretive fields need stronger review semantics before replication.
