"""Analyst Pass for TLDR Brand3.

This module asks an LLM to read a Brand Research Pack and produce the 9 TLDR
Brand3 blocks. It does not contain brand-specific heuristics. The only source of
truth is the organized evidence pack passed in by Brand Audit.
"""

from __future__ import annotations

import json
from dataclasses import is_dataclass
from typing import Any

from src.reports.brand_research_pack import BrandResearchPack
from src.features.magnetism.tldr_guardrails import validate_analyst_tldr


ANALYST_TLDR_PROMPT_VERSION = "brand3-analyst-tldr-v0.2"

TLDR_KEYS = [
    "core_purpose",
    "magnetism",
    "value_proposition",
    "personality",
    "brand_idea",
    "attributes",
    "values",
    "mission",
    "vision",
]

ANALYST_BLOCK_QUESTIONS = {
    "core_purpose": "Why does the brand appear to exist beyond the product?",
    "magnetism": "What phrase, tension, or promise is most likely to be remembered?",
    "value_proposition": "What does the brand offer, to whom, and what changes for that audience?",
    "personality": "What personality does the brand perform through tone, vocabulary, behavior, and visual stance?",
    "brand_idea": "What conceptual idea connects category, offer, expression, and metaphor?",
    "attributes": "Which 1-3 attributes are consistently demonstrated by product, behavior, proof, or language?",
    "values": "Which values does the brand appear to defend through what it says or does?",
    "mission": "What does the brand concretely do today?",
    "vision": "What future or category change is the brand trying to build?",
}

ANALYST_TLDR_SYSTEM_PROMPT = """You are Brand3's Analyst Pass.

You read a Brand Research Pack and write the 9 TLDR Brand3 blocks from evidence.
You are not a marketing generator. You are not a brand strategist inventing from
memory. You are an evidence analyst.

Rules:
- Use only the Research Pack and the evidence it contains.
- Do not invent founder intent, audience, mission, vision, or values.
- Distinguish declared, performed, inferred, and absent carefully.
- Use traceable evidence only.
- If evidence is weak or missing, say so explicitly.
- Return strict JSON only.
- Every block must be separate and must answer its own question.
- Do not promote founder story, press context, proof points, or page chrome into
  stronger claims than the evidence supports.
- Prefer absent/not_detected over an elegant but unsupported interpretation.
- Evidence gaps and confidence notes are negative evidence, not background noise.
"""

ANALYST_TLDR_SOURCE_RULES = [
    "owned_official, owned_product, owned_about, and owned_security_trust can support declared claims when the text is literal.",
    "press_or_founder can support context or inference, but should not become a declared mission or personality on its own.",
    "proof_point can support credibility, values, or outcome language, but not values without behavior.",
    "competitive_context can support category contrast only; it must not support identity, offer, proof, superiority, traction, or TLDR claims about the audited brand.",
    "social can support how the brand speaks or is perceived, but should be traceable.",
    "noise must not be used as positive evidence.",
    "If a block lacks usable evidence, mark it absent/not_detected rather than inventing a stronger reading.",
]

ANALYST_TLDR_NEGATIVE_EXAMPLES = [
    {
        "bad_move": "Using 'Book a demo', 'Login', pricing labels, newsletter text, or footer copy as a mission/value/personality claim.",
        "correct_move": "Treat it as noise or page chrome unless the Research Pack explicitly promotes it as brand evidence.",
    },
    {
        "bad_move": "Marking mission as declared because press says the company raised money to automate a category.",
        "correct_move": "Use press as context only; mission requires owned present-tense action language or must be inferred/absent.",
    },
    {
        "bad_move": "Calling values declared because the product has proof points or customer outcomes.",
        "correct_move": "Use proof points for performed credibility; values need explicit value language or repeated behavior.",
    },
    {
        "bad_move": "Turning a single decorative metaphor into the whole brand idea.",
        "correct_move": "Require repeated conceptual evidence across offer, expression, product behavior, or language.",
    },
]


def maybe_build_analyst_tldr(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    research_pack: Any,
    current_tldr: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Run the Analyst Pass and return a normalized TLDR payload.

    On LLM failure the function returns the current TLDR, if present, together
    with a controlled analysis_error field so the caller can keep the existing
    reading.
    """
    if llm is None or not getattr(llm, "api_key", None):
        return None

    result = run_analyst_tldr_pass(
        llm=llm,
        brand_name=brand_name,
        url=url,
        research_pack=research_pack,
        current_tldr=current_tldr,
    )
    if result.get("analysis_error"):
        validated = result.get("validated")
        if isinstance(validated, dict):
            payload = dict(validated)
        else:
            payload = _fallback_payload(
                current_tldr=current_tldr,
                reason=str(result["analysis_error"].get("reason") or "llm_error"),
                detail=str(result["analysis_error"].get("detail") or "The analyst pass failed."),
            )
        payload["analysis_error"] = result["analysis_error"]
        if "raw" in result:
            payload["analysis_raw"] = result.get("raw") or {}
        return payload
    validated = result.get("validated")
    if not isinstance(validated, dict) or not validated.get("tldr_brand3"):
        return _fallback_payload(
            current_tldr=current_tldr,
            reason="empty_tldr",
            detail="The analyst pass returned no usable TLDR blocks.",
        )
    return validated


def run_analyst_tldr_pass(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    research_pack: Any,
    current_tldr: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call the analyst LLM once and return raw, normalized, and validated payloads."""
    if llm is None or not getattr(llm, "api_key", None):
        return {
            "analysis_error": {
                "reason": "llm_unavailable",
                "detail": "No LLM API key is available for the Analyst Pass.",
            },
            "validated": _fallback_payload(
                current_tldr=current_tldr,
                reason="llm_unavailable",
                detail="No LLM API key is available for the Analyst Pass.",
            ),
        }

    prompt = build_analyst_tldr_prompt(
        brand_name=brand_name,
        url=url,
        research_pack=research_pack,
        current_tldr=current_tldr,
    )
    raw_response = llm._call_json(
        ANALYST_TLDR_SYSTEM_PROMPT,
        prompt,
        max_tokens=9000,
        json_schema=analyst_tldr_response_schema(),
        schema_name="brand3_analyst_tldr",
    )
    raw = _coerce_analyst_raw_json(raw_response)
    if not isinstance(raw, dict) or not raw:
        return {
            "analysis_error": {
                "reason": "llm_error",
                "detail": "The analyst pass did not return usable JSON.",
            },
            "raw": raw_response if isinstance(raw_response, dict) else {},
            "validated": _fallback_payload(
                current_tldr=current_tldr,
                reason="llm_error",
                detail="The analyst pass did not return usable JSON.",
            ),
        }

    normalized = normalize_analyst_response(raw, current_tldr=current_tldr, research_pack=research_pack)
    validated = validate_analyst_tldr(normalized, research_pack)
    return {
        "raw": raw,
        "normalized": normalized,
        "validated": validated,
    }


def _coerce_analyst_raw_json(raw: Any) -> dict[str, Any]:
    """Accept provider JSON-object drift when the only item is the payload."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], dict):
        return raw[0]
    return {}


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
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "entity_reading",
            "verdict_vs_current",
            "main_gain",
            "main_risk",
            "tldr_brand3",
        ],
        "properties": {
            "entity_reading": {"type": "string"},
            "verdict_vs_current": {"type": "string", "enum": ["better", "similar", "worse", "unknown"]},
            "main_gain": {"type": "string"},
            "main_risk": {"type": "string"},
            "tldr_brand3": {
                "type": "object",
                "additionalProperties": False,
                "required": TLDR_KEYS,
                "properties": {key: block_schema for key in TLDR_KEYS},
            },
        },
    }


def normalize_analyst_response(
    raw: dict[str, Any],
    *,
    current_tldr: dict[str, Any] | None = None,
    research_pack: Any | None = None,
) -> dict[str, Any]:
    blocks = raw.get("tldr_brand3") if isinstance(raw.get("tldr_brand3"), dict) else {}
    normalized_blocks: dict[str, Any] = {}
    validation_notes: list[str] = []
    source_index = _source_index(research_pack)

    for key in TLDR_KEYS:
        raw_block = blocks.get(key) if isinstance(blocks.get(key), dict) else {}
        block, notes = _normalize_block(key, raw_block, source_index)
        normalized_blocks[key] = block
        validation_notes.extend(notes)

    normalized = {
        "prompt_version": ANALYST_TLDR_PROMPT_VERSION,
        "entity_reading": _clean_text(raw.get("entity_reading")),
        "verdict_vs_current": _clean_text(raw.get("verdict_vs_current")) or "unknown",
        "main_gain": _clean_text(raw.get("main_gain")),
        "main_risk": _clean_text(raw.get("main_risk")),
        "validation_notes": _unique_texts(validation_notes),
        "tldr_brand3": normalized_blocks,
    }
    if current_tldr:
        normalized["current_tldr"] = _compact_current_tldr(current_tldr)
    return normalized


def _normalize_block(
    key: str,
    raw: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    answer = _clean_text(raw.get("answer") or raw.get("content"))
    evidence_used = _clean_list(raw.get("evidence_used") or raw.get("evidence"))
    evidence_sources = _normalize_evidence_sources(raw.get("evidence_sources"), source_index)
    reasoning = _clean_text(raw.get("reasoning") or raw.get("rationale"))
    counter_evidence = _clean_list(raw.get("counter_evidence"))

    claim_type = _normalize_choice(raw.get("claim_type"), {"declared", "performed", "inferred", "absent"}, fallback="inferred" if answer else "absent")
    mode = _normalize_choice(
        raw.get("mode"),
        {"literal", "compressed", "interpreted_from_discourse", "needs_human_review", "not_detected"},
        fallback="interpreted_from_discourse" if answer else "not_detected",
    )
    confidence = _normalize_choice(raw.get("confidence"), {"high", "medium", "low"}, fallback="medium" if answer else "low")
    detected = bool(raw.get("detected")) or bool(answer)
    human_review = bool(raw.get("human_review_recommended"))

    if answer and not evidence_used:
        notes.append(f"{key}: answer present but evidence_used was missing or empty.")
        human_review = True
        if mode == "literal":
            mode = "needs_human_review"

    if not detected:
        claim_type = "absent"
        mode = "not_detected"
        confidence = "low"
        answer = ""

    question = _clean_text(raw.get("question")) or ANALYST_BLOCK_QUESTIONS[key]
    if not reasoning and answer:
        reasoning = "The analyst pass derived this block from the provided Research Pack evidence."

    if not counter_evidence and claim_type in {"inferred", "performed"} and answer:
        counter_evidence = [
            "The brand does not explicitly declare this exact Brand3 articulation in the available evidence."
        ]

    block = {
        "block": key,
        "question": question,
        "answer": answer or None,
        "content": answer or None,
        "claim_type": claim_type,
        "mode": mode,
        "confidence": confidence,
        "reasoning": reasoning,
        "rationale": reasoning,
        "evidence_used": evidence_used,
        "evidence_sources": evidence_sources,
        "evidence": evidence_used,
        "counter_evidence": counter_evidence,
        "human_review_recommended": human_review or mode == "needs_human_review" or (bool(answer) and not evidence_used),
        "detected": bool(answer) and mode != "not_detected",
        "validation_notes": notes,
    }
    return block, notes


def _fallback_payload(
    *,
    current_tldr: dict[str, Any] | None,
    reason: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "prompt_version": ANALYST_TLDR_PROMPT_VERSION,
        "analysis_error": {
            "reason": reason,
            "detail": detail,
        },
        "validation_notes": [detail],
        "tldr_brand3": _compact_current_tldr(current_tldr or {}),
    }


def _compact_current_tldr(current_tldr: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in TLDR_KEYS:
        block = current_tldr.get(key) if isinstance(current_tldr, dict) else None
        if not isinstance(block, dict):
            continue
        compact[key] = {
            "block": key,
            "question": _clean_text(block.get("question")) or ANALYST_BLOCK_QUESTIONS[key],
            "answer": block.get("answer") or block.get("content"),
            "claim_type": block.get("claim_type"),
            "mode": block.get("mode"),
            "confidence": block.get("confidence"),
            "reasoning": _clean_text(block.get("reasoning") or block.get("rationale")),
            "evidence_used": _clean_list(block.get("evidence_used") or block.get("evidence")),
        }
    return compact


def _normalize_evidence_sources(value: Any, source_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, dict):
            source_key = _clean_text(item.get("source_key") or item.get("source_url") or item.get("url") or item.get("label"))
            url = _clean_text(item.get("url") or item.get("source_url"))
            label = _clean_text(item.get("label") or item.get("source_label"))
            source_type = _clean_text(item.get("source_type"))
        else:
            source_key = _clean_text(item)
            url = ""
            label = ""
            source_type = ""
        if not source_key and not url and not label:
            continue
        lookup_key = source_key or url or label
        if lookup_key.lower() in seen:
            continue
        seen.add(lookup_key.lower())
        metadata = source_index.get(lookup_key.lower(), {})
        output.append(
            {
                "source_key": source_key or metadata.get("source_key") or metadata.get("url") or lookup_key,
                "source_type": source_type or metadata.get("source_type", ""),
                "url": url or metadata.get("url", ""),
                "label": label or metadata.get("label", ""),
            }
        )
    return output


def _source_index(research_pack: Any | None) -> dict[str, dict[str, Any]]:
    pack = _research_pack_dict(research_pack)
    source_map = pack.get("source_map") if isinstance(pack, dict) else {}
    if not isinstance(source_map, dict):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for key, value in source_map.items():
        if not isinstance(value, dict):
            continue
        canonical = {
            "source_key": str(key),
            "source_type": _clean_text(value.get("source_type")),
            "url": _clean_text(value.get("url")),
            "label": _clean_text(value.get("label")),
        }
        for candidate in {str(key), canonical["url"], canonical["label"]}:
            candidate = _clean_text(candidate)
            if candidate:
                index[candidate.lower()] = canonical
    return index


def _research_pack_dict(research_pack: Any) -> dict[str, Any]:
    if research_pack is None:
        return {}
    if isinstance(research_pack, dict):
        return research_pack
    if isinstance(research_pack, BrandResearchPack) or is_dataclass(research_pack):
        return research_pack.to_dict()
    if hasattr(research_pack, "to_dict") and callable(research_pack.to_dict):
        payload = research_pack.to_dict()
        return payload if isinstance(payload, dict) else {}
    return {}


def _compact_research_pack_for_prompt(pack: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(pack, dict):
        return {}
    source_map = pack.get("source_map") if isinstance(pack.get("source_map"), dict) else {}
    compact = {
        "version": pack.get("version"),
        "input_url": pack.get("input_url"),
        "resolved_entity": pack.get("resolved_entity"),
        "entity_type": pack.get("entity_type"),
        "parent_brand": pack.get("parent_brand"),
        "official_urls": _compact_list(pack.get("official_urls"), limit=12, text_limit=180),
        "analyzed_urls": _compact_list(pack.get("analyzed_urls"), limit=20, text_limit=180),
        "source_map": _compact_source_map(source_map),
        "company_summary": _truncate_text(pack.get("company_summary"), 450),
        "product_summary": _truncate_text(pack.get("product_summary"), 450),
        "audience": _truncate_text(pack.get("audience"), 350),
        "offer": _truncate_text(pack.get("offer"), 450),
        "outcome": _truncate_text(pack.get("outcome"), 350),
        "category": _truncate_text(pack.get("category"), 160),
        "declared_purpose": _truncate_text(pack.get("declared_purpose"), 450),
        "declared_mission": _truncate_text(pack.get("declared_mission"), 450),
        "future_direction": _truncate_text(pack.get("future_direction"), 450),
        "tone_of_voice": _truncate_text(pack.get("tone_of_voice"), 220),
        "personality_signals": _compact_list(pack.get("personality_signals"), limit=8, text_limit=220),
        "visual_or_conceptual_signals": _compact_list(pack.get("visual_or_conceptual_signals"), limit=8, text_limit=220),
        "values_signals": _compact_list(pack.get("values_signals"), limit=8, text_limit=220),
        "attributes_signals": _compact_list(pack.get("attributes_signals"), limit=8, text_limit=220),
        "proof_points": _compact_evidence_list(pack.get("proof_points"), limit=8),
        "founder_or_press_context": _compact_evidence_list(pack.get("founder_or_press_context"), limit=8),
        "competitive_context": _compact_evidence_list(pack.get("competitive_context"), limit=4),
        "noise_rejected": _compact_evidence_list(pack.get("noise_rejected"), limit=4, text_limit=180),
        "evidence_gaps": _compact_list(pack.get("evidence_gaps"), limit=8, text_limit=260),
        "confidence_notes": _compact_list(pack.get("confidence_notes"), limit=8, text_limit=260),
        "evidence_counts": {
            "source_count": len(source_map),
            "proof_points": _safe_len(pack.get("proof_points")),
            "founder_or_press_context": _safe_len(pack.get("founder_or_press_context")),
            "competitive_context": _safe_len(pack.get("competitive_context")),
            "noise_rejected": _safe_len(pack.get("noise_rejected")),
        },
    }
    return compact


def _compact_source_map(source_map: dict[str, Any], *, limit: int = 35) -> dict[str, Any]:
    def priority(item: tuple[str, Any]) -> tuple[int, str]:
        value = item[1] if isinstance(item[1], dict) else {}
        source_type = str(value.get("source_type") or "")
        rank = {
            "owned_official": 0,
            "owned_product": 1,
            "owned_about": 2,
            "owned_security_trust": 3,
            "proof_point": 4,
            "press_or_founder": 5,
            "social": 6,
            "noise": 8,
        }.get(source_type, 7)
        return rank, str(item[0])

    compact: dict[str, Any] = {}
    for key, value in sorted(source_map.items(), key=priority)[:limit]:
        if not isinstance(value, dict):
            continue
        compact[str(key)] = {
            "url": _truncate_text(value.get("url"), 220),
            "source_type": _truncate_text(value.get("source_type"), 80),
            "label": _truncate_text(value.get("label"), 140),
            "surface_role": _truncate_text(value.get("surface_role"), 80),
            "entity_scope": _truncate_text(value.get("entity_scope"), 80),
            "title": _truncate_text(value.get("title"), 160),
        }
    return compact


def _compact_evidence_list(value: Any, *, limit: int, text_limit: int = 320) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        text = _truncate_text(item.get("text"), text_limit)
        source_url = _truncate_text(item.get("source_url"), 220)
        key = (text.lower(), source_url.lower())
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(
            {
                "text": text,
                "kind": _truncate_text(item.get("kind"), 40),
                "source_url": source_url,
                "source_type": _truncate_text(item.get("source_type"), 80),
                "source_label": _truncate_text(item.get("source_label"), 100),
                "topic": _truncate_text(item.get("topic"), 100),
                "confidence": _truncate_text(item.get("confidence"), 40),
            }
        )
        if len(output) >= limit:
            break
    return output


def _compact_list(value: Any, *, limit: int, text_limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _truncate_text(item, text_limit)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def _truncate_text(value: Any, limit: int) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _safe_len(value: Any) -> int:
    return len(value) if isinstance(value, list | dict) else 0


def _normalize_choice(value: Any, allowed: set[str], fallback: str) -> str:
    normalized = _clean_text(value).lower()
    return normalized if normalized in allowed else fallback


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    output: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _unique_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output
