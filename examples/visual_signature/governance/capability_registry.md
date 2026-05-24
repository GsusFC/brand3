# Visual Signature Capability Registry

Evidence-only governance registry for Visual Signature capabilities.

- Not a production enablement list: yes
- Capability presence != production approval: yes
- Readiness is scope-dependent: yes
- Evidence-only capabilities can still be not_ready: yes

## Registry Metadata

- Registry version: `visual-signature-capability-registry-1`
- Generated at: 2026-05-12T09:30:48.225578+00:00
- Capability count: 9
- Governance scope: `visual_signature`

## Governance Notes

- This is an evidence-only governance registry.
- Capability presence does not imply production approval.
- Readiness is scope-dependent and separate from capability presence.
- Evidence-only capabilities can still be not_ready.
- No scoring, rubric dimensions, production UI, production reports, or capture behavior are modified.

For the scope-based execution companion to this registry, see
[runtime_policy_matrix.md](./runtime_policy_matrix.md). Capability existence
does not imply runtime approval, runtime policy is scope-dependent,
`production_runtime` blocks runtime mutation, and the matrix is governance
metadata only. It does not change scoring, rubric dimensions, capture
behavior, production UI/reports, taxonomy, or runtime behavior.

## Capabilities

### viewport_obstruction_detection

- Description: Detects viewport obstructions such as cookie banners, consent modals, login walls, and overlays.
- Layer: vision
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `low`
- Scoring impact: `false`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`
- Dependencies: `raw_viewport_capture`, `dom_heuristics`, `obstruction_signals`
- Outputs: `viewport_obstruction`, `obstruction_audit`, `capture_manifest.obstruction_fields`
- Known limitations: Overlay ownership can be ambiguous., False positives remain possible on sticky site chrome.
- Governance notes: Detection is evidence-only., Does not click, dismiss, or mutate the page.

### affordance_semantics

- Description: Classifies visible interaction affordances such as close, consent, login, subscription, and checkout controls.
- Layer: perception
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `low`
- Scoring impact: `false`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`
- Dependencies: `visible_text`, `aria_label`, `role`, `dom_context`, `overlay_context`
- Outputs: `candidate_click_targets.affordance_category`, `dismissal_audit.affordance_category_distribution`
- Known limitations: Semantic labels are conservative by design., Classification does not imply click eligibility.
- Governance notes: Diagnostics only., Click behavior remains separate.

### affordance_localization

- Description: Determines whether a detected affordance belongs to the active obstruction or unrelated UI.
- Layer: perception
- Maturity state: `constrained`
- Evidence status: `validated`
- Mutation risk: `low`
- Scoring impact: `false`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`
- Dependencies: `dom_ancestry`, `viewport_location`, `z_index`, `overlay_context`, `aria_dialog_relationships`
- Outputs: `candidate_click_targets.affordance_owner`, `dismissal_audit.affordance_owner_distribution`
- Known limitations: Ownership can remain unknown when evidence is mixed., Localization is diagnostic-only and does not widen clicking.
- Governance notes: Used to explain rejected targets., Does not promote targets into execution.

### perceptual_state_machine

- Description: Tracks perceptual state transitions and mutation lineage for captured interfaces.
- Layer: perception
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `low`
- Scoring impact: `false`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`
- Dependencies: `raw_capture`, `obstruction_detection`, `safe_intervention_policy`
- Outputs: `perceptual_state`, `perceptual_transitions`, `mutation_audit`
- Known limitations: State vocabulary is intentionally small., Experimental mutation records remain supplemental to raw evidence.
- Governance notes: Supports evidence lineage and auditability., Does not alter scoring or capture defaults.

### mutation_audit

- Description: Records safe, minimal interaction attempts and before/after evidence lineage.
- Layer: mutation
- Maturity state: `constrained`
- Evidence status: `validated`
- Mutation risk: `moderate`
- Scoring impact: `false`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`
- Dependencies: `dismissal_flow`, `raw_viewport_capture`, `safe_affordance_discovery`
- Outputs: `mutation_audit`, `dismissal_audit`
- Known limitations: Safe attempts are opt-in and conservative., Mutation success never replaces raw evidence.
- Governance notes: Audit trail only., Supports reversible evidence-preserving captures.

### phase_two_review

- Description: Joins reviewed outcomes to Phase One records for human validation and eligibility control.
- Layer: validation
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `none`
- Scoring impact: `false`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `human_review_scaling`
- Prohibited scopes: `provider_pilot_use`, `production_runtime`, `scoring_integration`, `model_training`
- Dependencies: `phase_one_records`, `review_records`
- Outputs: `review_outcome`, `reviewed_dataset_eligibility`
- Known limitations: Human review remains required for uncertain records., Review coverage is sample-dependent.
- Governance notes: Human validation remains separate from scoring., Reviewed eligibility is a governance output only.

### calibration_bundle

- Description: Builds the evidence bundle that joins machine claims with reviewed outcomes.
- Layer: calibration
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `none`
- Scoring impact: `false`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `provider_pilot_use`, `human_review_scaling`
- Prohibited scopes: `production_runtime`, `scoring_integration`, `model_training`
- Dependencies: `phase_one_records`, `phase_two_reviews`, `capture_manifest`, `dismissal_audit`
- Outputs: `calibration_records`, `calibration_summary`, `calibration_manifest`
- Known limitations: Current bundle is small and category-sparse., High-confidence contradictions are still present.
- Governance notes: Evidence-only bundle generation., No scoring or runtime behavior changes.

### calibration_reliability_reporting

- Description: Produces evidence-only reliability interpretation of the calibration bundle.
- Layer: calibration
- Maturity state: `governed`
- Evidence status: `validated`
- Mutation risk: `none`
- Scoring impact: `false`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`, `human_review_scaling`
- Prohibited scopes: `provider_pilot_use`, `production_runtime`, `scoring_integration`, `model_training`
- Dependencies: `calibration_bundle`, `validated_records`
- Outputs: `calibration_reliability_report`
- Known limitations: Interpretive and descriptive only., Not a substitute for larger corpus sampling.
- Governance notes: Summarizes bundle quality and limitations., Does not imply readiness by itself.

### calibration_readiness_gate

- Description: Evaluates whether the calibration bundle is ready for a specific scope.
- Layer: governance
- Maturity state: `constrained`
- Evidence status: `validated`
- Mutation risk: `none`
- Scoring impact: `false`
- Runtime mutation: `false`
- Production enabled: `false`
- Allowed scopes: `broader_corpus_use`
- Prohibited scopes: `provider_pilot_use`, `human_review_scaling`, `production_runtime`, `scoring_integration`, `model_training`
- Dependencies: `calibration_bundle`, `calibration_manifest`, `calibration_corpus_manifest`
- Outputs: `calibration_readiness`, `calibration_governance_checkpoint`
- Known limitations: Current implementation only governs broader corpus use., Does not define readiness for production, scoring, runtime, provider pilot, or training.
- Governance notes: Scope-aware readiness is explicit and conservative., Unsupported scopes are not silently reused from broader-corpus thresholds.

## Validation Notes

- Prohibited scopes are disjoint from allowed scopes.
- Registry validation rejects score-impacting or production-enabled capabilities.
- The registry is evidence-only and does not alter runtime behavior.
