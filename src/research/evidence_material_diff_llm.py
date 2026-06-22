from __future__ import annotations

from typing import Any

from src.config import (
    BRAND3_EVIDENCE_LLM_MAX_ATTEMPTS,
    BRAND3_EVIDENCE_LLM_MODEL,
    BRAND3_EVIDENCE_LLM_TIMEOUT_SECONDS,
)
from src.features.llm_analyzer import LLMAnalyzer
from src.research.evidence_material_diff_llm_support import (
    _empty_payload,
    _material_diff_candidates,
    _normalize_response,
    _payload,
    _system_prompt,
    _transport,
    _user_prompt,
)
from src.research.evidence_semantic_llm import _call_structured_json


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
        "properties": {"items": {"type": "array", "items": item_schema}},
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
        return _empty_payload(
            candidates,
            status="disabled",
            reason="shadow_disabled",
            model=BRAND3_EVIDENCE_LLM_MODEL,
            version=MATERIAL_DIFF_SHADOW_VERSION,
        )
    if not candidates:
        return _empty_payload(
            candidates,
            status="ok",
            reason="",
            model=BRAND3_EVIDENCE_LLM_MODEL,
            version=MATERIAL_DIFF_SHADOW_VERSION,
        )

    analyzer = llm if llm is not None else LLMAnalyzer(model=BRAND3_EVIDENCE_LLM_MODEL)
    if analyzer is None or not getattr(analyzer, "api_key", None):
        return _empty_payload(
            candidates,
            status="unavailable",
            reason="llm_unavailable",
            model=BRAND3_EVIDENCE_LLM_MODEL,
            version=MATERIAL_DIFF_SHADOW_VERSION,
        )

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

    transport = _transport(analyzer)
    model = str(getattr(analyzer, "model", "") or BRAND3_EVIDENCE_LLM_MODEL)
    if normalized is None:
        from src.research.evidence_material_diff_llm_support import _latest_failure

        failure = _latest_failure(analyzer)
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
            version=MATERIAL_DIFF_SHADOW_VERSION,
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
        version=MATERIAL_DIFF_SHADOW_VERSION,
        attempt_count=attempt_count,
    )
