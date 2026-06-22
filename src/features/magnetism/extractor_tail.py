from __future__ import annotations

import re
from typing import Any

from .extractor_data import DECLARATIVE_TLDR_BLOCKS, GENERIC_MAGNETISM_TERMS, PERFORMED_TLDR_BLOCKS, SPECIFICITY_TERMS, STRATEGIC_TLDR_BLOCKS, TLDR_KEYS, TLDR_TO_LAYER
from .extractor_tail_text_support import (
    add_legacy_fields,
    apply_block_specific_content_rules,
    brand_audit_evidence_packet_summary,
    brand_audit_evidence_text,
    clean_evidence_phrase,
    clean_optional_string,
    compose_personality_content,
    contains_keyword,
    default_tldr_mode,
    default_tldr_rationale,
    derive_brand_idea_block,
    derive_evidence_packet_summary,
    derive_mission_block,
    derive_personality_block,
    derive_system_reading,
    derive_vision_block,
    evidence_list,
    enrich_layers_from_legacy_text,
    extract_three_terms,
    first_layer_evidences,
    first_matching_sentence,
    heuristic_finding,
    infer_brand_name,
    is_navigation_noise,
    is_unusable_audit_quote,
    joined_layer_evidence,
    legacy_value,
    normalize_evidence,
    sentences_from_text,
    snapshot_limitations,
    snapshot_limitations as _snapshot_limitations,
    snapshot_limitations as _tail_snapshot_limitations,
    tldr_content_from_layer,
    trim_evidence,
    visual_semantics_from_snapshot,
)


def magnetism_phrase_breakdown(text: str) -> dict[str, int]:
    if not text:
        return {
            "originality": 0,
            "specificity": 0,
            "memorability": 0,
            "verifiable_promise": 0,
        }

    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    word_count = len(words)
    generic_hits = sum(1 for word in words if word in GENERIC_MAGNETISM_TERMS)
    specific_hits = sum(1 for word in words if word in SPECIFICITY_TERMS)
    has_number = bool(re.search(r"\d", text))
    has_action = bool(re.search(r"\b(build|do|earn|save|ship|reduce|automate|protect|find|create|launch|inspire)\b", text.lower()))
    is_short_imperative = 2 <= word_count <= 4 and has_action

    originality = 92 if is_short_imperative else 85 - (generic_hits * 14)
    specificity = 35 + min(specific_hits * 18, 55) + (10 if has_number else 0)
    if is_short_imperative:
        specificity = max(specificity, 62)
    memorability = 95 if is_short_imperative else 80 if 2 <= word_count <= 8 else 58 if word_count <= 14 else 35
    verifiable = 45 + (25 if has_action else 0) + (20 if has_number or specific_hits >= 2 else 0)
    if is_short_imperative:
        verifiable = max(verifiable, 75)
    return {
        "originality": clamp(originality),
        "specificity": clamp(specificity),
        "memorability": clamp(memorability),
        "verifiable_promise": clamp(verifiable),
    }


def semantic_alignment_score(layers: dict[str, Any]) -> int:
    pairs = [
        ("mindspace", "gamespace"),
        ("aetherspace", "tactispace"),
        ("netspace", "ambientspace"),
    ]
    scores = []
    for left, right in pairs:
        left_detected = layers[left]["detected"]
        right_detected = layers[right]["detected"]
        if left_detected and right_detected:
            scores.append(85)
        elif left_detected or right_detected:
            scores.append(45)
        else:
            scores.append(55)

    envispace_bonus = 10 if layers["envispace"]["detected"] else -10
    return clamp(round(sum(scores) / len(scores)) + envispace_bonus)


def absence_of_contradiction_score(tldr: dict[str, Any]) -> int:
    values_text = " ".join(str(block.get("content") or "") for block in tldr.values() if block.get("content")).lower()
    contradiction_pairs = [
        ("playful", "institutional"),
        ("rebel", "compliance"),
        ("simple", "configurable"),
        ("premium", "cheap"),
    ]
    penalties = sum(1 for a, b in contradiction_pairs if a in values_text and b in values_text)
    return clamp(92 - penalties * 18)


def weighted_score(scores: dict[str, int], weights: dict[str, float]) -> int:
    return round(sum(scores[key] * weight for key, weight in weights.items()))


def int_between(value: Any, minimum: int, maximum: int) -> int | None:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(minimum, min(maximum, number))


def quadrant(magnetism_score: int, coherence_score: int) -> str:
    high_magnetism = magnetism_score >= 70
    high_coherence = coherence_score >= 70
    if high_magnetism and high_coherence:
        return "Señal fuerte · validar antes de escalar"
    if high_magnetism and not high_coherence:
        return "Eslogan sin estructura · peligrosa"
    if not high_magnetism and high_coherence:
        return "Bien pensada sin alma comercial"
    return "Marca sin escribir · target FLOC*"


def magnetism_tier(score: int) -> str:
    if score >= 85:
        return "Magnetic"
    if score >= 70:
        return "Memorable"
    return "Forgettable"


def coherence_tier(score: int) -> str:
    if score >= 80:
        return "Aligned"
    if score >= 50:
        return "Functional"
    return "Fragmented"


def legacy_value(block: dict[str, Any]) -> str:
    value = block.get("content")
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value or "(no detectado)")


def clamp(value: int | float) -> int:
    return max(0, min(100, int(round(value))))


def normalized_tldr_confidence(value: Any, detected: bool) -> str:
    confidence = str(value or "").strip().lower()
    if confidence in {"high", "medium", "low"}:
        return confidence
    return "low" if not detected else "medium"


def infer_claim_type(key: str, mode: str, detected: bool) -> str:
    if not detected:
        return "absent"
    if mode in {"literal", "compressed"} and key in DECLARATIVE_TLDR_BLOCKS:
        return "declared"
    if key in PERFORMED_TLDR_BLOCKS:
        return "performed"
    return "inferred"


def observations_for_block(key: str, evidence_used: list[str], content: Any) -> list[str]:
    observations: list[str] = []
    if evidence_used:
        observations.append(f"Uses {len(evidence_used)} traceable evidence item(s) selected for {key}.")
    if content:
        observations.append("Produces a bounded Brand3 articulation from the selected evidence.")
    if not observations:
        observations.append("No sufficient public evidence was selected for this block.")
    return observations


def default_counter_evidence(key: str, claim_type: str, detected: bool, layers: dict[str, Any]) -> list[str]:
    if not detected:
        return ["No sufficient public evidence was found for this TLDR block."]
    if claim_type == "inferred":
        return ["The brand does not explicitly declare this exact Brand3 articulation in the available evidence."]
    if key in STRATEGIC_TLDR_BLOCKS and not layers.get(TLDR_TO_LAYER[key], {}).get("detected"):
        return ["The primary Magenta Circle layer for this block is weak or absent."]
    return []


def should_recommend_human_review(
    key: str,
    claim_type: str,
    mode: str,
    confidence: str,
    detected: bool,
    evidence_used: list[str],
) -> bool:
    if not detected:
        return False
    if mode == "needs_human_review":
        return True
    if key in STRATEGIC_TLDR_BLOCKS and claim_type == "inferred":
        return confidence == "low" or len(evidence_used) < 2
    return False


def has_tldr_v03_contract(block: dict[str, Any]) -> bool:
    required = {
        "block",
        "question",
        "evidence_scope",
        "source_signal",
        "source_signal_path",
        "source_layer",
        "observations",
        "answer",
        "claim_type",
        "reasoning",
        "evidence_used",
        "counter_evidence",
        "human_review_recommended",
    }
    return required.issubset(block.keys())
