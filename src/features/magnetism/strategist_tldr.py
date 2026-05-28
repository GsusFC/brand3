"""Optional LLM strategist pass for TLDR Brand3.

The code-level block interpreters remain the default source of truth. This module
lets a constrained LLM write a better TLDR from the same canonical evidence, then
normalizes and downgrades over-claims before the result reaches the UI.
"""

from __future__ import annotations

import json
from typing import Any

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

TLDR_SOURCE_SIGNALS = {
    "core_purpose": "Essence → Core Purpose",
    "magnetism": "Emotions → Magnetism",
    "value_proposition": "Exchange → Value Proposition",
    "personality": "Voice → Personality",
    "brand_idea": "Expression → Brand Idea",
    "attributes": "Context / Beliefs → Attributes",
    "values": "Context / Beliefs → Values",
    "mission": "Action / Direction → Mission",
    "vision": "Action / Direction → Vision",
}

TLDR_SOURCE_LAYERS = {
    "core_purpose": "aetherspace",
    "magnetism": "mindspace",
    "value_proposition": "netspace",
    "personality": "gamespace",
    "brand_idea": "envispace",
    "attributes": "ambientspace",
    "values": "ambientspace",
    "mission": "tactispace",
    "vision": "tactispace",
}

ALLOWED_CLAIM_TYPES = {"declared", "performed", "inferred", "absent"}
ALLOWED_MODES = {
    "literal",
    "compressed",
    "interpreted_from_discourse",
    "needs_human_review",
    "not_detected",
}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}

STRATEGIST_TLDR_SYSTEM_PROMPT = """You are Brand3's strategic TLDR interpreter.

You write a TLDR from canonical public evidence, not from imagination. Your job is
to produce a useful strategic reading while preserving epistemic honesty.

Rules:
- Use only the provided evidence packet, brand context brief, Magenta signals, and current TLDR.
- Do not invent founder intent, market perception, values, mission, vision, or audience.
- If a block is not supported, return it as absent with mode=not_detected and confidence=low.
- Prefer clear human strategic language over generic consulting phrasing.
- Each block must answer a different exercise.
- evidence_used must quote or closely paraphrase available evidence.
- declared means the brand directly states it; inferred means Brand3 is articulating it.
- high confidence requires strong, block-specific evidence.
- If you synthesize across multiple signals, do not mark the block declared.

Return strict JSON only."""

BLOCK_EXERCISES = {
    "core_purpose": "Why does the brand appear to exist beyond the product? Use explicit purpose/about/manifesto signals. If missing, infer cautiously or mark absent.",
    "magnetism": "What phrase, tension, or promise is most likely to be remembered? Prefer hero/tagline/repeated short claims.",
    "value_proposition": "What does the brand offer, to whom, and what changes for that audience? Prioritize offer, audience, and outcome.",
    "personality": "What personality does the brand perform through tone, vocabulary, behavior, and visual stance?",
    "brand_idea": "What conceptual idea connects category, offer, expression, and metaphor? Avoid inventing a brand idea from one decorative phrase.",
    "attributes": "Which 1-3 attributes are consistently demonstrated by product, behavior, proof, or language?",
    "values": "Which values does the brand appear to defend through what it says or does? Mark absent if only generic feature words are present.",
    "mission": "What does the brand concretely do today? Do not use CTAs, future aspirations, blog posts, or pricing copy as mission.",
    "vision": "What future or category change is the brand trying to build? Require explicit future/change language; otherwise mark absent.",
}


def maybe_build_strategist_tldr(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    magenta_circle: dict[str, Any],
    strategic_evidence_packet: dict[str, Any],
    brand_context_brief: dict[str, Any],
    current_tldr: dict[str, Any],
) -> dict[str, Any] | None:
    """Run the optional strategist pass and return a validated TLDR payload."""
    if llm is None or not getattr(llm, "api_key", None):
        return None

    prompt = build_strategist_tldr_prompt(
        brand_name=brand_name,
        url=url,
        magenta_circle=magenta_circle,
        strategic_evidence_packet=strategic_evidence_packet,
        brand_context_brief=brand_context_brief,
        current_tldr=current_tldr,
    )
    raw = llm._call_json(STRATEGIST_TLDR_SYSTEM_PROMPT, prompt, max_tokens=9000)
    if not isinstance(raw, dict) or not raw:
        return None

    normalized = normalize_strategist_response(raw, current_tldr)
    if not normalized.get("tldr_brand3"):
        return None
    return normalized


def build_strategist_tldr_prompt(
    *,
    brand_name: str,
    url: str,
    magenta_circle: dict[str, Any],
    strategic_evidence_packet: dict[str, Any],
    brand_context_brief: dict[str, Any],
    current_tldr: dict[str, Any],
) -> str:
    payload = {
        "brand": {"name": brand_name, "url": url},
        "task": "Rewrite TLDR Brand3 as a better evidence-bound strategic reading.",
        "output_schema": {
            "entity_reading": "short explanation of what entity/products/brand context the evidence suggests",
            "verdict_vs_current": "better | similar | worse",
            "main_gain": "what improved vs current TLDR",
            "main_risk": "main methodological risk or ambiguity",
            "tldr_brand3": {
                key: {
                    "answer": "string or null",
                    "claim_type": "declared | performed | inferred | absent",
                    "mode": "literal | compressed | interpreted_from_discourse | needs_human_review | not_detected",
                    "confidence": "high | medium | low",
                    "reasoning": "concrete block-specific reasoning",
                    "evidence_used": ["traceable evidence strings"],
                    "counter_evidence": ["specific limitations"],
                    "human_review_recommended": "boolean",
                }
                for key in TLDR_KEYS
            },
        },
        "block_exercises": BLOCK_EXERCISES,
        "canonical_evidence_packet": _compact_packet(strategic_evidence_packet),
        "brand_context_brief": _compact_context(brand_context_brief),
        "magenta_signals": _compact_magenta(magenta_circle),
        "current_tldr": _compact_current_tldr(current_tldr),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def normalize_strategist_response(raw: dict[str, Any], current_tldr: dict[str, Any]) -> dict[str, Any]:
    blocks = raw.get("tldr_brand3") if isinstance(raw.get("tldr_brand3"), dict) else {}
    normalized_blocks: dict[str, Any] = {}
    validation_notes: list[str] = []

    for key in TLDR_KEYS:
        raw_block = blocks.get(key) if isinstance(blocks.get(key), dict) else {}
        block, notes = _normalize_block(key, raw_block)
        normalized_blocks[key] = block
        validation_notes.extend(notes)

    return {
        "entity_reading": _clean_text(raw.get("entity_reading")),
        "verdict_vs_current": _clean_text(raw.get("verdict_vs_current")) or "unknown",
        "main_gain": _clean_text(raw.get("main_gain")),
        "main_risk": _clean_text(raw.get("main_risk")),
        "validation_notes": validation_notes,
        "tldr_brand3": normalized_blocks,
    }


def _normalize_block(key: str, raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    answer = raw.get("answer")
    if answer is None:
        answer = raw.get("content")
    answer = _clean_answer(answer)
    evidence = _clean_list(raw.get("evidence_used") or raw.get("evidence"))
    reasoning = _clean_text(raw.get("reasoning") or raw.get("rationale"))
    counter_evidence = _clean_list(raw.get("counter_evidence"))

    detected = bool(answer)
    claim_type = _allowed(raw.get("claim_type"), ALLOWED_CLAIM_TYPES, "inferred" if detected else "absent")
    mode = _allowed(raw.get("mode"), ALLOWED_MODES, "interpreted_from_discourse" if detected else "not_detected")
    confidence = _allowed(raw.get("confidence"), ALLOWED_CONFIDENCE, "medium" if detected else "low")

    if not detected or claim_type == "absent" or mode == "not_detected":
        return _absent_block(key, reasoning, counter_evidence), notes

    if not evidence:
        notes.append(f"{key}: downgraded to absent because strategist provided no traceable evidence.")
        return _absent_block(
            key,
            "The strategist pass did not provide traceable evidence for this block.",
            ["No traceable evidence was attached to the strategist answer."],
        ), notes

    if claim_type == "declared" and not _answer_is_directly_supported(answer, evidence):
        claim_type = "inferred"
        mode = "interpreted_from_discourse"
        notes.append(f"{key}: downgraded from declared because the answer is synthesized, not a literal declaration.")
        counter_evidence.append("The strategist answer synthesizes available evidence rather than quoting a direct brand declaration.")

    if confidence == "high" and claim_type in {"inferred", "performed"}:
        confidence = "medium"
        notes.append(f"{key}: downgraded confidence from high to medium for a non-declared interpretation.")

    if mode == "literal" and not _answer_is_directly_supported(answer, evidence):
        mode = "compressed" if claim_type == "declared" else "interpreted_from_discourse"
        notes.append(f"{key}: mode changed from literal because the answer is not a direct quote.")

    human_review = bool(raw.get("human_review_recommended"))
    if claim_type == "inferred" or mode == "needs_human_review" or confidence == "low":
        human_review = True

    if not reasoning:
        reasoning = "The strategist pass articulated this block from the selected traceable evidence."
    if not counter_evidence and claim_type == "inferred":
        counter_evidence = ["The brand does not explicitly declare this exact Brand3 articulation in the available evidence."]

    source_layer = TLDR_SOURCE_LAYERS[key]
    return {
        "block": key,
        "question": BLOCK_EXERCISES[key],
        "evidence_scope": "Canonical Brand Audit evidence, Brand Context Brief, and Magenta signal evidence.",
        "source_signal": TLDR_SOURCE_SIGNALS[key],
        "source_signal_path": TLDR_SOURCE_SIGNALS[key],
        "source_layer": source_layer,
        "source_layers": [source_layer],
        "observations": ["Generated by the optional LLM strategist pass and validated by Brand3 guardrails."],
        "answer": answer,
        "content": answer,
        "detected": True,
        "claim_type": claim_type,
        "mode": mode,
        "confidence": confidence,
        "reasoning": reasoning,
        "rationale": reasoning,
        "evidence_used": evidence,
        "evidence": evidence,
        "counter_evidence": counter_evidence,
        "human_review_recommended": human_review,
    }, notes


def _absent_block(key: str, reasoning: str | None = None, counter_evidence: list[str] | None = None) -> dict[str, Any]:
    source_layer = TLDR_SOURCE_LAYERS[key]
    reason = reasoning or "Insufficient evidence to articulate this block responsibly."
    limitations = counter_evidence or ["No sufficient public evidence was found for this TLDR block."]
    return {
        "block": key,
        "question": BLOCK_EXERCISES[key],
        "evidence_scope": "Canonical Brand Audit evidence, Brand Context Brief, and Magenta signal evidence.",
        "source_signal": TLDR_SOURCE_SIGNALS[key],
        "source_signal_path": TLDR_SOURCE_SIGNALS[key],
        "source_layer": source_layer,
        "source_layers": [source_layer],
        "observations": ["No sufficient public evidence was selected for this block."],
        "answer": None,
        "content": None,
        "detected": False,
        "claim_type": "absent",
        "mode": "not_detected",
        "confidence": "low",
        "reasoning": reason,
        "rationale": reason,
        "evidence_used": [],
        "evidence": [],
        "counter_evidence": limitations,
        "human_review_recommended": False,
    }


def _compact_packet(packet: dict[str, Any]) -> dict[str, Any]:
    groups = packet.get("groups") if isinstance(packet.get("groups"), dict) else {}
    compact_groups: dict[str, list[str]] = {}
    for group, items in groups.items():
        compact_groups[str(group)] = _compact_items(items, limit=8)
    return {
        "groups": compact_groups,
        "warnings": packet.get("warnings") or [],
        "source_counts": packet.get("source_counts") or {},
    }


def _compact_context(context: dict[str, Any]) -> dict[str, Any]:
    signals = context.get("signals") if isinstance(context.get("signals"), dict) else {}
    compact: dict[str, list[dict[str, Any]]] = {}
    for key, values in signals.items():
        clean_values = []
        if isinstance(values, list):
            for item in values[:6]:
                if isinstance(item, dict):
                    clean_values.append(
                        {
                            "text": _truncate(_clean_text(item.get("text")), 300),
                            "role": item.get("role"),
                            "source_layer": item.get("source_layer"),
                            "source_group": item.get("source_group"),
                        }
                    )
        compact[str(key)] = clean_values
    return {"signals": compact, "warnings": context.get("warnings") or []}


def _compact_magenta(layers: dict[str, Any]) -> dict[str, Any]:
    compact = {}
    for key, layer in layers.items():
        if not isinstance(layer, dict):
            continue
        compact[key] = {
            "detected": bool(layer.get("detected")),
            "confidence": layer.get("confidence"),
            "finding": _truncate(_clean_text(layer.get("finding")), 400),
            "evidence": _clean_list(layer.get("evidence"))[:4],
        }
    return compact


def _compact_current_tldr(tldr: dict[str, Any]) -> dict[str, Any]:
    compact = {}
    for key in TLDR_KEYS:
        block = tldr.get(key) if isinstance(tldr, dict) else None
        if not isinstance(block, dict):
            continue
        compact[key] = {
            "answer": block.get("answer") or block.get("content"),
            "claim_type": block.get("claim_type"),
            "mode": block.get("mode"),
            "confidence": block.get("confidence"),
            "evidence_used": _clean_list(block.get("evidence_used") or block.get("evidence"))[:3],
            "reasoning": _truncate(_clean_text(block.get("reasoning") or block.get("rationale")), 300),
        }
    return compact


def _compact_items(items: Any, limit: int) -> list[str]:
    output: list[str] = []
    if not isinstance(items, list):
        return output
    for item in items[:limit]:
        if isinstance(item, dict):
            text = item.get("text") or item.get("quote") or item.get("content")
        else:
            text = getattr(item, "text", None) or getattr(item, "quote", None) or str(item)
        cleaned = _clean_text(text)
        if cleaned:
            output.append(_truncate(cleaned, 500))
    return output


def _answer_is_directly_supported(answer: Any, evidence: list[str]) -> bool:
    if isinstance(answer, list):
        answer_text = " ".join(str(item) for item in answer)
    else:
        answer_text = str(answer or "")
    answer_key = _normalize_for_match(answer_text)
    if not answer_key:
        return False
    for item in evidence:
        evidence_key = _normalize_for_match(item)
        if not evidence_key:
            continue
        if answer_key in evidence_key or evidence_key in answer_key:
            return True
    return False


def _normalize_for_match(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _clean_answer(value: Any) -> Any:
    if isinstance(value, list):
        cleaned = [_clean_text(item) for item in value]
        return [item for item in cleaned if item]
    return _clean_text(value)


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    output: list[str] = []
    seen: set[str] = set()
    for item in value:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output[:5]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _allowed(value: Any, allowed: set[str], fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else fallback
