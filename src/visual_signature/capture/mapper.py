"""Deterministic lab-only mapper for Brand3 visual diagnosis."""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import unique as _unique
from src.visual_signature.capture.models import (
    VisualDiagnosis,
    VisualDiagnosisCapture,
    VisualDiagnosisRead,
    VisualDiagnosisSignals,
)
from src.visual_signature._internal.diagnosis_heuristics import antipatterns as _antipatterns
from src.visual_signature._internal.diagnosis_heuristics import brand_fit as _brand_fit
from src.visual_signature._internal.diagnosis_heuristics import capture_summary as _capture
from src.visual_signature._internal.diagnosis_heuristics import diagnosis_confidence as _diagnosis_confidence
from src.visual_signature._internal.diagnosis_heuristics import distinctiveness as _distinctiveness
from src.visual_signature._internal.diagnosis_heuristics import evidence_refs as _evidence_refs
from src.visual_signature._internal.diagnosis_heuristics import has_visual_analysis_evidence as _has_visual_analysis_evidence
from src.visual_signature._internal.diagnosis_heuristics import identity_read as _identity_read
from src.visual_signature._internal.diagnosis_heuristics import limitations as _limitations
from src.visual_signature._internal.diagnosis_heuristics import negative_signals as _negative_signals
from src.visual_signature._internal.diagnosis_heuristics import obstruction_state as _obstruction_state
from src.visual_signature._internal.diagnosis_heuristics import positive_signals as _positive_signals
from src.visual_signature._internal.diagnosis_heuristics import polish as _polish
from src.visual_signature._internal.diagnosis_heuristics import reference_profile as _reference_profile
from src.visual_signature._internal.diagnosis_heuristics import template_likeness as _template_likeness


def build_visual_diagnosis(
    *,
    brand_name: str,
    website_url: str,
    screenshot_capture: dict[str, Any] | None = None,
    visual_signature_payload: dict[str, Any] | None = None,
    coherence_breakdown: dict[str, Any] | None = None,
    category_hint: str | None = None,
) -> VisualDiagnosis:
    """Build an explainable visual diagnosis from existing evidence.

    This mapper is intentionally cheap and deterministic. It does not call LLMs,
    does not mutate scoring, and should be treated as lab output only.
    """
    del brand_name, website_url
    payload = visual_signature_payload or {}
    capture = _capture(screenshot_capture, payload)
    evidence_refs = _evidence_refs(screenshot_capture, payload, coherence_breakdown)
    source = str(payload.get("source") or "")
    has_visual_analysis_evidence = _has_visual_analysis_evidence(payload)
    can_diagnose_without_capture = source in {
        "dom_css_visual_lab",
        "external_candidate_summary_legacy",
        "computed_style_visual_lab",
    } and has_visual_analysis_evidence

    if (not capture.available or capture.quality in {"missing", "poor"}) and not can_diagnose_without_capture:
        limitations = _unique([*capture.limitations, "visual_evidence_not_evaluable"])
        return VisualDiagnosis(
            status="unavailable",
            capture=capture,
            diagnosis=VisualDiagnosisRead(
                identity_read="not_evaluable",
                reference_profile="unknown",
                profile_confidence="low",
                distinctiveness="unknown",
                polish="unknown",
                brand_fit="unknown",
                template_likeness="unknown",
            ),
            signals=VisualDiagnosisSignals(
                negative=["visual evidence is unavailable or too weak to diagnose"],
                antipatterns=["capture_not_evaluable"],
            ),
            evidence_refs=evidence_refs,
            confidence="low",
            limitations=limitations,
        )
    if not has_visual_analysis_evidence:
        limitations = _unique([*capture.limitations, "visual_analysis_not_interpretable"])
        return VisualDiagnosis(
            status="unavailable",
            capture=capture,
            diagnosis=VisualDiagnosisRead(
                identity_read="not_evaluable",
                reference_profile="unknown",
                profile_confidence="low",
                distinctiveness="unknown",
                polish="unknown",
                brand_fit="unknown",
                template_likeness="unknown",
            ),
            signals=VisualDiagnosisSignals(
                positive=["screenshot evidence available"] if capture.available else [],
                negative=["visual analysis evidence is unavailable or not interpretable"],
                antipatterns=["visual_analysis_not_interpretable"],
            ),
            evidence_refs=evidence_refs,
            confidence="low",
            limitations=limitations,
        )

    profile, profile_confidence = _reference_profile(payload, category_hint)
    antipatterns = _antipatterns(payload, coherence_breakdown, capture, profile)
    positive = _positive_signals(payload, capture)
    negative = _negative_signals(payload, coherence_breakdown, capture, profile, antipatterns)
    distinctiveness = _distinctiveness(payload, antipatterns)
    polish = _polish(payload)
    template_likeness = _template_likeness(profile, antipatterns)
    brand_fit = _brand_fit(coherence_breakdown, antipatterns)
    identity_read = _identity_read(
        profile=profile,
        distinctiveness=distinctiveness,
        polish=polish,
        template_likeness=template_likeness,
        brand_fit=brand_fit,
        capture=capture,
        antipattern_list=antipatterns,
        allow_without_capture=can_diagnose_without_capture,
    )
    confidence = _diagnosis_confidence(capture, payload, coherence_breakdown, profile_confidence)
    limitations = _limitations(capture, payload, coherence_breakdown)
    status = "limited" if limitations else "usable"

    return VisualDiagnosis(
        status=status,
        capture=capture,
        diagnosis=VisualDiagnosisRead(
            identity_read=identity_read,
            reference_profile=profile,
            profile_confidence=profile_confidence,
            distinctiveness=distinctiveness,
            polish=polish,
            brand_fit=brand_fit,
            template_likeness=template_likeness,
        ),
        signals=VisualDiagnosisSignals(
            positive=_unique(positive),
            negative=_unique(negative),
            antipatterns=_unique(antipatterns),
        ),
        evidence_refs=evidence_refs,
        confidence=confidence,
        limitations=limitations,
    )
