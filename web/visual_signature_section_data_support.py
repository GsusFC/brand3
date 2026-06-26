"""Section-specific artifact summary helpers for Visual Signature web views."""

from __future__ import annotations

from typing import Any


def status_for(payload: dict[str, Any] | None, *, exists: bool) -> str:
    if not exists:
        return "missing"
    if not isinstance(payload, dict):
        return "available"
    for key in ("status", "readiness_status", "validation_status", "pilot_status", "record_type"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return "available"


def summary_for(payload: dict[str, Any] | None, artifact_type: str, *, exists: bool) -> dict[str, Any]:
    if not exists:
        return {"state": "missing_or_unknown"}
    if artifact_type != "json" or not isinstance(payload, dict):
        return {"state": "available"}
    keys = (
        "schema_version",
        "record_type",
        "generated_at",
        "checked_at",
        "completed_at",
        "status",
        "readiness_status",
        "validation_status",
        "pilot_status",
        "record_count",
        "capability_count",
        "policy_count",
        "error_count",
        "warning_count",
        "selected_review_queue_item_count",
        "current_capture_count",
        "reviewed_capture_count",
        "target_capture_count",
        "reviewer_coverage",
        "contradiction_rate",
        "unresolved_rate",
    )
    return {key: payload[key] for key in keys if key in payload}


def cards_for_section(section: str, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    card_keys = {
        "overview": [
            "governance_integrity_report",
            "capability_registry",
            "runtime_policy_matrix",
            "calibration_readiness",
            "calibration_reliability_report",
            "pilot_metrics",
            "reviewer_workflow_pilot",
        ],
        "governance": [
            "governance_integrity_report",
            "capability_registry",
            "runtime_policy_matrix",
            "three_track_validation_plan",
        ],
        "calibration": [
            "calibration_readiness",
            "calibration_manifest",
            "calibration_summary",
            "calibration_records",
            "calibration_reliability_report",
        ],
        "corpus": [
            "corpus_expansion_manifest",
            "pilot_metrics",
            "review_queue",
            "reviewer_workflow_pilot",
        ],
        "reviewer": [
            "reviewer_workflow_pilot",
            "review_queue",
            "reviewer_packet_index",
            "reviewer_viewer",
        ],
    }[section]
    return [artifacts[key] for key in card_keys]


def artifacts_for_section(section: str, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if section == "overview":
        return [
            artifacts[key]
            for key in (
                "governance_integrity_report",
                "capability_registry",
                "runtime_policy_matrix",
                "calibration_readiness",
                "calibration_reliability_report",
                "pilot_metrics",
                "reviewer_workflow_pilot",
            )
        ]
    return [artifact for artifact in artifacts.values() if artifact["section"] == section]


def items_for_section(
    section: str,
    *,
    load_json,
    artifact_path,
    as_list,
) -> list[dict[str, Any]]:
    if section == "governance":
        registry = load_json(artifact_path("capability_registry")) or {}
        return [
            {
                "title": item.get("capability_id", "capability"),
                "status": item.get("maturity_state") or item.get("evidence_status") or "record",
                "meta": {
                    "layer": item.get("layer"),
                    "evidence_status": item.get("evidence_status"),
                    "production_enabled": item.get("production_enabled", False),
                },
            }
            for item in as_list(registry.get("capabilities"))[:12]
        ]
    if section in {"corpus", "reviewer"}:
        queue = load_json(artifact_path("review_queue")) or {}
        pilot = load_json(artifact_path("reviewer_workflow_pilot")) or {}
        selected = set(as_list(pilot.get("selected_review_queue_item_ids")))
        rows = []
        for item in as_list(queue.get("queue_items")):
            if section == "corpus" or item.get("queue_id") in selected or item.get("queue_state") in {"queued", "needs_additional_evidence"}:
                rows.append(
                    {
                        "title": item.get("brand_name") or item.get("queue_id", "queue item"),
                        "status": item.get("queue_state") or "record",
                        "meta": {
                            "queue_id": item.get("queue_id"),
                            "category": item.get("category"),
                            "capture_id": item.get("capture_id"),
                            "selected_for_pilot": item.get("queue_id") in selected,
                        },
                    }
                )
        return rows[:20]
    if section == "calibration":
        readiness = load_json(artifact_path("calibration_readiness")) or {}
        return [
            {"title": str(reason), "status": "readiness_note", "meta": {}}
            for reason in as_list(readiness.get("block_reasons")) + as_list(readiness.get("warning_reasons"))
        ]
    return []
