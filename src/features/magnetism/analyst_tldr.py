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


ANALYST_TLDR_PROMPT_VERSION = "brand3-analyst-tldr-v0.1"

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
"""

ANALYST_TLDR_SOURCE_RULES = [
    "owned_official, owned_product, owned_about, and owned_security_trust can support declared claims when the text is literal.",
    "press_or_founder can support context or inference, but should not become a declared mission or personality on its own.",
    "proof_point can support credibility, values, or outcome language, but not values without behavior.",
    "social can support how the brand speaks or is perceived, but should be traceable.",
    "noise must not be used as positive evidence.",
    "If a block lacks usable evidence, mark it absent/not_detected rather than inventing a stronger reading.",
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
    raw = llm._call_json(ANALYST_TLDR_SYSTEM_PROMPT, prompt, max_tokens=9000)
    if not isinstance(raw, dict) or not raw:
        return {
            "analysis_error": {
                "reason": "llm_error",
                "detail": "The analyst pass did not return usable JSON.",
            },
            "raw": raw if isinstance(raw, dict) else {},
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
        "research_pack": _research_pack_dict(research_pack),
        "current_tldr": _compact_current_tldr(current_tldr or {}),
        "block_questions": ANALYST_BLOCK_QUESTIONS,
        "block_exercises": ANALYST_BLOCK_QUESTIONS,
        "source_rules": ANALYST_TLDR_SOURCE_RULES,
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
