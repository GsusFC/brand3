"""Discovery-derived calibration hints.

These hints are informational only. They are not applied to scoring,
calibration_profile, profile_source, prompts, cache keys, or feature extraction.
"""

from __future__ import annotations


def build_discovery_calibration_hint(entity_discovery, discovery_trust_basis=None, niche_classification=None) -> dict:
    entity = _dict(entity_discovery)
    niche = _dict(niche_classification)
    if not entity:
        return _hint(
            "base",
            "missing_entity_discovery",
            0.0,
            ["Entity discovery was unavailable."],
        )

    scope = entity.get("analysis_scope")
    entity_type = entity.get("entity_type")
    if scope == "ecosystem":
        return _hint(
            "ecosystem_or_protocol",
            "entity_discovery.analysis_scope=ecosystem",
            _confidence(entity.get("confidence"), 0.8),
            [],
        )
    if scope == "product_with_parent":
        return _hint(
            "product_with_parent",
            "entity_discovery.analysis_scope=product_with_parent",
            _confidence(entity.get("confidence"), 0.8),
            [],
        )
    if scope == "url_only":
        return _hint(
            "base",
            "url_only discovery scope",
            _confidence(entity.get("confidence"), 0.3),
            ["Audit basis is limited to the provided URL."],
        )
    if entity_type == "company" or scope == "company_brand":
        niche_confidence = _confidence(niche.get("confidence"), 0.0)
        if niche.get("predicted_niche") and niche_confidence >= 0.65:
            return _hint(
                str(niche["predicted_niche"]),
                "company entity uses high-confidence niche classification",
                niche_confidence,
                [],
            )
        if niche.get("predicted_niche"):
            return _hint(
                "base",
                "company entity without high-confidence niche classification",
                _confidence(niche.get("confidence"), _confidence(entity.get("confidence"), 0.5)),
                ["Niche classification confidence is below discovery calibration threshold."],
            )
        return _hint(
            "base",
            "company entity without niche confidence",
            _confidence(entity.get("confidence"), 0.5),
            [],
        )
    return _hint("base", "unhandled_entity_discovery", _confidence(entity.get("confidence"), 0.0), [])


def apply_discovery_calibration_hint(
    *,
    current_profile: str,
    current_profile_source: str,
    discovery_calibration_hint: dict | None,
    discovery_evidence_preview: dict | None = None,
    discovery_enrichment: dict | None = None,
    available_profiles: set[str] | list[str] | None = None,
) -> dict:
    hint = _dict(discovery_calibration_hint)
    evidence = _dict(discovery_evidence_preview)
    enrichment = _dict(discovery_enrichment)
    profiles = set(available_profiles or [])
    reason = _gate_failure_reason(hint, evidence, enrichment, profiles)
    if reason:
        return _decision(current_profile, current_profile_source, current_profile, current_profile_source, False, reason, hint.get("limitations") or [])
    return _decision(str(hint["recommended_profile"]), "discovery", current_profile, current_profile_source, True, "discovery_calibration_gate_passed", [])


def _hint(profile: str, reason: str, confidence: float, limitations: list[str]) -> dict:
    return {
        "recommended_profile": profile,
        "reason": reason,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "should_apply": False,
        "applied": False,
        "current_behavior": "informational_only",
        "limitations": limitations,
    }


def _decision(profile: str, source: str, previous_profile: str, previous_source: str, applied: bool, reason: str, limitations: list[str]) -> dict:
    return {
        "calibration_profile": profile,
        "profile_source": source,
        "applied": applied,
        "previous_calibration_profile": previous_profile,
        "previous_profile_source": previous_source,
        "reason": reason,
        "limitations": limitations,
    }


def _gate_failure_reason(hint: dict, evidence: dict, enrichment: dict, profiles: set[str]) -> str | None:
    recommended = hint.get("recommended_profile")
    if not hint:
        return "missing_discovery_calibration_hint"
    if hint.get("applied"):
        return "hint_already_applied"
    if not recommended:
        return "missing_recommended_profile"
    if _confidence(hint.get("confidence"), 0.0) < 0.75:
        return "low_confidence"
    if not evidence.get("recommended_to_use_for_scoring"):
        return "evidence_not_recommended"
    if not enrichment.get("applied"):
        return "discovery_enrichment_not_applied"
    if hint.get("limitations"):
        return "hint_has_limitations"
    if recommended == "product_with_parent" and recommended not in profiles:
        return "product_with_parent_profile_not_available"
    if recommended not in profiles:
        return "recommended_profile_unavailable"
    return None


def _dict(value) -> dict:
    return value if isinstance(value, dict) else getattr(value, "__dict__", {}) if value is not None else {}


def _confidence(value, fallback: float) -> float:
    try:
        return float(value if value is not None else fallback)
    except (TypeError, ValueError):
        return fallback
