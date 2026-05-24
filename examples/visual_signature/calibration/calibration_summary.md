# Visual Signature Calibration Summary

Evidence-only calibration output comparing machine claims against reviewed outcomes.

## Bundle Metadata

- Calibration run ID: `6bf278708eea4c4887aaebe799477f59`
- Generated at: 2026-05-11T22:27:42.269547+00:00
- Record count: 5
- Summary count consistency: true
- Evidence-only: yes
- No scoring impact: yes
- No rubric impact: yes
- No production UI/report impact: yes
- Missing review is insufficient_review: yes
- Unclear review is unresolved: yes

### Source Artifacts

- `examples/visual_signature/phase_one` -> `not-hashed`
- `examples/visual_signature/phase_two` -> `not-hashed`
- `examples/visual_signature/screenshots/capture_manifest.json` -> `85fdfed159fa60dc3598247d1ea25bc6b83fb20fffc01975eb1621e620734e8b`
- `examples/visual_signature/screenshots/dismissal_audit.json` -> `b35c54d794643d6bc23d6d66150e08ccc3cc30cd62467d0b48bc18fa77335a97`
- `examples/visual_signature/calibration_brands.json` -> `43c1f75398618cd042b4954745a7226a3660fc46ed2187dc2c97b83f7a31c780`

- Total claims: 5
- Reviewed claims: 5
- Confirmed: 2 (40%)
- Contradicted: 2 (40%)
- Unresolved: 1 (20%)
- Insufficient review: 0 (0%)
- High-confidence contradictions: 2
- Overconfidence rate: 40%
- Uncertainty accepted: 1 (20%)

## Category Breakdown

| Category | Claims | Reviewed | Confirmed | Contradicted | Unresolved | Insufficient review | High-conf contradiction | Overconfidence | Uncertainty accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AI-native | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0% | 1 |
| SaaS | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0% | 0 |
| ecommerce | 1 | 1 | 0 | 1 | 0 | 0 | 1 | 100% | 0 |
| editorial/media | 1 | 1 | 0 | 1 | 0 | 0 | 1 | 100% | 0 |
| wellness/lifestyle | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0% | 0 |

## Claim Kind Breakdown

| Claim Kind | Claims | Reviewed | Confirmed | Contradicted | Unresolved | Insufficient review | High-conf contradiction | Overconfidence | Uncertainty accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| capture_state | 5 | 5 | 2 | 2 | 1 | 0 | 2 | 40% | 1 |

## Source Breakdown

- `affordance_targets`: 563 (avg per claim: 112.60)
- `capture_manifest`: 5 (avg per claim: 1.00)
- `dismissal_audit`: 5 (avg per claim: 1.00)
- `phase_one_eligibility`: 5 (avg per claim: 1.00)
- `phase_one_mutation_audit`: 1 (avg per claim: 0.20)
- `phase_one_state`: 5 (avg per claim: 1.00)
- `phase_one_transition_records`: 16 (avg per claim: 3.20)
- `phase_two_review`: 5 (avg per claim: 1.00)

## Agreement Distribution

- confirmed:2, contradicted:2, unresolved:1

## Confidence Buckets

- high:5
