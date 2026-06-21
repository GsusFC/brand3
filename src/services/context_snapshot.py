"""Snapshot-derived context readiness helpers."""

from __future__ import annotations

from src.quality.trust import quality_label


def _context_readiness_from_snapshot(snapshot: dict) -> dict:
    for item in reversed(snapshot.get("raw_inputs") or []):
        if item.get("source") != "context" or not isinstance(item.get("payload"), dict):
            continue
        payload = item["payload"]
        coverage = float(payload.get("coverage") or 0.0)
        confidence = float(payload.get("confidence") or 0.0)
        if coverage < 0.3:
            status = "insufficient_data"
        elif confidence < 0.6:
            status = "degraded"
        else:
            status = "good"
        return {
            "available": True,
            "coverage": coverage,
            "confidence": confidence,
            "coverage_label": quality_label(coverage),
            "confidence_label": quality_label(confidence),
            "status": status,
            "confidence_reason": payload.get("confidence_reason") or [],
            "context_score": payload.get("context_score"),
        }
    return {
        "available": False,
        "coverage": 0.0,
        "confidence": 0.0,
        "coverage_label": "baja",
        "confidence_label": "baja",
        "status": "insufficient_data",
        "confidence_reason": ["context_scan_unavailable"],
    }
