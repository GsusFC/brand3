# Brand3 EntityNarrativeState Builder v0 Outputs Review

Date: 2026-05-17

Scope: offline builder-output review only. No runtime integration, prompts, scoring, generation, rendering, payload format, Visual Signature code, LLM calls, or manual fixtures were changed.

## Generated Outputs

The offline builder v0 was run against the existing payload and diagnostic examples for five cases.

Created builder-output artifacts:

```text
examples/reports/narrative_harness/entity_state/launchdarkly.entity_narrative_state.v0.json
examples/reports/narrative_harness/entity_state/iris.entity_narrative_state.v0.json
examples/reports/narrative_harness/entity_state/watermelon.entity_narrative_state.v0.json
examples/reports/narrative_harness/entity_state/builtwith_kit_com.entity_narrative_state.v0.json
examples/reports/narrative_harness/entity_state/netlify_snapshot_mock.entity_narrative_state.v0.json
```

Existing manual fixtures were preserved:

```text
examples/reports/narrative_harness/entity_state/builtwith_kit_com.entity_narrative_state.json
examples/reports/narrative_harness/entity_state/netlify_snapshot_mock.entity_narrative_state.json
```

The `.v0.json` suffix marks the new files as deterministic builder outputs, not manual fixture replacements.

## Output Matrix

| Case | Case family | Safe attribution | Fallback language | Evidence coverage | Decision mode | Related surfaces |
|---|---|---:|---|---|---|---:|
| Builtwith | owned_claim_repetition | high / 11 | fallback_like_repetition | mixed, 4 missing | hidden_generic | 0 |
| Netlify | fallback_language_repetition | inactive / 0 | fallback_like_repetition | mixed, 2 missing | not_applicable_empty | 0 |
| LaunchDarkly | owned_claim_repetition | high / 13 | fallback_like_repetition | mixed, 7 missing | compressed_candidate | 0 |
| Iris | owned_claim_repetition | high / 15 | fallback_like_repetition | mixed, 6 missing | hidden_generic | 0 |
| Watermelon | owned_claim_repetition | high / 9 | fallback_like_repetition | mixed, 6 missing | compressed_candidate | 0 |

## Builder Output vs Manual Fixture Expectations

### Builtwith

The builder reproduces the strongest measured expectations from the manual fixture:

- high owned-claim density,
- attribution budget over budget,
- corroboration caveat budget over budget,
- fallback-like evidence-pool repetition,
- mixed evidence URL coverage,
- hidden generic decision-space mode,
- suggested compression candidates.

What it does not reproduce:

- the manual fixture's richer entity ambiguity around Kit, BuiltWith, and adjacent surfaces,
- manually consolidated `primary_tension`,
- manually curated contradiction candidates.

That difference is correct for v0. The builder does not have an explicit related-surface source or an entity-resolution layer. It preserves uncertainty instead of inferring that related names/domains are equivalent.

### Netlify

The builder matches the second fixture's main expectation:

- safe attribution remains inactive,
- attribution and corroboration budgets remain absent,
- fallback-language budget activates,
- decision-space mode is `not_applicable_empty`,
- evidence URL coverage remains mixed.

This confirms that inactive budgets can stay inactive. The builder does not force every case into every failure family.

### LaunchDarkly

LaunchDarkly confirms the Phase 2 synthesis:

- global evidence was available,
- but finding-level evidence URL coverage is mixed,
- safe attribution and corroboration budgets still activate,
- decision-space is only advisory.

The builder correctly avoids creating a false `primary_tension` beyond payload text. It compiles composition pressure without inventing a strategic failure.

### Iris

Iris activates the expected owned-claim and caveat budgets, and preserves the payload tension as review-gated.

However, the builder does not surface the broader Iris related-domain problem described in the Phase 2 audit unless the upstream snapshot carries explicit related-surface metadata. In the current architecture that metadata should come from `entity_resolution.related_surfaces`; `observed_related_surfaces` is only the legacy alias.

The live Iris fixture has been migrated to the packet field, so this limitation is now only a property of older historical outputs or alias-only inputs.

This is a useful limitation. The builder is behaving conservatively, but the input contract is only rich enough when the packet or compatibility alias supplies explicit related-surface entries.

### Watermelon

Watermelon shows the same limitation more clearly.

The Phase 2 memo identifies ecosystem complexity around:

- `watermelon.sh`,
- `watermelon.ai`,
- `watermelon.market`,
- `watermelon.us`,
- GitHub surfaces,
- Product Hunt,
- ambiguous Watermelon-name surfaces.

The builder output leaves `observed_related_surfaces` empty because the normalized snapshot did not provide an explicit related-surface list.

That is the right failure mode for v0. It avoids treating third-party evidence URLs or name-adjacent domains as entity aliases. But it also means the builder cannot yet represent the most important Watermelon composition pressure unless the upstream data contract supplies explicit related surfaces, ideally via `entity_resolution.related_surfaces`.

The live Watermelon fixture now supplies that packet field explicitly; this paragraph remains as the historical explanation for the older alias-only outputs in this review set.

## Fields That Worked

### `owned_claim_density`

This field works well.

It cleanly separates Netlify from the other four cases:

- Netlify: inactive.
- Builtwith, LaunchDarkly, Iris, Watermelon: high.

The field is derived directly from `safe_attribution_total` and phrase counts. It does not over-interpret the reason for the repetition.

### `attribution_budget`

This worked as a conditional field.

It appears only when safe attribution exceeds the budget. It stays absent for Netlify.

This matches the contract: inactive budgets should remain inactive or absent.

### `corroboration_caveat_budget`

This also works as a conditional field.

It activates for the cases where the observation repetition family exceeds threshold and stays absent for Netlify.

The field remains diagnostic. It does not decide how reports should be rewritten.

### `fallback_language_budget`

This field generalized across cases.

It captures two different patterns:

- Netlify's true fallback-like phrase: `the available sources`.
- Phase 2's good-data fallback-like phrase: `the evidence pool`.

The field currently uses `fallback_like_repetition`, not `fallback_mode`, which is the right distinction.

### `evidence_url_coverage`

This is the strongest builder field.

It turns missing finding-level URLs into a coverage metric, not an editorial verdict:

- Builtwith: 4 findings missing URLs.
- Netlify: 2.
- LaunchDarkly: 7.
- Iris: 6.
- Watermelon: 6.

It also identifies affected dimensions, usually `coherencia` and `diferenciacion`, with some Builtwith/LaunchDarkly variation.

### `decision_space_mode`

This field is useful and remains advisory.

It distinguishes:

- `hidden_generic`: Builtwith and Iris.
- `compressed_candidate`: LaunchDarkly and Watermelon.
- `not_applicable_empty`: Netlify.

That matches the render-aware findings: some generic decision-space text is suppressed visually, but the payload risk still exists.

### `compression_candidates`

The candidates are appropriately conservative:

- `typical_decision`,
- `safe_attribution`,
- `evidence_url_coverage`.

Every item is marked `suggested_only: true`. No rewritten prose is generated.

## Fields That Became Too Conservative

### `observed_related_surfaces`

This is the main conservative field.

The builder leaves it empty across all five outputs when the current inputs do not provide explicit related-surface metadata.

That protects the system from a dangerous mistake:

```text
third-party evidence URL != entity-related surface
```

But it also means Iris and Watermelon lose an important part of their Phase 2 pressure. Their related-surface complexity exists in the audit memo, not in the machine-readable diagnostics.

Conclusion:

`observed_related_surfaces` is correctly conservative, but it is now best treated as a legacy compatibility alias for `entity_resolution.related_surfaces`.

### `primary_entity_signal`

This field is useful but shallow.

It can anchor brand and URL from optional output snapshots, but it cannot resolve:

- Kit vs BuiltWith,
- Iris design surfaces,
- Watermelon ecosystem surfaces.

That is expected. The builder should not become an entity resolver.

### `primary_tension`

The builder only copies payload tension when present and marks it low-confidence / human-review.

This is conservative and safe. It also means the builder does not reconstruct the richer tensions from Phase 2 memos.

That is acceptable for v0. Tension synthesis should not be automated from phrase-count diagnostics.

## Fields That Need Snapshot Metadata To Be Useful

### `metadata.brand` and `metadata.url`

The report narrative payload examples do not consistently carry brand or URL. The builder needed optional output snapshots to fill these fields.

Without snapshot metadata, these would remain `unknown`.

### `source_ownership_summary`

This field only becomes useful when the optional snapshot provides evidence totals or discovery enrichment counts.

Current generated states include a source summary, but it should still be treated as coarse:

- it depends on available snapshot keys,
- it does not classify source ownership per finding,
- it does not know whether a specific caveat has local or global evidence support.

### `observed_related_surfaces`

This field needs explicit related-surface metadata.

It should not be populated from arbitrary evidence URLs. Doing so would collapse source discovery into entity resolution and create false aliases.

Future input contracts should provide a separate machine-readable related-surface list if Brand3 wants the builder to represent Iris/Watermelon-style entity ambiguity.

## Does `observed_related_surfaces` Remain Mostly Unknown?

Yes.

The builder output shows:

```text
observed_related_surfaces: []
needs_review: false
```

for all five generated states.

This is not because the Phase 2 audits lacked related-surface pressure. It is because the current machine-readable inputs do not expose that pressure in a safe field.

The correct next improvement is not to let the builder infer surfaces from evidence URLs. The correct next improvement is to expose explicit related-surface metadata from discovery or a separate offline entity-discovery artifact.

## Does The Builder Preserve Uncertainty Correctly?

Mostly yes.

Positive signs:

- every output remains `offline_only`,
- no output is used by scoring, prompts, rendering, or runtime,
- no contradiction candidates are invented,
- primary tension is review-gated when present,
- decision-space mode is advisory only,
- compression candidates are suggested-only,
- related surfaces are not inferred from evidence URLs.

The main weakness is that the builder can look under-informative for the most interesting composition cases. That is the expected tradeoff of a safe v0.

## Recommended Next Step

Do not integrate this builder into runtime.

Do not change prompts from these outputs yet.

The next useful step is to improve the offline input contract around entity/surface metadata.

Recommended options:

1. Add a small offline memo/spec for `observed_related_surfaces` source contract.
2. Decide whether the data should come from existing `entity_discovery`, discovery enrichment, or a new offline related-surface extractor.
3. Only after that, run builder v0 again on Iris and Watermelon to test whether entity ambiguity can be represented without unsafe inference.

The builder is useful now for:

- evidence URL coverage,
- safe attribution pressure,
- caveat repetition,
- fallback-like language,
- decision-space advisory mode.

It is not yet enough for:

- entity hierarchy,
- ecosystem ambiguity,
- surface ownership,
- contradiction prioritization.
