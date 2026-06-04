"""Pure response presenters for the public Brand3 Scanner API."""

from __future__ import annotations

from typing import Any, Literal


Lang = Literal["es", "en"]


def lang_query(lang: Lang) -> str:
    return f"?lang={lang}"


def scanner_status_payload(
    row: dict[str, Any],
    *,
    phase: str,
    readiness: dict[str, Any],
    lang: Lang = "es",
) -> dict[str, Any]:
    scan_id = int(row.get("id") or 0)
    status = str(row.get("status") or "queued")
    return {
        "id": scan_id,
        "status": status,
        "phase": phase,
        "brand_name": row.get("brand_name"),
        "url": row.get("url"),
        "source_run_id": row.get("source_run_id"),
        "created_at": row.get("created_at"),
        "started_at": row.get("started_at"),
        "completed_at": row.get("completed_at"),
        "error_message": row.get("error_message"),
        "scanner_readiness": readiness,
        "result_available": status == "ready",
        "status_url": f"/api/v1/scanner/{scan_id}",
        "result_url": f"/api/v1/scanner/{scan_id}/result",
        "evidence_url": f"/api/v1/scanner/{scan_id}/evidence",
        "methodology_url": f"/api/v1/scanner/{scan_id}/methodology",
        "audit_url": f"/api/v1/scanner/{scan_id}/audit",
        "ui_url": f"/magnetism-scanner/scan/{scan_id}{lang_query(lang)}" if status == "ready" else None,
    }
