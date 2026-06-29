"""Post-LLM guardrails for Analyst Pass TLDR Brand3 output.

This module does not rewrite strategy. It validates the strategist output against
the research pack and degrades or flags blocks that overreach their evidence.
"""

from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any

from src.features.magnetism.analyst_tldr_block_candidates import (
    shortlist_rows_for_block,
    shortlist_texts_for_block,
    signal_candidates_for_block,
)


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
_EVIDENCE_SNAP_BLOCKS = {"core_purpose", "magnetism", "value_proposition", "mission"}
_TERM_CANONICAL_BLOCKS = {"personality", "attributes", "values"}


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
    shortlist_rows = shortlist_rows_for_block(pack, key)
    shortlist_texts = [row.get("text", "") for row in shortlist_rows if row.get("text")]
    signal_candidates = signal_candidates_for_block(pack, key)

    if key == "core_purpose" and _should_absent_core_purpose(
        pack,
        answer=answer,
        evidence_used=evidence_used,
        shortlist_texts=shortlist_texts,
    ):
        warnings.append("core_purpose: functional offer language without declared purpose should remain absent.")
        return _absent_block(
            key,
            warnings,
            degraded,
            reason="Functional offer language without declared purpose cannot support a core purpose block.",
        )

    if key == "brand_idea" and _should_absent_brand_idea(
        pack,
        answer=answer,
        evidence_used=evidence_used,
        shortlist_texts=shortlist_texts,
    ):
        warnings.append("brand_idea: generic category language plus proof points cannot support a conceptual brand idea.")
        return _absent_block(
            key,
            warnings,
            degraded,
            reason="Generic category language plus proof points cannot support a conceptual brand idea block.",
        )

    if (
        key == "brand_idea"
        and claim_type == "inferred"
        and _should_review_brand_idea_single_literal(
            pack,
            answer=answer,
            evidence_used=evidence_used,
            shortlist_texts=shortlist_texts,
            signal_candidates=signal_candidates,
        )
    ):
        warnings.append("brand_idea: a single literal offer/tagline without conceptual reinforcement requires human review.")
        if mode != "needs_human_review":
            degraded.append(_degrade_entry(key, "mode", mode, "needs_human_review", "single_literal_brand_idea_requires_review"))
            mode = "needs_human_review"
        if confidence == "high":
            degraded.append(_degrade_entry(key, "confidence", confidence, "medium", "single_literal_brand_idea_requires_review"))
            confidence = "medium"
        validated["human_review_recommended"] = True

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
    if key == "values" and _should_absent_values(
        pack,
        answer=answer,
        evidence_used=evidence_used,
        signal_candidates=signal_candidates,
        has_owned_literal=has_owned_literal,
    ):
        warnings.append("values: absent because no canonical value signals were present in the research pack.")
        return _absent_block(
            key,
            warnings,
            degraded,
            reason="No canonical value signals were present in the research pack for this values block.",
        )

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
    return _canonicalize_block_payload(
        key,
        validated,
        pack,
        evidence_profiles=evidence_profiles,
    ), warnings, degraded


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


def _should_absent_core_purpose(
    pack: dict[str, Any],
    *,
    answer: str,
    evidence_used: list[str],
    shortlist_texts: list[str],
) -> bool:
    if not answer:
        return False
    declared_purpose = _clean_text(pack.get("declared_purpose"))
    if declared_purpose:
        return False
    if not evidence_used:
        return False
    normalized_answer = _normalize_for_match(answer)
    normalized_evidence = " ".join(_normalize_for_match(item) for item in evidence_used if item)
    normalized_shortlist = " ".join(_normalize_for_match(item) for item in shortlist_texts if item)
    if not normalized_evidence and not normalized_shortlist:
        return False
    functional_pack_markers = (
        "manage spend",
        "manage spending",
        "spending",
        "expense management",
        "company cards",
        "cards and expense software",
        "spend management",
        "software",
        "automate",
        "automation",
        "streamline",
        "simplify",
    )
    functional_markers = (
        "manage spend",
        "manage spending",
        "spending",
        "control de gastos",
        "expense management",
        "automatizar",
        "automate",
        "streamline",
        "simplify",
        "software",
        "tarjetas de empresa",
        "company cards",
    )
    beyond_product_markers = (
        "why",
        "purpose",
        "exists",
        "exist",
        "believe",
        "change the way",
        "transform the way",
        "beyond",
        "make business spending",
        "free businesses",
        "unlock",
        "empower",
    )
    looks_functional = any(marker in normalized_answer for marker in functional_markers)
    if not looks_functional:
        return False
    evidence_looks_functional = any(marker in normalized_evidence for marker in functional_pack_markers)
    shortlist_looks_functional = any(marker in normalized_shortlist for marker in functional_pack_markers)
    has_pack_purpose_signal = any(marker in normalized_evidence for marker in beyond_product_markers) or any(
        marker in normalized_shortlist for marker in beyond_product_markers
    )
    answer_uses_purpose_rhetoric = any(marker in normalized_answer for marker in beyond_product_markers)
    if (evidence_looks_functional or shortlist_looks_functional) and not has_pack_purpose_signal:
        return True
    if answer_uses_purpose_rhetoric and not has_pack_purpose_signal:
        return True
    return False


def _should_absent_values(
    pack: dict[str, Any],
    *,
    answer: str,
    evidence_used: list[str],
    signal_candidates: list[str],
    has_owned_literal: bool,
) -> bool:
    if not answer:
        return False
    if signal_candidates:
        return False
    if not evidence_used:
        return False
    normalized_evidence = [_normalize_for_match(item) for item in evidence_used if item]
    declared_mission = _normalize_for_match(pack.get("declared_mission"))
    declared_purpose = _normalize_for_match(pack.get("declared_purpose"))
    if has_owned_literal and normalized_evidence:
        if all(
            item
            and (
                (declared_mission and (item in declared_mission or declared_mission in item))
                or (declared_purpose and (item in declared_purpose or declared_purpose in item))
            )
            for item in normalized_evidence
        ):
            return True
        return False
    return True


def _should_absent_brand_idea(
    pack: dict[str, Any],
    *,
    answer: str,
    evidence_used: list[str],
    shortlist_texts: list[str],
) -> bool:
    if not answer:
        return False
    normalized_answer = _normalize_for_match(answer)
    normalized_evidence = [_normalize_for_match(item) for item in evidence_used if item]
    normalized_shortlist = [_normalize_for_match(item) for item in shortlist_texts if item]
    if not normalized_evidence and not normalized_shortlist:
        return False
    conceptual_pack_items = pack.get("visual_or_conceptual_signals")
    if isinstance(conceptual_pack_items, list):
        conceptual_pack = [_normalize_for_match(item) for item in conceptual_pack_items if _clean_text(item)]
    else:
        single = _normalize_for_match(conceptual_pack_items)
        conceptual_pack = [single] if single else []
    if conceptual_pack:
        return False
    generic_category_markers = (
        "platform",
        "software",
        "infrastructure",
        "deployment layer",
        "tool",
        "solution",
    )
    proof_markers = (
        "million monthly",
        "trusted by",
        "customers",
        "faster",
        "build + deploy",
        "used by",
        "serves over",
        "visits",
    )
    conceptual_answer_markers = (
        "default layer",
        "default deployment layer",
        "operating system",
        "engine",
        "bridge",
        "movement",
        "metaphor",
        "category shift",
        "new model",
        "future of",
    )
    evidence_blob = " ".join(normalized_evidence)
    shortlist_blob = " ".join(normalized_shortlist)
    generic_evidence = any(marker in evidence_blob for marker in generic_category_markers) or any(
        marker in shortlist_blob for marker in generic_category_markers
    )
    proof_evidence = any(marker in evidence_blob for marker in proof_markers)
    answer_is_conceptual_but_unbacked = any(marker in normalized_answer for marker in conceptual_answer_markers)
    return generic_evidence and proof_evidence and answer_is_conceptual_but_unbacked


def _should_review_brand_idea_single_literal(
    pack: dict[str, Any],
    *,
    answer: str,
    evidence_used: list[str],
    shortlist_texts: list[str],
    signal_candidates: list[str],
) -> bool:
    if not answer:
        return False
    if signal_candidates:
        return False
    conceptual_pack_items = pack.get("visual_or_conceptual_signals")
    if isinstance(conceptual_pack_items, list):
        conceptual_pack = [_clean_text(item) for item in conceptual_pack_items if _clean_text(item)]
    else:
        conceptual_pack = [_clean_text(conceptual_pack_items)] if _clean_text(conceptual_pack_items) else []
    if conceptual_pack:
        return False
    unique_evidence = _unique_texts(evidence_used)
    if len(unique_evidence) != 1:
        return False
    unique_shortlist = _unique_texts(shortlist_texts)
    if len(unique_shortlist) > 1:
        return False
    normalized_answer = _normalize_for_match(answer)
    normalized_evidence = _normalize_for_match(unique_evidence[0])
    if not normalized_evidence:
        return False
    if normalized_answer == normalized_evidence:
        return False
    if len(normalized_evidence.split()) < 5:
        return False
    return True


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


def _canonicalize_block_payload(
    key: str,
    block: dict[str, Any],
    pack: dict[str, Any],
    *,
    evidence_profiles: list[dict[str, str]],
) -> dict[str, Any]:
    canonical = dict(block)
    answer = _clean_text(canonical.get("answer") or canonical.get("content"))
    if key in {"attributes", "values"}:
        answer = _canonicalize_term_list_answer(answer)
    answer = _canonicalize_semantic_answer(key, answer, pack)
    evidence_used = _canonicalize_evidence_used(
        key,
        canonical.get("evidence_used"),
        pack,
    )
    counter_evidence = _sorted_unique_texts(canonical.get("counter_evidence"))
    warnings = _sorted_unique_texts(canonical.get("validation_warnings"))
    source_map = pack.get("source_map") if isinstance(pack.get("source_map"), dict) else {}
    evidence_sources = _canonicalize_evidence_sources(
        canonical.get("evidence_sources"),
        source_map if isinstance(source_map, dict) else {},
        key=key,
        pack=pack,
        evidence_used=evidence_used,
    )
    reasoning = _canonical_reasoning(
        key,
        claim_type=str(canonical.get("claim_type") or "absent"),
        mode=str(canonical.get("mode") or "not_detected"),
        evidence_profiles=evidence_profiles,
        evidence_count=len(evidence_used),
        human_review=bool(canonical.get("human_review_recommended")),
    )
    canonical.update(
        {
            "answer": answer or None,
            "content": answer or None,
            "evidence_used": evidence_used,
            "evidence": evidence_used,
            "evidence_sources": evidence_sources,
            "counter_evidence": counter_evidence,
            "validation_warnings": warnings,
            "reasoning": reasoning,
            "rationale": reasoning,
        }
    )
    return canonical


def _canonicalize_term_list_answer(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    parts = [_clean_list_term(part) for part in text.split(",")]
    parts = [part for part in parts if part]
    if len(parts) < 2:
        return text
    return ", ".join(sorted(parts, key=lambda item: item.lower()))


def _clean_list_term(value: str) -> str:
    return _clean_text(str(value).strip(" [](){}'\""))


def _sorted_unique_texts(value: Any) -> list[str]:
    return sorted(_clean_list(value), key=lambda item: item.lower())


def _canonicalize_evidence_used(
    key: str,
    value: Any,
    pack: dict[str, Any],
) -> list[str]:
    evidence_used = _sorted_unique_texts(value)
    if key not in _EVIDENCE_SNAP_BLOCKS:
        return evidence_used
    shortlist = shortlist_texts_for_block(pack, key)
    if not shortlist:
        return evidence_used
    matched: list[str] = []
    for item in evidence_used:
        normalized_item = _normalize_for_match(item)
        for candidate in shortlist:
            normalized_candidate = _normalize_for_match(candidate)
            if not normalized_candidate:
                continue
            if (
                normalized_item == normalized_candidate
                or normalized_item in normalized_candidate
                or normalized_candidate in normalized_item
            ):
                if candidate not in matched:
                    matched.append(candidate)
                break
    return matched or evidence_used


def _canonicalize_semantic_answer(
    key: str,
    answer: str,
    pack: dict[str, Any],
) -> str:
    cleaned = _clean_text(answer)
    if key not in _TERM_CANONICAL_BLOCKS or not cleaned:
        return cleaned
    candidates = signal_candidates_for_block(pack, key)
    if not candidates:
        return cleaned
    matched: list[str] = []
    normalized_answer = _normalize_for_match(cleaned)
    for candidate in candidates:
        normalized_candidate = _normalize_for_match(candidate)
        if not normalized_candidate:
            continue
        if (
            normalized_answer == normalized_candidate
            or normalized_candidate in normalized_answer
            or normalized_answer in normalized_candidate
        ):
            if candidate not in matched:
                matched.append(candidate)
    if key == "personality":
        if len(matched) >= 2:
            return ", ".join(matched[:2])
        return cleaned
    if len(matched) < 2:
        return cleaned
    return ", ".join(sorted(matched, key=lambda item: item.lower()))


def _canonicalize_evidence_sources(
    value: Any,
    source_map: dict[str, Any],
    *,
    key: str = "",
    pack: dict[str, Any] | None = None,
    evidence_used: list[str] | None = None,
) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    source_index = _source_lookup_index(source_map)
    shortlist_index = _shortlist_source_index(pack or {}, key, evidence_used or [])
    for item in value:
        if not isinstance(item, dict):
            continue
        source_key = _clean_text(item.get("source_key") or item.get("url") or item.get("label"))
        matched = shortlist_index.get(_normalize_source_lookup_key(source_key), {})
        if not matched and source_key.lower() in {"input_url", "homepage", "home"} and shortlist_index:
            matched = next(iter(shortlist_index.values()))
        if not matched:
            matched = source_index.get(_normalize_source_lookup_key(source_key), {})
        url = _clean_text(item.get("url") or matched.get("url") or source_key)
        label = _clean_text(item.get("label") or matched.get("label") or matched.get("title"))
        if label.lower() in {"input_url", "homepage", "home"}:
            label = ""
        canonical_source_key = source_key
        if canonical_source_key.lower() in {"input_url", "homepage", "home"}:
            canonical_source_key = _clean_text(matched.get("url") or matched.get("label") or matched.get("title"))
        source_type = _clean_text(item.get("source_type") or matched.get("source_type"))
        row = {
            "source_key": _canonical_source_key(canonical_source_key or matched.get("url") or url or label),
            "source_type": source_type,
            "url": _canonical_source_key(url),
            "label": label,
        }
        signature = (
            row["source_key"].lower(),
            row["source_type"].lower(),
            row["url"].lower(),
            row["label"].lower(),
        )
        if signature in seen or not any(row.values()):
            continue
        seen.add(signature)
        normalized.append(row)
    return sorted(
        normalized,
        key=lambda item: (
            item.get("source_key", "").lower(),
            item.get("source_type", "").lower(),
            item.get("url", "").lower(),
            item.get("label", "").lower(),
        ),
    )


def _shortlist_source_index(
    pack: dict[str, Any],
    key: str,
    evidence_used: list[str],
) -> dict[str, dict[str, str]]:
    if not pack or not key or not evidence_used:
        return {}
    by_text = {
        _normalize_for_match(row.get("text")): row
        for row in shortlist_rows_for_block(pack, key)
        if _normalize_for_match(row.get("text"))
    }
    source_map = pack.get("source_map") if isinstance(pack.get("source_map"), dict) else {}
    source_index = _source_lookup_index(source_map)
    result: dict[str, dict[str, str]] = {}
    for text in evidence_used:
        normalized_text = _normalize_for_match(text)
        row = by_text.get(normalized_text)
        if not row:
            for candidate_text, candidate_row in by_text.items():
                if (
                    normalized_text == candidate_text
                    or normalized_text in candidate_text
                    or candidate_text in normalized_text
                ):
                    row = candidate_row
                    break
        if not row:
            continue
        source_key = _canonical_source_key(row.get("source_key"))
        matched = source_index.get(_normalize_source_lookup_key(source_key), {})
        payload = {
            "url": _clean_text(matched.get("url") or source_key),
            "label": _clean_text(matched.get("label") or matched.get("title")),
            "title": _clean_text(matched.get("title")),
            "source_type": _clean_text(matched.get("source_type")),
        }
        for alias in (
            source_key,
            payload.get("url"),
            payload.get("label"),
            payload.get("title"),
        ):
            normalized = _normalize_source_lookup_key(alias)
            if normalized:
                result[normalized] = payload
    return result


def _source_lookup_index(source_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for key, value in source_map.items():
        if not isinstance(value, dict):
            continue
        candidates = {
            _normalize_source_lookup_key(str(key)),
            _normalize_source_lookup_key(value.get("url")),
            _normalize_source_lookup_key(value.get("label")),
            _normalize_source_lookup_key(value.get("title")),
        }
        for candidate in candidates:
            if candidate:
                index[candidate] = value
    return index


def _normalize_source_lookup_key(value: Any) -> str:
    text = _clean_text(value).lower()
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text.rstrip("/")
    return text


def _canonical_source_key(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text.rstrip("/")
    return text


def _canonical_reasoning(
    key: str,
    *,
    claim_type: str,
    mode: str,
    evidence_profiles: list[dict[str, str]],
    evidence_count: int,
    human_review: bool,
) -> str:
    if mode == "not_detected" or claim_type == "absent":
        return f"No traceable evidence supported the {key} block."
    source_kinds = sorted(
        {
            str(profile.get("source_kind") or "unknown")
            for profile in evidence_profiles
            if str(profile.get("source_kind") or "").strip()
        }
    )
    kinds = ", ".join(source_kinds) if source_kinds else "unknown"
    review = " Human review recommended." if human_review or mode == "needs_human_review" else ""
    return (
        f"{claim_type.capitalize()} {key} reading in {mode} mode from "
        f"{evidence_count} traceable evidence item(s); source kinds: {kinds}.{review}"
    )
