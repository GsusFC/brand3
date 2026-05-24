# Visual Signature Runtime Policy Matrix

Evidence-only governance matrix for Visual Signature capabilities under different readiness scopes.

- Capability existence != runtime approval: yes
- Readiness is scope-dependent: yes
- Runtime policy is governance-only: yes
- No production enablement is implied: yes

## Registry Metadata

- Matrix version: `visual-signature-runtime-policy-matrix-1`
- Generated at: 2026-05-12T11:31:32.190822+00:00
- Governance scope: `visual_signature`
- Capability count: 9
- Policy count: 60

## Scope Legend

- `allowed`: capability may be used within the evaluated evidence-only scope.
- `blocked`: capability must not be used within the evaluated scope.
- `review_only`: capability may be reviewed or inspected, but not used for runtime execution.
- `experimental_only`: capability is limited to experimental diagnostics and is not approved for broader use.

## Runtime Mutation Guardrail

- broader_corpus_use: experimental_only
- provider_pilot_use: experimental_only
- human_review_scaling: review_only
- production_runtime: blocked
- scoring_integration: blocked
- model_training: blocked

## Capabilities

### viewport_obstruction_detection

- Description: Detects viewport obstructions such as cookie banners, consent modals, login walls, and overlays.
- Layer: vision
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `low`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`

| Scope | Policy |
| --- | --- |
| broader_corpus_use | allowed |
| provider_pilot_use | allowed |
| human_review_scaling | allowed |
| production_runtime | review_only |
| scoring_integration | blocked |
| model_training | blocked |

### affordance_semantics

- Description: Classifies visible interaction affordances such as close, consent, login, subscription, and checkout controls.
- Layer: perception
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `low`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`

| Scope | Policy |
| --- | --- |
| broader_corpus_use | review_only |
| provider_pilot_use | review_only |
| human_review_scaling | allowed |
| production_runtime | review_only |
| scoring_integration | blocked |
| model_training | blocked |

### affordance_localization

- Description: Determines whether a detected affordance belongs to the active obstruction or unrelated UI.
- Layer: perception
- Maturity state: `constrained`
- Evidence status: `validated`
- Mutation risk: `low`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`

| Scope | Policy |
| --- | --- |
| broader_corpus_use | review_only |
| provider_pilot_use | review_only |
| human_review_scaling | allowed |
| production_runtime | review_only |
| scoring_integration | blocked |
| model_training | blocked |

### perceptual_state_machine

- Description: Tracks perceptual state transitions and mutation lineage for captured interfaces.
- Layer: perception
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `low`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`

| Scope | Policy |
| --- | --- |
| broader_corpus_use | review_only |
| provider_pilot_use | review_only |
| human_review_scaling | allowed |
| production_runtime | review_only |
| scoring_integration | blocked |
| model_training | blocked |

### mutation_audit

- Description: Records safe, minimal interaction attempts and before/after evidence lineage.
- Layer: mutation
- Maturity state: `constrained`
- Evidence status: `validated`
- Mutation risk: `moderate`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`

| Scope | Policy |
| --- | --- |
| broader_corpus_use | experimental_only |
| provider_pilot_use | experimental_only |
| human_review_scaling | review_only |
| production_runtime | blocked |
| scoring_integration | blocked |
| model_training | blocked |

### phase_two_review

- Description: Joins reviewed outcomes to Phase One records for human validation and eligibility control.
- Layer: validation
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `none`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `human_review_scaling`
- Prohibited scopes: `provider_pilot_use`, `production_runtime`, `scoring_integration`, `model_training`

| Scope | Policy |
| --- | --- |
| broader_corpus_use | review_only |
| provider_pilot_use | review_only |
| human_review_scaling | allowed |
| production_runtime | blocked |
| scoring_integration | blocked |
| model_training | blocked |

### calibration_bundle

- Description: Builds the evidence bundle that joins machine claims with reviewed outcomes.
- Layer: calibration
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `none`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`

| Scope | Policy |
| --- | --- |
| broader_corpus_use | allowed |
| provider_pilot_use | allowed |
| human_review_scaling | allowed |
| production_runtime | review_only |
| scoring_integration | blocked |
| model_training | blocked |

### calibration_reliability_reporting

- Description: Produces evidence-only reliability interpretation of the calibration bundle.
- Layer: calibration
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `none`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `human_review_scaling`
- Prohibited scopes: `provider_pilot_use`, `production_runtime`, `scoring_integration`, `model_training`

| Scope | Policy |
| --- | --- |
| broader_corpus_use | allowed |
| provider_pilot_use | review_only |
| human_review_scaling | allowed |
| production_runtime | review_only |
| scoring_integration | blocked |
| model_training | blocked |

### calibration_readiness_gate

- Description: Evaluates whether the calibration bundle is ready for a specific scope.
- Layer: governance
- Maturity state: `constrained`
- Evidence status: `validated`
- Mutation risk: `none`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`
- Prohibited scopes: `provider_pilot_use`, `human_review_scaling`, `production_runtime`, `scoring_integration`, `model_training`

| Scope | Policy |
| --- | --- |
| broader_corpus_use | review_only |
| provider_pilot_use | blocked |
| human_review_scaling | blocked |
| production_runtime | blocked |
| scoring_integration | blocked |
| model_training | blocked |

## Validation Notes

- All capability IDs must exist in the capability registry.
- All readiness scopes are explicit and validated.
- `production_runtime` never silently allows runtime mutation.
- Blocked and allowed states are not co-located for the same capability/scope.
