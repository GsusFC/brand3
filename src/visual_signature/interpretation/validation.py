"""Validation rules for Lab-only visual interpretation outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from src.visual_signature.interpretation.models import VisualEvidencePack, VisualInterpretation


@dataclass
class InterpretationValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def validate_visual_interpretation(
    pack: VisualEvidencePack,
    interpretation: VisualInterpretation,
) -> InterpretationValidation:
    errors: list[str] = []
    warnings: list[str] = []

    if not interpretation.brand_name:
        errors.append("brand_name_missing")
    elif interpretation.brand_name != pack.brand_name:
        errors.append("brand_name_mismatch")
    if not interpretation.website_url:
        errors.append("website_url_missing")
    elif interpretation.website_url != pack.website_url:
        errors.append("website_url_mismatch")

    if pack.status == "not_evaluable" or not pack.screenshot_available:
        if interpretation.status != "not_evaluable":
            errors.append("not_evaluable_pack_must_not_return_usable_interpretation")
        if interpretation.confidence != "low":
            errors.append("not_evaluable_pack_must_return_low_confidence")

    if pack.capture_quality in {"blocked", "missing"} and interpretation.status != "not_evaluable":
        errors.append("blocked_or_missing_capture_must_be_not_evaluable")

    if interpretation.status in {"usable", "limited"}:
        if not interpretation.visual_positioning:
            errors.append("usable_interpretation_requires_visual_positioning")
        if not interpretation.evidence_used:
            errors.append("usable_interpretation_requires_evidence")
        if not interpretation.strengths and not interpretation.risks:
            warnings.append("usable_interpretation_has_no_strengths_or_risks")

    allowed_refs = set(pack.evidence_refs)
    for item in interpretation.evidence_used:
        if not item.ref:
            errors.append("evidence_used_ref_missing")
            continue
        if allowed_refs and item.ref not in allowed_refs:
            errors.append(f"unknown_evidence_ref:{item.ref}")
        if not item.observation:
            errors.append(f"evidence_observation_missing:{item.ref}")

    for recommendation in interpretation.recommendations:
        if len(recommendation.split()) < 3:
            warnings.append("recommendation_too_short")

    return InterpretationValidation(valid=not errors, errors=errors, warnings=warnings)
