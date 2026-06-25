"""Analyst pass orchestration for the executive Brand Audit.

This module owns the public workflow surface for the Brand Audit Analyst pass:
prompt/schema building, LLM invocation, normalization and fallback payloads.
"""

from __future__ import annotations

import json
from typing import Any

from src.reports.brand_audit_analyst_support import (
    _clean_list,
    _clean_text,
    _coerce_raw_json,
    _compact_features,
    _compact_research_pack,
    _normalize_choice,
    _research_pack_dict,
    _score_fallback_diagnosis,
    _unique_texts,
)


BRAND_AUDIT_ANALYST_PROMPT_VERSION = "brand-audit-executive-v0.1"

AUDIT_DIMENSIONS = [
    "coherencia",
    "diferenciacion",
    "presencia",
    "percepcion",
    "vitalidad",
]

DIMENSION_QUESTIONS = {
    "coherencia": "Does the brand say one clear thing across owned evidence?",
    "diferenciacion": "Is the brand meaningfully distinct from category alternatives?",
    "presencia": "Is the brand visible and traceable across relevant public surfaces?",
    "percepcion": "How does the brand appear to be perceived or signaled externally?",
    "vitalidad": "Does the brand show recent activity, momentum, or living proof?",
}

SYSTEM_PROMPT = """You are Brand3's Brand Audit Analyst Pass.

You read a Brand Research Pack, dimension scores, and extracted feature signals.
Your task is to write an executive audit by dimension.

Rules:
- Use only the Research Pack, dimension scores, and feature signals provided.
- Do not invent market position, traction, reputation, audience, or intent.
- Separate diagnosis, findings, evidence, and recommendation.
- If evidence is weak or missing, say so explicitly.
- Recommendations must be based on observed gaps, not generic consulting advice.
- Return strict JSON only.
"""


def run_brand_audit_analyst_pass(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    research_pack: Any,
    dimensions: dict[str, Any],
    features_by_dim: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Call the analyst LLM once and return a normalized executive audit."""
    if llm is None or not getattr(llm, "api_key", None):
        return _fallback_payload(
            reason="llm_unavailable",
            detail="No LLM API key is available for the Brand Audit Analyst Pass.",
            dimensions=dimensions,
        )
    if not callable(getattr(llm, "_call_json", None)):
        return _fallback_payload(
            reason="llm_json_unavailable",
            detail="The configured LLM object cannot run structured JSON analyst calls.",
            dimensions=dimensions,
        )

    prompt = build_brand_audit_analyst_prompt(
        brand_name=brand_name,
        url=url,
        research_pack=research_pack,
        dimensions=dimensions,
        features_by_dim=features_by_dim,
    )
    try:
        raw_response = llm._call_json(
            SYSTEM_PROMPT,
            prompt,
            max_tokens=9000,
            json_schema=brand_audit_analyst_response_schema(),
            schema_name="brand_audit_executive_v2",
        )
    except Exception as exc:
        return _fallback_payload(
            reason="llm_error",
            detail=f"The Brand Audit Analyst Pass failed: {exc}",
            dimensions=dimensions,
        )
    raw = _coerce_raw_json(raw_response)
    if not raw:
        return _fallback_payload(
            reason="llm_error",
            detail="The Brand Audit Analyst Pass did not return usable JSON.",
            dimensions=dimensions,
            raw=raw_response if isinstance(raw_response, dict) else {},
        )
    return normalize_brand_audit_analyst_response(raw, dimensions=dimensions)


def build_brand_audit_analyst_prompt(
    *,
    brand_name: str,
    url: str,
    research_pack: Any,
    dimensions: dict[str, Any],
    features_by_dim: dict[str, dict[str, Any]],
) -> str:
    payload = {
        "prompt_version": BRAND_AUDIT_ANALYST_PROMPT_VERSION,
        "brand": {"name": brand_name, "url": url},
        "task": "Write an executive Brand Audit by dimension from the supplied evidence only.",
        "research_pack": _compact_research_pack(_research_pack_dict(research_pack)),
        "dimension_scores": {key: dimensions.get(key) for key in AUDIT_DIMENSIONS},
        "feature_signals": _compact_features(features_by_dim),
        "dimension_questions": DIMENSION_QUESTIONS,
        "required_output": {
            "executive_summary": "2-4 sentence evidence-bound summary",
            "primary_risk": "main risk in the current brand evidence",
            "primary_opportunity": "main opportunity visible in the evidence",
            "dimensions": {
                key: {
                    "dimension": key,
                    "question": DIMENSION_QUESTIONS[key],
                    "diagnosis": "short diagnostic judgment",
                    "findings": ["specific findings"],
                    "evidence": ["traceable evidence strings or score-backed observations"],
                    "recommendation": "specific next action",
                    "confidence": "high | medium | low",
                    "limitations": ["specific evidence gaps"],
                }
                for key in AUDIT_DIMENSIONS
            },
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def brand_audit_analyst_response_schema() -> dict[str, Any]:
    dimension_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "dimension",
            "question",
            "diagnosis",
            "findings",
            "evidence",
            "recommendation",
            "confidence",
            "limitations",
        ],
        "properties": {
            "dimension": {"type": "string", "enum": AUDIT_DIMENSIONS},
            "question": {"type": "string"},
            "diagnosis": {"type": "string"},
            "findings": {"type": "array", "items": {"type": "string"}},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "recommendation": {"type": "string"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "limitations": {"type": "array", "items": {"type": "string"}},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "executive_summary",
            "primary_risk",
            "primary_opportunity",
            "dimensions",
        ],
        "properties": {
            "executive_summary": {"type": "string"},
            "primary_risk": {"type": "string"},
            "primary_opportunity": {"type": "string"},
            "dimensions": {
                "type": "object",
                "additionalProperties": False,
                "required": AUDIT_DIMENSIONS,
                "properties": {key: dimension_schema for key in AUDIT_DIMENSIONS},
            },
        },
    }


def normalize_brand_audit_analyst_response(
    raw: dict[str, Any],
    *,
    dimensions: dict[str, Any],
) -> dict[str, Any]:
    raw_dimensions = raw.get("dimensions") if isinstance(raw.get("dimensions"), dict) else {}
    normalized_dimensions: dict[str, dict[str, Any]] = {}
    validation_notes: list[str] = []
    for key in AUDIT_DIMENSIONS:
        block, notes = _normalize_dimension(key, raw_dimensions.get(key), dimensions.get(key))
        normalized_dimensions[key] = block
        validation_notes.extend(notes)
    return {
        "prompt_version": BRAND_AUDIT_ANALYST_PROMPT_VERSION,
        "executive_summary": _clean_text(raw.get("executive_summary")),
        "primary_risk": _clean_text(raw.get("primary_risk")),
        "primary_opportunity": _clean_text(raw.get("primary_opportunity")),
        "dimensions": normalized_dimensions,
        "validation_notes": _unique_texts(validation_notes),
    }


def _normalize_dimension(
    key: str,
    raw: Any,
    score: Any,
) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    raw_block = raw if isinstance(raw, dict) else {}
    evidence = _clean_list(raw_block.get("evidence"))
    findings = _clean_list(raw_block.get("findings"))
    diagnosis = _clean_text(raw_block.get("diagnosis"))
    recommendation = _clean_text(raw_block.get("recommendation"))
    limitations = _clean_list(raw_block.get("limitations"))
    confidence = _normalize_choice(raw_block.get("confidence"), {"high", "medium", "low"}, fallback="medium")

    if not raw_block:
        notes.append(f"{key}: missing analyst dimension block.")
        confidence = "low"
        limitations.append("The analyst response did not include this dimension.")
    if diagnosis and not evidence:
        notes.append(f"{key}: diagnosis present without evidence.")
        confidence = "low"
        limitations.append("No traceable evidence was attached to this dimension diagnosis.")

    return {
        "dimension": key,
        "question": _clean_text(raw_block.get("question")) or DIMENSION_QUESTIONS[key],
        "score": score,
        "diagnosis": diagnosis or _score_fallback_diagnosis(key, score),
        "findings": findings,
        "evidence": evidence,
        "recommendation": recommendation,
        "confidence": confidence,
        "limitations": _unique_texts(limitations),
    }, notes


def _fallback_payload(
    *,
    reason: str,
    detail: str,
    dimensions: dict[str, Any],
    raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "prompt_version": BRAND_AUDIT_ANALYST_PROMPT_VERSION,
        "analysis_error": {"reason": reason, "detail": detail},
        "executive_summary": "",
        "primary_risk": "",
        "primary_opportunity": "",
        "dimensions": {
            key: {
                "dimension": key,
                "question": DIMENSION_QUESTIONS[key],
                "score": dimensions.get(key),
                "diagnosis": _score_fallback_diagnosis(key, dimensions.get(key)),
                "findings": [],
                "evidence": [],
                "recommendation": "",
                "confidence": "low",
                "limitations": [detail],
            }
            for key in AUDIT_DIMENSIONS
        },
        "validation_notes": [detail],
    }
    if raw is not None:
        payload["raw"] = raw
    return payload
