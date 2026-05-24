"""Evidence-only three-track validation plan for Visual Signature."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.calibration.readiness_models import ReadinessScope


THREE_TRACK_VALIDATION_PLAN_SCHEMA_VERSION = "visual-signature-three-track-validation-plan-1"
GOVERNANCE_SCOPE = "visual_signature"

VALID_TRACK_IDS: tuple[str, ...] = (
    "reviewer_workflow_validation",
    "corpus_real_validation",
    "provider_pilot_validation",
)

VALID_READINESS_SCOPES: tuple[ReadinessScope, ...] = (
    "broader_corpus_use",
    "human_review_scaling",
    "provider_pilot_use",
)

RECOMMENDED_ORDER: tuple[str, ...] = (
    "reviewer_workflow_validation",
    "corpus_real_validation",
    "provider_pilot_validation",
)


def build_three_track_validation_plan() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    tracks = [
        {
            "track_id": "reviewer_workflow_validation",
            "readiness_scope": "human_review_scaling",
            "goal": "Validate review queue usability, reviewer decisions, unresolved handling, contradiction handling, reviewer coverage, and review consistency without fake review data.",
            "scope": [
                "review queue usability",
                "reviewer decisions",
                "unresolved handling",
                "contradiction handling",
                "reviewer coverage",
                "review consistency",
            ],
            "inputs": [
                "review_queue.json",
                "pilot_metrics.json",
                "corpus_expansion_manifest.json",
                "reviewed Phase Two outputs where applicable",
                "governance integrity report",
                "calibration bundle summary and readiness files",
            ],
            "required_artifacts": [
                "real reviewer decisions",
                "unresolved cases preserved",
                "contradiction records",
                "reviewer coverage summary",
                "review queue state distribution",
            ],
            "success_criteria": [
                "review actions are explicit and reproducible",
                "unresolved cases remain unresolved",
                "contradictory outcomes are retained, not flattened",
                "reviewer coverage is measurable",
                "review records can be joined back to capture evidence",
            ],
            "block_conditions": [
                "synthetic or fabricated review data",
                "missing reviewer identity or timestamp",
                "unresolved cases collapsed into approval",
                "contradiction handling ambiguous",
                "review coverage too thin to support governance claims",
            ],
            "risks": [
                "review labels can drift without calibration",
                "reviewer disagreement can be misread as noise",
                "queue state semantics can become overloaded",
                "sparse review data can create false confidence",
            ],
            "manual_review_needed": True,
            "estimated_minimum_sample_size": 15,
            "explicit_non_goals": [
                "no scoring integration",
                "no runtime enablement",
                "no model training",
                "no production UI/report changes",
                "no capture behavior changes",
            ],
        },
        {
            "track_id": "corpus_real_validation",
            "readiness_scope": "broader_corpus_use",
            "goal": "Validate that 20-50 real captures can move through the evidence pipeline cleanly and remain usable for governance review.",
            "scope": [
                "real captures only",
                "category distribution across the current corpus categories",
                "screenshot validity and obstruction diagnostics",
                "affordance, localization, and state-machine outputs",
                "evidence completeness",
                "no scoring use",
            ],
            "inputs": [
                "capture_manifest.json",
                "dismissal_audit.json",
                "dismissal_audit.md",
                "governance_integrity_report.json",
                "calibration_readiness.json",
                "corpus_expansion_manifest.json",
                "review_queue.json",
                "pilot_metrics.json",
            ],
            "required_artifacts": [
                "validated capture manifests",
                "obstruction / affordance / state outputs where present",
                "review records for sampled captures",
                "corpus expansion manifest and metrics",
                "integrity report showing governance consistency",
            ],
            "success_criteria": [
                "20-50 real captures ingested",
                "category spread is materially broader than the current 5-capture scaffold",
                "screenshots are valid enough for evidence use",
                "obstruction and affordance diagnostics are present where applicable",
                "raw evidence remains primary and unchanged",
                "no scoring dependency appears",
            ],
            "block_conditions": [
                "missing raw evidence",
                "repeated invalid screenshots",
                "category concentration remains too narrow",
                "unresolved obstruction or mutation lineage gaps dominate",
                "any scoring linkage appears",
            ],
            "risks": [
                "capture quality varies by site",
                "category distribution can stay skewed",
                "obstruction heuristics may over-classify overlays",
                "evidence completeness can look better than it is if review is sparse",
            ],
            "manual_review_needed": True,
            "estimated_minimum_sample_size": 20,
            "explicit_non_goals": [
                "no scoring integration",
                "no rubric changes",
                "no runtime enablement",
                "no model training",
                "no production UI/report changes",
            ],
        },
        {
            "track_id": "provider_pilot_validation",
            "readiness_scope": "provider_pilot_use",
            "goal": "Define and validate the offline structure needed for a future multimodal provider pilot without making live provider calls.",
            "scope": [
                "provider-pilot inputs and outputs",
                "cache requirements",
                "cost tracking",
                "raw response storage",
                "normalized annotation overlay",
                "hallucination / unsupported-inference analysis",
                "reviewer comparison",
                "no live provider calls yet",
            ],
            "inputs": [
                "governance artifacts",
                "calibration bundle",
                "review outcomes",
                "corpus expansion records",
                "provider-pilot schema drafts",
                "provider output normalization rules",
            ],
            "required_artifacts": [
                "provider-pilot input schema",
                "raw response storage contract",
                "normalized annotation schema",
                "cost accounting fields",
                "comparison fields against human review",
                "unsupported inference markers",
            ],
            "success_criteria": [
                "provider-pilot contract is explicit and testable offline",
                "raw provider outputs can be stored without loss",
                "normalization preserves provenance",
                "hallucination and unsupported inference can be compared against human review",
                "cost tracking fields are defined",
            ],
            "block_conditions": [
                "live provider execution enabled too early",
                "raw responses cannot be preserved",
                "normalization loses provenance",
                "cost tracking is missing",
                "comparison against human review is not representable",
            ],
            "risks": [
                "provider output formats drift",
                "normalization can hide failure modes",
                "cost fields can be under-specified",
                "early live calls can contaminate governance signals",
            ],
            "manual_review_needed": True,
            "estimated_minimum_sample_size": 10,
            "explicit_non_goals": [
                "no live provider enablement",
                "no model training",
                "no scoring integration",
                "no runtime mutation",
                "no production UI/report changes",
            ],
        },
    ]

    return {
        "schema_version": THREE_TRACK_VALIDATION_PLAN_SCHEMA_VERSION,
        "record_type": "three_track_validation_plan",
        "generated_at": generated_at,
        "recommended_order": list(RECOMMENDED_ORDER),
        "tracks": tracks,
        "global_constraints": [
            "Tracks remain independent.",
            "No track is production-ready.",
            "No scoring is enabled.",
            "No model training is enabled.",
            "No runtime mutation is enabled.",
            "No taxonomy expansion is introduced.",
            "No capture behavior changes are introduced.",
        ],
        "current_state_implications": [
            "Governance integrity is valid but readiness remains scope-qualified.",
            "Broader corpus readiness is still not_ready.",
            "Corpus expansion pilot readiness is still not_ready.",
            "Provider pilot validation remains offline only.",
        ],
        "notes": [
            "Evidence-only governance artifact.",
            "No scoring, rubric dimensions, production UI, production reports, runtime behavior, or capture behavior are modified.",
        ],
    }


def validate_three_track_validation_plan_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        if payload.get("schema_version") != THREE_TRACK_VALIDATION_PLAN_SCHEMA_VERSION:
            errors.append(f"invalid schema_version: {payload.get('schema_version')!r}")
        if payload.get("record_type") != "three_track_validation_plan":
            errors.append(f"invalid record_type: {payload.get('record_type')!r}")
        tracks = payload.get("tracks", [])
        if len({track.get("track_id") for track in tracks}) != len(tracks):
            errors.append("track_id values must be unique")
        if len(tracks) != 3:
            errors.append("three_track_validation_plan must contain exactly 3 tracks")
        track_ids = [track.get("track_id") for track in tracks]
        if set(track_ids) != set(VALID_TRACK_IDS):
            errors.append(f"track_ids must match the expected tracks: {VALID_TRACK_IDS}")
        if payload.get("recommended_order") != list(RECOMMENDED_ORDER):
            errors.append("recommended_order must match the reviewed order")
        if payload.get("recommended_order") != list(track_ids):
            errors.append("recommended_order must match the order of tracks")
        for track in tracks:
            if track.get("readiness_scope") not in VALID_READINESS_SCOPES:
                errors.append(f"invalid readiness scope: {track.get('readiness_scope')!r}")
            if not track.get("manual_review_needed", False):
                errors.append(f"manual_review_needed must be true: {track.get('track_id')!r}")
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))
    return errors


def write_three_track_validation_plan(
    *,
    output_root: str | Path | None = None,
) -> dict[str, str]:
    root = Path(output_root) if output_root is not None else Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "governance"
    root.mkdir(parents=True, exist_ok=True)
    payload = build_three_track_validation_plan()
    errors = validate_three_track_validation_plan_payload(payload)
    if errors:
        raise ValueError("invalid three-track validation plan: " + "; ".join(errors))

    json_path = root / "three_track_validation_plan.json"
    md_path = root / "three_track_validation_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(three_track_validation_plan_markdown(payload) + "\n", encoding="utf-8")
    return {
        "three_track_validation_plan_json": str(json_path),
        "three_track_validation_plan_md": str(md_path),
    }


def three_track_validation_plan_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Three-Track Validation Plan",
        "",
        "Evidence-only governance plan for the three next validation tracks.",
        "",
        "- No scoring impact.",
        "- No rubric impact.",
        "- No production UI/report impact.",
        "- No runtime mutation enablement.",
        "- No provider execution enablement.",
        "- No taxonomy changes.",
        "- No capture behavior changes.",
        "",
        "## Recommended Order",
        "",
    ]
    for index, track_id in enumerate(payload["recommended_order"], start=1):
        lines.append(f"{index}. `{track_id}`")
    lines.extend(
        [
            "",
            "## Scope Mapping",
            "",
        ]
    )
    for track in payload["tracks"]:
        lines.append(f"- `{track['track_id']}` -> `{track['readiness_scope']}`")
    lines.extend(
        [
            "",
            "## Tracks",
            "",
        ]
    )
    for track in payload["tracks"]:
        lines.extend(
            [
                f"### {track['track_id']}",
                "",
                f"- Readiness scope: `{track['readiness_scope']}`",
                f"- Goal: {track['goal']}",
                "- Scope:",
            ]
        )
        lines.extend(f"  - {item}" for item in track["scope"])
        lines.append("- Inputs:")
        lines.extend(f"  - {item}" for item in track["inputs"])
        lines.append("- Required artifacts:")
        lines.extend(f"  - {item}" for item in track["required_artifacts"])
        lines.append("- Success criteria:")
        lines.extend(f"  - {item}" for item in track["success_criteria"])
        lines.append("- Block conditions:")
        lines.extend(f"  - {item}" for item in track["block_conditions"])
        lines.append("- Risks:")
        lines.extend(f"  - {item}" for item in track["risks"])
        lines.append(f"- Manual review needed: {'yes' if track['manual_review_needed'] else 'no'}")
        lines.append(f"- Estimated minimum sample size: {track['estimated_minimum_sample_size']}")
        lines.append("- Explicit non-goals:")
        lines.extend(f"  - {item}" for item in track["explicit_non_goals"])
        lines.append("")
    lines.extend(
        [
            "## Global Constraints",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["global_constraints"])
    lines.extend(
        [
            "",
            "## Current State Implications",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["current_state_implications"])
    lines.extend(
        [
            "",
            "## Explicit Non-Goals",
            "",
            "- no scoring impact",
            "- no rubric impact",
            "- no production UI/report impact",
            "- no runtime mutation enablement",
            "- no provider execution enablement",
            "- no taxonomy changes",
            "- no capture behavior changes",
            "",
            "No track implies production readiness.",
            "",
            "This plan is evidence-only governance metadata.",
        ]
    )
    return "\n".join(lines).rstrip()
