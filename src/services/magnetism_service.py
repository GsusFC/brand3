"""Application service for Magnetism scans.

This module keeps acquisition decisions out of web routes and out of the
Magnetism extractor. URL scans go through Brand Audit, then Magnetism interprets
that persisted snapshot. Manual text remains a legacy direct/debug path.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.config import BRAND3_DB_PATH
from src.features.llm_analyzer import LLMAnalyzer
from src.features.magnetism.extractor import MagnetismExtractor
from src.services.brand_service import run as run_brand_audit
from src.storage.sqlite_store import SQLiteStore


BrandAuditRunner = Callable[[str], dict[str, Any]]


def run_magnetism_from_url(
    url: str,
    *,
    llm: LLMAnalyzer | None = None,
    audit_runner: BrandAuditRunner = run_brand_audit,
    db_path: str = BRAND3_DB_PATH,
) -> dict[str, Any]:
    """Run canonical Magnetism for a URL via a persisted Brand Audit snapshot."""
    audit_result = audit_runner(url)
    run_id = audit_result.get("run_id") if isinstance(audit_result, dict) else None
    if not run_id:
        raise RuntimeError(
            "Brand Audit did not return a run_id for canonical Magnetism analysis."
        )
    return run_magnetism_from_audit_run(int(run_id), llm=llm, db_path=db_path)


def run_magnetism_from_audit_run(
    run_id: int,
    *,
    llm: LLMAnalyzer | None = None,
    db_path: str = BRAND3_DB_PATH,
) -> dict[str, Any]:
    """Run Magnetism from an existing Brand Audit run snapshot."""
    snapshot = load_brand_audit_snapshot(run_id, db_path=db_path)
    return run_magnetism_from_audit_snapshot(snapshot, llm=llm)


def run_magnetism_from_audit_snapshot(
    snapshot: dict[str, Any],
    *,
    llm: LLMAnalyzer | None = None,
) -> dict[str, Any]:
    """Run Magnetism from an already loaded Brand Audit snapshot."""
    return MagnetismExtractor(llm=llm).extract_from_audit_snapshot(snapshot)


def run_legacy_manual_magnetism(
    manual_text: str,
    *,
    llm: LLMAnalyzer | None = None,
) -> dict[str, Any]:
    """Run legacy direct Magnetism for pasted evidence without public acquisition."""
    return MagnetismExtractor(llm=llm).extract(url=None, manual_text=manual_text or None)


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
