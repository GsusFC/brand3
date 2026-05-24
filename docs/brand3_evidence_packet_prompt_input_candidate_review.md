# Brand3 Evidence Packet Prompt Input Candidate Review

Date: 2026-05-18  
Scope: offline input-shape only. No prose generation, no prompt rollout, no scoring, no renderer, no persisted payload, no Visual Signature changes.

## What Was Built

`build_prompt_input_candidate_v0(packet)` converts an existing Evidence Packet v0 into a stricter prompt-input candidate.

It includes only dimensions with readiness `ready` or `thin`. It excludes `blocked`, `abstain`, and `review_required` dimensions. It also filters out evidence that is technical/internal, visual metric, trust/security, noise, unresolved related-surface, marketplace/review-gated, or empty-text.

## Case Summary

| Case | included dimensions | excluded dimensions | review-required dimensions | included evidence |
| --- | --- | --- | --- | --- |
| Linear | coherencia, presencia, percepcion, diferenciacion, vitalidad | - | - | 12 |
| Vercel | coherencia, presencia, percepcion, diferenciacion, vitalidad | - | - | 12 |
| Builtwith/Kit | - | coherencia, presencia, percepcion, diferenciacion, vitalidad | - | 0 |
| Watermelon | coherencia, presencia, percepcion | diferenciacion, vitalidad | - | 3 |
| LaunchDarkly | presencia, percepcion, diferenciacion, vitalidad | - | coherencia | 12 |

## Objective Assessment

The candidate reduces noisy input while preserving useful evidence in stable cases.

- Linear keeps all five dimensions and includes bounded competitor-comparison evidence for `diferenciacion`.
- Vercel keeps all five dimensions.
- LaunchDarkly keeps four dimensions and excludes `coherencia` because it is review-required.
- Watermelon keeps only `coherencia`, `presencia`, and `percepcion`; `diferenciacion` and `vitalidad` stay out.
- Builtwith/Kit includes no dimensions, which is the correct conservative behavior for an entity-mixed case.

## Prompt Contract Improvement

This is materially cleaner than passing the raw dimension evidence pool to the model. The candidate gives the model:

- included evidence only,
- excluded evidence separately,
- readiness status,
- abstention reasons,
- review-required dimensions,
- dimension-specific constraints.

The most important shift is that blocked dimensions are explicit. The model is no longer asked to rationalize weak or mixed inputs into findings.

## Remaining Weakness Against Deep Research

The candidate is still weaker than Deep Research because:

- some provenance is `snapshot://...` instead of source URL/text grounded;
- source-quality reasoning is deterministic and shallow;
- related-surface/entity relation is heuristic;
- it does not discover missing evidence, it only filters what Brand3 already collected.

## Recommendation

Good enough for one controlled non-runtime generation comparison, preferably Linear first:

1. current narrative input;
2. prompt-input candidate;
3. same model;
4. no report mutation;
5. compare output quality and overreach.

Do not integrate this into runtime yet.

## Artifacts

- `src/reports/evidence_packet_prompt_input.py`
- `tests/test_evidence_packet_prompt_input.py`
- `examples/reports/evidence_packet_prompt_input/*.prompt_input_candidate.v0.json`
- `docs/brand3_evidence_packet_prompt_input_candidate_review.json`
