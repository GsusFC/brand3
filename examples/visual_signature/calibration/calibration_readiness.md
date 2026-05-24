# Visual Signature Calibration Readiness

Evidence-only readiness gate for broader calibration corpus use.

- Evidence-only: yes
- No scoring impact: yes
- No rubric impact: yes
- No production UI/report impact: yes
- Missing review is insufficient_review: yes
- Unclear review is unresolved: yes

## Bundle Metadata

- Calibration run ID: `6bf278708eea4c4887aaebe799477f59`
- Checked at: 2026-05-12T07:27:50.390205+00:00
- Scope evaluated: `broader_corpus_use`
- Status: `not_ready`
- Bundle valid: true
- Summary count consistency: true
- Record count: 5
- Reviewed claims: 5
- Source corpus manifest: `examples/visual_signature/calibration_corpus/corpus_manifest.json`

### Thresholds Used

- Minimum total claims: 15
- Minimum reviewed claims: 15
- Minimum categories: 3
- Minimum claims per category: 3
- Minimum confidence buckets: 3
- Maximum contradiction rate: 25%
- Maximum high-confidence contradictions: 1
- Maximum unresolved rate: 25%

### Scope Note

- This `ready` / `not_ready` result applies only to the scope above.
- It does not imply production readiness, scoring readiness, runtime readiness, provider-pilot readiness, or model-training readiness.
- Unsupported scopes are reported via warnings and do not silently reuse broader corpus thresholds.

## Summary Metrics

- Contradiction rate: 40%
- Unresolved rate: 20%
- Overconfidence rate: 40%

## Block Reasons

- small_sample_size
- insufficient_reviewed_claims
- insufficient_category_depth
- insufficient_confidence_spread
- contradiction_rate_too_high
- high_confidence_contradictions_too_high

## Warning Reasons

- corpus_category_coverage_limited:5/12
- corpus_manifest_loaded

## Category Coverage

| Category | Claims | Reviewed | Share | Min required | Meets minimum |
| --- | ---: | ---: | ---: | ---: | --- |
| AI-native | 1 | 1 | 20% | 3 | false |
| SaaS | 1 | 1 | 20% | 3 | false |
| ecommerce | 1 | 1 | 20% | 3 | false |
| editorial/media | 1 | 1 | 20% | 3 | false |
| wellness/lifestyle | 1 | 1 | 20% | 3 | false |

## Confidence Bucket Coverage

| Bucket | Claims | Reviewed | Share | Min required | Meets minimum |
| --- | ---: | ---: | ---: | ---: | --- |
| high | 5 | 5 | 100% | 1 | true |
| low | 0 | 0 | 0% | 1 | false |
| medium | 0 | 0 | 0% | 1 | false |
| unknown | 0 | 0 | 0% | 1 | false |

## Recommendation

- Hold broader corpus use until sample size, category depth, and confidence spread improve.

## Notes

- Evidence-only readiness gate.
- No scoring, rubric dimensions, production reports, or UI are modified.
- Scope evaluated: broader_corpus_use
- Bundle validation must pass before readiness can be positive.
- Observed categories: 5
- Observed confidence buckets: 1
- Validation errors: 0
- Corpus manifest categories: 12
- Corpus manifest broader calibration target: 15
- Thresholds are conservative and intended to block broader corpus use until sample size and spread improve.
