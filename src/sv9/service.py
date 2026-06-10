"""SV9 application service.

Shadow-phase entrypoints (design doc section 16, step 0): SV9 runs over
persisted Brand Audit snapshots via replay. It never collects, never touches
V5 scoring, and never renders anywhere public.

Acquisition stays owned by Brand Audit; detection (Pass 1) stays owned by the
existing TLDR extraction. SV9 inserts the ladder engine between detection and
the editorial layer.
"""

from __future__ import annotations

from typing import Any

from src.config import BRAND3_DB_PATH, LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.features.magnetism.extractor import MagnetismExtractor
from src.services.magnetism_service import load_brand_audit_snapshot
from src.sv9.aggregator import aggregate
from src.sv9.evaluator import evaluate_snapshot_components
from src.sv9.models import Sv9ScanResult
from src.sv9.signals import collect_signals


def run_sv9_from_audit_run(
    run_id: int,
    *,
    llm: LLMAnalyzer | None = None,
    db_path: str = BRAND3_DB_PATH,
) -> Sv9ScanResult:
    """Run SV9 from an existing Brand Audit run snapshot, without re-collecting."""
    snapshot = load_brand_audit_snapshot(run_id, db_path=db_path)
    return run_sv9_from_audit_snapshot(snapshot, llm=llm)


def run_sv9_from_audit_snapshot(
    snapshot: dict[str, Any],
    *,
    llm: LLMAnalyzer | None = None,
    magnetism_result: dict[str, Any] | None = None,
) -> Sv9ScanResult:
    """Run SV9 over a loaded Brand Audit snapshot.

    Pass `magnetism_result` to reuse an already-computed Pass 1 extraction
    (e.g. a persisted Magnetism scan payload) and skip re-detection.
    """
    llm = _effective_llm(llm)
    if magnetism_result is None:
        magnetism_result = MagnetismExtractor(llm=llm).extract_from_audit_snapshot(snapshot)

    tldr = magnetism_result.get("tldr_brand3") or {}
    brand_name = str(
        magnetism_result.get("brand_name")
        or snapshot.get("brand_name")
        or snapshot.get("url")
        or ""
    )
    url = str(magnetism_result.get("source_url") or snapshot.get("url") or "")
    source_run_id = _to_int(magnetism_result.get("source_run_id") or snapshot.get("id"))

    signals = collect_signals(snapshot)
    components = evaluate_snapshot_components(
        tldr=tldr,
        signals=signals,
        brand_name=brand_name,
        url=url,
        llm=llm,
    )
    return aggregate(
        components,
        brand_name=brand_name,
        url=url,
        source_run_id=source_run_id,
    )


def _effective_llm(llm: LLMAnalyzer | None) -> LLMAnalyzer | None:
    if llm is not None:
        return llm
    candidate = LLMAnalyzer(model=LLM_PREMIUM_MODEL)
    if getattr(candidate, "api_key", None):
        return candidate
    return None


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
