"""Post-LLM guardrails for Analyst Pass TLDR Brand3 output.

This module does not rewrite strategy. It validates the strategist output against
the research pack and degrades or flags blocks that overreach their evidence.
"""

from __future__ import annotations

from dataclasses import is_dataclass
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

_DIRECTLY_DECLARABLE_BLOCKS = {
    "core_purpose",
    "value_proposition",
    "mission",
    "magnetism",
}
_STRATEGIC_BLOCKS = {
    "core_purpose",
    "magnetism",
    "value_proposition",
    "personality",
    "brand_idea",
    "attributes",
    "values",
    "mission",
    "vision",
}
_SOURCE_KIND_ORDER = ("owned_literal", "owned_signal", "proof_point", "press_or_founder", "social", "noise", "unknown")


def validate_analyst_tldr(tldr: dict[str, Any], research_pack: Any) -> dict[str, Any]:
    """Validate a strategist TLDR payload against the research pack.

    The function is intentionally additive: it preserves the strategist output,
    but it may downgrade claim_type/mode/confidence, mark human review, or
    suppress unsupported blocks.
    """

    normalized = _normalize_tldr_payload(tldr)
    pack = _research_pack_dict(research_pack)
    catalog = _build_evidence_catalog(pack)
    validation_warnings: list[str] = []
    degraded_fields: list[dict[str, str]] = []

    blocks = normalized.get("tldr_brand3") if isinstance(normalized.get("tldr_brand3"), dict) else {}
    validated_blocks: dict[str, Any] = {}
    for key in TLDR_KEYS:
        raw_block = blocks.get(key) if isinstance(blocks.get(key), dict) else {}
        block, warnings, degraded = _validate_block(key, raw_block, pack, catalog)
        validated_blocks[key] = block
        validation_warnings.extend(warnings)
        degraded_fields.extend(degraded)

    normalized["tldr_brand3"] = validated_blocks
    normalized["validation_warnings"] = _unique_texts(validation_warnings)
    normalized["degraded_fields"] = degraded_fields
    return normalized


def _validate_block(
    key: str,
    block: dict[str, Any],
    pack: dict[str, Any],
    catalog: list[dict[str, str]],
) -> tuple[dict[str, Any], list[str], list[dict[str, str]]]:
    warnings: list[str] = []
    degraded: list[dict[str, str]] = []
    validated = dict(block)

    answer = _clean_text(validated.get("answer") or validated.get("content"))
    evidence_used = _clean_list(validated.get("evidence_used") or validated.get("evidence"))
    claim_type = _normalize_choice(validated.get("claim_type"), {"declared", "performed", "inferred", "absent"}, fallback="inferred" if answer else "absent")
    mode = _normalize_choice(
        validated.get("mode"),
        {"literal", "compressed", "interpreted_from_discourse", "needs_human_review", "not_detected"},
        fallback="interpreted_from_discourse" if answer else "not_detected",
    )
    confidence = _normalize_choice(validated.get("confidence"), {"high", "medium", "low"}, fallback="medium" if answer else "low")
    detected = bool(validated.get("detected")) or bool(answer)

    if not answer or not evidence_used:
        if answer and not evidence_used:
            warnings.append(f"{key}: answer present but no traceable evidence was attached.")
            degraded.append(_degrade_entry(key, "mode", mode, "not_detected", "answer_without_evidence"))
            degraded.append(_degrade_entry(key, "claim_type", claim_type, "absent", "answer_without_evidence"))
        return _absent_block(key, warnings, degraded, reason="No traceable evidence was attached to the strategist answer.")

    evidence_profiles = [_classify_evidence(item, pack, catalog, key=key) for item in evidence_used]
    source_kinds = {profile["source_kind"] for profile in evidence_profiles if profile["source_kind"]}
    source_types = {profile["source_type"] for profile in evidence_profiles if profile["source_type"]}
    has_noise = "noise" in source_kinds
    has_press = "press_or_founder" in source_kinds
    has_proof = "proof_point" in source_kinds
    has_owned_literal = any(profile["source_kind"] == "owned_literal" for profile in evidence_profiles)
    mixed_sources = len({kind for kind in source_kinds if kind != "unknown"}) > 1
    weak_evidence = not has_owned_literal and (has_noise or has_press or has_proof or mixed_sources)

    if key == "personality" and (has_press or _contains_any(answer, ("founder", "founder story", "exit", "press", "interview"))):
        warnings.append("personality: founder story or press context cannot be treated as declared personality.")
        degraded.append(_degrade_entry(key, "claim_type", claim_type, "inferred", "founder_story_is_not_declared_personality"))
        claim_type = "inferred"
        if confidence == "high":
            degraded.append(_degrade_entry(key, "confidence", confidence, "medium", "founder_story_is_not_declared_personality"))
            confidence = "medium"
        mode = "needs_human_review" if weak_evidence else "interpreted_from_discourse"
        detected = bool(answer)
        validated["human_review_recommended"] = True

    if key == "mission" and has_press:
        warnings.append("mission: press/founder context cannot become a declared mission.")
        if claim_type == "declared":
            degraded.append(_degrade_entry(key, "claim_type", claim_type, "inferred", "press_context_not_literal_mission"))
            claim_type = "inferred"
        if mode == "literal":
            degraded.append(_degrade_entry(key, "mode", mode, "interpreted_from_discourse", "press_context_not_literal_mission"))
            mode = "interpreted_from_discourse"
        validated["human_review_recommended"] = True

    if key == "values" and has_proof and not has_owned_literal:
        warnings.append("values: proof points alone are not enough to declare values without observed behavior.")
        if confidence == "high":
            degraded.append(_degrade_entry(key, "confidence", confidence, "medium", "proof_point_requires_behavior"))
            confidence = "medium"
        mode = "needs_human_review" if mixed_sources or has_proof else mode
        validated["human_review_recommended"] = True

    if key == "vision" and (has_noise or _contains_any(answer, ("feed", "article prediction", "prediction", "blog", "post", "page chrome"))):
        warnings.append("vision: blog/feed predictions and page chrome cannot become vision.")
        return _absent_block(key, warnings, degraded, reason="Feed/blog/page-chrome noise cannot support a vision block.")

    if key == "value_proposition" and (has_noise or _contains_any(answer, ("menu", "navigation", "header", "footer", "page chrome"))):
        warnings.append("value_proposition: page chrome cannot support a value proposition.")
        return _absent_block(key, warnings, degraded, reason="Page chrome cannot support a value proposition.")

    if claim_type == "declared" and key in _DIRECTLY_DECLARABLE_BLOCKS and not has_owned_literal:
        warnings.append(f"{key}: declared claim downgraded because the evidence is not literal/owned.")
        degraded.append(_degrade_entry(key, "claim_type", claim_type, "inferred", "declared_requires_owned_literal_evidence"))
        claim_type = "inferred"
        if mode == "literal":
            degraded.append(_degrade_entry(key, "mode", mode, "interpreted_from_discourse", "declared_requires_owned_literal_evidence"))
            mode = "interpreted_from_discourse"

    if weak_evidence and key in _STRATEGIC_BLOCKS and answer:
        if mode != "needs_human_review":
            degraded.append(_degrade_entry(key, "mode", mode, "needs_human_review", "weak_or_mixed_evidence"))
            mode = "needs_human_review"
        validated["human_review_recommended"] = True

    if confidence == "high" and (claim_type == "inferred" or weak_evidence or mixed_sources):
        target = "medium" if has_owned_literal else "low"
        if confidence != target:
            warnings.append(f"{key}: high confidence downgraded because the evidence is inferential or mixed.")
            degraded.append(_degrade_entry(key, "confidence", confidence, target, "high_confidence_requires_strong_evidence"))
            confidence = target

    if mixed_sources and mode not in {"not_detected", "needs_human_review"}:
        warnings.append(f"{key}: mixed sources require human review.")
        degraded.append(_degrade_entry(key, "mode", mode, "needs_human_review", "mixed_sources_require_review"))
        mode = "needs_human_review"
        validated["human_review_recommended"] = True

    if claim_type == "inferred" and weak_evidence and mode != "needs_human_review":
        warnings.append(f"{key}: inferred strategic reading with weak evidence requires human review.")
        degraded.append(_degrade_entry(key, "mode", mode, "needs_human_review", "weak_inferred_strategic_reading"))
        mode = "needs_human_review"
        validated["human_review_recommended"] = True

    if not detected:
        claim_type = "absent"
        mode = "not_detected"
        confidence = "low"
        answer = ""

    validated.update(
        {
            "answer": answer or None,
            "content": answer or None,
            "detected": bool(answer) and mode != "not_detected",
            "claim_type": claim_type,
            "mode": mode,
            "confidence": confidence,
            "evidence_used": evidence_used,
            "evidence": evidence_used,
            "validation_warnings": warnings,
            "degraded_fields": degraded,
        }
    )
    if not validated.get("human_review_recommended"):
        validated["human_review_recommended"] = bool(mode == "needs_human_review")
    return validated, warnings, degraded


def _absent_block(
    key: str,
    warnings: list[str],
    degraded: list[dict[str, str]],
    *,
    reason: str,
) -> tuple[dict[str, Any], list[str], list[dict[str, str]]]:
    block = {
        "block": key,
        "answer": None,
        "content": None,
        "detected": False,
        "claim_type": "absent",
        "mode": "not_detected",
        "confidence": "low",
        "evidence_used": [],
        "evidence": [],
        "counter_evidence": [reason],
        "human_review_recommended": False,
        "validation_warnings": warnings,
        "degraded_fields": degraded,
    }
    return block, warnings, degraded


def _build_evidence_catalog(pack: dict[str, Any]) -> list[dict[str, str]]:
    catalog: list[dict[str, str]] = []

    def add(text: Any, source_kind: str, source_type: str = "", block_hint: str = "") -> None:
        cleaned = _clean_text(text)
        if not cleaned:
            return
        catalog.append(
            {
                "text": cleaned,
                "source_kind": source_kind,
                "source_type": source_type,
                "block_hint": block_hint,
            }
        )

    add(pack.get("declared_purpose"), "owned_literal", "owned_about", "mission")
    add(pack.get("declared_mission"), "owned_literal", "owned_about", "mission")
    add(pack.get("offer"), "owned_literal", "owned_official", "value_proposition")
    add(pack.get("product_summary"), "owned_signal", "owned_official", "value_proposition")
    add(pack.get("company_summary"), "owned_signal", "owned_official", "core_purpose")
    add(pack.get("audience"), "owned_signal", "owned_official", "value_proposition")
    add(pack.get("outcome"), "owned_signal", "owned_official", "value_proposition")
    add(pack.get("future_direction"), "owned_signal", "owned_official", "vision")
    add(pack.get("tone_of_voice"), "owned_signal", "owned_official", "personality")

    for item in pack.get("proof_points") or []:
        if isinstance(item, dict):
            add(item.get("text"), "proof_point", str(item.get("source_type") or ""), "values")
    for item in pack.get("founder_or_press_context") or []:
        if isinstance(item, dict):
            add(item.get("text"), "press_or_founder", str(item.get("source_type") or ""), "mission")
    for item in pack.get("noise_rejected") or []:
        if isinstance(item, dict):
            add(item.get("text"), "noise", str(item.get("source_type") or ""), str(item.get("topic") or ""))

    source_map = pack.get("source_map") or {}
    if isinstance(source_map, dict):
        for source in source_map.values():
            if not isinstance(source, dict):
                continue
            source_type = str(source.get("source_type") or "")
            add(source.get("title"), "owned_literal" if source_type.startswith("owned") else _kind_for_source_type(source_type), source_type)
            add(source.get("label"), "owned_signal" if source_type.startswith("owned") else _kind_for_source_type(source_type), source_type)
    return catalog


def _kind_for_source_type(source_type: str) -> str:
    if source_type.startswith("owned"):
        return "owned_signal"
    if source_type in {"press_or_founder", "news"}:
        return "press_or_founder"
    if source_type == "proof_point":
        return "proof_point"
    if source_type == "social":
        return "social"
    if source_type == "noise":
        return "noise"
    return "unknown"


def _classify_evidence(
    text: str,
    pack: dict[str, Any],
    catalog: list[dict[str, str]],
    *,
    key: str,
) -> dict[str, str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return {"source_kind": "unknown", "source_type": "", "matched_text": ""}

    best = {"source_kind": "unknown", "source_type": "", "matched_text": ""}
    normalized = _normalize_for_match(cleaned)
    for candidate in catalog:
        candidate_text = candidate["text"]
        candidate_norm = _normalize_for_match(candidate_text)
        if not candidate_norm:
            continue
        if normalized == candidate_norm or normalized in candidate_norm or candidate_norm in normalized:
            return {
                "source_kind": candidate["source_kind"],
                "source_type": candidate["source_type"],
                "matched_text": candidate_text,
            }

    if _contains_any(cleaned, ("menu", "navigation", "header", "footer", "page chrome", "feed", "article prediction")):
        return {"source_kind": "noise", "source_type": "", "matched_text": cleaned}
    if _contains_any(cleaned, ("founder", "press", "interview", "exit", "announc", "launch", "raised", "raises")):
        return {"source_kind": "press_or_founder", "source_type": "", "matched_text": cleaned}
    if _contains_any(cleaned, ("testimonial", "customer", "client", "trusted by", "used by", "case study", "review")):
        return {"source_kind": "proof_point", "source_type": "", "matched_text": cleaned}
    if key == "vision" and _contains_any(cleaned, ("future", "new model", "new paradigm", "next generation", "prediction")):
        return {"source_kind": "unknown", "source_type": "", "matched_text": cleaned}
    return best


def _degrade_entry(block: str, field: str, old: str, new: str, reason: str) -> dict[str, str]:
    return {
        "block": block,
        "field": field,
        "from": old,
        "to": new,
        "reason": reason,
    }


def _normalize_tldr_payload(tldr: dict[str, Any]) -> dict[str, Any]:
    if isinstance(tldr.get("tldr_brand3"), dict):
        return dict(tldr)
    return {"tldr_brand3": dict(tldr) if isinstance(tldr, dict) else {}}


def _research_pack_dict(research_pack: Any) -> dict[str, Any]:
    if research_pack is None:
        return {}
    if is_dataclass(research_pack):
        return dict(research_pack.to_dict())
    if hasattr(research_pack, "to_dict") and callable(research_pack.to_dict):
        payload = research_pack.to_dict()
        return payload if isinstance(payload, dict) else {}
    return research_pack if isinstance(research_pack, dict) else {}


def _normalize_choice(value: Any, allowed: set[str], fallback: str) -> str:
    normalized = _clean_text(value).lower()
    return normalized if normalized in allowed else fallback


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _normalize_for_match(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    low = (text or "").lower()
    return any(needle in low for needle in needles)


def _unique_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out
