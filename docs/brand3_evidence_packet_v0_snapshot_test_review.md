# Brand3 Evidence Packet v0 Snapshot Test Review

## Purpose

This review tests the hardened local Evidence Packet v0 on two additional real snapshots:

- Watermelon: ambiguous ecosystem / related-surface pressure.
- LaunchDarkly: cleaner, high-evidence, lower-ambiguity case.

The question was:

Does the local packet distinguish clean evidence from ambiguity without blocking everything?

## Artifacts

Generated:

- `examples/reports/evidence_packet/watermelon.local_evidence_packet.v0.json`
- `examples/reports/evidence_packet/launchdarkly.local_evidence_packet.v0.json`

Existing reference:

- `examples/reports/evidence_packet/builtwith_kit_com.local_evidence_packet.v0.json`

No network, LLM, Deep Research, Exa, Firecrawl, Playwright, scoring, prompt, renderer, payload, or Visual Signature behavior was changed.

## Summary Counts

| Case | Eligible | Not eligible | Missing | Ambiguity | Related surfaces | Review gates | Noise |
|---|---:|---:|---:|---:|---:|---:|---:|
| Builtwith / Kit | 0 | 26 | 12 | 5 | 12 | 7 | 0 |
| Watermelon | 3 | 32 | 13 | 3 | 5 | 3 | 1 |
| LaunchDarkly | 13 | 16 | 10 | 1 | 1 | 1 | 0 |

The spread is useful:

- Builtwith blocks almost everything.
- Watermelon allows only audited-surface evidence while review-gating related surfaces.
- LaunchDarkly keeps substantial finding-eligible evidence.

This suggests the packet is not globally over-conservative.

## Watermelon Result

Watermelon now behaves closer to the desired evidence contract.

Finding-eligible evidence is limited to audited-surface claims from `watermelon.sh`.

Related or ambiguous surfaces are not treated as clean evidence:

- `watermelon.us` is unresolved.
- LinkedIn company candidate is unresolved.
- Crunchbase Watermelon profile is unresolved.
- `github.com/WatermelonCorp/watermellon-registry` is repository/developer-surface evidence only.
- `github.com/watermelontools` is repository evidence and remains unresolved, not merged.
- Product Hunt / SoftwareSuggest are marketplace/listing evidence and review-gated.

The explicit off-topic produce article is now excluded as noise:

- `perishablenews.com/produce/fresh-pro-announces-honey-watermelons-brand-refresh-new-mascot/`

This is the intended behavior: preserve the audited surface, prevent ecosystem collapse, and force review for adjacent surfaces.

Remaining Watermelon risk:

- `github.com/WatermelonCorp` may actually be related, but the local packet cannot prove relation from existing snapshot metadata strongly enough.
- Local v0 still lacks the stronger explicit-link discovery seen in the manual Deep Research reference.

## LaunchDarkly Result

LaunchDarkly produced substantial eligible evidence:

- official homepage;
- about page;
- platform page;
- product/blog update;
- external release/update references;
- owned reliability and scale claims.

The packet did not collapse into total blocking.

It created one review-gated ambiguity:

- `https://www.linkedin.com/company/launchdarkly`

This is conservative but acceptable because the local social collector appears to create social profile candidates without verifying that the target brand controls the profile. A future enrichment step could verify social ownership, but the local packet should not assume it.

Remaining LaunchDarkly risk:

- Some external sources such as alternatives posts and release aggregators are still eligible. They may need source-quality weighting before generation.
- Empty-text URL evidence remains present in eligible evidence when the source URL is strong enough; generation should not consume those without source snippets.

## What The Test Proves

The hardened packet can distinguish case types:

- severe ambiguity / weak evidence: Builtwith;
- ecosystem ambiguity: Watermelon;
- cleaner owned/external evidence: LaunchDarkly.

That means the builder is not merely "block everything".

It is conservative enough to stop bad input, but permissive enough to preserve useful LaunchDarkly evidence.

## What Still Needs Hardening

Before feeding this into generation, local v0 still needs:

- better explicit-link extraction from raw inputs;
- source-quality scoring that is not Brand3 scoring;
- stricter handling of empty-text URL evidence;
- social-profile verification status;
- distinction between external mention, external validation, comparison page, and release aggregator;
- optional nested `dimensions` object matching the Deep Research reference.

## Recommendation

Do not feed the packet into generation yet.

The next implementation step should be a narrow evidence-contract hardening pass:

- block or downgrade empty-text URL evidence from finding eligibility;
- add source role subtypes for comparison pages, release aggregators, and social candidates;
- extract explicit links from audited pages when available;
- then rerun Watermelon and LaunchDarkly.

After that, test packet-filtered prompt input in lab only.

## Non-Goals Preserved

- No runtime integration.
- No prompt changes.
- No scoring changes.
- No report generation changes.
- No rendering changes.
- No persisted payload changes.
- No Visual Signature changes.
- No Deep Research calls.
- No Exa/Firecrawl/API calls.
- No generation input changes.

