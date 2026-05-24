# Evidence Packet Real Validation Batch v2

- Created: 2026-05-18T10:51:22.685274+00:00
- Executed LLM calls: True
- Resolved cases: 6
- Unresolved cases: 23
- Snapshot cases materialized: 6
- Requests prepared: 5
- Requests skipped: 3
- Overall pass: False

## Group metrics
- group_a: selected=4, executed=3, coverage_gap=1, all_rows_pass=True
- group_b: selected=2, executed=2, coverage_gap=3, all_rows_pass=False
- group_c: selected=0, executed=0, coverage_gap=5, all_rows_pass=False

## Executed rows
- group_a::vercel::diferenciacion (status=ready, findings=2)
- group_a::launchdarkly::diferenciacion (status=ready, findings=2)
- group_a::linear::diferenciacion (status=ready, findings=2)
- group_b::iris::percepcion (status=ready, findings=2)
- group_b::watermelon::percepcion (status=thin, findings=1)

## Skipped
- group_a::netlify::diferenciacion reason=status_not_executable_for_lab_call status=blocked
- controls::builtwith_kit_com::coherencia reason=status_not_executable_for_lab_call status=blocked
- controls::builtwith_kit_com::percepcion reason=status_not_executable_for_lab_call status=blocked
