from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.visual_signature.phase_zero import PHASE_ZERO_ROOT
from src.visual_signature.phase_zero.catalog import (
    DATASET_ELIGIBILITY_RECORD,
    MUTATION_AUDIT,
    OBSERVATION_RECORD,
    OBSERVATION_REGISTRY,
    PHASE_ZERO_MANIFEST,
    REASONING_TRACE,
    REVIEW_RECORD,
    SCORING_REGISTRY,
    STATE_RECORD,
    STATE_REGISTRY,
    TRANSITION_RECORD,
    TRANSITION_REGISTRY,
    UNCERTAINTY_POLICY,
    UNCERTAINTY_PROFILE,
)
from src.visual_signature.phase_zero.models import (
    DatasetEligibilityRecord,
    MutationAuditRecord,
    PerceptualObservationRecord,
    PerceptualStateRecord,
    ReasoningTrace,
    ReviewRecord,
    ScoringRegistry,
    StateRegistry,
    TransitionRecord,
    TransitionRegistry,
    UncertaintyPolicy,
    UncertaintyProfile,
    ObservationRegistry,
)


SCHEMA_BUILDERS: list[tuple[str, type[Any]]] = [
    ("schemas/observation_registry.schema.json", ObservationRegistry),
    ("schemas/state_registry.schema.json", StateRegistry),
    ("schemas/transition_registry.schema.json", TransitionRegistry),
    ("schemas/scoring_registry.schema.json", ScoringRegistry),
    ("schemas/uncertainty_policy.schema.json", UncertaintyPolicy),
    ("schemas/uncertainty_profile.schema.json", UncertaintyProfile),
    ("schemas/reasoning_trace.schema.json", ReasoningTrace),
    ("schemas/perceptual_observation.schema.json", PerceptualObservationRecord),
    ("schemas/perceptual_state.schema.json", PerceptualStateRecord),
    ("schemas/transition_record.schema.json", TransitionRecord),
    ("schemas/mutation_audit.schema.json", MutationAuditRecord),
    ("schemas/review_record.schema.json", ReviewRecord),
    ("schemas/dataset_eligibility.schema.json", DatasetEligibilityRecord),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Phase Zero JSON artifacts.")
    parser.add_argument("--root", type=Path, default=PHASE_ZERO_ROOT)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)

    phase_zero_root: Path = args.root
    repo_root: Path = args.repo_root
    phase_zero_root.mkdir(parents=True, exist_ok=True)
    _ensure_directories(phase_zero_root)

    generated: list[str] = []

    _write_json(phase_zero_root / "taxonomy" / "observation_registry.json", OBSERVATION_REGISTRY)
    _write_json(phase_zero_root / "taxonomy" / "state_registry.json", STATE_REGISTRY)
    _write_json(phase_zero_root / "taxonomy" / "transition_registry.json", TRANSITION_REGISTRY)
    _write_json(phase_zero_root / "taxonomy" / "scoring_registry.json", SCORING_REGISTRY)
    _write_json(phase_zero_root / "taxonomy" / "uncertainty_policy.json", UNCERTAINTY_POLICY)
    _write_json(phase_zero_root / "fixtures" / "uncertainty_profile.example.json", UNCERTAINTY_PROFILE)
    generated.extend(
        [
            "taxonomy/observation_registry.json",
            "taxonomy/state_registry.json",
            "taxonomy/transition_registry.json",
            "taxonomy/scoring_registry.json",
            "taxonomy/uncertainty_policy.json",
            "fixtures/uncertainty_profile.example.json",
        ]
    )

    for relative_path, model in SCHEMA_BUILDERS:
        _write_json(phase_zero_root / relative_path, model.model_json_schema())
        generated.append(relative_path)

    _write_json(phase_zero_root / "fixtures" / "observation_record.example.json", OBSERVATION_RECORD)
    _write_json(phase_zero_root / "fixtures" / "state_record.example.json", STATE_RECORD)
    _write_json(phase_zero_root / "fixtures" / "transition_record.example.json", TRANSITION_RECORD)
    _write_json(phase_zero_root / "fixtures" / "mutation_audit.example.json", MUTATION_AUDIT)
    _write_json(phase_zero_root / "fixtures" / "review_record.example.json", REVIEW_RECORD)
    _write_json(phase_zero_root / "fixtures" / "reasoning_trace.example.json", REASONING_TRACE)
    _write_json(phase_zero_root / "fixtures" / "dataset_eligibility.example.json", DATASET_ELIGIBILITY_RECORD)
    generated.extend(
        [
            "fixtures/observation_record.example.json",
            "fixtures/state_record.example.json",
            "fixtures/transition_record.example.json",
            "fixtures/mutation_audit.example.json",
            "fixtures/review_record.example.json",
            "fixtures/reasoning_trace.example.json",
            "fixtures/dataset_eligibility.example.json",
        ]
    )

    _write_json(phase_zero_root / "manifests" / "phase_zero_manifest.json", PHASE_ZERO_MANIFEST)
    generated.append("manifests/phase_zero_manifest.json")

    _write_typescript_interface(repo_root / "src" / "visual_signature" / "phase_zero" / "types.ts")

    print(json.dumps({"root": str(phase_zero_root), "generated": generated}, indent=2))
    return 0


def _ensure_directories(root: Path) -> None:
    for relative in ("taxonomy", "schemas", "fixtures", "manifests"):
        (root / relative).mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_typescript_interface(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """export type ConfidenceLevel = "low" | "medium" | "high";
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
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
