# Brand3 Evidence Packet Linear Operability Test

Date: 2026-05-18  
Target: `https://linear.app`  
Run: `80`  
Scope: lab/offline after one normal Brand3 audit.

## Result

Evidence Packet v0 produced this readiness split:

| Dimension | Status |
| --- | --- |
| coherencia | ready |
| presencia | thin |
| percepcion | ready |
| diferenciacion | abstain |
| vitalidad | ready |

Counts:

- finding-eligible evidence: 10
- blocked/not-eligible evidence: 24
- review flags: 1
- source inventory entries: 36

## Objective Reading

Linear is a good new test case. It is stable, high-evidence, and entity-clear. The packet did not over-filter the whole case: `coherencia`, `percepcion`, and `vitalidad` remained usable.

The critical finding is `diferenciacion`.

The normal audit did discover competitors and computed competitor comparisons, but Evidence Packet v0 still abstains because it does not extract `competitor_web_comparison` into a conservative differentiation evidence shape. That means the blocker is no longer generic evidence eligibility. It is a specific transformation gap: competitor/comparison data exists upstream, but the packet does not know how to make it narratively eligible.

## Dimension Notes

- `coherencia`: ready. Visual metrics remain non-narrative, while owned textual evidence can carry the dimension.
- `presencia`: thin. The packet is still conservative around official/social/channel verification.
- `percepcion`: ready. External perception evidence survives filtering.
- `diferenciacion`: abstain. Needs competitor/comparison extraction, not prose refinement.
- `vitalidad`: ready. Recent activity survives, while URL-only recency evidence is blocked.

## Decision

Do not keep adding generic readiness rules.

The next useful implementation is narrow:

1. Read `competitor_web_comparison` and discovery competitor metadata from the snapshot.
2. Create bounded differentiation evidence items.
3. Keep them explicitly comparative and non-strategic.
4. Rerun Linear.

Kill or pause this path if Linear still abstains on `diferenciacion` after that extractor.

## Artifacts

- Packet: `examples/reports/evidence_packet/linear.local_evidence_packet.v0.json`
- Audit output: `output/linear-20260518-095648.json`
- Machine review: `docs/brand3_evidence_packet_linear_operability_test.json`
