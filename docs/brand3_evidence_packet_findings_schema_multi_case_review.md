# Brand3 Evidence Packet Findings Schema Multi-Case Review

Date: 2026-05-18  
Scope: lab-only, non-runtime, one trial batch.

## Trial Setup

Executed targets:
- linear / diferenciacion (`ready`)
- vercel / diferenciacion (`ready`)
- launchdarkly / diferenciacion (`ready`)
- watermelon / percepcion (`thin`)

Negative control:
- builtwith_kit_com / percepcion (`blocked`) was skipped by contract.

## Pass/Fail Criteria

- no `typical_decision` in outputs: **True**
- non-empty `limits` in outputs: **True**
- `risky_terms_outside_limits` empty: **True**
- blocked dimensions skipped/abstained: **True**
- thin case remained qualified: **True**
- evidence URLs valid against candidate input: **True**

Overall trial pass: **True**

## Findings

Drift reduction is consistent beyond Linear. All executed outputs removed `typical_decision`, included `limits`, and kept risky language only inside explicit non-claim limits.

Useful interpretation was preserved:
- ready differentiation cases returned concrete relative-distance findings;
- the thin Watermelon perception case returned one bounded finding with no broad strategic drift.

Mechanical risk exists: ready differentiation cases tend to produce a symmetric two-finding pattern (closest vs most-different competitor). This is acceptable for lab evidence-discipline, but should be watched before any wider rollout.

## Decision Gate

Result: **PASS**

Decision: adopt this schema as **lab default** for Evidence Packet prompt-input experiments.

This is not a production decision. Runtime prompts remain unchanged.

## Before Any Production Redesign

- expand validation to more dimensions and case types;
- reduce formulaic repetition while preserving constraints;
- improve provenance richness for snapshot-derived evidence;
- define runtime-safe fallback behavior for zero-finding cases;
- design compatibility mapping to existing Finding payload before touching production prompt contracts.

## Artifacts

- `scripts/evidence_packet_findings_schema_multi_case_trial.py`
- `examples/reports/evidence_packet_findings_schema_trial/multi_case_v0/request_manifest.json`
- `examples/reports/evidence_packet_findings_schema_trial/multi_case_v0/raw_outputs.json`
- `examples/reports/evidence_packet_findings_schema_trial/multi_case_v0/comparison.json`
- `examples/reports/evidence_packet_findings_schema_trial/multi_case_v0/cost_observation.json`
- `examples/reports/evidence_packet_findings_schema_trial/multi_case_v0/trial_notes.md`
- `docs/brand3_evidence_packet_findings_schema_multi_case_review.json`
