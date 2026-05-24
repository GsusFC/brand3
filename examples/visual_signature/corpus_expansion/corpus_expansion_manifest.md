# Visual Signature Corpus Expansion Manifest

Evidence-only governance manifest for the reviewed-corpus expansion pilot.

- Evidence-only: yes
- Governance-only: yes
- No scoring impact: yes
- No runtime enablement: yes
- No model-training enablement: yes

- Pilot run ID: `visual-signature-corpus-expansion-pilot-1`
- Generated at: 2026-05-12T10:43:08.621714+00:00
- Readiness scope: `human_review_scaling`
- Readiness status: `not_ready`
- Target capture count: 20
- Current capture count: 5
- Reviewed capture count: 2
- Reviewer coverage: 40%
- Contradiction rate: 20%
- Unresolved rate: 20%

## Current State

- This pilot is sized for 20-50 reviewed captures.
- Current reviewed captures: 2
- Current total captures: 5
- Readiness remains `not_ready` until the reviewed corpus is expanded.

## Category Distribution

| Category | Count |
| --- | ---: |
| AI-native | 1 |
| SaaS | 1 |
| ecommerce | 1 |
| editorial/media | 1 |
| wellness_lifestyle | 1 |

## Confidence Distribution

| Bucket | Count |
| --- | ---: |
| high | 2 |
| low | 1 |
| medium | 1 |
| unknown | 1 |

## Readiness Thresholds

- Scope evaluated: `human_review_scaling`
- This result applies only to the evaluated scope.
- It does not imply production, scoring, runtime, provider-pilot, or model-training readiness.

## Block Reasons

- small_sample_size
- insufficient_reviewed_captures
- insufficient_category_depth

## Governance Notes

- Evidence-only governance manifest.
- Capability presence in the corpus expansion pipeline does not imply production approval.
- Readiness is scope-dependent and separate from scoring, runtime, and training.

## Current Limitations

- Current corpus expansion state is a scaffold, not a production corpus.
- This bundle is insufficient for model training.
- This bundle is insufficient for production scoring.
- This bundle is evidence-only corpus expansion.
- Readiness is not yet broad enough for reviewed-corpus expansion.
- Block reason: small_sample_size
- Block reason: insufficient_reviewed_captures
- Block reason: insufficient_category_depth
