# Brand3 Magnetism Data Quality Batch - 2026-05-24

## Scope

Measurement over existing Brand Audit snapshots using the shared evidence path:

- Command: `./.venv/bin/python scripts/magnetism_brand_audit_batch_review.py --limit 100 --dedupe`
- Rows generated: 47 deduped brands
- Markdown artifact: `scratch/magnetism_brand_audit_batch_review/review-20260524-065138.md`
- JSON artifact: `scratch/magnetism_brand_audit_batch_review/review-20260524-065138.json`

The goal was not to improve interpretation yet. The goal was to measure whether the current evidence packet gives the TLDR Block Interpreters enough usable data.

## Aggregate Results

### Value Proposition

- high: 30 / 47
- medium: 8 / 47
- low: 9 / 47

Interpretation: product_offer extraction is usable. The extractor usually captures something that can support a value proposition.

Main gaps:

- product_offer missing in 7 / 47
- audience missing in 17 / 47
- outcome missing in 13 / 47
- value_prop_audience_not_named: 7 rows
- value_prop_outcome_not_stated: 10 rows

Quality issue: the value proposition often exists, but it is frequently over-broad or mixed with multiple offer candidates. This creates many human review flags.

### Mission

- medium: 6 / 47
- low: 41 / 47

Interpretation: mission is the weakest block in this measurement.

Main gaps:

- mission_language present in only 10 / 47
- mission_language missing in 37 / 47
- mission_not_declared: 31 rows

Quality issue: many brands may have operational evidence, but the current evidence grouping does not consistently classify it as mission_language. The strict interpreter then correctly refuses to invent a mission.

### Vision

- medium: 4 / 47
- low: 43 / 47

Interpretation: vision is also weak, but this may be partly correct. Most public pages do not state a real future/category-change claim.

Main gaps:

- vision_language present in only 9 / 47
- vision_language missing in 38 / 47
- interpreted_vision_needs_review: 4 rows

Quality issue: when vision appears, it is usually interpreted from future-facing language rather than a formal vision statement.

## Evidence Group Presence

Observed group presence across 47 rows:

- product_offer: 40
- outcome: 34
- audience: 30
- proof_points: 35
- personality_tone: 31
- values_language: 25
- hero_claims: 22
- mission_language: 10
- vision_language: 9
- third_party_context: 44

Notable imbalance:

- product_offer and outcome are relatively strong.
- mission_language and vision_language are sparse.
- third_party_context is very common and can pollute value proposition candidates when not weighted carefully.

## Review Flags

Rows with human review flags: 47 / 47.

Top flags:

- human_review_blocks: 46
- mission_not_declared: 31
- purpose_hypothesis_needs_review: 14
- value_prop_outcome_not_stated: 10
- value_prop_audience_not_named: 7
- limited_observable_layers: 7
- interpreted_vision_needs_review: 4

Interpretation: the system is being methodologically honest, but the current evidence quality causes nearly every row to need review. That is acceptable for v0.3, but too noisy for a polished operator workflow.

## Representative Observations

Good signals:

- Stripe: value proposition and mission both appear from strong operating evidence.
- Sentry: value proposition is concise and product-specific.
- Vercel: value proposition is clear and concrete.
- HeyGen: value proposition is strong, with scale and language coverage.

Weak or noisy signals:

- Vexture: value proposition includes title/search-like fragments.
- Apple: value proposition appears from company/category summary rather than direct owned positioning.
- Temporal: value proposition contains event/conference/navigation noise.
- Dribbble: value proposition captured a promotion rather than core offer.
- Claude / ChatGPT: evidence can collapse into generic platform/company details.

## Diagnosis

The main quality bottleneck is not the new Block Interpreter architecture. It is upstream evidence grouping and source weighting.

Current pattern:

1. The packet often captures product_offer.
2. The packet less reliably captures audience and outcome.
3. The packet rarely captures mission_language and vision_language.
4. Third-party context appears frequently and sometimes competes with owned evidence.
5. Multiple offer candidates trigger human review almost by default.

This suggests the next improvement should target the evidence packet, not another TLDR refactor.

## Recommended Next PR

Focus: improve evidence packet quality for TLDR inputs.

Suggested scope:

1. Add source-weighted candidate ranking inside the evidence packet summary or group builder.
2. Prefer owned homepage/product/about evidence over third_party_context for product_offer.
3. Add stricter filtering for navigation, promotions, event pages, and search/title snippets.
4. Improve mission_language classification from present-tense operational claims.
5. Improve audience/outcome extraction so value proposition confidence is less dependent on broad product_offer text.
6. Add a batch regression test or fixture for the known noisy examples:
   - Vexture
   - Apple
   - Temporal
   - Dribbble
   - Claude / ChatGPT

## Decision

Do not change the TLDR interpreter contract yet.

The next useful work is to make the shared extractor/evidence packet produce cleaner, better-classified data. Once that improves, rerun this same batch and compare:

- value_proposition high/medium/low distribution
- mission_language presence
- vision_language presence
- human_review_blocks rate
- known noisy examples
