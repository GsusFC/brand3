# Visual Signature Calibration Reliability Report

Evidence-only interpretation of the hardened calibration bundle.

- Evidence-only: yes
- No scoring impact: yes
- No rubric impact: yes
- No production UI/report impact: yes

## Bundle Metadata Summary

- Calibration run ID: `6bf278708eea4c4887aaebe799477f59`
- Manifest validation status: `valid`
- Bundle validation status: `valid`
- Validation errors: `none`
- Generated at: 2026-05-11T22:27:42.269547+00:00
- Record count: 5
- Summary count consistency: true
- Summary markdown present: yes
- Summary markdown lines: 69
- Source roots: `examples/visual_signature/phase_one`, `examples/visual_signature/phase_two`
- Source artifact refs: 5
- Source artifact hashes: 3

### Schema Versions

- `calibration_claim`: `visual-signature-calibration-claim-1`
- `calibration_generated_file`: `visual-signature-calibration-generated-file-1`
- `calibration_manifest`: `visual-signature-calibration-manifest-1`
- `calibration_record`: `visual-signature-calibration-record-1`
- `calibration_records`: `visual-signature-calibration-records-1`
- `calibration_summary`: `visual-signature-calibration-summary-1`
- `review_outcome`: `visual-signature-calibration-review-outcome-1`

## Aggregate Findings

- Total claims: 5
- Reviewed claims: 5
- Confirmed: 2 (40%)
- Contradicted: 2 (40%)
- Unresolved: 1 (20%)
- Insufficient review: 0 (0%)
- High-confidence contradictions: 2
- Overconfidence rate: 40%
- Uncertainty accepted: 1 (20%)

### Confidence Bucket Analysis

- high: 5

### Overconfidence Findings

- Allbirds: `claim=REVIEW_REQUIRED_STATE`, `agreement=contradicted`, `confidence=high`
- The Verge: `claim=OBSTRUCTED_STATE`, `agreement=contradicted`, `confidence=high`

### Underconfidence Findings

- none surfaced in this bundle

### Uncertainty Alignment Findings

- calibrated: 2
- overconfident: 2
- underconfident: 0
- uncertainty_accepted: 1
- insufficient_data: 0

## Category Breakdown

| Category | Claims | Reviewed | Confirmed | Contradicted | Unresolved | Insufficient review | High-conf contradiction | Overconfidence | Uncertainty accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AI-native | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0% | 1 |
| SaaS | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0% | 0 |
| ecommerce | 1 | 1 | 0 | 1 | 0 | 0 | 1 | 100% | 0 |
| editorial/media | 1 | 1 | 0 | 1 | 0 | 0 | 1 | 100% | 0 |
| wellness/lifestyle | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0% | 0 |

## Perception Source Breakdown

| Source | Count | Avg per claim |
| --- | ---: | ---: |
| affordance_targets | 563 | 112.60 |
| capture_manifest | 5 | 1.00 |
| dismissal_audit | 5 | 1.00 |
| phase_one_eligibility | 5 | 1.00 |
| phase_one_mutation_audit | 1 | 0.20 |
| phase_one_state | 5 | 1.00 |
| phase_one_transition_records | 16 | 3.20 |
| phase_two_review | 5 | 1.00 |

## Claim Kind Breakdown

| Claim Kind | Claims | Reviewed | Confirmed | Contradicted | Unresolved | Insufficient review | High-conf contradiction | Overconfidence | Uncertainty accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| capture_state | 5 | 5 | 2 | 2 | 1 | 0 | 2 | 40% | 1 |

## Notable Confirmed Claims

- Headspace: `claim=UNSAFE_MUTATION_BLOCKED`, `review=rejected/no/uncertainty_accepted=false`, `alignment=calibrated`
- Linear: `claim=OBSTRUCTED_STATE`, `review=rejected/no/uncertainty_accepted=false`, `alignment=calibrated`

## Notable Contradicted Claims

- Allbirds: `claim=REVIEW_REQUIRED_STATE`, `review=approved/partial/uncertainty_accepted=true`, `alignment=overconfident`
- The Verge: `claim=OBSTRUCTED_STATE`, `review=approved/yes/uncertainty_accepted=true`, `alignment=overconfident`

## Unresolved Claims Needing Review

- OpenAI: `claim=OBSTRUCTED_STATE`, `review=needs_more_evidence/partial/uncertainty_accepted=false`, `alignment=uncertainty_accepted`

## Limitations

- Sample size is small: 5 claims across 5 categories.
- Confidence is saturated at high: 5 of 5 claims.
- No medium, low, or unknown confidence claims surfaced in this bundle.
- Each category currently has one claim, so category-level conclusions are directional only.
- This bundle shows 2 high-confidence contradictions, which is enough to flag calibration risk but not enough for corpus-wide policy changes.
- The bundle does not contain any insufficient_review records, so the missing-review branch is not exercised here.

## Recommendation

- The bundle is coherent and validated, but it is not ready for broader corpus use as a calibration basis.
- It is suitable for evidence-only inspection and small-scale calibration review.
- Broader corpus use should wait for more claims per category and a wider spread of confidence buckets.
