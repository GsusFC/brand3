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

from src.config import BRAND3_DB_PATH, LLM_MODEL, LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.features.magnetism.extractor import MagnetismExtractor
from src.services.magnetism_service import load_brand_audit_snapshot
from src.sv9.aggregator import aggregate
from src.sv9.editorial import build_editorial
from src.sv9.evaluator import evaluate_snapshot_components
from src.sv9.models import Sv9ScanResult
from src.sv9.signals import (
    audit_visual_method,
    collect_signals,
    compute_vision_observations,
    merge_signals,
    vision_signals,
)
from src.sv9.store import Sv9Store


def run_sv9_from_audit_run(
    run_id: int,
    *,
    llm: LLMAnalyzer | None = None,
    db_path: str = BRAND3_DB_PATH,
) -> Sv9ScanResult:
    """Run SV9 from an existing Brand Audit run snapshot, without re-collecting."""
    snapshot = load_brand_audit_snapshot(run_id, db_path=db_path)
    return run_sv9_from_audit_snapshot(snapshot, llm=llm)


def materialize_sv9_scan(
    run_id: int,
    *,
    db_path: str = BRAND3_DB_PATH,
    llm: LLMAnalyzer | None = None,
    editorial: bool = True,
) -> tuple[int, Sv9ScanResult]:
    """Full shadow pipeline for one audit run — the single source of truth for
    the replay script, the web materialization button, and retries.

    Includes everything a bare run_sv9_from_audit_run lacks: pinned Pass 1
    detection (re-evaluations stay comparable), the vision pass over the
    persisted screenshot when audit-time visual analysis fell back to local
    pixels (Idea de marca and Coherencia starve without it), and the editorial
    voice. Returns (scan_id, result).
    """
    snapshot = load_brand_audit_snapshot(run_id, db_path=db_path)
    store = Sv9Store(db_path)
    try:
        detection = store.get_detection(run_id)
        if detection is None:
            detection = detect_for_snapshot(snapshot, llm=llm)
            store.save_detection(run_id, detection)

        extra_signals = None
        vision_payload = store.get_visual_evidence(run_id)
        if vision_payload is None and audit_visual_method(snapshot) != "vision":
            vision_payload = compute_vision_observations(snapshot)
            if vision_payload is not None:
                store.save_visual_evidence(run_id, vision_payload)
        if vision_payload is not None:
            extra_signals = vision_signals(vision_payload)

        result = run_sv9_from_audit_snapshot(
            snapshot, llm=llm, magnetism_result=detection, extra_signals=extra_signals
        )
        scan_id = store.save_scan(result)

        if editorial:
            editorial_llm = llm if llm is not None else LLMAnalyzer(model=LLM_MODEL)
            if getattr(editorial_llm, "api_key", None):
                payload = build_editorial(result.to_dict(), llm=editorial_llm)
                if payload["component_messages"] or payload["executive_reading"]:
                    store.save_editorial(
                        scan_id,
                        component_messages=payload["component_messages"],
                        executive_reading=payload["executive_reading"],
                    )
        return scan_id, result
    finally:
        store.close()


def run_sv9_from_audit_snapshot(
    snapshot: dict[str, Any],
    *,
    llm: LLMAnalyzer | None = None,
    magnetism_result: dict[str, Any] | None = None,
    extra_signals: dict[str, Any] | None = None,
) -> Sv9ScanResult:
    """Run SV9 over a loaded Brand Audit snapshot.

    Pass `magnetism_result` to reuse an already-computed Pass 1 extraction
    (e.g. a persisted Magnetism scan payload) and skip re-detection.
    `extra_signals` ({component: [signal, ...]}) merge on top of the snapshot
    signals — e.g. the SV9-time vision pass over the persisted screenshot.
    """
    llm = _effective_llm(llm)
    if magnetism_result is None:
        magnetism_result = MagnetismExtractor(llm=llm).extract_from_audit_snapshot(snapshot)

    # get_run_snapshot nests run metadata under "run"; manual snapshots may
    # carry it at the top level. Accept both shapes.
    run_meta = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    tldr = magnetism_result.get("tldr_brand3") or {}
    brand_name = str(
        magnetism_result.get("brand_name")
        or run_meta.get("brand_name")
        or snapshot.get("brand_name")
        or ""
    )
    url = str(
        magnetism_result.get("source_url")
        or magnetism_result.get("url")
        or run_meta.get("url")
        or snapshot.get("url")
        or ""
    )
    source_run_id = _to_int(
        magnetism_result.get("source_run_id")
        or run_meta.get("id")
        or snapshot.get("id")
    )

    signals = merge_signals(collect_signals(snapshot), extra_signals)
    components = evaluate_snapshot_components(
        tldr=tldr,
        signals=signals,
        brand_name=brand_name,
        url=url,
        llm=llm,
    )
    result = aggregate(
        components,
        brand_name=brand_name,
        url=url,
        source_run_id=source_run_id,
    )
    result.evaluator_model = getattr(llm, "model", None)
    return result


def detect_for_snapshot(
    snapshot: dict[str, Any],
    *,
    llm: LLMAnalyzer | None = None,
) -> dict[str, Any]:
    """Run Pass 1 (TLDR detection) over a snapshot and return its payload.

    Detection is not deterministic across runs; callers that re-evaluate the
    same run should persist this payload (Sv9Store.save_detection) and reuse it
    so the evaluator is the only moving part.
    """
    return MagnetismExtractor(llm=_effective_llm(llm)).extract_from_audit_snapshot(snapshot)


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
