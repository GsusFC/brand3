# Brand3 Evidence Packet Findings Schema Trial Review

Date: 2026-05-18  
Case: Linear  
Dimension: `diferenciacion`  
Scope: lab-only, one LLM call, no runtime integration.

## What Was Tested

The trial replaced the current findings schema field `typical_decision` with explicit evidence-bound fields:

- `evidence_anchor`
- `observation`
- `bounded_interpretation`
- `limits`

The input was the Evidence Packet prompt-input candidate for Linear differentiation: two bounded competitor-comparison evidence items.

## Result

The model returned one finding: **Competitor relative positioning distance**.

It did not emit `typical_decision`. The output stayed focused on relative positioning distance:

- Wrike as closest measured competitor.
- ProjectManager as most different measured competitor.
- average distance and competitor count preserved.

The `limits` field explicitly states that the snapshot does not prove superiority, product quality, adoption, customer choice, durable defensibility, or planning direction.

## Comparison To Previous Candidate Schema

Previous schema:

- produced one relevant finding,
- but still included strategic option framing through `typical_decision`,
- and reintroduced strategy language.

New schema:

- produced one narrow finding,
- removed `typical_decision`,
- kept risky terms only inside `limits` as explicit non-claims,
- stayed closer to the evidence.

## Assessment

Removing `typical_decision` reduced strategic drift. The model preserved useful interpretation but stopped turning the evidence into decision-space prose.

The result is somewhat drier and more mechanical than the current Brand3 finding style, but that is acceptable for Evidence Packet mode. The goal here is not richer prose; it is preventing weak or narrow evidence from becoming strategic narrative.

## Decision

This schema is better for Evidence Packet inputs than the current findings schema.

It should remain lab-only for now, but it is a credible candidate for a future production prompt redesign after multi-case testing.

## Remaining Risks

- The schema is narrower and less editorial.
- It still depends on snapshot-derived competitor comparison provenance.
- It needs tests beyond Linear/diferenciacion before any production use.

## Artifacts

- `examples/reports/evidence_packet_findings_schema_trial/linear_diferenciacion/request.json`
- `examples/reports/evidence_packet_findings_schema_trial/linear_diferenciacion/raw_output.json`
- `examples/reports/evidence_packet_findings_schema_trial/linear_diferenciacion/comparison.json`
- `examples/reports/evidence_packet_findings_schema_trial/linear_diferenciacion/cost_observation.json`
