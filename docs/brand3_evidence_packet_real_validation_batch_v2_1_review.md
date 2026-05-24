# Brand3 Evidence Packet Real Validation Batch v2.1 Review

- Overall pass: `True`
- Executed rows: `7`
- Skipped rows: `4`
- Resolved cases: `9`
- Unresolved cases: `0`

## Group behavior
- `group_a`: selected=3, executed=2, coverage_gap=0, readiness={'ready': 2, 'thin': 0, 'blocked': 1, 'abstain': 0, 'review_required': 0, 'other': 0}
- `group_b`: selected=3, executed=3, coverage_gap=0, readiness={'ready': 1, 'thin': 2, 'blocked': 0, 'abstain': 0, 'review_required': 0, 'other': 0}
- `group_c`: selected=3, executed=2, coverage_gap=0, readiness={'ready': 2, 'thin': 0, 'blocked': 1, 'abstain': 0, 'review_required': 0, 'other': 0}

## Pass criteria
- Global: `{'no_typical_decision': True, 'limits_present': True, 'risky_terms_outside_limits_empty': True, 'evidence_urls_valid': True, 'parse_failures_unrecovered': 0, 'blocked_controls_skipped': True}`
- Group-level: `{'group_a_majority_ready_low_review_pressure': True, 'group_b_product_system_mixed_ready_thin': True, 'group_c_expressive_stays_bounded': True}`

## Recommendation
- Promote v2.1 dry-path as default lab benchmark for pre-runtime candidate integration.
