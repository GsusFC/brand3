"""Application service for Reverse Engineering scans.

Reverse Engineering should consume the same Brand Audit snapshot boundary as
other Brand3 lenses. Direct text input remains available only as a legacy/debug
path for ad-hoc evidence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.config import BRAND3_DB_PATH
from src.features.llm_analyzer import LLMAnalyzer
from src.features.reverse_engineering.extractor import ReverseEngineeringExtractor
from src.services.brand_service import run as run_brand_audit
from src.storage.sqlite_store import SQLiteStore


BrandAuditRunner = Callable[[str], dict[str, Any]]
LEGACY_REVERSE_DEPRECATION = {
    "status": "deprecated",
    "replacement": "run_reverse_engineering_from_audit_snapshot",
    "reason": (
        "Brand Audit owns acquisition; Reverse Engineering should interpret "
        "CanonicalBrandEvidence from a persisted snapshot."
    ),
}


def run_reverse_engineering_from_url(
    url: str,
    *,
    llm: LLMAnalyzer | None = None,
    audit_runner: BrandAuditRunner = run_brand_audit,
    db_path: str = BRAND3_DB_PATH,
) -> dict[str, Any]:
    """Run canonical Reverse Engineering for a URL via Brand Audit."""
    audit_result = audit_runner(url)
    run_id = audit_result.get("run_id") if isinstance(audit_result, dict) else None
    if not run_id:
        raise RuntimeError(
            "Brand Audit did not return a run_id for canonical Reverse Engineering."
        )
    return run_reverse_engineering_from_audit_run(int(run_id), llm=llm, db_path=db_path)


def run_reverse_engineering_from_audit_run(
    run_id: int,
    *,
    llm: LLMAnalyzer | None = None,
    db_path: str = BRAND3_DB_PATH,
) -> dict[str, Any]:
    """Run Reverse Engineering from an existing Brand Audit run snapshot."""
    snapshot = load_brand_audit_snapshot(run_id, db_path=db_path)
    return run_reverse_engineering_from_audit_snapshot(snapshot, llm=llm)


def run_reverse_engineering_from_audit_snapshot(
    snapshot: dict[str, Any],
    *,
    llm: LLMAnalyzer | None = None,
) -> dict[str, Any]:
    """Run Reverse Engineering from an already loaded Brand Audit snapshot."""
    return ReverseEngineeringExtractor(llm=llm).extract_from_audit_snapshot(snapshot)


def run_legacy_reverse_engineering(
    web_markdown: str,
    *,
    mentions: list[str] | None = None,
    visual_signature: dict[str, Any] | None = None,
    brand_name: str = "Unknown Brand",
    llm: LLMAnalyzer | None = None,
) -> dict[str, Any]:
    """Run legacy direct Reverse Engineering without public acquisition."""
    result = ReverseEngineeringExtractor(llm=llm).extract(
        web_markdown=web_markdown,
        mentions=mentions or [],
        visual_signature=visual_signature,
        brand_name=brand_name,
    )
    result["source"] = "direct_reverse_engineering_legacy"
    result["extraction_mode"] = "legacy_direct"
    result["canonical_evidence_source"] = None
    result["deprecation"] = dict(LEGACY_REVERSE_DEPRECATION)
    return result


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
