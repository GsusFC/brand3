# Brand3 Evidence Packet Real Validation Batch v2 Review

- Overall pass: `False`
- Executed rows: `5`
- Skipped rows: `3`
- Resolved cases: `6`
- Unresolved cases: `23`

## Group behavior
- `group_a`: selected=4, executed=3, coverage_gap=1, readiness={'ready': 3, 'thin': 0, 'blocked': 1, 'abstain': 0, 'review_required': 0, 'other': 0}
- `group_b`: selected=2, executed=2, coverage_gap=3, readiness={'ready': 1, 'thin': 1, 'blocked': 0, 'abstain': 0, 'review_required': 0, 'other': 0}
- `group_c`: selected=0, executed=0, coverage_gap=5, readiness={'ready': 0, 'thin': 0, 'blocked': 0, 'abstain': 0, 'review_required': 0, 'other': 0}

## Pass criteria
- Global: `{'no_typical_decision': True, 'limits_present': True, 'risky_terms_outside_limits_empty': False, 'evidence_urls_valid': True, 'parse_failures_unrecovered': 0, 'blocked_controls_skipped': True}`
- Group-level: `{'group_a_majority_ready_low_review_pressure': True, 'group_b_conservative_thin_or_review': True, 'group_c_strong_abstain_or_blocked_discipline': False}`

## Recommendation
- Keep v2 experimental. Resolve failure classes before promotion.
