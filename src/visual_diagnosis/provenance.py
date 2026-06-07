"""Signal provenance helpers for Visual Diagnosis Lab."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


SignalKind = Literal["antipattern", "positive", "negative", "limitation"]
EvidenceLevel = Literal["observed", "inferred", "conflicting", "weak_evidence"]
ConfidenceLevel = Literal["high", "medium", "low"]


@dataclass
class VisualSignalProvenance:
    signal: str
    kind: SignalKind
    sources: list[str] = field(default_factory=list)
    confidence: ConfidenceLevel = "low"
    evidence_level: EvidenceLevel = "weak_evidence"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_signal_provenance(
    *,
    diagnosis: dict[str, Any],
    source_comparison: list[dict[str, Any]],
    available_source_types: list[str],
) -> list[dict[str, Any]]:
    rows: list[VisualSignalProvenance] = []
    signals = diagnosis.get("signals") if isinstance(diagnosis.get("signals"), dict) else {}
    for kind, values in [
        ("antipattern", signals.get("antipatterns") or []),
        ("positive", signals.get("positive") or []),
        ("negative", signals.get("negative") or []),
        ("limitation", diagnosis.get("limitations") or []),
    ]:
        for signal in values:
            rows.append(
                _provenance_for_signal(
                    signal=str(signal),
                    kind=kind,  # type: ignore[arg-type]
                    source_comparison=source_comparison,
                    available_source_types=available_source_types,
                )
            )
    return [_dedupe_sources(row).to_dict() for row in rows]


def _provenance_for_signal(
    *,
    signal: str,
    kind: SignalKind,
    source_comparison: list[dict[str, Any]],
    available_source_types: list[str],
) -> VisualSignalProvenance:
    matched_sources = _sources_reporting_signal(signal, kind, source_comparison)
    if signal.startswith("viewport_obstruction_"):
        return VisualSignalProvenance(
            signal=signal,
            kind=kind,
            sources=["screenshot_vision"],
            confidence="high",
            evidence_level="observed",
            notes=["viewport obstruction requires screenshot or vision evidence"],
        )
    if signal == "visual_promise_mismatch" or signal == "current Magnetism visual_identity is weak":
        return VisualSignalProvenance(
            signal=signal,
            kind=kind,
            sources=["magnetism"],
            confidence="high",
            evidence_level="observed",
            notes=["derived from Magnetism visual_identity threshold"],
        )
    if signal == "screenshot_missing":
        return VisualSignalProvenance(
            signal=signal,
            kind=kind,
            sources=["screenshot_vision"],
            confidence="high",
            evidence_level="weak_evidence",
            notes=["missing screenshot or vision evidence"],
        )
    if signal == "coherence_breakdown_missing":
        return VisualSignalProvenance(
            signal=signal,
            kind=kind,
            sources=["magnetism"],
            confidence="high",
            evidence_level="weak_evidence",
            notes=["missing Magnetism coherence evidence"],
        )
    if signal in {"card_heavy_composition", "flat_typographic_hierarchy", "template_saas_layout"}:
        sources = matched_sources or _intersection(available_source_types, ["computed_style", "web_payload", "visual_signature"])
        return VisualSignalProvenance(
            signal=signal,
            kind=kind,
            sources=sources,
            confidence=_confidence_for_sources(sources),
            evidence_level="observed" if sources else "weak_evidence",
            notes=["layout or typography signal"],
        )
    if signal == "weak_cta_weight":
        sources = matched_sources or _intersection(available_source_types, ["computed_style", "web_payload"])
        return VisualSignalProvenance(
            signal=signal,
            kind=kind,
            sources=sources,
            confidence="medium" if sources else "low",
            evidence_level="inferred",
            notes=["absence of detectable CTA is an inference, not direct visual proof"],
        )
    if signal in {"generic_ai_aesthetic", "overused_gradient_palette", "low_distinctiveness_hero"}:
        sources = matched_sources or _intersection(available_source_types, ["computed_style", "web_payload", "screenshot_vision"])
        return VisualSignalProvenance(
            signal=signal,
            kind=kind,
            sources=sources,
            confidence="medium" if len(sources) >= 2 else "low",
            evidence_level="inferred",
            notes=["heuristic aesthetic signal"],
        )
    if signal.endswith("_only") or signal.endswith("_missing") or "missing" in signal:
        return VisualSignalProvenance(
            signal=signal,
            kind=kind,
            sources=matched_sources or available_source_types,
            confidence="medium",
            evidence_level="weak_evidence",
            notes=["limitation or missing-evidence marker"],
        )
    if "external_candidate_summary_legacy" in available_source_types:
        matched_sources = [
            source for source in matched_sources if source != "external_candidate_summary_legacy"
        ] or matched_sources
    return VisualSignalProvenance(
        signal=signal,
        kind=kind,
        sources=matched_sources or available_source_types,
        confidence=_confidence_for_sources(matched_sources or available_source_types),
        evidence_level="observed" if matched_sources else "inferred",
        notes=[],
    )


def _sources_reporting_signal(
    signal: str,
    kind: SignalKind,
    source_comparison: list[dict[str, Any]],
) -> list[str]:
    field = {
        "antipattern": "antipatterns",
        "limitation": "limitations",
        "positive": None,
        "negative": None,
    }[kind]
    if field is None:
        return []
    sources = []
    for row in source_comparison:
        values = row.get(field) if isinstance(row, dict) else []
        if signal in (values or []):
            source = str(row.get("source_type") or "")
            if source:
                sources.append(source)
    return _dedupe(sources)


def _confidence_for_sources(sources: list[str]) -> ConfidenceLevel:
    if not sources:
        return "low"
    non_legacy = [source for source in sources if source != "external_candidate_summary_legacy"]
    if not non_legacy:
        return "low"
    if len(set(non_legacy)) >= 2:
        return "high"
    return "medium"


def _intersection(values: list[str], wanted: list[str]) -> list[str]:
    return [item for item in wanted if item in values]


def _dedupe_sources(row: VisualSignalProvenance) -> VisualSignalProvenance:
    row.sources = _dedupe(row.sources)
    if row.sources == ["external_candidate_summary_legacy"]:
        row.confidence = "low"
        row.notes = [*row.notes, "legacy external evidence is low-confidence by policy"]
    return row


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
