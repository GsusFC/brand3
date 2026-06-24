"""Executable TLDR Brand3 block interpreter specs.

The specs define the exercise each migrated TLDR block must perform. This
module owns candidate selection, evidence acceptance, and block-level metadata
for migrated TLDR blocks while the extractor remains responsible for scanner
orchestration.
"""

from __future__ import annotations

import re
from typing import Any

from src.reports.vertical_signals import (
    product_offer_family_allows_multiple_lines,
    product_offer_family_for_text,
)
from src.features.magnetism.block_interpreters_selection import (
    TLDR_BLOCK_INTERPRETER_SPECS,
    _invalid_source_role_for_block,
    block_evidence_candidates,
    get_tldr_block_interpreter_spec,
    source_role_for_candidate,
    source_role_for_url,
    strategic_packet_candidates,
    strategic_packet_candidate_priority,
)
from src.features.magnetism.block_interpreters_helpers import (
    _contains_keyword,
    _has_audience_signal,
    _has_future_signal,
    _has_formal_mission_signal,
    _has_operating_activity_signal,
    _has_offer_signal,
    _has_outcome_signal,
    _is_bad_value_prop_candidate,
    _is_developer_cloud_positioning,
    _is_feed_or_article_noise,
    _is_market_prediction_noise,
    _is_navigation_noise,
    _is_rhetorical_future_question_noise,
    _is_testimonial_evidence,
    _is_truncated_evidence,
    _is_vague_mission_slogan,
    _is_values_statement_as_mission,
    _is_weak_value_prop_addition,
)
from src.features.magnetism.block_interpreters_outputs_impl import (
    apply_editorial_policy_guardrails,
    answer_from_spec,
    claim_type_from_spec,
    confidence_from_spec,
    counter_evidence_from_spec,
    evidence_from_spec,
    human_review_from_spec,
    mode_from_spec,
    observations_from_spec,
    reasoning_from_spec,
)


def interpret_tldr_block(
    block: str,
    spec: dict[str, Any],
    candidates: list[dict[str, str]],
    layers: dict[str, Any],
    primary_layer_key: str,
) -> dict[str, Any] | None:
    """Interpret a TLDR block from candidate evidence using its executable spec."""
    accepted = accepted_block_evidence(block, spec, candidates)
    if not accepted:
        sufficiency = evidence_sufficiency_from_spec(block, candidates, accepted)
        return {
            "content": None,
            "detected": False,
            "claim_type": "absent",
            "mode": "not_detected",
            "confidence": "low",
            "evidence": [],
            "rationale": "Insufficient evidence to articulate this block responsibly.",
            "reasoning": "Insufficient evidence to articulate this block responsibly.",
            "observations": [f"Applied executable {block} interpreter spec."],
            "counter_evidence": sufficiency.get("missing_evidence", []),
            "source_layers": [primary_layer_key],
            "human_review_recommended": sufficiency.get("status") in {"partial", "polluted"},
            "evidence_sufficiency": sufficiency,
        }

    evidence = accepted[0]["text"]
    diagnostics = block_evidence_diagnostics(block, accepted, layers, primary_layer_key)
    answer = answer_from_spec(block, evidence, accepted)
    display_evidence = evidence_from_spec(block, evidence, answer, accepted)
    mode = mode_from_spec(block, diagnostics)
    confidence = confidence_from_spec(block, diagnostics, accepted)
    claim_type = claim_type_from_spec(block, diagnostics)
    counter_evidence = counter_evidence_from_spec(block, diagnostics)
    human_review = human_review_from_spec(block, diagnostics, confidence, counter_evidence)
    sufficiency = evidence_sufficiency_from_spec(block, candidates, accepted, diagnostics, counter_evidence)
    if sufficiency.get("decision") == "interpret_with_review":
        human_review = True
    reasoning_evidence = display_evidence[0] if display_evidence else evidence
    reasoning = reasoning_from_spec(block, reasoning_evidence, diagnostics)
    mode, confidence, counter_evidence, human_review = apply_editorial_policy_guardrails(
        block,
        answer,
        reasoning,
        mode,
        confidence,
        counter_evidence,
        human_review,
    )

    return {
        "content": answer,
        "detected": True,
        "claim_type": claim_type,
        "mode": mode,
        "confidence": confidence,
        "evidence": display_evidence,
        "rationale": reasoning,
        "reasoning": reasoning,
        "observations": observations_from_spec(block, diagnostics),
        "counter_evidence": counter_evidence,
        "source_layers": list(dict.fromkeys(item["layer"] for item in accepted)),
        "human_review_recommended": human_review,
        "evidence_sufficiency": sufficiency,
    }


def evidence_sufficiency_from_spec(
    block: str,
    candidates: list[dict[str, str]],
    accepted: list[dict[str, str]],
    diagnostics: dict[str, Any] | None = None,
    counter_evidence: list[str] | None = None,
) -> dict[str, Any]:
    """Assess whether the available evidence is enough to interpret a TLDR block."""
    diagnostics = diagnostics or {}
    counter_evidence = counter_evidence or []
    noise_detected = _noise_detected_for_block(block, candidates, accepted)
    available_evidence = [item["text"] for item in accepted[:3] if item.get("text")]
    best_sources = _candidate_source_labels(accepted or candidates)
    missing_evidence = list(counter_evidence)

    if not candidates:
        status = "insufficient"
        missing_evidence.append(f"No candidate evidence was available for {block}.")
    elif not accepted:
        status = "polluted" if noise_detected else "insufficient"
        if noise_detected:
            missing_evidence.append("Candidate evidence was rejected as feed, article, CTA, navigation, or market-prediction noise.")
        else:
            minimum_rule = TLDR_BLOCK_INTERPRETER_SPECS[block]["minimum_evidence_rule"]
            missing_evidence.append(f"No candidate evidence met the minimum rule: {minimum_rule}")
    elif block == "value_proposition":
        strong = diagnostics.get("has_offer") and diagnostics.get("has_outcome")
        status = "sufficient" if strong else "partial"
    elif block == "mission":
        status = "sufficient" if diagnostics.get("has_operating_activity") else "partial"
    elif block == "vision":
        status = "sufficient" if diagnostics.get("has_formal_vision") and not noise_detected else "partial"
    else:
        status = "sufficient" if accepted and not noise_detected else "partial"

    if status == "sufficient":
        decision = "interpret"
    elif status == "partial":
        decision = "interpret_with_review"
    else:
        decision = "not_detected"

    return {
        "status": status,
        "available_evidence": available_evidence,
        "missing_evidence": list(dict.fromkeys(missing_evidence)),
        "noise_detected": noise_detected,
        "best_sources": best_sources,
        "decision": decision,
    }


def _candidate_source_labels(candidates: list[dict[str, str]]) -> list[str]:
    labels: list[str] = []
    for item in candidates:
        label = str(item.get("group") or item.get("source") or item.get("layer") or "unknown")
        if label and label not in labels:
            labels.append(label)
    return labels[:5]


def _noise_detected_for_block(
    block: str,
    candidates: list[dict[str, str]],
    accepted: list[dict[str, str]],
) -> bool:
    accepted_texts = {item.get("text") for item in accepted}
    rejected = [item for item in candidates if item.get("text") not in accepted_texts]
    for item in rejected:
        text = str(item.get("text") or "")
        low = text.lower()
        if _invalid_source_role_for_block(block, item):
            return True
        if _is_navigation_noise(text) or _is_feed_or_article_noise(text) or _is_truncated_evidence(text):
            return True
        if block == "vision" and (_is_market_prediction_noise(text) or _is_rhetorical_future_question_noise(text)):
            return True
        if block == "mission" and (_is_vague_mission_slogan(low) or _is_testimonial_evidence(low) or _is_values_statement_as_mission(low)):
            return True
        if block == "value_proposition" and _is_bad_value_prop_candidate(text):
            return True
    return False


def accepted_block_evidence(
    block: str,
    spec: dict[str, Any],
    candidates: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Filter evidence candidates according to the block's executable spec."""
    accepted: list[dict[str, str]] = []
    allowed_groups = set(spec.get("strategic_groups") or [])
    for candidate in candidates:
        text = candidate["text"]
        low = text.lower()
        if any(term in low for term in spec["reject"]):
            continue
        if _invalid_source_role_for_block(block, candidate):
            continue
        group = candidate.get("group")
        from_packet = str(candidate.get("source", "")).startswith("strategic:")
        if from_packet:
            if group not in allowed_groups:
                continue
            if block == "mission" and (
                _is_testimonial_evidence(low)
                or _is_truncated_evidence(low)
                or _is_feed_or_article_noise(text)
                or _is_vague_mission_slogan(low)
                or _is_values_statement_as_mission(low)
                or not (_has_operating_activity_signal(low) or _has_formal_mission_signal(low))
            ):
                continue
            if block == "vision" and (
                _is_truncated_evidence(low)
                or _is_feed_or_article_noise(text)
                or _is_market_prediction_noise(text)
                or _is_rhetorical_future_question_noise(text)
                or not _has_future_signal(low)
            ):
                continue
            if block == "value_proposition" and _is_bad_value_prop_candidate(text):
                continue
        else:
            if not any(_contains_keyword(low, term) for term in spec["look_for"]):
                continue
            if block == "mission" and (
                _is_truncated_evidence(low)
                or _is_feed_or_article_noise(text)
                or _is_vague_mission_slogan(low)
                or _is_values_statement_as_mission(low)
                or not (_has_operating_activity_signal(low) or _has_formal_mission_signal(low))
            ):
                continue
            if block == "vision" and (
                _is_truncated_evidence(low)
                or _is_feed_or_article_noise(text)
                or _is_market_prediction_noise(text)
                or _is_rhetorical_future_question_noise(text)
                or not _has_future_signal(low)
            ):
                continue
            if block == "value_proposition" and (_is_bad_value_prop_candidate(text) or not _has_offer_signal(low)):
                continue
        accepted.append(candidate)
    if block == "value_proposition" and accepted:
        has_offer_candidate = any(
            str(item.get("group") or "") == "product_offer" or _has_offer_signal(str(item.get("text") or "").lower())
            for item in accepted
        )
        if not has_offer_candidate:
            return []
    return accepted


def block_evidence_diagnostics(
    block: str,
    accepted: list[dict[str, str]],
    layers: dict[str, Any],
    primary_layer_key: str,
) -> dict[str, Any]:
    text = "\n".join(item["text"] for item in accepted).lower()
    groups = {str(item.get("group")) for item in accepted if item.get("group")}
    source_roles = sorted({str(item.get("source_role") or "unknown") for item in accepted})
    explicit_sources = [str(item.get("source") or "") for item in accepted]
    product_offer_count = sum(
        1 for item in accepted if str(item.get("group") or "") == "product_offer"
    )
    has_multiple_offers = _has_divergent_product_offers(accepted)
    return {
        "has_explicit_evidence": any(
            source == "evidence" or source.startswith("strategic:")
            for source in explicit_sources
        ),
        "has_offer": _has_offer_signal(text) or "product_offer" in groups,
        "has_audience": _has_audience_signal(text) or "audience" in groups,
        "has_outcome": _has_outcome_signal(text) or "outcome" in groups,
        "has_operating_activity": _has_operating_activity_signal(text) or "mission_language" in groups,
        "has_future": _has_future_signal(text) or "vision_language" in groups,
        "has_formal_vision": bool(
            re.search(r"\b(our vision is|vision is|nuestra visión es|nuestra vision es)\b", text)
        ),
        "candidate_count": len(accepted),
        "product_offer_count": product_offer_count,
        "has_multiple_offers": has_multiple_offers,
        "accepted_groups": sorted(groups),
        "source_roles": source_roles,
        "primary_layer_detected": bool(layers.get(primary_layer_key, {}).get("detected")),
    }


def _has_divergent_product_offers(accepted: list[dict[str, str]]) -> bool:
    product_offers = [
        item for item in accepted if str(item.get("group") or "") == "product_offer"
    ]
    if len(product_offers) <= 1:
        return False

    families = {
        family
        for item in product_offers
        if (family := product_offer_family_for_text(str(item.get("text") or "")))
    }
    if len(families) > 1:
        return True
    if len(families) == 1:
        return not product_offer_family_allows_multiple_lines(next(iter(families)))
    return True
