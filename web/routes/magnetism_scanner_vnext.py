"""Evidence vNext helpers for Magnetism Scanner routes."""

from __future__ import annotations

import logging

from src.config import BRAND3_DB_PATH, BRAND3_EVIDENCE_LLM_MODEL
from src.research.evidence_vnext import (
    build_evidence_vnext_packet_from_snapshot,
    build_evidence_vnext_semantic_assessment,
    compare_legacy_current_and_vnext_from_snapshot,
)
from src.research.evidence_vnext_report import build_batch_report
from src.features.llm_analyzer import LLMAnalyzer
from src.storage.sqlite_store import SQLiteStore

_LOG = logging.getLogger(__name__)


def _load_evidence_vnext_diagnostic(run_id: int) -> dict | None:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(run_id)
    finally:
        store.close()
    if snapshot is None:
        return None
    comparison = compare_legacy_current_and_vnext_from_snapshot(snapshot)
    report = build_batch_report([comparison], db_path=BRAND3_DB_PATH)
    return {
        "diagnostic": "evidence_vnext",
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "run_id": run_id,
        "report": report,
    }


def _evidence_vnext_research_summary(source_run_id: object) -> dict | None:
    """Compact vNext diagnostics for the human-facing research tab."""
    if source_run_id is None:
        return None
    try:
        run_id = int(source_run_id)
    except (TypeError, ValueError):
        return None
    try:
        diagnostic = _load_evidence_vnext_diagnostic(run_id)
    except Exception:
        _LOG.exception("Failed to build evidence vNext research summary for run_id=%s", run_id)
        return None
    if not diagnostic:
        return None

    report = diagnostic.get("report") or {}
    totals = report.get("totals") or {}
    row = _first_dict(report.get("rows"))
    readiness = _first_dict((report.get("readiness_matrix") or {}).get("rows"))
    exa = _first_dict(((report.get("acquisition_diagnostics") or {}).get("exa") or {}).get("rows"))
    semantic_llm = _first_dict((report.get("semantic_llm") or {}).get("rows"))
    return {
        "run_id": run_id,
        "json_href": f"/magnetism-scanner/run/{run_id}/evidence-vnext",
        "view_href": f"/magnetism-scanner/run/{run_id}/evidence-vnext/view",
        "status": row.get("status") or "",
        "promotion_status": row.get("promotion_status") or "",
        "readiness_status": readiness.get("readiness_status") or "",
        "projected_promotion_status": readiness.get("projected_promotion_status") or "",
        "next_action": readiness.get("next_action") or "",
        "human_required": readiness.get("human_required"),
        "accepted": totals.get("accepted") or 0,
        "review_required": totals.get("review_required") or 0,
        "rejected": totals.get("rejected") or 0,
        "reclassified_to_noise": totals.get("reclassified_to_noise") or 0,
        "changed_fields": totals.get("changed_fields") or 0,
        "lost_fields": totals.get("lost_fields") or 0,
        "material_lost_fields": totals.get("material_lost_fields") or 0,
        "exa_strategy": exa.get("strategy") or "",
        "exa_status": exa.get("status") or "",
        "exa_competitor_intent_enabled": bool(exa.get("competitor_intent_enabled")),
        "exa_planned_intents": exa.get("planned_intents") or [],
        "review_reasons": _top_reason_names(report.get("top_review_reasons")),
        "rejected_reasons": _top_reason_names(report.get("top_rejected_reasons")),
        "semantic_llm_status": semantic_llm.get("status") or "",
        "semantic_llm_model": semantic_llm.get("model") or "",
    }


def _first_dict(value: object) -> dict:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def _top_reason_names(value: object, *, limit: int = 3) -> list[str]:
    if not isinstance(value, dict):
        return []
    return [str(key) for key, _count in sorted(value.items(), key=lambda item: item[1], reverse=True)[:limit]]


def _load_evidence_vnext_llm_shadow(run_id: int, *, no_cache: bool = False) -> dict | None:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(run_id)
    finally:
        store.close()
    if snapshot is None:
        return None

    packet = build_evidence_vnext_packet_from_snapshot(snapshot)
    heuristic = build_evidence_vnext_semantic_assessment(packet)
    llm = None
    if no_cache:
        llm = LLMAnalyzer(model=BRAND3_EVIDENCE_LLM_MODEL)
        llm.use_cache = False
    from web.routes import magnetism_scanner as _public_scanner

    llm_assessment = _public_scanner.build_llm_semantic_assessment(
        packet,
        llm=llm,
        enabled=True,
    )
    return {
        "diagnostic": "evidence_vnext_llm_shadow",
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "run_id": run_id,
        "brand_name": packet.brand_name,
        "url": packet.url,
        "no_cache": no_cache,
        "summary": _evidence_llm_shadow_summary(heuristic, llm_assessment),
        "disagreements": _evidence_llm_shadow_disagreements(heuristic, llm_assessment, packet=packet),
        "heuristic": {
            "classifier": heuristic.get("classifier") or "",
            "summary": heuristic.get("summary") or {},
        },
        "llm": llm_assessment,
    }


def _evidence_llm_shadow_summary(heuristic: dict, llm: dict) -> dict:
    disagreements = _evidence_llm_shadow_disagreements(heuristic, llm)
    return {
        "llm_status": llm.get("status") or "",
        "llm_model": llm.get("model") or "",
        "llm_transport": llm.get("transport") or "",
        "llm_reason": llm.get("reason") or "",
        "llm_attempt_count": llm.get("attempt_count") or 0,
        "llm_batch_count": llm.get("batch_count") or 0,
        "llm_retry_count": llm.get("retry_count") or 0,
        "heuristic_accepted_material": (heuristic.get("summary") or {}).get("accepted_material_count") or 0,
        "heuristic_accepted_weak": (heuristic.get("summary") or {}).get("accepted_weak_count") or 0,
        "llm_accepted_material": (llm.get("summary") or {}).get("accepted_material_count") or 0,
        "llm_accepted_weak": (llm.get("summary") or {}).get("accepted_weak_count") or 0,
        "semantic_class_disagreement_count": sum(1 for item in disagreements if item.get("class_changed")),
        "materiality_disagreement_count": sum(1 for item in disagreements if item.get("materiality_changed")),
    }


def _evidence_llm_shadow_disagreements(heuristic: dict, llm: dict, *, packet=None) -> list[dict]:
    heuristic_by_id = {
        str(item.get("observation_id") or ""): item
        for item in heuristic.get("assessments") or []
        if isinstance(item, dict)
    }
    observations_by_id = {}
    if packet is not None:
        observations_by_id = {item.observation_id: item for item in packet.observations}
    out: list[dict] = []
    for item in llm.get("assessments") or []:
        if not isinstance(item, dict):
            continue
        observation_id = str(item.get("observation_id") or "")
        baseline = heuristic_by_id.get(observation_id)
        if not baseline:
            continue
        class_changed = item.get("semantic_class") != baseline.get("semantic_class")
        materiality_changed = item.get("materiality") != baseline.get("materiality")
        if not class_changed and not materiality_changed:
            continue
        observation = observations_by_id.get(observation_id)
        context = {}
        if observation is not None:
            context = {
                "url": observation.url,
                "provider": observation.provider,
                "feature_name": observation.feature_name,
                "source_class": observation.source_class,
                "eligibility": observation.eligibility,
                "gate_status": observation.gate_status,
                "classification_reason": observation.classification_reason,
                "text_preview": observation.text[:240],
            }
        out.append(
            {
                "observation_id": observation_id,
                "class_changed": class_changed,
                "materiality_changed": materiality_changed,
                "heuristic_class": baseline.get("semantic_class") or "",
                "llm_class": item.get("semantic_class") or "",
                "heuristic_materiality": baseline.get("materiality") or "",
                "llm_materiality": item.get("materiality") or "",
                "heuristic_entity_fit": baseline.get("entity_fit") or "",
                "llm_entity_fit": item.get("entity_fit") or "",
                "heuristic_reason_codes": list(baseline.get("reason_codes") or []),
                "llm_reason_codes": list(item.get("reason_codes") or []),
                "context": context,
            }
        )
    return out[:25]
