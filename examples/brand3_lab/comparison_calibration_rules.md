# Brand3 Comparison Calibration Rules

Generated: 2026-05-15
Status: experimental calibration spec
Scope: local-only Brand3 Lab comparison calibration

## Purpose

These rules define how local draft exports from `/brand3-lab/perceptual-narrative-comparison` can be normalized into calibration logs for evaluating Brand3 perceptual reasoning quality over time.

This is not production persistence. It is not scoring integration. It is not an official review-record system.

## Source Export Contract

Accepted viewer export:

- `schema_version`: `brand3-perceptual-narrative-comparison-draft-1`
- `record_type`: `perceptual_narrative_comparison_review_draft`
- `draft_only`: `true`
- `official_record`: `false`
- `persistence_status`: `not_persisted`

Anything missing those fields should be rejected or treated as an untrusted draft.

## Export Normalization Rules

1. Normalize `brand_id` as the stable case key.
2. Keep original `brand` label for human readability.
3. Map empty decisions to `unreviewed`.
4. Preserve notes verbatim, but never treat notes as validated fact.
5. Tag overreach modes only when notes or reviewer controls explicitly indicate them.
6. Treat `unsafe_overreach` as a veto signal even if other reviewers prefer the perceptual version.
7. Do not infer safe augmentation from `perceptual_better` alone; safety requires no overreach veto and at least medium confidence.
8. Store source artifact paths and optional hashes so calibration can be traced back to the exact paired examples.
9. Keep normalized logs under `examples/brand3_lab/` or another local lab path only.
10. Never write normalized logs into report output, scoring output, Visual Signature records, or production databases.

## Reviewer Agreement Model

Model: `majority_with_overreach_veto_v1`

Decision meanings:

- `baseline_better`: baseline narrative was clearer, safer, or more proportionate.
- `perceptual_better`: perceptual narrative improved specificity without unsafe overreach.
- `mixed`: perceptual layer helped in places but harmed or overreached elsewhere.
- `unsafe_overreach`: perceptual narrative introduced unsupported interpretation, invented intent, or unsafe emotional/strategic claims.
- `unreviewed`: reviewer did not evaluate the pair.

Agreement levels:

- `strong_agreement`: at least 75% of non-unreviewed reviewers select the same non-unsafe decision.
- `moderate_agreement`: more than 50% select the same non-unsafe decision.
- `split`: no majority decision.
- `unsafe_veto`: at least one reviewer selects `unsafe_overreach`.

Unsafe veto rule:

If any reviewer selects `unsafe_overreach`, the case should not count as a safe augmentation win until a later review resolves the flagged issue.

## Disagreement Patterns

Track disagreement patterns explicitly:

- `safety_vs_specificity`: one reviewer prefers perceptual specificity while another flags overreach.
- `baseline_conservatism`: reviewers prefer baseline because evidence is too thin.
- `voice_preference_split`: reviewers agree both are safe but disagree on voice quality.
- `evidence_threshold_split`: reviewers disagree about whether the perceptual claim is sufficiently anchored.
- `brand3_voice_split`: reviewers disagree on whether the augmented version feels Brand3/FLOC* or just more stylized.

## Confidence Aggregation Rules

Model: `weighted_reviewer_consensus_v1`

Inputs:

- reviewer decision
- reviewer confidence bucket
- unsafe overreach flags
- safe augmentation label
- feels Brand3 consistency
- notes indicating evidence limits

Case-level confidence:

- `high`: strong agreement, no unsafe veto, at least two reviewers, and most reviewers mark high or medium confidence.
- `medium`: moderate agreement or mixed preference with no unsafe veto.
- `low`: split agreement, low reviewer confidence, or unresolved evidence-threshold dispute.
- `insufficient`: fewer than two reviewed votes or too many `unreviewed` decisions.

Aggregate confidence:

- Prefer trend-level confidence over single-case confidence.
- Do not generalize from fewer than six reviewed pairs.
- Treat high overreach frequency as a block on rollout even if perceptual preference is high.
- Treat `mixed` as useful signal, not failure.

## Metrics To Track

Reviewer agreement:

- agreement ratio per case
- majority decision per case
- unsafe veto count
- split cases by surface type

Disagreement patterns:

- frequency of safety vs specificity splits
- frequency of evidence threshold splits
- where baseline conservatism appears
- where Brand3 voice preference is unstable

Overreach detection:

- unsafe_overreach rate
- overreach mode frequency
- overreach by brand/surface class
- repeat offender phrases from reviewer notes

Safe augmentation zones:

- cases where perceptual_better wins without unsafe veto
- surface classes where safe augmentation repeats
- evidence types associated with safe wins

Narrative preference trends:

- baseline_better rate
- perceptual_better rate
- mixed rate
- unsafe_overreach rate

Feels Brand3 consistency:

- high consistency when reviewers prefer perceptual language and notes mention evidence-bound specificity
- medium consistency when reviewers mark mixed but no unsafe veto
- low consistency when notes mention stylization, generic sophistication, or unsupported interpretation

## Calibration Recommendation Rules

- If `unsafe_overreach_rate` is above 20%, do not expand the experiment.
- If `perceptual_better_rate` is high but `mixed_rate` is also high, refine acceptance gates before rollout.
- If `baseline_better_rate` is high for sparse evidence cases, route those cases to baseline fallback.
- If `feels_brand3_consistency` is low, improve language rules before adding more pattern coverage.
- If safe wins cluster around evidence-rich cases, deploy only in evidence-rich lab contexts.
