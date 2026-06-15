"""Application service for Magnetism scans.

This module keeps acquisition decisions out of web routes and out of the
Magnetism extractor. URL scans go through Brand Audit, then Magnetism interprets
that persisted snapshot. Manual text remains a legacy direct/debug path.
"""

from __future__ import annotations

import logging
import inspect
from collections.abc import Callable
from typing import Any

from src.config import BRAND3_DB_PATH, LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.features.magnetism.extractor import MagnetismExtractor
from src.services.brand_service import run as run_brand_audit
from src.storage.sqlite_store import SQLiteStore

log = logging.getLogger(__name__)


BrandAuditRunner = Callable[[str], dict[str, Any]]


_AUDIT_TO_SCANNER_PHASE = {
    "collecting": "collecting",
    "extracting": "extracting",
    "scoring": "interpreting",
    "finalizing": "interpreting",
}


def run_magnetism_from_url(
    url: str,
    *,
    llm: LLMAnalyzer | None = None,
    run_input_sources: set[str] | None = None,
    audit_runner: BrandAuditRunner = run_brand_audit,
    db_path: str = BRAND3_DB_PATH,
    progress_cb: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run canonical Magnetism for a URL via a persisted Brand Audit snapshot."""
    llm = _effective_llm(llm)
    audit_result = _run_audit_with_progress(
        url,
        audit_runner,
        progress_cb=progress_cb,
        run_input_sources=run_input_sources,
    )
    run_id = audit_result.get("run_id") if isinstance(audit_result, dict) else None
    if not run_id:
        raise RuntimeError(
            "Brand Audit did not return a run_id for canonical Magnetism analysis."
        )
    _emit_progress(progress_cb, "interpreting")
    return run_magnetism_from_audit_run(int(run_id), llm=llm, db_path=db_path)


def run_magnetism_from_audit_run(
    run_id: int,
    *,
    llm: LLMAnalyzer | None = None,
    db_path: str = BRAND3_DB_PATH,
) -> dict[str, Any]:
    """Run Magnetism from an existing Brand Audit run snapshot."""
    llm = _effective_llm(llm)
    snapshot = load_brand_audit_snapshot(run_id, db_path=db_path)
    return run_magnetism_from_audit_snapshot(snapshot, llm=llm)


def run_magnetism_from_audit_snapshot(
    snapshot: dict[str, Any],
    *,
    llm: LLMAnalyzer | None = None,
) -> dict[str, Any]:
    """Run Magnetism from an already loaded Brand Audit snapshot."""
    return MagnetismExtractor(llm=_effective_llm(llm)).extract_from_audit_snapshot(snapshot)


def run_legacy_manual_magnetism(
    manual_text: str,
    *,
    llm: LLMAnalyzer | None = None,
) -> dict[str, Any]:
    """Run legacy direct Magnetism for pasted evidence without public acquisition."""
    return MagnetismExtractor(llm=_effective_llm(llm)).extract(url=None, manual_text=manual_text or None)


def ensure_sv9_scan_for_source_run(
    source_run_id: int | None,
    *,
    db_path: str = BRAND3_DB_PATH,
    magnetism_result: dict[str, Any] | None = None,
) -> int | None:
    """Materialize or reuse the shadow SV9 scan for a Brand Audit run."""
    if source_run_id is None or int(source_run_id) <= 0:
        return None
    try:
        from src.sv9.rubric import RUBRIC_VERSION
        from src.sv9.service import materialize_sv9_scan
        from src.sv9.store import Sv9Store

        sv9_store = Sv9Store(db_path)
        try:
            existing = sv9_store.get_scan_for_run(int(source_run_id), rubric_version=RUBRIC_VERSION)
            if existing:
                return int(existing["id"])
            if _is_reusable_sv9_detection(magnetism_result, int(source_run_id)):
                sv9_store.save_detection(int(source_run_id), magnetism_result)
        finally:
            sv9_store.close()
        # Full pipeline (pinned detection, vision signals, editorial): the
        # button must produce the same scan quality as the replay script.
        scan_id, _result = materialize_sv9_scan(int(source_run_id), db_path=db_path)
        return scan_id
    except Exception:  # noqa: BLE001
        log.exception("SV9 materialization failed source_run_id=%s", source_run_id)
        return None


def _is_reusable_sv9_detection(payload: dict[str, Any] | None, source_run_id: int) -> bool:
    """Return whether a completed Magnetism payload is safe as SV9 Pass 1."""
    if not isinstance(payload, dict):
        return False
    if _payload_source_run_id(payload) != int(source_run_id):
        return False
    return isinstance(payload.get("tldr_brand3"), dict)


def _payload_source_run_id(payload: dict[str, Any]) -> int | None:
    try:
        value = payload.get("source_run_id")
        if value is None:
            return None
        source_run_id = int(value)
    except (TypeError, ValueError):
        return None
    return source_run_id if source_run_id > 0 else None


def _effective_llm(llm: LLMAnalyzer | None) -> LLMAnalyzer | None:
    """Use the configured Magnetism analyst LLM unless the caller supplied one."""
    if llm is not None:
        return llm
    candidate = LLMAnalyzer(model=LLM_PREMIUM_MODEL)
    if getattr(candidate, "api_key", None):
        return candidate
    return None


def _run_audit_with_progress(
    url: str,
    audit_runner: BrandAuditRunner,
    *,
    progress_cb: Callable[[str], None] | None,
    run_input_sources: set[str] | None = None,
) -> dict[str, Any]:
    """Run Brand Audit and map its internal phases onto Scanner phases."""
    _emit_progress(progress_cb, "collecting")

    def audit_progress_cb(phase: str) -> None:
        _emit_progress(progress_cb, _AUDIT_TO_SCANNER_PHASE.get(phase, "interpreting"))

    signature = inspect.signature(audit_runner)
    if "progress_cb" not in signature.parameters:
        return audit_runner(url)
    if "run_input_sources" in signature.parameters:
        return audit_runner(
            url,
            run_input_sources=run_input_sources,
            progress_cb=audit_progress_cb,
        )

    return audit_runner(url, progress_cb=audit_progress_cb)


def _emit_progress(progress_cb: Callable[[str], None] | None, phase: str) -> None:
    if progress_cb is None:
        return
    progress_cb(phase)


def load_brand_audit_snapshot(
    run_id: int,
    *,
    db_path: str = BRAND3_DB_PATH,
) -> dict[str, Any]:
    store = SQLiteStore(db_path)
    try:
        snapshot = store.get_run_snapshot(run_id)
    finally:
        store.close()
    if snapshot is None:
        raise RuntimeError(
            f"Brand Audit run #{run_id} could not be loaded as a snapshot."
        )
    return snapshot
