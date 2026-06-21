"""Shared constants and helpers for the Visual Signature web lab."""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VISUAL_SIGNATURE_ROOT = PROJECT_ROOT / "examples" / "visual_signature"

ARTIFACTS: dict[str, dict[str, str]] = {
    "capture_manifest": {
        "label": "Capture manifest",
        "path": "screenshots/capture_manifest.json",
        "type": "json",
        "section": "overview",
    },
    "dismissal_audit": {
        "label": "Dismissal audit",
        "path": "screenshots/dismissal_audit.json",
        "type": "json",
        "section": "overview",
    },
    "governance_integrity_report": {
        "label": "Governance integrity report",
        "path": "governance/governance_integrity_report.json",
        "type": "json",
        "section": "governance",
    },
    "capability_registry": {
        "label": "Capability registry",
        "path": "governance/capability_registry.json",
        "type": "json",
        "section": "governance",
    },
    "runtime_policy_matrix": {
        "label": "Runtime policy matrix",
        "path": "governance/runtime_policy_matrix.json",
        "type": "json",
        "section": "governance",
    },
    "three_track_validation_plan": {
        "label": "Three-track validation plan",
        "path": "governance/three_track_validation_plan.json",
        "type": "json",
        "section": "governance",
    },
    "calibration_readiness": {
        "label": "Calibration readiness",
        "path": "calibration/calibration_readiness.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_manifest": {
        "label": "Calibration manifest",
        "path": "calibration/calibration_manifest.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_summary": {
        "label": "Calibration summary",
        "path": "calibration/calibration_summary.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_records": {
        "label": "Calibration records",
        "path": "calibration/calibration_records.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_reliability_report": {
        "label": "Calibration reliability report",
        "path": "calibration/calibration_reliability_report.md",
        "type": "markdown",
        "section": "calibration",
    },
    "corpus_expansion_manifest": {
        "label": "Corpus expansion manifest",
        "path": "corpus_expansion/corpus_expansion_manifest.json",
        "type": "json",
        "section": "corpus",
    },
    "pilot_metrics": {
        "label": "Pilot metrics",
        "path": "corpus_expansion/pilot_metrics.json",
        "type": "json",
        "section": "corpus",
    },
    "review_queue": {
        "label": "Review queue",
        "path": "corpus_expansion/review_queue.json",
        "type": "json",
        "section": "reviewer",
    },
    "reviewer_workflow_pilot": {
        "label": "Reviewer workflow pilot",
        "path": "corpus_expansion/reviewer_workflow_pilot.json",
        "type": "json",
        "section": "reviewer",
    },
    "reviewer_packet_index": {
        "label": "Reviewer packet index",
        "path": "corpus_expansion/reviewer_packets/reviewer_packet_index.md",
        "type": "markdown",
        "section": "reviewer",
    },
    "reviewer_viewer": {
        "label": "Reviewer viewer",
        "path": "corpus_expansion/reviewer_viewer/index.html",
        "type": "html",
        "section": "reviewer",
    },
}

HUMAN_REVIEW_DESIGN_PATH = DEFAULT_VISUAL_SIGNATURE_ROOT / "human_review_ui_design.json"
REVIEW_SEMANTICS_PATH = DEFAULT_VISUAL_SIGNATURE_ROOT / "review_semantics.json"


def visual_signature_root() -> Path:
    return Path(os.environ.get("BRAND3_VISUAL_SIGNATURE_ROOT", str(DEFAULT_VISUAL_SIGNATURE_ROOT)))


def artifact_path(key: str, *, root: Path | None = None) -> Path | None:
    spec = ARTIFACTS.get(key)
    if not spec:
        return None
    root = root or visual_signature_root()
    return root / spec["path"]


def artifact_file_response_payload(key: str) -> tuple[Path, str] | None:
    spec = ARTIFACTS.get(key)
    path = artifact_path(key)
    if not spec or path is None or not path.exists() or not _is_under_root(path):
        return None
    media_type = {
        "json": "application/json",
        "markdown": "text/markdown; charset=utf-8",
        "html": "text/html; charset=utf-8",
    }.get(spec["type"], "text/plain; charset=utf-8")
    return path, media_type


def screenshot_file_response_payload(filename: str) -> tuple[Path, str] | None:
    path = visual_signature_root() / "screenshots" / filename
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        return None
    if not path.exists() or not _is_under_root(path):
        return None
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }[path.suffix.lower()]
    return path, media_type


def _related_variant_payload(variant: dict[str, Any], selected_filename: str) -> dict[str, Any]:
    payload = dict(variant)
    payload["is_current"] = payload.get("filename") == selected_filename
    return payload


def _artifact_payload(key: str) -> dict[str, Any]:
    spec = ARTIFACTS[key]
    path = artifact_path(key)
    exists = bool(path and path.exists())
    payload = _load_json(path) if exists and spec["type"] == "json" else None
    return {
        "key": key,
        "label": spec["label"],
        "type": spec["type"],
        "section": spec["section"],
        "exists": exists,
        "path": str(path) if path else "",
        "source_href": f"/visual-signature/artifacts/{key}",
        "status": _status_for(payload, exists=exists),
        "summary": _summary_for(payload, spec["type"], exists=exists),
        "raw_json": _pretty_json(payload) if payload is not None else "",
    }


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else {"items": value}


def _status_for(payload: dict[str, Any] | None, *, exists: bool) -> str:
    if not exists:
        return "missing"
    if not isinstance(payload, dict):
        return "available"
    for key in ("status", "readiness_status", "validation_status", "pilot_status", "record_type"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return "available"


def _summary_for(payload: dict[str, Any] | None, artifact_type: str, *, exists: bool) -> dict[str, Any]:
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


def _cards_for_section(section: str, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
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


def _artifacts_for_section(section: str, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
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


def _items_for_section(section: str, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if section == "governance":
        registry = _load_json(artifact_path("capability_registry")) or {}
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
            for item in _as_list(registry.get("capabilities"))[:12]
        ]
    if section in {"corpus", "reviewer"}:
        queue = _load_json(artifact_path("review_queue")) or {}
        pilot = _load_json(artifact_path("reviewer_workflow_pilot")) or {}
        selected = set(_as_list(pilot.get("selected_review_queue_item_ids")))
        rows = []
        for item in _as_list(queue.get("queue_items")):
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
        readiness = _load_json(artifact_path("calibration_readiness")) or {}
        rows = []
        for reason in _as_list(readiness.get("block_reasons")) + _as_list(readiness.get("warning_reasons")):
            rows.append({"title": str(reason), "status": "readiness_note", "meta": {}})
        return rows
    return []




def _pretty_json(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return ""
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _nested(payload: dict[str, Any], key: str, nested_key: str) -> Any:
    value = payload.get(key)
    return value.get(nested_key) if isinstance(value, dict) else None


def _find_manifest_row(payload: dict[str, Any], brand_name: str) -> dict[str, Any] | None:
    target = brand_name.lower()
    for row in _as_list(payload.get("results")):
        if isinstance(row, dict) and str(row.get("brand_name") or "").lower() == target:
            return row
    return None


def _slugify(value: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in normalized.split("-") if part)


def _is_under_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(visual_signature_root().resolve())
    except ValueError:
        return False
    return True
