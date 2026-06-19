from __future__ import annotations

import json
from typing import Any

from src.config import (
    BRAND3_EVIDENCE_LLM_MODEL,
    BRAND3_EVIDENCE_LLM_MAX_ATTEMPTS,
    BRAND3_EVIDENCE_LLM_TIMEOUT_SECONDS,
)
from src.features.llm_analyzer import LLMAnalyzer
from src.research.evidence_semantic_llm import (
    _call_structured_json,
    _latest_llm_failure,
    _structured_transport,
    _truncate,
)


MATERIAL_DIFF_SHADOW_VERSION = "evidence_material_diff_llm_shadow_v0_1"
TARGET_NEXT_ACTION = "manual_audit_projected_material_changes"
VERDICTS = {"approve_vnext_material", "send_back_for_evidence_correction", "keep_manual_review"}
RISK_LEVELS = {"low", "medium", "high"}
ENTITY_FITS = {"strong", "partial", "missing", "wrong_entity"}
SOURCE_TRUSTS = {"strong", "acceptable", "weak", "untrusted", "missing"}


def material_diff_response_schema() -> dict[str, Any]:
    item_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "id",
            "v",
            "risk",
            "entity",
            "trust",
            "conf",
            "approved",
            "blocked",
            "r",
        ],
        "properties": {
            "id": {"type": "string"},
            "v": {"type": "string", "enum": sorted(VERDICTS)},
            "risk": {"type": "string", "enum": sorted(RISK_LEVELS)},
            "entity": {"type": "string", "enum": sorted(ENTITY_FITS)},
            "trust": {"type": "string", "enum": sorted(SOURCE_TRUSTS)},
            "conf": {"type": "number"},
            "approved": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            "blocked": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            "r": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": item_schema,
            }
        },
    }


def build_material_diff_llm_shadow(
    report: dict[str, Any],
    *,
    llm: Any | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    """Review material-diff work orders with an optional structured LLM.

    This is shadow-only: it does not alter the vNext report, readiness,
    adjudication records, or promotion state.
    """

    candidates = _material_diff_candidates(report)
    if not enabled:
        return _empty_payload(candidates, status="disabled", reason="shadow_disabled")
    if not candidates:
        return _empty_payload(candidates, status="ok", reason="")

    analyzer = llm if llm is not None else LLMAnalyzer(model=BRAND3_EVIDENCE_LLM_MODEL)
    if analyzer is None or not getattr(analyzer, "api_key", None):
        return _empty_payload(candidates, status="unavailable", reason="llm_unavailable")

    max_attempts = max(1, int(BRAND3_EVIDENCE_LLM_MAX_ATTEMPTS or 1))
    attempt_count = 0
    normalized: list[dict[str, Any]] | None = None
    expected_ids = {str(item["work_order_id"]) for item in candidates}
    for _attempt in range(max_attempts):
        attempt_count += 1
        raw = _call_structured_json(
            analyzer,
            system=_system_prompt(),
            user=_user_prompt(candidates),
            max_tokens=2200,
            json_schema=material_diff_response_schema(),
            schema_name="brand3_material_diff_shadow",
            timeout_seconds=BRAND3_EVIDENCE_LLM_TIMEOUT_SECONDS,
        )
        normalized = _normalize_response(raw, expected_ids=expected_ids)
        if normalized is not None:
            break

    transport = _structured_transport(analyzer)
    model = str(getattr(analyzer, "model", "") or BRAND3_EVIDENCE_LLM_MODEL)
    if normalized is None:
        failure = _latest_llm_failure(analyzer)
        reason = str(failure.get("reason") or "") or "schema_validation_error"
        if reason == "llm_error":
            reason = "schema_validation_error"
        return _payload(
            candidates,
            status="error",
            reason=reason,
            model=model,
            transport=transport,
            assessments=[],
            detail=str(failure.get("error") or "The LLM material diff shadow did not return usable JSON."),
            attempt_count=attempt_count,
        )

    return _payload(
        candidates,
        status="ok",
        reason="",
        model=model,
        transport=transport,
        assessments=normalized,
        attempt_count=attempt_count,
    )


def _payload(
    candidates: list[dict[str, Any]],
    *,
    status: str,
    reason: str,
    model: str,
    transport: str,
    assessments: list[dict[str, Any]],
    detail: str = "",
    attempt_count: int = 0,
) -> dict[str, Any]:
    repair_plan = _repair_plan(candidates, assessments)
    decision_packets = _decision_packets(repair_plan)
    return {
        "version": MATERIAL_DIFF_SHADOW_VERSION,
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "model_effect": status == "ok" and bool(assessments),
        "status": status,
        "reason": reason,
        "detail": detail,
        "model": model,
        "transport": transport,
        "candidate_count": len(candidates),
        "assessment_count": len(assessments),
        "attempt_count": attempt_count,
        "retry_count": max(0, attempt_count - 1) if candidates else 0,
        "candidates": candidates,
        "assessments": assessments,
        "repair_plan": repair_plan,
        "decision_packets": decision_packets,
        "summary": _summary(candidates, assessments, repair_plan, decision_packets),
    }


def _empty_payload(candidates: list[dict[str, Any]], *, status: str, reason: str) -> dict[str, Any]:
    return _payload(
        candidates,
        status=status,
        reason=reason,
        model=BRAND3_EVIDENCE_LLM_MODEL,
        transport="",
        assessments=[],
    )


def _summary(
    candidates: list[dict[str, Any]],
    assessments: list[dict[str, Any]],
    repair_plan: list[dict[str, Any]],
    decision_packets: list[dict[str, Any]],
) -> dict[str, Any]:
    verdict_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {}
    trust_counts: dict[str, int] = {}
    repair_action_counts: dict[str, int] = {}
    packet_action_counts: dict[str, int] = {}
    for item in assessments:
        for key, counts in (
            ("verdict", verdict_counts),
            ("material_risk", risk_counts),
            ("source_trust", trust_counts),
        ):
            value = str(item.get(key) or "")
            if value:
                counts[value] = counts.get(value, 0) + 1
    for item in repair_plan:
        action = str(item.get("action") or "")
        if action:
            repair_action_counts[action] = repair_action_counts.get(action, 0) + 1
    for item in decision_packets:
        action = str(item.get("recommended_decision") or "")
        if action:
            packet_action_counts[action] = packet_action_counts.get(action, 0) + 1
    auto_clear_candidates = [
        item["work_order_id"]
        for item in assessments
        if item.get("verdict") == "approve_vnext_material"
        and item.get("material_risk") == "low"
        and item.get("source_trust") in {"strong", "acceptable"}
        and item.get("entity_fit") == "strong"
        and float(item.get("confidence") or 0.0) >= 0.75
    ]
    return {
        "candidate_count": len(candidates),
        "assessment_count": len(assessments),
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "material_risk_counts": dict(sorted(risk_counts.items())),
        "source_trust_counts": dict(sorted(trust_counts.items())),
        "auto_clear_candidate_count": len(auto_clear_candidates),
        "auto_clear_candidate_ids": auto_clear_candidates,
        "repair_action_counts": dict(sorted(repair_action_counts.items())),
        "decision_packet_count": len(decision_packets),
        "decision_packet_action_counts": dict(sorted(packet_action_counts.items())),
    }


def _repair_plan(candidates: list[dict[str, Any]], assessments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(item.get("work_order_id") or ""): item for item in assessments}
    out: list[dict[str, Any]] = []
    for candidate in candidates:
        work_order_id = str(candidate.get("work_order_id") or "")
        assessment = by_id.get(work_order_id)
        if not assessment:
            continue
        out.append(_repair_action(candidate, assessment))
    return out


def _repair_action(candidate: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
    verdict = str(assessment.get("verdict") or "")
    source_trust = str(assessment.get("source_trust") or "")
    entity_fit = str(assessment.get("entity_fit") or "")
    material_risk = str(assessment.get("material_risk") or "")
    reason_codes = set(str(item) for item in assessment.get("reason_codes") or [])
    if entity_fit in {"wrong_entity", "partial", "missing"}:
        action = "recheck_entity_boundary"
        lane = "entity_repair"
        priority = "high"
        rationale = "The model found insufficient entity fit; repair must resolve entity ownership before material use."
    elif source_trust == "missing" or "missing_source_url" in reason_codes:
        action = "backfill_source_url_or_remove_material"
        lane = "provenance_repair"
        priority = "high"
        rationale = "The material diff depends on evidence without source provenance; find the source URL or remove the material claim."
    elif source_trust in {"weak", "untrusted"}:
        action = "quarantine_weak_source_from_material"
        lane = "source_trust_repair"
        priority = "high"
        rationale = "The source is too weak for material proof; keep it out of material fields unless a stronger source replaces it."
    elif verdict == "approve_vnext_material" and material_risk == "low":
        action = "manual_fast_approve_candidate"
        lane = "human_fast_path"
        priority = "medium"
        rationale = "The model found low-risk material changes with acceptable source trust; route to a fast human approve path."
    elif source_trust == "acceptable":
        action = "prepare_trust_review_packet"
        lane = "human_review_packet"
        priority = "medium"
        rationale = "The source may be usable, but the model still recommends manual judgment before promotion."
    else:
        action = "keep_manual_material_review"
        lane = "manual_review"
        priority = "medium"
        rationale = "The model did not find a safe automatic repair or fast approve path."

    return {
        "work_order_id": candidate.get("work_order_id") or "",
        "run_id": candidate.get("run_id"),
        "brand_name": candidate.get("brand_name") or "",
        "action": action,
        "lane": lane,
        "priority": priority,
        "rationale": rationale,
        "source_trust": source_trust,
        "entity_fit": entity_fit,
        "material_risk": material_risk,
        "verdict": verdict,
        "affected_material_fields": list(candidate.get("affected_material_fields") or []),
        "blocked_material_fields": list(assessment.get("blocked_material_fields") or []),
        "source_urls": _candidate_source_urls(candidate),
        "search_hints": _candidate_search_hints(candidate),
    }


def _decision_packets(repair_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_decision_packet(item) for item in repair_plan]


def _decision_packet(repair: dict[str, Any]) -> dict[str, Any]:
    action = str(repair.get("action") or "")
    work_order_id = str(repair.get("work_order_id") or "")
    run_id = repair.get("run_id")
    source_urls = list(repair.get("source_urls") or [])
    affected_fields = list(repair.get("affected_material_fields") or [])
    search_hints = list(repair.get("search_hints") or [])
    base_record = {
        "work_order_id": work_order_id,
        "run_id": run_id,
        "reviewer": "",
        "rationale": str(repair.get("rationale") or ""),
        "affected_material_fields": ", ".join(affected_fields),
    }
    if action == "backfill_source_url_or_remove_material":
        return {
            "packet_id": f"repair:{action}:{run_id}",
            "work_order_id": work_order_id,
            "run_id": run_id,
            "brand_name": repair.get("brand_name") or "",
            "action": action,
            "recommended_decision": "source_url_attached_or_exclude_unsourced_quote",
            "allowed_decisions": ["source_url_attached", "replace_with_sourced_equivalent", "exclude_unsourced_quote"],
            "required_fields": ["decision", "reviewer", "rationale", "quote_text", "source_url"],
            "instructions": [
                "Search the provided exact quote hints.",
                "Attach a source only if the source contains the same claim with clear attribution.",
                "If only a near-equivalent source is found, replace the quote with a sourced equivalent.",
                "If no source is found, exclude the unsourced material quote.",
            ],
            "record": {
                **base_record,
                "decision": "",
                "quote_text": search_hints[0] if search_hints else "",
                "source_url": "",
                "replacement_quote": "",
                "search_hints": search_hints,
            },
            "requires_recompute": True,
        }
    if action == "quarantine_weak_source_from_material":
        return {
            "packet_id": f"repair:{action}:{run_id}",
            "work_order_id": work_order_id,
            "run_id": run_id,
            "brand_name": repair.get("brand_name") or "",
            "action": action,
            "recommended_decision": "quarantine_source_from_material",
            "allowed_decisions": ["quarantine_source_from_material", "replace_with_stronger_source"],
            "required_fields": ["decision", "reviewer", "rationale", "quarantined_source_urls"],
            "instructions": [
                "Remove weak or adversarial source URLs from material proof fields.",
                "Keep the source only as risk/context evidence if useful.",
                "Replace with a stronger source before recomputing if the claim remains important.",
            ],
            "record": {
                **base_record,
                "decision": "quarantine_source_from_material",
                "quarantined_source_urls": ", ".join(source_urls),
                "replacement_source_url": "",
            },
            "requires_recompute": True,
        }
    if action == "prepare_trust_review_packet":
        return {
            "packet_id": f"repair:{action}:{run_id}",
            "work_order_id": work_order_id,
            "run_id": run_id,
            "brand_name": repair.get("brand_name") or "",
            "action": action,
            "recommended_decision": "manual_trust_review",
            "allowed_decisions": ["approve_vnext_material", "send_back_for_evidence_correction"],
            "required_fields": ["decision", "reviewer", "rationale", "reviewed_source_urls"],
            "instructions": [
                "Review the source URLs and decide whether they are trustworthy enough for material proof.",
                "Approve only if the material fields are directly supported by the cited sources.",
                "Send back if source quality or claim fit remains ambiguous.",
            ],
            "record": {
                **base_record,
                "decision": "",
                "reviewed_source_urls": ", ".join(source_urls),
            },
            "requires_recompute": False,
        }
    return {
        "packet_id": f"repair:{action or 'manual_review'}:{run_id}",
        "work_order_id": work_order_id,
        "run_id": run_id,
        "brand_name": repair.get("brand_name") or "",
        "action": action or "manual_review",
        "recommended_decision": "manual_review",
        "allowed_decisions": ["manual_review_completed"],
        "required_fields": ["decision", "reviewer", "rationale"],
        "instructions": ["Review the repair action manually."],
        "record": {**base_record, "decision": ""},
        "requires_recompute": False,
    }


def _candidate_source_urls(candidate: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for bucket in ("remaining_review_examples", "projected_material_overlaps"):
        for item in candidate.get(bucket) or []:
            if isinstance(item, dict) and item.get("url"):
                urls.append(str(item["url"]))
    return sorted(set(urls))


def _candidate_search_hints(candidate: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    brand = str(candidate.get("brand_name") or "").strip()
    for bucket in ("remaining_review_examples", "projected_material_overlaps"):
        for item in candidate.get(bucket) or []:
            if not isinstance(item, dict):
                continue
            text = _truncate(str(item.get("text_preview") or ""), 140)
            if text:
                hints.append(f'"{text}" {brand}'.strip())
    return hints[:4]


def _material_diff_candidates(report: dict[str, Any]) -> list[dict[str, Any]]:
    work_orders = report.get("work_orders") if isinstance(report.get("work_orders"), list) else []
    out: list[dict[str, Any]] = []
    for item in work_orders:
        if not isinstance(item, dict) or str(item.get("next_action") or "") != TARGET_NEXT_ACTION:
            continue
        context = item.get("context") if isinstance(item.get("context"), dict) else {}
        remaining = context.get("remaining_review_examples") if isinstance(context.get("remaining_review_examples"), list) else []
        overlaps = context.get("projected_material_overlaps") if isinstance(context.get("projected_material_overlaps"), list) else []
        changed = context.get("changed_material_fields") if isinstance(context.get("changed_material_fields"), list) else []
        out.append(
            {
                "work_order_id": str(item.get("work_order_id") or ""),
                "run_id": item.get("run_id"),
                "brand_name": str(item.get("brand_name") or ""),
                "task": str(item.get("task") or ""),
                "next_action": str(item.get("next_action") or ""),
                "affected_material_fields": list(context.get("affected_material_fields") or []),
                "changed_material_field_names": list(context.get("changed_material_field_names") or []),
                "remaining_review_examples": [_example_payload(example) for example in remaining[:6] if isinstance(example, dict)],
                "projected_material_overlaps": [_example_payload(example) for example in overlaps[:6] if isinstance(example, dict)],
                "changed_material_fields": [_changed_field_payload(field) for field in changed[:6] if isinstance(field, dict)],
            }
        )
    return [item for item in out if item["work_order_id"]]


def _example_payload(example: dict[str, Any]) -> dict[str, Any]:
    return {
        "feature_name": str(example.get("feature_name") or ""),
        "provider": str(example.get("provider") or ""),
        "source_class": str(example.get("source_class") or ""),
        "classification_reason": str(example.get("classification_reason") or ""),
        "url": str(example.get("url") or ""),
        "text_preview": _truncate(str(example.get("text_preview") or example.get("text") or ""), 500),
    }


def _changed_field_payload(field: dict[str, Any]) -> dict[str, Any]:
    return {
        "field": str(field.get("field") or ""),
        "current_preview": _truncate(str(field.get("current_preview") or ""), 700),
        "vnext_preview": _truncate(str(field.get("vnext_preview") or ""), 700),
    }


def _normalize_response(raw: Any, *, expected_ids: set[str]) -> list[dict[str, Any]] | None:
    if not isinstance(raw, dict):
        return None
    rows = raw.get("items")
    if not isinstance(rows, list):
        return None
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            return None
        work_order_id = str(row.get("id") or row.get("work_order_id") or "")
        verdict = str(row.get("v") or row.get("verdict") or "")
        material_risk = str(row.get("risk") or row.get("material_risk") or "")
        entity_fit = str(row.get("entity") or row.get("entity_fit") or "")
        source_trust = str(row.get("trust") or row.get("source_trust") or "")
        confidence = row.get("conf", row.get("confidence"))
        approved = row.get("approved", row.get("approved_material_fields"))
        blocked = row.get("blocked", row.get("blocked_material_fields"))
        reason_codes = row.get("r", row.get("reason_codes"))
        if work_order_id not in expected_ids or work_order_id in seen:
            return None
        if verdict not in VERDICTS or material_risk not in RISK_LEVELS:
            return None
        if entity_fit not in ENTITY_FITS or source_trust not in SOURCE_TRUSTS:
            return None
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            return None
        if not isinstance(approved, list) or not all(isinstance(item, str) for item in approved):
            return None
        if not isinstance(blocked, list) or not all(isinstance(item, str) for item in blocked):
            return None
        if not isinstance(reason_codes, list) or not all(isinstance(item, str) for item in reason_codes):
            return None
        seen.add(work_order_id)
        normalized.append(
            {
                "work_order_id": work_order_id,
                "verdict": verdict,
                "material_risk": material_risk,
                "entity_fit": entity_fit,
                "source_trust": source_trust,
                "confidence": max(0.0, min(1.0, float(confidence))),
                "approved_material_fields": [item.strip() for item in approved if item.strip()][:6],
                "blocked_material_fields": [item.strip() for item in blocked if item.strip()][:6],
                "reason_codes": [item.strip() for item in reason_codes if item.strip()][:4],
            }
        )
    if seen != expected_ids:
        return None
    return normalized


def _system_prompt() -> str:
    return (
        "You review Brand3 vNext material field changes in shadow mode. "
        "Return only compact JSON matching the schema. Do not promote, persist, or adjudicate. "
        "Approve only when the vNext material fields are supported by strong entity fit and source trust. "
        "If source provenance is missing or source trust is weak, keep manual review or send back."
    )


def _user_prompt(candidates: list[dict[str, Any]]) -> str:
    payload = {
        "output_contract": {
            "items": [
                {
                    "id": "work_order_id",
                    "v": "approve_vnext_material | send_back_for_evidence_correction | keep_manual_review",
                    "risk": "low | medium | high",
                    "entity": "strong | partial | missing | wrong_entity",
                    "trust": "strong | acceptable | weak | untrusted | missing",
                    "conf": "confidence_0_to_1",
                    "approved": ["approved material field names"],
                    "blocked": ["blocked material field names"],
                    "r": ["short_reason_code"],
                }
            ]
        },
        "rules": {
            "approve_vnext_material": "Use only when changed material fields are clearly better supported, entity fit is strong, source trust is strong or acceptable, and risk is low.",
            "send_back_for_evidence_correction": "Use when the field needs source repair, wrong entity cleanup, or material evidence replacement.",
            "keep_manual_review": "Use when the evidence may be valid but requires human judgment because source trust, materiality, or entity fit is uncertain.",
        },
        "candidates": candidates,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
