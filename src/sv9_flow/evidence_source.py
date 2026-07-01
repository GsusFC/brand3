"""Evidence source classification helpers for SV9 Flow."""

from __future__ import annotations

from typing import Any

SOURCE_CLASS_OWNED_COPY = "owned_copy"
SOURCE_CLASS_EXTERNAL_PROOF = "external_proof"
SOURCE_CLASS_DERIVED_STRATEGY = "derived_strategy"
SOURCE_CLASS_ACQUISITION_METADATA = "acquisition_metadata"
SOURCE_CLASS_VISUAL_SIGNAL = "visual_signal"
SOURCE_CLASS_OTHER = "other"

ACQUISITION_NOISE_TERMS = (
    "failed to scrape",
    "insufficient credits",
    "payment required",
    "followers_count",
    "avg_engagement_rate",
    "visual_analysis_error",
    "screenshot failed",
    "heuristic_score_used",
)


def classify_source(
    *,
    ref: str = "",
    source: str,
    evidence_type: str,
    content: str,
) -> str:
    """Classify evidence by authority before block-specific scoring.

    The class is intentionally coarse. It is used to prevent acquisition
    metadata and derived summaries from carrying the same strategic weight as
    primary owned copy or external proof.
    """

    ref_l = str(ref or "").lower()
    source_l = str(source or "").lower()
    type_l = str(evidence_type or "").lower()
    content_l = str(content or "").lower()

    if source_l in {"visual_signature", "visual_acquisition"} or ref_l.startswith(("visual_signature.", "visual_acquisition.")):
        return SOURCE_CLASS_VISUAL_SIGNAL
    if source_l in {"web", "homepage", "home", "about", "website", "owned", "owned_web", "owned_surface"}:
        return SOURCE_CLASS_OWNED_COPY
    if source_l == "entity_research_packet":
        return SOURCE_CLASS_ACQUISITION_METADATA
    if source_l == "report_narrative":
        return SOURCE_CLASS_DERIVED_STRATEGY
    if source_l in {"context", "social", "competitors", "screenshot_capture"}:
        return SOURCE_CLASS_ACQUISITION_METADATA
    if source_l == "legacy_feature":
        if type_l.startswith("vitalidad.") or type_l.startswith("percepcion."):
            return SOURCE_CLASS_EXTERNAL_PROOF
        if type_l.startswith(("coherencia.", "diferenciacion.")):
            return SOURCE_CLASS_DERIVED_STRATEGY
    if "external_candidate" in content_l or "third-party" in content_l or "third party" in content_l:
        return SOURCE_CLASS_EXTERNAL_PROOF
    return SOURCE_CLASS_OTHER


def source_class_for_record(record: Any) -> str:
    metadata = getattr(record, "metadata", None)
    if isinstance(metadata, dict):
        value = str(metadata.get("source_class") or "").strip()
        if value:
            return _normalized_source_class(value)
    return classify_source(
        ref=str(getattr(record, "ref", "") or ""),
        source=str(getattr(record, "source", "") or ""),
        evidence_type=str(getattr(record, "evidence_type", "") or ""),
        content=str(getattr(record, "content", "") or ""),
    )


def is_acquisition_noise(value: Any) -> bool:
    metadata = getattr(value, "metadata", None)
    metadata_text = ""
    if isinstance(metadata, dict):
        metadata_text = " ".join(str(item) for item in metadata.values())
    text = " ".join(
        (
            str(getattr(value, "source", "") or ""),
            str(getattr(value, "evidence_type", "") or ""),
            str(getattr(value, "content", value) or ""),
            metadata_text,
        )
    ).lower()
    return any(term in text for term in ACQUISITION_NOISE_TERMS)


def _normalized_source_class(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"owned_copy", "owned_surface", "audited_surface", "owned", "same_root_surface"}:
        return SOURCE_CLASS_OWNED_COPY
    if normalized in {
        "external_proof",
        "external_third_party",
        "marketplace_listing",
        "trust_security",
        "repository",
        "competitor_comparison",
    }:
        return SOURCE_CLASS_EXTERNAL_PROOF
    if normalized in {"derived_strategy", "report_narrative"}:
        return SOURCE_CLASS_DERIVED_STRATEGY
    if normalized in {
        "acquisition_metadata",
        "related_unresolved",
        "technical_internal",
        "visual_internal_metric",
        "noise",
        "social_metadata",
        "entity_research_packet",
    }:
        return SOURCE_CLASS_ACQUISITION_METADATA
    if normalized in {"visual_signal", "visual_signature", "visual_acquisition"}:
        return SOURCE_CLASS_VISUAL_SIGNAL
    return normalized or SOURCE_CLASS_OTHER
