"""Worker queue helper functions."""

from __future__ import annotations

import json
import sqlite3

from src.quality.publication_readiness import is_publishable_report
from src.services.magnetism_service import ensure_sv9_scan_for_source_run


def _analysis_report_readiness(
    result: dict,
    *,
    run_id: int | None,
    db_path: str,
) -> dict | None:
    audit = result.get("audit") if isinstance(result, dict) else None
    if not isinstance(audit, dict):
        audit = {}
    readiness = audit.get("report_readiness")
    if isinstance(readiness, dict):
        return readiness
    if not run_id:
        return None
    try:
        from src.reports.derivation import build_report_readiness_from_snapshot
        from src.storage.sqlite_store import SQLiteStore

        store = SQLiteStore(db_path)
        try:
            snapshot = store.get_run_snapshot(run_id)
        finally:
            store.close()
        if not snapshot:
            return None
        derived = build_report_readiness_from_snapshot(snapshot)
        return derived if isinstance(derived, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _is_publishable_report(readiness: dict | None) -> bool:
    return is_publishable_report(readiness)


def _run_brand_scan(url: str, progress_cb=None) -> dict:
    from src.services.brand_service import run as brand_service_run

    from ..config import settings

    return brand_service_run(
        url,
        use_social=True,
        use_llm=True,
        enable_visual_signature_shadow_run=settings.visual_signature_scan_enabled,
        progress_cb=progress_cb,
    )


def _run_magnetism_scan(job: dict, progress_cb=None) -> dict:
    from src.services.magnetism_service import (
        run_legacy_manual_magnetism,
        run_magnetism_from_audit_run,
        run_magnetism_from_url,
    )

    input_type = str(job.get("input_type") or "url")
    input_value = str(job.get("input_value") or "")
    if input_type == "audit_run":
        if progress_cb is not None:
            progress_cb("interpreting")
        return run_magnetism_from_audit_run(int(input_value))
    if input_type == "manual":
        if progress_cb is not None:
            progress_cb("extracting")
        return run_legacy_manual_magnetism(input_value)
    if progress_cb is not None:
        progress_cb("collecting")
    return run_magnetism_from_url(input_value, progress_cb=progress_cb)


def _ensure_sv9_scan_for_magnetism_result(payload: dict, db_path: str) -> int | None:
    source_run_id = _payload_source_run_id(payload)
    if source_run_id is None:
        return None
    try:
        return ensure_sv9_scan_for_source_run(
            source_run_id,
            db_path=db_path,
            magnetism_result=payload,
        )
    except Exception:
        return None


def _payload_source_run_id(payload: dict) -> int | None:
    try:
        value = payload.get("source_run_id")
        if value is None:
            return None
        source_run_id = int(value)
    except (TypeError, ValueError):
        return None
    return source_run_id if source_run_id > 0 else None


def _complete_magnetism_scan(token: str, payload: dict, now: str, db_path: str) -> None:
    from web.storage import (
        _magnetism_payload_insert_state,
        _magnetism_public_fields_from_payload,
    )

    payload_json = _json_payload(payload)
    source_run_id = _payload_source_run_id(payload)
    normalized_payload, _status, _error_message = _magnetism_payload_insert_state(
        payload_json,
        source_run_id=source_run_id,
    )
    magnetism_score, coherence_score, quadrant = _magnetism_public_fields_from_payload(
        normalized_payload,
        magnetism_score=int(payload.get("magnetism_score") or 0),
        coherence_score=int(payload.get("coherence_score") or 0),
        quadrant=str(payload.get("quadrant") or "pending"),
    )
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            UPDATE magnetism_scans
            SET brand_name = ?,
                url = ?,
                magnetism_score = ?,
                coherence_score = ?,
                quadrant = ?,
                raw_payload = ?,
                source_run_id = COALESCE(?, source_run_id),
                status = 'ready',
                phase = 'ready',
                phase_updated_at = ?,
                completed_at = ?,
                error_message = NULL
            WHERE token = ?
            """,
            (
                str(payload.get("brand_name") or "Unknown Brand"),
                str(payload.get("url") or "Manual Upload"),
                magnetism_score,
                coherence_score,
                quadrant,
                normalized_payload,
                source_run_id,
                now,
                now,
                token,
            ),
        )
        conn.commit()


def _fail_magnetism_scan_with_payload(token: str, reason: str, payload: dict, now: str, db_path: str) -> None:
    payload_json = _json_payload(payload)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            UPDATE magnetism_scans
            SET raw_payload = ?,
                status = 'failed',
                phase = 'failed',
                phase_updated_at = ?,
                completed_at = ?,
                error_message = ?
            WHERE token = ?
            """,
            (payload_json, now, now, reason[:500], token),
        )
        conn.commit()


def _json_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


__all__ = [
    "_analysis_report_readiness",
    "_is_publishable_report",
    "_run_brand_scan",
    "_run_magnetism_scan",
    "_ensure_sv9_scan_for_magnetism_result",
    "_complete_magnetism_scan",
    "_fail_magnetism_scan_with_payload",
]
