"""Shared Scanner API response models derived from persisted scan payloads."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from src.features.magnetism.extractor import MagnetismExtractor
from src.features.magnetism.readiness import assess_scanner_readiness
from src.features.magnetism.scan_mode import scan_mode_from_payload, scan_mode_from_row
from src.quality.publication_readiness import scanner_publication_decision_payload

from .presenters import (
    scanner_methodology_payload,
    scanner_research_evidence_payload,
    scanner_result_metadata,
)


def magnetism_scan_model_from_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = normalized_scan_payload(row)
    return scan_model_from_payload(row, payload, scan_id=int(row["id"]))


def normalized_scan_payload(row: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(row["raw_payload"])
    except Exception:
        raise HTTPException(status_code=500, detail="Corrupted scan payload in database.")
    if not payload.get("metrics") or not payload.get("tldr_brand3"):
        payload = MagnetismExtractor(llm=None)._normalize_analysis(payload)
    else:
        payload = MagnetismExtractor(llm=None).ensure_tldr_v03_contract(payload)
    return payload


def scan_model_from_payload(row: dict[str, Any], payload: dict[str, Any], *, scan_id: int) -> dict[str, Any]:
    try:
        dt = datetime.fromisoformat(row["created_at"].replace(" ", "T"))
        formatted_date = dt.strftime("%B %d, %Y at %I:%M %p UTC")
    except Exception:
        formatted_date = row["created_at"]

    return {
        "id": scan_id,
        "title": f"Magnetism: {payload['brand_name']}",
        "brand_name": payload["brand_name"],
        "url": payload["url"],
        "created_at": formatted_date,
        "magnetism_score": payload["magnetism_score"],
        "coherence_score": payload["coherence_score"],
        "quadrant": payload["quadrant"],
        "executive_headline": payload["executive_headline"],
        "observations": payload["observations"],
        "tldr_grid": payload["tldr_grid"],
        "tldr_brand3": payload.get("tldr_brand3") or {},
        "tldr_strategy": payload.get("tldr_strategy") or {},
        "metrics": payload.get("metrics") or {},
        "diagnosis": payload.get("diagnosis") or {},
        "limitations": payload.get("limitations") or [],
        "source": payload.get("source") or "direct_scan",
        "source_run_id": payload.get("source_run_id") or row.get("source_run_id"),
        "extraction_mode": payload.get("extraction_mode") or "unknown",
        "canonical_evidence_source": payload.get("canonical_evidence_source"),
        "direct_source_provider": payload.get("direct_source_provider"),
        "deprecation": payload.get("deprecation") or {},
        "evidence_packet_summary": payload.get("evidence_packet_summary") or {},
        "content_distillation_summary": payload.get("content_distillation_summary") or {},
        "system_reading": payload.get("system_reading") or {},
        "score_breakdown": payload["score_breakdown"],
        "magenta_circle": payload["magenta_circle"],
        "fallback_used": payload.get("fallback_used", False),
        "scan_mode": scan_mode_from_payload(
            payload,
            source_run_id=payload.get("source_run_id") or row.get("source_run_id"),
        ).to_payload(),
        "payload": payload,
    }


def research_evidence_model(payload: dict[str, Any]) -> dict[str, Any]:
    return scanner_research_evidence_payload(
        payload,
        entity_packet=entity_research_packet(payload),
    )


def methodology_model(payload: dict[str, Any]) -> dict[str, Any]:
    return scanner_methodology_payload(
        payload,
        result_metadata=scanner_result_metadata_model(payload),
    )


def scanner_result_metadata_model(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = scanner_result_metadata(
        payload,
        scanner_readiness=scanner_readiness_from_payload(payload),
        publication_decision=publication_decision_from_payload(payload),
    )
    metadata["scan_mode"] = scan_mode_from_payload(
        payload,
        source_run_id=payload.get("source_run_id"),
    ).to_payload()
    return metadata


def scanner_scan_mode_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return scan_mode_from_row(row).to_payload()


def scanner_readiness_from_row(row: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    raw_payload = row.get("raw_payload")
    if raw_payload:
        try:
            loaded = json.loads(raw_payload)
        except Exception:
            loaded = {}
        if isinstance(loaded, dict):
            payload = loaded
    input_type = str(row.get("input_type") or ("audit_run" if row.get("source_run_id") else "url"))
    readiness = payload.get("scanner_readiness")
    if isinstance(readiness, dict):
        return readiness
    return assess_scanner_readiness(input_type, payload).to_payload()


def scanner_readiness_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    readiness = payload.get("scanner_readiness")
    if isinstance(readiness, dict):
        return readiness
    input_type = "manual" if is_manual_magnetism_payload(payload) else "url"
    return assess_scanner_readiness(input_type, payload).to_payload()


def publication_decision_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    decision = payload.get("publication_decision")
    if isinstance(decision, dict):
        return decision
    return scanner_publication_decision_payload(scanner_readiness_from_payload(payload))


def is_manual_magnetism_payload(payload: dict[str, Any]) -> bool:
    return (
        payload.get("source") in {"legacy_direct", "direct_magnetism_legacy"}
        or payload.get("extraction_mode") == "legacy_direct"
        or bool(payload.get("direct_source_provider"))
        or payload.get("url") == "manual"
    )


def entity_research_packet(payload: dict[str, Any]) -> dict[str, Any]:
    research_pack = payload.get("research_pack") or {}
    entity = research_pack.get("entity") or {}
    if isinstance(entity, dict) and (entity.get("owned_surfaces") or entity.get("product_surfaces")):
        return entity
    return {}
