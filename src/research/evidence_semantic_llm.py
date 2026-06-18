from __future__ import annotations

import json
from typing import Any

from src.config import (
    BRAND3_EVIDENCE_LLM_BATCH_SIZE,
    BRAND3_EVIDENCE_LLM_CLASSIFIER_ENABLED,
    BRAND3_EVIDENCE_LLM_MAX_ATTEMPTS,
    BRAND3_EVIDENCE_LLM_MODEL,
    BRAND3_EVIDENCE_LLM_NATIVE_STRUCTURED_OUTPUT,
    BRAND3_EVIDENCE_LLM_TIMEOUT_SECONDS,
)
from src.features.llm_analyzer import LLMAnalyzer
from src.research.evidence_vnext import EvidenceVNextPacket


SEMANTIC_CLASSES = {
    "owned_brand_evidence",
    "customer_case",
    "market_news",
    "direct_brand_evidence",
    "competitor_comparison",
    "tangential",
    "wrong_entity",
}
ENTITY_FITS = {"strong", "partial", "missing", "wrong_entity"}
MATERIALITIES = {"high", "medium", "low", "not_applicable"}

LLM_SEMANTIC_CLASSIFIER_VERSION = "evidence_vnext_llm_semantic_assessment_v0_1"


def llm_semantic_response_schema() -> dict[str, Any]:
    item_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "id",
            "c",
            "e",
            "m",
            "conf",
            "r",
        ],
        "properties": {
            "id": {"type": "string"},
            "c": {"type": "string", "enum": sorted(SEMANTIC_CLASSES)},
            "e": {"type": "string", "enum": sorted(ENTITY_FITS)},
            "m": {"type": "string", "enum": sorted(MATERIALITIES)},
            "conf": {"type": "number"},
            "r": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
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


def build_llm_semantic_assessment(
    packet: EvidenceVNextPacket,
    *,
    llm: Any | None = None,
    enabled: bool | None = None,
) -> dict[str, Any]:
    """Run the optional LLM semantic classifier in shadow mode."""

    effective_enabled = BRAND3_EVIDENCE_LLM_CLASSIFIER_ENABLED if enabled is None else bool(enabled)
    if not effective_enabled:
        return _empty_payload(packet, status="disabled", reason="classifier_disabled")

    analyzer = llm if llm is not None else LLMAnalyzer(model=BRAND3_EVIDENCE_LLM_MODEL)
    if analyzer is None or not getattr(analyzer, "api_key", None):
        return _empty_payload(packet, status="unavailable", reason="llm_unavailable")

    accepted = list(packet.accepted)
    if not accepted:
        return _empty_payload(packet, status="ok", reason="")

    assessments: list[dict[str, Any]] = []
    attempt_count = 0
    transport = _structured_transport(analyzer)
    batch_size = max(1, int(BRAND3_EVIDENCE_LLM_BATCH_SIZE or 8))
    max_attempts = max(1, int(BRAND3_EVIDENCE_LLM_MAX_ATTEMPTS or 1))
    batches = _chunks(accepted, batch_size)
    batch_count = len(batches)
    for batch in batches:
        normalized: list[dict[str, Any]] | None = None
        for _attempt in range(max_attempts):
            attempt_count += 1
            raw = _call_structured_json(
                analyzer,
                system=_system_prompt(),
                user=_user_prompt(packet, batch),
                max_tokens=2500,
                json_schema=llm_semantic_response_schema(),
                schema_name="brand3_evidence_semantic_classifier",
                timeout_seconds=BRAND3_EVIDENCE_LLM_TIMEOUT_SECONDS,
            )
            normalized = _normalize_response(raw, expected_ids={item.observation_id for item in batch})
            if normalized is not None:
                break
        if normalized is None:
            failure = _latest_llm_failure(analyzer)
            reason = str(failure.get("reason") or "")
            if not reason or reason == "llm_error":
                reason = "schema_validation_error"
            return _empty_payload(
                packet,
                status="error",
                reason=reason,
                detail=str(failure.get("error") or "The LLM classifier did not return usable JSON."),
                model=str(getattr(analyzer, "model", "") or BRAND3_EVIDENCE_LLM_MODEL),
                transport=transport,
                attempt_count=attempt_count,
                batch_count=batch_count,
            )
        assessments.extend(normalized)

    return _payload(
        packet,
        status="ok",
        model=str(getattr(analyzer, "model", "") or BRAND3_EVIDENCE_LLM_MODEL),
        transport=transport,
        assessments=assessments,
        attempt_count=attempt_count,
        batch_count=batch_count,
    )


def _payload(
    packet: EvidenceVNextPacket,
    *,
    status: str,
    model: str,
    assessments: list[dict[str, Any]],
    transport: str = "",
    reason: str = "",
    detail: str = "",
    attempt_count: int = 0,
    batch_count: int = 0,
) -> dict[str, Any]:
    summary = _summary(packet, assessments)
    return {
        "version": LLM_SEMANTIC_CLASSIFIER_VERSION,
        "runtime_effect": False,
        "prompt_effect": False,
        "model_effect": status == "ok",
        "classifier": "llm_shadow_v0",
        "status": status,
        "model": model,
        "transport": transport,
        "reason": reason,
        "detail": detail,
        "attempt_count": attempt_count,
        "batch_count": batch_count,
        "retry_count": max(0, attempt_count - batch_count),
        "assessments": assessments,
        "summary": summary,
    }


def _empty_payload(
    packet: EvidenceVNextPacket,
    *,
    status: str,
    reason: str,
    detail: str = "",
    model: str = "",
    transport: str = "",
    attempt_count: int = 0,
    batch_count: int = 0,
) -> dict[str, Any]:
    return _payload(
        packet,
        status=status,
        model=model or BRAND3_EVIDENCE_LLM_MODEL,
        transport=transport,
        assessments=[],
        reason=reason,
        detail=detail,
        attempt_count=attempt_count,
        batch_count=batch_count,
    )


def _summary(packet: EvidenceVNextPacket, assessments: list[dict[str, Any]]) -> dict[str, Any]:
    class_counts: dict[str, int] = {}
    materiality_counts: dict[str, int] = {}
    entity_fit_counts: dict[str, int] = {}
    accepted_material = 0
    accepted_weak = 0
    for item in assessments:
        semantic_class = str(item.get("semantic_class") or "")
        materiality = str(item.get("materiality") or "")
        entity_fit = str(item.get("entity_fit") or "")
        class_counts[semantic_class] = class_counts.get(semantic_class, 0) + 1
        materiality_counts[materiality] = materiality_counts.get(materiality, 0) + 1
        entity_fit_counts[entity_fit] = entity_fit_counts.get(entity_fit, 0) + 1
        if materiality in {"high", "medium"} and semantic_class not in {"tangential", "wrong_entity"}:
            accepted_material += 1
        if materiality == "low" or semantic_class in {"tangential", "wrong_entity", "competitor_comparison"}:
            accepted_weak += 1
    accepted_count = len(packet.accepted)
    return {
        "assessment_count": len(assessments),
        "accepted_count": accepted_count,
        "accepted_material_count": accepted_material,
        "accepted_weak_count": accepted_weak,
        "accepted_material_rate": _safe_ratio(accepted_material, accepted_count),
        "accepted_weak_rate": _safe_ratio(accepted_weak, accepted_count),
        "semantic_class_counts": dict(sorted(class_counts.items())),
        "materiality_counts": dict(sorted(materiality_counts.items())),
        "entity_fit_counts": dict(sorted(entity_fit_counts.items())),
    }


def _normalize_response(raw: Any, *, expected_ids: set[str]) -> list[dict[str, Any]] | None:
    if not isinstance(raw, dict):
        return None
    rows = raw.get("items")
    if rows is None:
        rows = raw.get("assessments")
    if not isinstance(rows, list):
        return None
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            return None
        observation_id = str(row.get("id") or row.get("observation_id") or "")
        semantic_class = str(row.get("c") or row.get("semantic_class") or "")
        entity_fit = str(row.get("e") or row.get("entity_fit") or "")
        materiality = str(row.get("m") or row.get("materiality") or "")
        if observation_id not in expected_ids or observation_id in seen:
            return None
        if semantic_class not in SEMANTIC_CLASSES or entity_fit not in ENTITY_FITS or materiality not in MATERIALITIES:
            return None
        confidence = row.get("conf", row.get("confidence"))
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            return None
        reason_codes = row.get("r", row.get("reason_codes"))
        if not isinstance(reason_codes, list) or not all(isinstance(item, str) for item in reason_codes):
            return None
        seen.add(observation_id)
        normalized.append(
            {
                "observation_id": observation_id,
                "semantic_class": semantic_class,
                "entity_fit": entity_fit,
                "materiality": materiality,
                "confidence": max(0.0, min(1.0, float(confidence))),
                "reason_codes": [item.strip() for item in reason_codes if item.strip()][:5],
            }
        )
    if seen != expected_ids:
        return None
    return normalized


def _system_prompt() -> str:
    return (
        "You classify Brand3 evidence candidates. Return only compact JSON matching the schema. "
        "Do not decide whether evidence is admissible; Python has already admitted it. "
        "Classify semantic usefulness, entity fit, and materiality for brand strategy. "
        "Use short reason codes only."
    )


def _user_prompt(packet: EvidenceVNextPacket, observations: list[Any]) -> str:
    payload = {
        "brand_name": packet.brand_name,
        "brand_url": packet.url,
        "output_contract": {
            "items": [
                {
                    "id": "observation_id",
                    "c": "semantic_class",
                    "e": "entity_fit",
                    "m": "materiality",
                    "conf": "confidence_0_to_1",
                    "r": ["short_reason_code"],
                }
            ]
        },
        "classification_rules": {
            "owned_brand_evidence": "Owned or official brand source with direct product/company evidence.",
            "customer_case": "Customer story, implementation, case study, or customer proof involving the brand.",
            "market_news": "News, announcement, launch, funding, acquisition, partnership, or market event about the brand.",
            "direct_brand_evidence": "External page directly describing the brand, product, audience, offer, or market role.",
            "competitor_comparison": "Alternatives, competitors, ranked lists, or comparison pages where the brand is contextual.",
            "tangential": "Mentions the brand but is weak, indirect, generic, or not useful for strategic narrative.",
            "wrong_entity": "Appears to be a different entity or the brand fit is wrong.",
        },
        "evidence": [
            {
                "observation_id": item.observation_id,
                "url": item.url,
                "source_class": item.source_class,
                "provider": item.provider,
                "feature_name": item.feature_name,
                "text": _truncate(item.text, 1400),
            }
            for item in observations
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _call_structured_json(
    analyzer: Any,
    *,
    system: str,
    user: str,
    max_tokens: int,
    json_schema: dict[str, Any],
    schema_name: str,
    timeout_seconds: int,
) -> Any:
    if _structured_transport(analyzer) == "gemini_native":
        return analyzer._call_json_gemini_native(
            system,
            user,
            max_tokens=max_tokens,
            json_schema=json_schema,
            schema_name=schema_name,
            timeout_seconds=timeout_seconds,
        )
    return analyzer._call_json(
        system,
        user,
        max_tokens=max_tokens,
        json_schema=json_schema,
        schema_name=schema_name,
        strict_schema=True,
        timeout_seconds=timeout_seconds,
    )


def _structured_transport(analyzer: Any) -> str:
    if BRAND3_EVIDENCE_LLM_NATIVE_STRUCTURED_OUTPUT and _can_use_gemini_native_structured_output(analyzer):
        return "gemini_native"
    return "openai_compatible"


def _can_use_gemini_native_structured_output(analyzer: Any) -> bool:
    if not hasattr(analyzer, "_call_json_gemini_native"):
        return False
    base_url = str(getattr(analyzer, "base_url", "") or "").lower()
    return "generativelanguage.googleapis.com" in base_url


def _latest_llm_failure(llm: Any) -> dict[str, Any]:
    failures = getattr(llm, "call_failures", None)
    if isinstance(failures, list) and failures:
        latest = failures[-1]
        if isinstance(latest, dict):
            return latest
    reason = getattr(llm, "last_failure_reason", None)
    return {"reason": reason or "llm_error", "error": ""}


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _truncate(text: str, limit: int) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)
