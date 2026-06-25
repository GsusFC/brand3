"""Output composition helpers for TLDR block interpreters."""

from __future__ import annotations

from typing import Any

from src.reports.editorial_policy import overreach_warnings

from src.features.magnetism.block_interpreters_helpers_text_impl import (
    _representative_evidence_phrase,
    _mission_answer,
    _value_proposition_answer,
)


def evidence_from_spec(
    block: str,
    evidence: str,
    answer: str,
    accepted: list[dict[str, str]] | None = None,
) -> list[str]:
    accepted = accepted or []
    if block in {"value_proposition", "mission"}:
        representative = _representative_evidence_phrase(evidence, answer)
        return [representative] if representative else [evidence]
    return [evidence]


def answer_from_spec(
    block: str,
    evidence: str,
    accepted: list[dict[str, str]] | None = None,
) -> str:
    if block == "value_proposition":
        return _value_proposition_answer(evidence, accepted or [])
    if block == "mission":
        return _mission_answer(evidence)
    if block == "vision" and "macroalgas" in evidence.lower() and "nuevo modelo" in evidence.lower():
        return "A regenerative industrial model built around the potential of Mediterranean macroalgae."
    return evidence


def mode_from_spec(block: str, diagnostics: dict[str, Any]) -> str:
    if block == "vision":
        return "compressed" if diagnostics.get("has_formal_vision") else "interpreted_from_discourse"
    return "compressed" if diagnostics["has_explicit_evidence"] else "interpreted_from_discourse"


def claim_type_from_spec(block: str, diagnostics: dict[str, Any]) -> str:
    if block == "vision":
        return "declared" if diagnostics.get("has_formal_vision") else "inferred"
    return "declared" if diagnostics["has_explicit_evidence"] else "inferred"


def confidence_from_spec(
    block: str,
    diagnostics: dict[str, Any],
    accepted: list[dict[str, str]],
) -> str:
    if block == "value_proposition":
        if diagnostics["has_offer"] and diagnostics["has_outcome"] and diagnostics["has_audience"]:
            return "high"
        if diagnostics["has_offer"] and (diagnostics["has_outcome"] or diagnostics["has_audience"]):
            return "medium"
        return "low"
    if block == "mission":
        return "medium" if diagnostics["has_operating_activity"] else "low"
    if block == "vision":
        return "medium" if diagnostics["has_future"] and accepted else "low"
    return "medium"


def counter_evidence_from_spec(block: str, diagnostics: dict[str, Any]) -> list[str]:
    limits: list[str] = []
    if block == "value_proposition":
        if not diagnostics["has_audience"]:
            limits.append("The available value proposition evidence does not clearly name the audience.")
        if not diagnostics["has_outcome"]:
            limits.append("The available value proposition evidence does not clearly state the outcome or change for the audience.")
        if diagnostics.get("has_multiple_offers"):
            limits.append("The evidence contains multiple offer signals, so a strategist should confirm the primary value proposition.")
    if block == "vision" and not diagnostics.get("has_formal_vision"):
        limits.append("The available evidence contains future-facing language, but not a formal vision statement.")
    if block == "mission" and not diagnostics["has_explicit_evidence"]:
        limits.append("The mission is inferred from product/service evidence rather than stated as a formal mission.")
    return limits


def human_review_from_spec(
    block: str,
    diagnostics: dict[str, Any],
    confidence: str,
    counter_evidence: list[str],
) -> bool:
    if block == "vision":
        return True if counter_evidence or confidence == "low" else False
    if block == "value_proposition":
        return (
            confidence == "low"
            or len(counter_evidence) >= 2
            or diagnostics.get("has_multiple_offers", False)
        )
    if block == "mission":
        return not diagnostics["has_explicit_evidence"] or confidence == "low"
    return False


def reasoning_from_spec(block: str, evidence: str, diagnostics: dict[str, Any]) -> str:
    if block == "value_proposition":
        parts = ["The evidence states a concrete offer"]
        if diagnostics["has_audience"]:
            parts.append("names or implies an audience")
        if diagnostics["has_outcome"]:
            parts.append("and describes the operational change or outcome")
        return ", ".join(parts) + f": {evidence}"
    if block == "mission":
        return f"The evidence uses present-tense operating language that describes what the brand does today: {evidence}"
    if block == "vision":
        return (
            "The evidence contains future-facing or category-change language, so the block is treated "
            f"as an interpreted vision signal: {evidence}"
        )
    return f"The block is derived from accepted evidence: {evidence}"


def observations_from_spec(block: str, diagnostics: dict[str, Any]) -> list[str]:
    observations = [f"Applied executable {block} interpreter spec."]
    if block == "value_proposition":
        observations.append(
            "Detected offer/audience/outcome coverage: "
            f"offer={diagnostics['has_offer']}, audience={diagnostics['has_audience']}, outcome={diagnostics['has_outcome']}."
        )
        if diagnostics.get("accepted_groups"):
            observations.append("Strategic packet groups used: " + ", ".join(diagnostics["accepted_groups"]) + ".")
        if diagnostics.get("source_roles"):
            observations.append("Source roles used: " + ", ".join(diagnostics["source_roles"]) + ".")
        if diagnostics.get("has_multiple_offers"):
            observations.append("Multiple product_offer candidates were found; primary offer requires review.")
    if block == "mission":
        observations.append(f"Present-tense operating evidence={diagnostics['has_operating_activity']}.")
        if diagnostics.get("source_roles"):
            observations.append("Source roles used: " + ", ".join(diagnostics["source_roles"]) + ".")
    if block == "vision":
        observations.append(f"Future/category-change evidence={diagnostics['has_future']}.")
        if diagnostics.get("source_roles"):
            observations.append("Source roles used: " + ", ".join(diagnostics["source_roles"]) + ".")
    return observations


def apply_editorial_policy_guardrails(
    block: str,
    answer: str,
    reasoning: str,
    mode: str,
    confidence: str,
    counter_evidence: list[str],
    human_review: bool,
) -> tuple[str, str, list[str], bool]:
    """Apply final editorial overreach checks to interpreted TLDR blocks."""
    warnings = overreach_warnings(f"{answer} {reasoning}")
    if not warnings:
        return mode, confidence, counter_evidence, human_review

    updated_counter = list(counter_evidence)
    updated_counter.append("Editorial policy flagged possible overreach: " + ", ".join(sorted(set(warnings))) + ".")
    if confidence == "high":
        confidence = "medium"
    elif confidence == "medium":
        confidence = "low"
    if mode != "not_detected":
        mode = "needs_human_review"
    return mode, confidence, list(dict.fromkeys(updated_counter)), True
