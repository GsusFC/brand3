export type ConfidenceLevel = "low" | "medium" | "high";
export type PerceptionLayer = "functional" | "editorial";

export interface PhaseZeroRegistryDocument<T> {
  schema_version: string;
  taxonomy_version: string;
  registry_type: string;
  items: T[];
}

export type ObservationRegistryDocument = PhaseZeroRegistryDocument<ObservationDefinition>;
export type StateRegistryDocument = PhaseZeroRegistryDocument<StateDefinition>;
export type TransitionRegistryDocument = PhaseZeroRegistryDocument<TransitionDefinition>;
export type ScoringRegistryDocument = PhaseZeroRegistryDocument<ScoreDefinition>;

export interface UncertaintyPolicy {
  schema_version: string;
  taxonomy_version: string;
  policy_type: "uncertainty_policy";
  confidence_threshold: number;
  reviewer_required_threshold: number;
  known_unknown_labels: string[];
  uncertainty_reasons: string[];
  reviewer_required_labels: string[];
}

export interface ObservationDefinition {
  key: string;
  layer: PerceptionLayer;
  description: string;
  value_type: "categorical" | "numeric" | "boolean" | "text";
  notes: string[];
}

export interface StateDefinition {
  key: string;
  description: string;
  terminal: boolean;
  review_required: boolean;
  mutation_allowed: boolean;
}

export interface TransitionDefinition {
  key: string;
  from_states: string[];
  to_state: string;
  description: string;
  requires_lineage: boolean;
  requires_evidence: boolean;
}

export interface ScoreDefinition {
  key: string;
  description: string;
  observation_keys: string[];
  enabled: boolean;
  boundary_note: string;
}

export interface UncertaintyProfile {
  schema_version: string;
  taxonomy_version: string;
  record_type: "uncertainty_profile";
  confidence: number;
  confidence_level: ConfidenceLevel;
  known_unknowns: string[];
  uncertainty_reasons: string[];
  reviewer_required: boolean;
  unsupported_inference: boolean;
}

export interface ReasoningStatement {
  statement: string;
  confidence: number;
  evidence_refs: string[];
  warnings: string[];
}

export interface ReasoningTrace {
  schema_version: string;
  taxonomy_version: string;
  record_type: "reasoning_trace";
  trace_id: string;
  created_at: string;
  summary: string;
  statements: ReasoningStatement[];
  unsupported_inference_warnings: string[];
  review_required: boolean;
  lineage_refs: string[];
}

export type ReviewStatus = "approved" | "rejected" | "needs_more_evidence";
export type VisuallySupported = "yes" | "partial" | "no";

export interface ReviewRecord {
  schema_version: string;
  taxonomy_version: string;
  record_type: "review_record";
  review_id: string;
  capture_id: string;
  reviewer_id: string;
  reviewed_at: string;
  review_status: ReviewStatus;
  visually_supported: VisuallySupported;
  unsupported_inference_present: boolean;
  uncertainty_accepted: boolean;
  notes: string[];
}

export interface PerceptualObservationRecord {
  schema_version: string;
  taxonomy_version: string;
  record_type: "perceptual_observation";
  record_id: string;
  created_at: string;
  capture_id: string;
  brand_name: string;
  website_url: string;
  perception_layer: PerceptionLayer;
  observation_key: string;
  observation_value: string;
  confidence: number;
  uncertainty: UncertaintyProfile;
  evidence_refs: string[];
  reasoning_trace: ReasoningTrace;
  lineage_refs: string[];
}

export interface TransitionRecord {
  schema_version: string;
  taxonomy_version: string;
  record_type: "transition_record";
  transition_id: string;
  created_at: string;
  capture_id: string;
  from_state: string;
  to_state: string;
  reason: string;
  confidence: number;
  evidence_refs: string[];
  lineage_refs: string[];
  mutation_ref: string | null;
  notes: string[];
}

export interface PerceptualStateRecord {
  schema_version: string;
  taxonomy_version: string;
  record_type: "perceptual_state";
  record_id: string;
  created_at: string;
  capture_id: string;
  brand_name: string;
  website_url: string;
  perceptual_state: string;
  confidence: number;
  uncertainty: UncertaintyProfile;
  transitions: TransitionRecord[];
  reasoning_trace: ReasoningTrace;
  lineage_refs: string[];
}

export interface MutationAuditRecord {
  schema_version: string;
  taxonomy_version: string;
  record_type: "mutation_audit";
  mutation_id: string;
  created_at: string;
  capture_id: string;
  brand_name: string;
  website_url: string;
  mutation_type: string;
  before_state: string;
  after_state: string;
  attempted: boolean;
  successful: boolean;
  reversible: boolean;
  risk_level: "low" | "medium" | "high" | "blocking";
  trigger: string;
  evidence_preserved: boolean;
  before_artifact_ref: string;
  after_artifact_ref: string | null;
  lineage_refs: string[];
  integrity_notes: string[];
}

export interface DatasetEligibilityRecord {
  schema_version: string;
  taxonomy_version: string;
  record_type: "dataset_eligibility";
  record_id: string;
  created_at: string;
  capture_id: string;
  brand_name: string;
  website_url: string;
  eligible: boolean;
  reasons: string[];
  blocked_reasons: string[];
  raw_evidence_preserved: boolean;
  mutation_lineage_preserved: boolean;
  schema_valid: boolean;
  review_required: boolean;
  review_completed: boolean;
  uncertainty_below_threshold: boolean;
  confidence_threshold: number;
  observed_confidence: number;
  unsupported_inference_found: boolean;
  evidence_refs: string[];
  lineage_refs: string[];
}
