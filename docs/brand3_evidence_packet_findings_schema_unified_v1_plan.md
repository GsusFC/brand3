# Brand3 Evidence Packet Findings Schema Unified Trial v1 Plan

Date: 2026-05-18  
Scope: lab-only, non-runtime.

## Objective

Run one unified batch that covers:
- `diferenciacion` ready cases,
- `coherencia` ready/thin cases,
- `vitalidad` ready case,
- `percepcion` thin case,
- blocked/review controls.

This is a schema-discipline gate, not a production rollout.

## Executable Targets

- `linear::diferenciacion` (`ready`)
- `vercel::diferenciacion` (`ready`)
- `launchdarkly::diferenciacion` (`ready`)
- `linear::coherencia` (`ready`)
- `vercel::coherencia` (`thin`)
- `launchdarkly::vitalidad` (`ready`)
- `watermelon::percepcion` (`thin`)

## Control Targets (Must Be Skipped)

- `watermelon::vitalidad` (`blocked`)
- `builtwith_kit_com::coherencia` (`blocked`)
- `builtwith_kit_com::percepcion` (`blocked`)
- `launchdarkly::coherencia` (`review_required`)

## Pass Criteria

- no `typical_decision`
- non-empty `limits`
- no risky terms outside `limits`
- blocked/review controls skipped
- thin cases remain qualified
- evidence URLs valid against candidate input

## Risk Gate Note

For `vitalidad` only, factual org/news usage like `leadership team expansion`
is treated as non-strategic. Strategic leadership claims remain blocked.

## Artifacts

- `scripts/evidence_packet_findings_schema_unified_v1_trial.py`
- `examples/reports/evidence_packet_findings_schema_trial/unified_v1/request_manifest.json`
- `examples/reports/evidence_packet_findings_schema_trial/unified_v1/raw_outputs.json`
- `examples/reports/evidence_packet_findings_schema_trial/unified_v1/comparison.json`
- `examples/reports/evidence_packet_findings_schema_trial/unified_v1/cost_observation.json`
- `examples/reports/evidence_packet_findings_schema_trial/unified_v1/trial_notes.md`
