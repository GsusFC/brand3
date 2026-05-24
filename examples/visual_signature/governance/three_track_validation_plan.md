# Visual Signature Three-Track Validation Plan

Evidence-only governance plan for the three next validation tracks.

- No scoring impact.
- No rubric impact.
- No production UI/report impact.
- No runtime mutation enablement.
- No provider execution enablement.
- No taxonomy changes.
- No capture behavior changes.

## Recommended Order

1. `reviewer_workflow_validation`
2. `corpus_real_validation`
3. `provider_pilot_validation`

## Scope Mapping

- `reviewer_workflow_validation` -> `human_review_scaling`
- `corpus_real_validation` -> `broader_corpus_use`
- `provider_pilot_validation` -> `provider_pilot_use`

## Tracks

### reviewer_workflow_validation

- Readiness scope: `human_review_scaling`
- Goal: Validate review queue usability, reviewer decisions, unresolved handling, contradiction handling, reviewer coverage, and review consistency without fake review data.
- Scope:
  - review queue usability
  - reviewer decisions
  - unresolved handling
  - contradiction handling
  - reviewer coverage
  - review consistency
- Inputs:
  - review_queue.json
  - pilot_metrics.json
  - corpus_expansion_manifest.json
  - reviewed Phase Two outputs where applicable
  - governance integrity report
  - calibration bundle summary and readiness files
- Required artifacts:
  - real reviewer decisions
  - unresolved cases preserved
  - contradiction records
  - reviewer coverage summary
  - review queue state distribution
- Success criteria:
  - review actions are explicit and reproducible
  - unresolved cases remain unresolved
  - contradictory outcomes are retained, not flattened
  - reviewer coverage is measurable
  - review records can be joined back to capture evidence
- Block conditions:
  - synthetic or fabricated review data
  - missing reviewer identity or timestamp
  - unresolved cases collapsed into approval
  - contradiction handling ambiguous
  - review coverage too thin to support governance claims
- Risks:
  - review labels can drift without calibration
  - reviewer disagreement can be misread as noise
  - queue state semantics can become overloaded
  - sparse review data can create false confidence
- Manual review needed: yes
- Estimated minimum sample size: 15
- Explicit non-goals:
  - no scoring integration
  - no runtime enablement
  - no model training
  - no production UI/report changes
  - no capture behavior changes

### corpus_real_validation

- Readiness scope: `broader_corpus_use`
- Goal: Validate that 20-50 real captures can move through the evidence pipeline cleanly and remain usable for governance review.
- Scope:
  - real captures only
  - category distribution across the current corpus categories
  - screenshot validity and obstruction diagnostics
  - affordance, localization, and state-machine outputs
  - evidence completeness
  - no scoring use
- Inputs:
  - capture_manifest.json
  - dismissal_audit.json
  - dismissal_audit.md
  - governance_integrity_report.json
  - calibration_readiness.json
  - corpus_expansion_manifest.json
  - review_queue.json
  - pilot_metrics.json
- Required artifacts:
  - validated capture manifests
  - obstruction / affordance / state outputs where present
  - review records for sampled captures
  - corpus expansion manifest and metrics
  - integrity report showing governance consistency
- Success criteria:
  - 20-50 real captures ingested
  - category spread is materially broader than the current 5-capture scaffold
  - screenshots are valid enough for evidence use
  - obstruction and affordance diagnostics are present where applicable
  - raw evidence remains primary and unchanged
  - no scoring dependency appears
- Block conditions:
  - missing raw evidence
  - repeated invalid screenshots
  - category concentration remains too narrow
  - unresolved obstruction or mutation lineage gaps dominate
  - any scoring linkage appears
- Risks:
  - capture quality varies by site
  - category distribution can stay skewed
  - obstruction heuristics may over-classify overlays
  - evidence completeness can look better than it is if review is sparse
- Manual review needed: yes
- Estimated minimum sample size: 20
- Explicit non-goals:
  - no scoring integration
  - no rubric changes
  - no runtime enablement
  - no model training
  - no production UI/report changes

### provider_pilot_validation

- Readiness scope: `provider_pilot_use`
- Goal: Define and validate the offline structure needed for a future multimodal provider pilot without making live provider calls.
- Scope:
  - provider-pilot inputs and outputs
  - cache requirements
  - cost tracking
  - raw response storage
  - normalized annotation overlay
  - hallucination / unsupported-inference analysis
  - reviewer comparison
  - no live provider calls yet
- Inputs:
  - governance artifacts
  - calibration bundle
  - review outcomes
  - corpus expansion records
  - provider-pilot schema drafts
  - provider output normalization rules
- Required artifacts:
  - provider-pilot input schema
  - raw response storage contract
  - normalized annotation schema
  - cost accounting fields
  - comparison fields against human review
  - unsupported inference markers
- Success criteria:
  - provider-pilot contract is explicit and testable offline
  - raw provider outputs can be stored without loss
  - normalization preserves provenance
  - hallucination and unsupported inference can be compared against human review
  - cost tracking fields are defined
- Block conditions:
  - live provider execution enabled too early
  - raw responses cannot be preserved
  - normalization loses provenance
  - cost tracking is missing
  - comparison against human review is not representable
- Risks:
  - provider output formats drift
  - normalization can hide failure modes
  - cost fields can be under-specified
  - early live calls can contaminate governance signals
- Manual review needed: yes
- Estimated minimum sample size: 10
- Explicit non-goals:
  - no live provider enablement
  - no model training
  - no scoring integration
  - no runtime mutation
  - no production UI/report changes

## Global Constraints

- Tracks remain independent.
- No track is production-ready.
- No scoring is enabled.
- No model training is enabled.
- No runtime mutation is enabled.
- No taxonomy expansion is introduced.
- No capture behavior changes are introduced.

## Current State Implications

- Governance integrity is valid but readiness remains scope-qualified.
- Broader corpus readiness is still not_ready.
- Corpus expansion pilot readiness is still not_ready.
- Provider pilot validation remains offline only.

## Explicit Non-Goals

- no scoring impact
- no rubric impact
- no production UI/report impact
- no runtime mutation enablement
- no provider execution enablement
- no taxonomy changes
- no capture behavior changes

No track implies production readiness.

This plan is evidence-only governance metadata.
