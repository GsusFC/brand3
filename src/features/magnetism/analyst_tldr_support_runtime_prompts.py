"""Prompt and schema helpers for Analyst TLDR support."""

from __future__ import annotations

import json
import os
from typing import Any

from src.features.magnetism.analyst_tldr_support_runtime_processing import (
    _bounded_int,
    _clean_list,
    _clean_text,
    _compact_current_tldr,
    _compact_evidence_basis,
    _compact_research_pack_for_prompt,
    _normalize_choice,
    _research_pack_dict,
)
from src.features.magnetism.analyst_tldr_support_runtime_constants import (
    ANALYST_BLOCK_QUESTIONS,
    ANALYST_TLDR_NEGATIVE_EXAMPLES,
    ANALYST_TLDR_PROMPT_VERSION,
    ANALYST_TLDR_SOURCE_RULES,
    ANALYST_TLDR_TIMEOUT_SECONDS,
    SYSTEM_READING_PROMPT_VERSION,
    SYSTEM_READING_TIMEOUT_SECONDS,
    TLDR_KEYS,
)


def _coerce_analyst_raw_json(raw: Any) -> dict[str, Any]:
    """Accept common provider JSON-object drift around the TLDR payload."""
    value = raw
    for _ in range(4):
        if isinstance(value, str):
            try:
                value = json.loads(value.strip())
            except json.JSONDecodeError:
                return {}
            continue
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
            continue
        if isinstance(value, dict):
            if isinstance(value.get("tldr_brand3"), dict):
                return value
            for key in ("payload", "content", "output", "response", "result", "data", "message"):
                nested = value.get(key)
                if isinstance(nested, (dict, list, str)):
                    value = nested
                    break
            else:
                return value
            continue
        return {}
    return {}


def _system_reading_system_prompt() -> str:
    return """You are Brand3's Strategic Interpretation specialist.

Only reason from the provided evidence and numeric context. Do not invent details.
Do not use strategy recommendations, competitor speculation, or generic marketing advice.
Return strict JSON only.
"""


def system_reading_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "prompt_version",
            "derived_from",
            "strategic_tensions",
            "validation_questions",
            "credibility_support",
        ],
        "properties": {
            "prompt_version": {"type": "string"},
            "derived_from": {"type": "string"},
            "strategic_tensions": {
                "type": "array",
                "maxItems": 5,
                "items": {"type": "string"},
            },
            "validation_questions": {
                "type": "array",
                "maxItems": 5,
                "items": {"type": "string"},
            },
            "credibility_support": {
                "type": "object",
                "additionalProperties": False,
                "required": ["status", "count", "evidence", "reading"],
                "properties": {
                    "status": {"type": "string", "enum": ["observed", "not_detected", "partial"]},
                    "count": {"type": "integer", "minimum": 0},
                    "evidence": {"type": "array", "items": {"type": "object"}, "maxItems": 5},
                    "reading": {"type": "string"},
                },
            },
        },
    }


def _analyst_tldr_timeout_seconds() -> int:
    raw = os.environ.get("BRAND3_ANALYST_TLDR_TIMEOUT_SECONDS")
    if not raw:
        return ANALYST_TLDR_TIMEOUT_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return ANALYST_TLDR_TIMEOUT_SECONDS
    return max(1, value)


def _system_reading_timeout_seconds() -> int:
    raw = os.environ.get("BRAND3_SYSTEM_READING_TIMEOUT_SECONDS")
    if not raw:
        return SYSTEM_READING_TIMEOUT_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return SYSTEM_READING_TIMEOUT_SECONDS
    return max(1, value)


def _coerce_system_reading_raw_json(raw: Any) -> dict[str, Any]:
    value = raw
    for _ in range(4):
        if isinstance(value, str):
            try:
                value = json.loads(value.strip())
            except json.JSONDecodeError:
                return {}
            continue
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
            continue
        if isinstance(value, dict):
            if isinstance(value.get("strategic_tensions"), list):
                return value
            for key in ("payload", "content", "output", "response", "result", "message", "data"):
                nested = value.get(key)
                if isinstance(nested, (dict, list, str)):
                    value = nested
                    break
            else:
                return value
            continue
        break
    return {} if not isinstance(value, dict) else value


def build_system_reading_prompt(
    *,
    brand_name: str,
    url: str,
    tldr: dict[str, Any],
    layers: dict[str, Any],
    metrics: dict[str, Any],
    evidence_packet_summary: dict[str, Any] | None = None,
) -> str:
    proof_support = {
        "status": "not_detected",
        "count": 0,
        "reading": "No proof support context was supplied.",
    }
    if isinstance(evidence_packet_summary, dict):
        raw_support = evidence_packet_summary.get("proof_support")
        if isinstance(raw_support, dict):
            proof_support = raw_support

    payload = {
        "prompt_version": SYSTEM_READING_PROMPT_VERSION,
        "task": "Generate a compact strategic reading for end-user explanation.",
        "brand": {
            "name": brand_name,
            "url": url,
        },
        "scoring": {
            "magnetism_score": int(metrics.get("magnetism_score") or 0),
            "coherence_score": int(metrics.get("coherence_score") or 0),
            "quadrant": metrics.get("quadrant"),
            "magnetism_breakdown": metrics.get("magnetism_breakdown"),
            "coherence_breakdown": metrics.get("coherence_breakdown"),
        },
        "detected_signals": {
            "tl_dr": {
                key: bool(
                    block.get("detected") or block.get("answer") or block.get("content")
                )
                for key, block in (tldr or {}).items()
                if isinstance(block, dict) and key in TLDR_KEYS
            },
            "weak_layers": [
                key for key, layer in (layers or {}).items()
                if isinstance(layer, dict) and not layer.get("detected")
            ],
            "evidence_basis": _compact_evidence_basis(evidence_packet_summary),
        },
        "proof_context": {
            "status": proof_support.get("status"),
            "count": proof_support.get("count"),
            "reading": proof_support.get("reading"),
        },
        "required_output": {
            "strategic_tensions": ["up to 3 short, observable tensions"],
            "validation_questions": ["up to 3 short, actionable questions"],
            "credibility_support": {
                "status": "observed | partial | not_detected",
                "count": "integer",
                "evidence": [
                    {
                        "url": "optional",
                        "title": "optional",
                        "label": "optional",
                        "source_type": "optional",
                    }
                ],
                "reading": "short conclusion paragraph",
            },
            "derived_from": "short sentence on source basis",
            "prompt_version": SYSTEM_READING_PROMPT_VERSION,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def normalize_system_reading(raw: dict[str, Any]) -> dict[str, Any]:
    tensions = _clean_list(raw.get("strategic_tensions"))
    questions = _clean_list(raw.get("validation_questions"))
    proof_support = raw.get("credibility_support")
    if not isinstance(proof_support, dict):
        proof_support = {}
    status = _normalize_choice(
        proof_support.get("status"),
        {"observed", "partial", "not_detected"},
        fallback="not_detected",
    )
    evidence = proof_support.get("evidence") if isinstance(proof_support.get("evidence"), list) else []
    return {
        "prompt_version": SYSTEM_READING_PROMPT_VERSION,
        "derived_from": _clean_text(raw.get("derived_from")) or "TLDR Brand3 blocks and Magenta signal coverage",
        "strategic_tensions": tensions[:3],
        "validation_questions": questions[:3],
        "credibility_support": {
            "status": status,
            "count": _bounded_int(proof_support.get("count"), maximum=100),
            "evidence": evidence[:5] if isinstance(evidence, list) else [],
            "reading": _clean_text(proof_support.get("reading")) or "No usable proof support was available.",
        },
        "interpretation_mode": "llm_system_reading",
    }


def build_analyst_tldr_prompt(
    *,
    brand_name: str,
    url: str,
    research_pack: Any,
    current_tldr: dict[str, Any] | None = None,
) -> str:
    payload = {
        "prompt_version": ANALYST_TLDR_PROMPT_VERSION,
        "brand": {
            "name": brand_name,
            "url": url,
        },
        "task": "Write the 9 TLDR Brand3 blocks from the Research Pack only.",
        "research_pack": _compact_research_pack_for_prompt(_research_pack_dict(research_pack)),
        "current_tldr": _compact_current_tldr(current_tldr or {}),
        "block_questions": ANALYST_BLOCK_QUESTIONS,
        "block_exercises": ANALYST_BLOCK_QUESTIONS,
        "source_rules": ANALYST_TLDR_SOURCE_RULES,
        "negative_examples": ANALYST_TLDR_NEGATIVE_EXAMPLES,
        "required_output": {
            "entity_reading": "short explanation of the entity reading",
            "verdict_vs_current": "better | similar | worse | unknown",
            "main_gain": "what improved versus the current TLDR",
            "main_risk": "main methodological risk or ambiguity",
            "scoring_context": {
                "expressive_magnetism_score": "0-100 score for clarity, memorability, tension and emotional pull",
                "earned_magnetism_score": "0-100 score after checking whether the promise is credible in its category",
                "promise_requires_evidence": "boolean",
                "evidence_duty_status": "not_required | satisfied | partial | weak",
                "coherence_evidence_duty_penalty": "0-25 suggested coherence penalty when required proof is partial or weak",
                "reasoning": "short explanation of the evidence-duty judgement",
                "evidence_gaps": ["missing proof, authority, methodology, validation, integration or trust signal"],
            },
            "tldr_brand3": {
                key: {
                    "block": key,
                    "question": ANALYST_BLOCK_QUESTIONS[key],
                    "answer": "string or null",
                    "claim_type": "declared | performed | inferred | absent",
                    "mode": "literal | compressed | interpreted_from_discourse | needs_human_review | not_detected",
                    "confidence": "high | medium | low",
                    "reasoning": "block-specific reasoning",
                    "evidence_used": ["traceable evidence strings"],
                    "evidence_sources": [
                        {
                            "source_key": "source_map key, URL, or stable identifier",
                            "source_type": "owned_official | owned_product | owned_about | owned_security_trust | press_or_founder | proof_point | social | noise | unknown",
                            "url": "optional url",
                            "label": "optional label",
                        }
                    ],
                    "counter_evidence": ["specific limitations"],
                    "human_review_recommended": "boolean",
                }
                for key in TLDR_KEYS
            },
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def analyst_tldr_response_schema() -> dict[str, Any]:
    """Provider-facing JSON Schema for the Analyst Pass response.

    Validation and semantic downgrades still happen in Python guardrails. The
    provider schema only reduces syntactic drift and missing top-level keys.
    """
    block_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "block",
            "question",
            "answer",
            "claim_type",
            "mode",
            "confidence",
            "reasoning",
            "evidence_used",
            "evidence_sources",
            "counter_evidence",
            "human_review_recommended",
        ],
        "properties": {
            "block": {"type": "string", "enum": TLDR_KEYS},
            "question": {"type": "string"},
            "answer": {"type": ["string", "null"]},
            "claim_type": {"type": "string", "enum": ["declared", "performed", "inferred", "absent"]},
            "mode": {
                "type": "string",
                "enum": [
                    "literal",
                    "compressed",
                    "interpreted_from_discourse",
                    "needs_human_review",
                    "not_detected",
                ],
            },
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "reasoning": {"type": "string"},
            "evidence_used": {"type": "array", "items": {"type": "string"}},
            "evidence_sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["source_key", "source_type", "url", "label"],
                    "properties": {
                        "source_key": {"type": "string"},
                        "source_type": {
                            "type": "string",
                            "enum": [
                                "owned_official",
                                "owned_product",
                                "owned_about",
                                "owned_security_trust",
                                "press_or_founder",
                                "proof_point",
                                "social",
                                "noise",
                                "unknown",
                            ],
                        },
                        "url": {"type": "string"},
                        "label": {"type": "string"},
                    },
                },
            },
            "counter_evidence": {"type": "array", "items": {"type": "string"}},
            "human_review_recommended": {"type": "boolean"},
        },
    }
    scoring_context_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "expressive_magnetism_score",
            "earned_magnetism_score",
            "promise_requires_evidence",
            "evidence_duty_status",
            "coherence_evidence_duty_penalty",
            "reasoning",
            "evidence_gaps",
        ],
        "properties": {
            "expressive_magnetism_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "earned_magnetism_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "promise_requires_evidence": {"type": "boolean"},
            "evidence_duty_status": {
                "type": "string",
                "enum": ["not_required", "satisfied", "partial", "weak"],
            },
            "coherence_evidence_duty_penalty": {"type": "integer", "minimum": 0, "maximum": 25},
            "reasoning": {"type": "string"},
            "evidence_gaps": {"type": "array", "items": {"type": "string"}},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "entity_reading",
            "verdict_vs_current",
            "main_gain",
            "main_risk",
            "scoring_context",
            "tldr_brand3",
        ],
        "properties": {
            "entity_reading": {"type": "string"},
            "verdict_vs_current": {"type": "string", "enum": ["better", "similar", "worse", "unknown"]},
            "main_gain": {"type": "string"},
            "main_risk": {"type": "string"},
            "scoring_context": scoring_context_schema,
            "tldr_brand3": {
                "type": "object",
                "additionalProperties": False,
                "required": TLDR_KEYS,
                "properties": {key: block_schema for key in TLDR_KEYS},
            },
        },
    }


__all__ = [
    "_coerce_analyst_raw_json",
    "_coerce_system_reading_raw_json",
    "_system_reading_system_prompt",
    "_analyst_tldr_timeout_seconds",
    "_system_reading_timeout_seconds",
    "system_reading_response_schema",
    "build_system_reading_prompt",
    "normalize_system_reading",
    "build_analyst_tldr_prompt",
    "analyst_tldr_response_schema",
]

