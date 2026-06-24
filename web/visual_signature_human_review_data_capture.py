"""Helpers for Visual Signature human review capture and evidence payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .visual_signature_data_support import _is_under_root
from .visual_signature_data_support import _slugify
from .visual_signature_data_support import visual_signature_root


def _human_review_queue_item(item: dict[str, Any], *, active: bool) -> dict[str, Any]:
    capture_id = _slugify(str(item.get("capture_id") or item.get("brand_name") or ""))
    return {
        "queue_id": item.get("queue_id") or f"queue_{capture_id}",
        "capture_id": capture_id,
        "brand_name": item.get("brand_name") or capture_id.replace("-", " ").title(),
        "category": item.get("category") or "unknown",
        "queue_state": item.get("queue_state") or "queued",
        "confidence_bucket": item.get("confidence_bucket") or "unknown",
        "website_url": item.get("website_url") or "",
        "active": active,
        "href": f"/visual-signature/reviewer/human-review/{capture_id}",
    }


def _fallback_evidence_for_capture(queue_item: dict[str, Any]) -> dict[str, Any]:
    root = visual_signature_root()
    capture_id = queue_item["capture_id"]
    return {
        "brand_name": queue_item["brand_name"],
        "capture_id": capture_id,
        "website_url": queue_item.get("website_url") or "",
        "capture_status": "available",
        "obstruction_type": "unknown",
        "obstruction_severity": "unknown",
        "dismissal_attempted": False,
        "dismissal_successful": False,
        "perceptual_state": "evidence_record",
        "evidence_notes": [],
        "variants": [
            _screenshot_variant_payload("raw viewport", root / "screenshots" / f"{capture_id}.png"),
            _screenshot_variant_payload("clean attempt", root / "screenshots" / f"{capture_id}.clean-attempt.png"),
            _screenshot_variant_payload("full page", root / "screenshots" / f"{capture_id}.full-page.png"),
        ],
    }


def _human_review_active_capture(queue_item: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    variants = evidence.get("variants") or []
    raw_variant = next((variant for variant in variants if variant.get("label") == "raw viewport"), None)
    return {
        "queue_id": queue_item["queue_id"],
        "capture_id": queue_item["capture_id"],
        "brand_name": evidence.get("brand_name") or queue_item["brand_name"],
        "category": queue_item.get("category") or "unknown",
        "website_url": evidence.get("website_url") or queue_item.get("website_url") or "",
        "queue_state": queue_item.get("queue_state") or "queued",
        "confidence_bucket": queue_item.get("confidence_bucket") or "unknown",
        "capture_status": evidence.get("capture_status") or "available",
        "perceptual_state": evidence.get("perceptual_state") or "evidence_record",
        "obstruction_type": evidence.get("obstruction_type") or "unknown",
        "obstruction_severity": evidence.get("obstruction_severity") or "unknown",
        "dismissal_attempted": bool(evidence.get("dismissal_attempted")),
        "dismissal_successful": bool(evidence.get("dismissal_successful")),
        "evidence_notes": evidence.get("evidence_notes") or [],
        "variants": variants,
        "primary_variant": raw_variant or (variants[0] if variants else None),
        "evidence_refs": [variant["href"] for variant in variants if variant.get("exists")],
    }


def _human_review_source_artifacts(root: Path, active: dict[str, Any]) -> list[dict[str, str]]:
    capture_id = active["capture_id"]
    artifact_paths = [
        ("review_queue.json", root / "corpus_expansion" / "review_queue.json"),
        ("reviewer_workflow_pilot.json", root / "corpus_expansion" / "reviewer_workflow_pilot.json"),
        ("capture_manifest.json", root / "screenshots" / "capture_manifest.json"),
        ("dismissal_audit.json", root / "screenshots" / "dismissal_audit.json"),
        ("phase_one state", root / "phase_one" / "records" / capture_id / "state.json"),
        ("phase_one obstruction", root / "phase_one" / "records" / capture_id / "obstruction.json"),
        ("phase_two review", root / "phase_two" / "records" / capture_id / "reviewed_dataset_eligibility.json"),
    ]
    return [
        {
            "label": label,
            "path": str(path),
            "status": "available" if path.exists() else "missing_or_unknown",
        }
        for label, path in artifact_paths
    ]


def _screenshot_variant_payload(label: str, path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else (visual_signature_root() / path)
    exists = resolved.exists() and _is_under_root(resolved)
    filename = resolved.name
    return {
        "label": label,
        "exists": exists,
        "filename": filename,
        "path": str(resolved),
        "href": f"/visual-signature/screenshots/{filename}",
        "preview_href": f"/visual-signature/screenshots/{filename}/preview",
        "alt": f"{label} screenshot: {filename}",
    }


__all__ = [
    "_fallback_evidence_for_capture",
    "_human_review_active_capture",
    "_human_review_queue_item",
    "_human_review_source_artifacts",
    "_screenshot_variant_payload",
]

