# Visual Signature Calibration Governance Checkpoint

This checkpoint documents the current validated state of the Visual Signature
calibration bundle, the reliability report, and the scope-aware readiness gate.

## Current Validated Artifacts

- `calibration_manifest.json`
- `calibration_records.json`
- `calibration_summary.json`
- `calibration_summary.md`
- `calibration_reliability_report.md`
- `calibration_readiness.json`
- `calibration_readiness.md`

## Current Readiness State

- Readiness scope: `broader_corpus_use`
- Readiness status: `not_ready`
- Block reasons:
  - `small_sample_size`
  - `insufficient_reviewed_claims`
  - `insufficient_category_depth`
  - `insufficient_confidence_spread`
  - `contradiction_rate_too_high`
  - `high_confidence_contradictions_too_high`

## What Validation Means

Bundle validation means the calibration bundle is structurally coherent and
internally consistent:

- the records file exists and validates
- the summary file exists and validates
- the manifest file exists and validates
- record counts match
- summary counts match
- hashes and generated-file references are consistent

Validation does not mean broader corpus readiness.

## What Readiness Means

Readiness means the current validated bundle meets the conservative gates for
the evaluated scope.

For this checkpoint, readiness is scoped to `broader_corpus_use` only.
The current `ready` / `not_ready` result applies only to that scope.

It does not imply:

- production readiness
- scoring readiness
- runtime readiness
- provider-pilot readiness
- model-training readiness

## Bundle vs Report vs Readiness

### Validated bundle

The validated bundle is the evidence set itself:

- records
- summary
- manifest

It answers: "Is the bundle internally coherent?"

### Reliability report

The reliability report interprets the validated bundle:

- agreement rates
- contradiction rates
- confidence analysis
- uncertainty alignment
- category/source breakdowns

It answers: "What does the bundle say?"

### Readiness gate

The readiness gate checks whether the validated bundle is fit for a particular
scope.

It answers: "Should this bundle be used for broader corpus work?"

### Scope-aware readiness

Scope-aware readiness makes the evaluation target explicit. In this repository,
the current scope is `broader_corpus_use`.

For the official Visual Signature capability governance map, see
[capability_registry.md](../governance/capability_registry.md). Capability
presence does not imply production approval. Readiness is scope-dependent, and
the registry is evidence-only governance metadata that does not modify scoring,
rubric dimensions, runtime behavior, reports, or UI.

For the scope-based execution companion, see
[runtime_policy_matrix.md](../governance/runtime_policy_matrix.md). Capability
existence does not imply runtime approval, runtime policy is scope-dependent,
`production_runtime` blocks runtime mutation, and the matrix is governance
metadata only. It does not change scoring, rubric dimensions, capture
behavior, production UI/reports, taxonomy, or runtime behavior.

## Explicit Non-Goals

- no scoring impact
- no rubric impact
- no production UI impact
- no production report impact
- no capture behavior change
- no model training

## Current Limitations

- small sample size
- insufficient category depth
- insufficient confidence spread
- high contradiction rate

The current bundle is useful for evidence-only calibration review, but not yet
for broader corpus use.

## Recommended Next Phase

Two safe next directions remain:

1. Capability registry, if the goal is to formalize and constrain future
   calibration-related features.
2. Broader reviewed corpus expansion, if the goal is to improve readiness by
   increasing category depth and confidence spread.

## Notes

- This checkpoint is evidence-only.
- It does not alter scoring, rubric dimensions, production UI, production
  reports, or capture behavior.
