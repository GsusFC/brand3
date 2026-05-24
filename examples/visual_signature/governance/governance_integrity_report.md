# Governance Integrity Check

Evidence-only governance consistency check for Visual Signature artifacts.

- Readiness scope: `broader_corpus_use`
- Readiness status: `not_ready`
- Status: `valid`
- Checked at: 2026-05-12T11:47:28.529305+00:00
- Error count: 0
- Warning count: 0

## Checked Artifacts

- capability_registry: `/Users/gsus/Antigravity/Brand3/brand3/examples/visual_signature/governance/capability_registry.json`
- runtime_policy_matrix: `/Users/gsus/Antigravity/Brand3/brand3/examples/visual_signature/governance/runtime_policy_matrix.json`
- calibration_readiness: `/Users/gsus/Antigravity/Brand3/brand3/examples/visual_signature/calibration/calibration_readiness.json`
- calibration_governance_checkpoint: `/Users/gsus/Antigravity/Brand3/brand3/examples/visual_signature/calibration/calibration_governance_checkpoint.md`
- technical_checkpoint: `/Users/gsus/Antigravity/Brand3/brand3/examples/visual_signature/technical_checkpoint.md`
- reliable_visual_perception: `/Users/gsus/Antigravity/Brand3/brand3/examples/visual_signature/reliable_visual_perception.md`

## Errors

- none

## Warnings

- none

## Enforced Invariants

- All runtime policy capability IDs exist in the capability registry.
- All readiness scopes are valid known scopes.
- Capability allowed and prohibited scopes do not overlap.
- production_enabled is false for every capability.
- scoring_impact is false for every capability.
- production_runtime blocks runtime mutation.
- The runtime policy matrix does not silently allow prohibited scopes.
- Governance docs reference both the capability registry and runtime policy matrix.
- Calibration readiness remains scope-qualified, not generic.
- Governance docs retain evidence-only / no scoring / no production implication language.
