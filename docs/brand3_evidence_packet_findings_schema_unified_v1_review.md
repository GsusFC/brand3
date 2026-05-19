# Brand3 Evidence Packet Findings Schema Unified Trial v1 Review

Date: 2026-05-18  
Scope: lab-only, non-runtime, one unified batch.

## Trial Coverage

Executed targets:
- `linear::diferenciacion` (`ready`)
- `vercel::diferenciacion` (`ready`)
- `launchdarkly::diferenciacion` (`ready`)
- `linear::coherencia` (`ready`)
- `vercel::coherencia` (`thin`)
- `launchdarkly::vitalidad` (`ready`)
- `watermelon::percepcion` (`thin`)

Skipped controls (expected):
- `watermelon::vitalidad` (`blocked`)
- `builtwith_kit_com::coherencia` (`blocked`)
- `builtwith_kit_com::percepcion` (`blocked`)
- `launchdarkly::coherencia` (`review_required`)

## Pass/Fail Result

- `no_typical_decision`: **True**
- `limits_present`: **True**
- `risky_terms_outside_limits_empty`: **True**
- `blocked_or_review_controls_skipped`: **True**
- `thin_cases_qualified`: **True**
- `evidence_urls_valid`: **True**

Overall: **PASS**

## Robustness Outcome

The trial now includes a lab-only parse-repair path (single retry on JSON parse failure).
In this execution, all 7 case-dim calls completed with valid JSON output and no provider call failures.

## Quality Signal

For all 7 executed case-dim runs:
- schema stayed bounded,
- `typical_decision` stayed absent,
- risky terms outside limits stayed empty,
- URL discipline held.

## Decision

Unified v1.1 is **operational and robust enough for lab default unified batches**.

Keep production unchanged; this remains lab-only.

## Artifacts

- `scripts/evidence_packet_findings_schema_unified_v1_trial.py`
- `examples/reports/evidence_packet_findings_schema_trial/unified_v1/request_manifest.json`
- `examples/reports/evidence_packet_findings_schema_trial/unified_v1/raw_outputs.json`
- `examples/reports/evidence_packet_findings_schema_trial/unified_v1/comparison.json`
- `examples/reports/evidence_packet_findings_schema_trial/unified_v1/cost_observation.json`
- `examples/reports/evidence_packet_findings_schema_trial/unified_v1/trial_notes.md`
