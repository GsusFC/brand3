"""Parallel evidence vNext experiment.

This module is intentionally offline and side-effect free. It adapts the
existing snapshot into a stricter evidence view, then builds a filtered
EvidenceGraph/BrandResearchPack so we can compare it against current outputs
without changing acquisition, scoring, runtime routes, or prompts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from src.reports.brand_research_pack import BrandResearchPack, build_brand_research_pack_from_snapshot
from src.reports.evidence_packet import build_evidence_packet_v0
from src.research.evidence_vnext_acquisition_contracts import (
    AcquisitionContractExclusion,
    AcquisitionContractResult,
    _acquisition_diagnostics_from_snapshot,
    _clean_text,
    apply_evidence_vnext_acquisition_contracts,
)
from src.research.evidence_graph import EvidenceClaim, EvidenceGraph, build_evidence_graph_from_snapshot
from src.research.pack_comparison import FieldComparison
from src.research.research_pack_builder import build_brand_research_pack_from_graph
from src.research.evidence_vnext_semantics import (
    build_evidence_vnext_semantic_assessment as _build_evidence_vnext_semantic_assessment,
)


EVIDENCE_VNEXT_VERSION = "brand3_evidence_vnext_v0_1"

ACCEPTED_ELIGIBILITIES = {"eligible_for_narrative_finding", "observation_only"}
REVIEW_ELIGIBILITIES = {"requires_human_review", "trust_security_review_only"}
REJECTED_ELIGIBILITIES = {"technical_only", "reject_noise", "blocked_empty_text"}
ACCEPTED_SOURCE_CLASSES = {
    "audited_surface",
    "owned_surface",
    "external_third_party",
    "repository",
    "competitor_comparison",
}
REVIEW_SOURCE_CLASSES = {"related_unresolved", "marketplace_listing", "trust_security"}
REJECTED_SOURCE_CLASSES = {"technical_internal", "visual_internal_metric", "noise"}

TEXT_FIELDS = (
    "company_summary",
    "product_summary",
    "audience",
    "offer",
    "outcome",
    "category",
    "declared_purpose",
    "declared_mission",
    "future_direction",
    "tone_of_voice",
)

LIST_FIELDS = (
    "personality_signals",
    "visual_or_conceptual_signals",
    "values_signals",
    "attributes_signals",
    "evidence_gaps",
    "confidence_notes",
)

EVIDENCE_FIELDS = (
    "proof_points",
    "founder_or_press_context",
    "competitive_context",
    "noise_rejected",
)

MATERIAL_FIELDS = {
    "company_summary",
    "product_summary",
    "audience",
    "offer",
    "outcome",
    "declared_purpose",
    "declared_mission",
    "future_direction",
    "proof_points",
    "founder_or_press_context",
    "competitive_context",
}

INTERNAL_ANALYSIS_FEATURES = {
    "content_authenticity",
    "brand_personality",
}
INTERNAL_ANALYSIS_PROVIDERS = {
    "content_analysis",
}


@dataclass(frozen=True, slots=True)
class SourceObservation:
    """One normalized source/evidence observation for the vNext gate."""

    observation_id: str
    text: str
    url: str
    dimension: str
    provider: str
    feature_name: str
    source_class: str
    eligibility: str
    gate_status: str
    classification_reason: str = ""
    limits: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "observation_id": self.observation_id,
            "text": self.text,
            "url": self.url,
            "dimension": self.dimension,
            "provider": self.provider,
            "feature_name": self.feature_name,
            "source_class": self.source_class,
            "eligibility": self.eligibility,
            "gate_status": self.gate_status,
            "classification_reason": self.classification_reason,
            "limits": self.limits,
        }


@dataclass(frozen=True, slots=True)
class EvidenceVNextPacket:
    """Gate result used to build and compare vNext outputs."""

    version: str
    run_id: int | None
    brand_name: str
    url: str
    observations: tuple[SourceObservation, ...]
    legacy_packet_summary: dict[str, Any] = field(default_factory=dict)

    @property
    def accepted(self) -> tuple[SourceObservation, ...]:
        return tuple(item for item in self.observations if item.gate_status == "accepted")

    @property
    def review_required(self) -> tuple[SourceObservation, ...]:
        return tuple(item for item in self.observations if item.gate_status == "review_required")

    @property
    def rejected(self) -> tuple[SourceObservation, ...]:
        return tuple(item for item in self.observations if item.gate_status == "rejected")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "runtime_effect": False,
            "prompt_effect": False,
            "run_id": self.run_id,
            "brand_name": self.brand_name,
            "url": self.url,
            "observations": [item.to_dict() for item in self.observations],
            "accepted": [item.to_dict() for item in self.accepted],
            "review_required": [item.to_dict() for item in self.review_required],
            "rejected": [item.to_dict() for item in self.rejected],
            "summary": self.summary(),
            "legacy_packet_summary": dict(self.legacy_packet_summary),
        }

    def summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        source_class_counts: dict[str, int] = {}
        eligibility_counts: dict[str, int] = {}
        review_reason_counts: dict[str, int] = {}
        rejected_reason_counts: dict[str, int] = {}
        for item in self.observations:
            status_counts[item.gate_status] = status_counts.get(item.gate_status, 0) + 1
            source_class_counts[item.source_class] = source_class_counts.get(item.source_class, 0) + 1
            eligibility_counts[item.eligibility] = eligibility_counts.get(item.eligibility, 0) + 1
            if item.gate_status == "review_required":
                reason = _observation_reason(item)
                review_reason_counts[reason] = review_reason_counts.get(reason, 0) + 1
            elif item.gate_status == "rejected":
                reason = _observation_reason(item)
                rejected_reason_counts[reason] = rejected_reason_counts.get(reason, 0) + 1
        return {
            "observation_count": len(self.observations),
            "accepted_count": len(self.accepted),
            "review_required_count": len(self.review_required),
            "rejected_count": len(self.rejected),
            "status_counts": dict(sorted(status_counts.items())),
            "source_class_counts": dict(sorted(source_class_counts.items())),
            "eligibility_counts": dict(sorted(eligibility_counts.items())),
            "review_reason_counts": dict(sorted(review_reason_counts.items())),
            "rejected_reason_counts": dict(sorted(rejected_reason_counts.items())),
        }


@dataclass(frozen=True, slots=True)
class EvidenceVNextComparison:
    """Comparison of legacy/current graph/vNext outputs for one snapshot."""

    run_id: int | None
    brand_name: str
    url: str
    current_graph_summary: dict[str, Any]
    vnext_graph_summary: dict[str, Any]
    gate_summary: dict[str, Any]
    reclassified_to_noise_count: int
    fields: tuple[FieldComparison, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "brand_name": self.brand_name,
            "url": self.url,
            "current_graph_summary": dict(self.current_graph_summary),
            "vnext_graph_summary": dict(self.vnext_graph_summary),
            "gate_summary": dict(self.gate_summary),
            "reclassified_to_noise_count": self.reclassified_to_noise_count,
            "fields": [item.to_dict() for item in self.fields],
            "summary": self.summary(),
        }

    def summary(self) -> dict[str, Any]:
        gained = [item.field for item in self.fields if item.legacy_empty and not item.graph_empty]
        lost = [item.field for item in self.fields if not item.legacy_empty and item.graph_empty]
        changed = [item.field for item in self.fields if item.changed]
        material_lost = [
            item.field
            for item in self.fields
            if not item.legacy_empty
            and item.graph_empty
            and item.field in MATERIAL_FIELDS
            and not _preview_looks_nonmaterial(item.legacy_preview)
        ]
        non_material_lost = [field for field in lost if field not in material_lost]
        review_count = int(self.gate_summary.get("review_required_count") or 0)
        rejected_count = int(self.gate_summary.get("rejected_count") or 0)
        scorecard = _scorecard_status(
            material_lost=material_lost,
            non_material_lost=non_material_lost,
            review_count=review_count,
            rejected_count=rejected_count,
        )
        return {
            "gained_fields": gained,
            "lost_fields": lost,
            "material_lost_fields": material_lost,
            "non_material_lost_fields": non_material_lost,
            "changed_fields": changed,
            "gained_count": len(gained),
            "lost_count": len(lost),
            "material_lost_count": len(material_lost),
            "non_material_lost_count": len(non_material_lost),
            "changed_count": len(changed),
            "claim_delta": int(self.vnext_graph_summary.get("claim_count") or 0)
            - int(self.current_graph_summary.get("claim_count") or 0),
            "noise_delta": int(self.vnext_graph_summary.get("noise_claim_count") or 0)
            - int(self.current_graph_summary.get("noise_claim_count") or 0),
            "reclassified_to_noise_count": self.reclassified_to_noise_count,
            "scorecard": scorecard,
        }


def build_evidence_vnext_packet_from_snapshot(snapshot: dict[str, Any]) -> EvidenceVNextPacket:
    """Build the offline vNext gate packet from the existing snapshot."""

    packet = build_evidence_packet_v0(snapshot)
    observations = _observations_from_packet(packet, snapshot=snapshot)
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    return EvidenceVNextPacket(
        version=EVIDENCE_VNEXT_VERSION,
        run_id=_optional_int(run.get("id")),
        brand_name=str(run.get("brand_name") or ""),
        url=str(run.get("url") or ""),
        observations=tuple(observations),
        legacy_packet_summary={
            "case_id": packet.get("case_id") or "",
            "counts": (packet.get("metadata") or {}).get("counts") or {},
            "dimension_readiness": packet.get("dimension_readiness") or {},
        },
    )


def build_vnext_evidence_graph_from_snapshot(snapshot: dict[str, Any]) -> EvidenceGraph:
    """Build an EvidenceGraph filtered by the vNext evidence gate."""

    base_graph = build_evidence_graph_from_snapshot(snapshot)
    gate = build_evidence_vnext_packet_from_snapshot(snapshot)
    filtered_claims = _filter_claims(base_graph.claims, gate)
    return EvidenceGraph(
        version=f"{base_graph.version}+evidence_vnext",
        run=base_graph.run,
        sources=base_graph.sources,
        claims=filtered_claims,
        gaps=_unique(list(base_graph.gaps) + _vnext_gaps(gate, filtered_claims)),
        warnings=_unique(list(base_graph.warnings) + _vnext_warnings(gate)),
        shadow_sources=base_graph.shadow_sources,
        dedupe_stats={
            **dict(base_graph.dedupe_stats),
            "vnext_input_claim_count": len(base_graph.claims),
            "vnext_filtered_claim_count": len(filtered_claims),
            "vnext_removed_claim_count": len(base_graph.claims) - len(filtered_claims),
        },
    )


def build_vnext_brand_research_pack_from_snapshot(snapshot: dict[str, Any]) -> BrandResearchPack:
    """Build a BrandResearchPack from the vNext filtered graph."""

    return build_brand_research_pack_from_graph(build_vnext_evidence_graph_from_snapshot(snapshot))


def build_evidence_vnext_semantic_assessment(packet: EvidenceVNextPacket) -> dict[str, Any]:
    return _build_evidence_vnext_semantic_assessment(packet)


def compare_evidence_vnext_from_snapshot(snapshot: dict[str, Any]) -> EvidenceVNextComparison:
    """Compare current graph-backed pack against vNext filtered pack."""

    current_graph = build_evidence_graph_from_snapshot(snapshot)
    current_pack = build_brand_research_pack_from_graph(current_graph).to_dict()
    vnext_graph = build_vnext_evidence_graph_from_snapshot(snapshot)
    vnext_pack = build_brand_research_pack_from_graph(vnext_graph).to_dict()
    gate = build_evidence_vnext_packet_from_snapshot(snapshot)
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    fields = tuple(
        _compare_field(field, current_pack.get(field), vnext_pack.get(field))
        for field in (*TEXT_FIELDS, *LIST_FIELDS, *EVIDENCE_FIELDS)
    )
    return EvidenceVNextComparison(
        run_id=_optional_int(run.get("id")),
        brand_name=str(run.get("brand_name") or ""),
        url=str(run.get("url") or ""),
        current_graph_summary=current_graph.summary(),
        vnext_graph_summary=vnext_graph.summary(),
        gate_summary=gate.summary(),
        reclassified_to_noise_count=_reclassified_to_noise_count(vnext_graph.claims),
        fields=fields,
    )


def compare_legacy_current_and_vnext_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return all three pack payloads for lab inspection."""

    acquisition_contracts = apply_evidence_vnext_acquisition_contracts(snapshot)
    acquisition_diagnostics = _acquisition_diagnostics_from_snapshot(snapshot)
    legacy = build_brand_research_pack_from_snapshot(snapshot)
    current_graph = build_evidence_graph_from_snapshot(snapshot)
    current = build_brand_research_pack_from_graph(current_graph)
    vnext_graph = build_vnext_evidence_graph_from_snapshot(snapshot)
    vnext = build_brand_research_pack_from_graph(vnext_graph)
    gate = build_evidence_vnext_packet_from_snapshot(snapshot)
    semantic = build_evidence_vnext_semantic_assessment(gate)
    semantic_llm = _maybe_build_llm_semantic_assessment(gate)
    return {
        "runtime_effect": False,
        "prompt_effect": False,
        "model_effect": False,
        "legacy_pack": legacy.to_dict(),
        "current_graph_pack": current.to_dict(),
        "vnext_pack": vnext.to_dict(),
        "current_graph": current_graph.to_dict(),
        "vnext_graph": vnext_graph.to_dict(),
        "vnext_gate": gate.to_dict(),
        "vnext_semantic_assessment": semantic,
        "vnext_semantic_llm_assessment": semantic_llm,
        "vnext_acquisition_contracts": acquisition_contracts.to_dict(),
        "vnext_acquisition_diagnostics": acquisition_diagnostics,
        "vnext_comparison": compare_evidence_vnext_from_snapshot(snapshot).to_dict(),
    }


def _maybe_build_llm_semantic_assessment(gate: EvidenceVNextPacket) -> dict[str, Any]:
    try:
        from src.research.evidence_semantic_llm import build_llm_semantic_assessment

        return build_llm_semantic_assessment(gate)
    except Exception as exc:
        return {
            "version": "evidence_vnext_llm_semantic_assessment_v0_1",
            "runtime_effect": False,
            "prompt_effect": False,
            "model_effect": False,
            "classifier": "llm_shadow_v0",
            "status": "error",
            "reason": "llm_classifier_exception",
            "detail": str(exc)[:200],
            "assessments": [],
            "summary": {
                "assessment_count": 0,
                "accepted_count": len(gate.accepted),
                "accepted_material_count": 0,
                "accepted_weak_count": 0,
                "accepted_material_rate": 0.0,
                "accepted_weak_rate": 0.0,
                "semantic_class_counts": {},
                "materiality_counts": {},
                "entity_fit_counts": {},
            },
        }


def _observations_from_packet(packet: dict[str, Any], *, snapshot: dict[str, Any]) -> list[SourceObservation]:
    observations: list[SourceObservation] = []
    seen: set[tuple[str, str, str, str]] = set()
    dimension_inputs = packet.get("dimension_evidence_inputs") if isinstance(packet.get("dimension_evidence_inputs"), dict) else {}
    url_hints = _dimension_url_hints(dimension_inputs)
    text_url_hints = _snapshot_text_url_hints(snapshot)
    audit_root = _root_domain(_host(str(packet.get("audit_url") or "")))
    for dimension, items in dimension_inputs.items():
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            text = _clean_text(item.get("text"))
            url = str(item.get("url") or "").strip()
            source_class = str(item.get("source_class") or "")
            eligibility = str(item.get("eligibility") or "")
            classification_reason = str(item.get("classification_reason") or "")
            limits = str(item.get("limits") or "")
            if _is_internal_analysis_observation(item):
                source_class = "visual_internal_metric"
                eligibility = "technical_only"
                classification_reason = "internal_analysis_not_market_evidence"
            source_class, eligibility, classification_reason = _correct_exa_visual_false_positive(
                url=url,
                text=text,
                audit_root=audit_root,
                provider=str(item.get("feature_source") or ""),
                source_class=source_class,
                eligibility=eligibility,
                classification_reason=classification_reason,
            )
            if not url and text and classification_reason in {"missing_evidence_url", "owned_claim_without_url"}:
                inferred_url = url_hints.get(_dimension_group_key(str(dimension or ""), item))
                if inferred_url:
                    url = inferred_url
                    source_class, eligibility, classification_reason = _apply_inferred_url(
                        url=url,
                        audit_root=audit_root,
                        source_class=source_class,
                        eligibility=eligibility,
                        classification_reason=classification_reason,
                        reason="evidence_url_inferred_from_same_feature",
                    )
                    limits = _append_limit(limits, "URL inferred by evidence vNext from same feature evidence_url.")
            if not url and text and classification_reason in {"missing_evidence_url", "owned_claim_without_url"}:
                inferred_url = _infer_url_for_text(text, text_url_hints, audit_root=audit_root)
                if inferred_url:
                    url = inferred_url
                    source_class, eligibility, classification_reason = _apply_inferred_url(
                        url=url,
                        audit_root=audit_root,
                        source_class=source_class,
                        eligibility=eligibility,
                        classification_reason=classification_reason,
                        reason="evidence_url_inferred_from_raw_source_text",
                    )
                    limits = _append_limit(limits, "URL inferred by evidence vNext from raw source text match.")
            key = (str(dimension), text.lower(), url.lower(), eligibility)
            if key in seen:
                continue
            seen.add(key)
            observations.append(
                SourceObservation(
                    observation_id=f"obs_{len(observations) + 1:04d}",
                    text=text,
                    url=url,
                    dimension=str(dimension or ""),
                    provider=str(item.get("feature_source") or ""),
                    feature_name=str(item.get("feature_name") or ""),
                    source_class=source_class,
                    eligibility=eligibility,
                    gate_status=_gate_status(source_class=source_class, eligibility=eligibility, text=text),
                    classification_reason=classification_reason,
                    limits=limits,
                )
            )
    return _apply_covered_by_accepted_source(observations, audit_root=audit_root)


def _apply_covered_by_accepted_source(
    observations: list[SourceObservation],
    *,
    audit_root: str,
) -> list[SourceObservation]:
    accepted = [item for item in observations if item.gate_status == "accepted" and item.url and item.text]
    if not accepted:
        return observations
    covered: list[SourceObservation] = []
    for item in observations:
        if item.gate_status != "review_required" or item.classification_reason != "missing_evidence_url" or item.url:
            covered.append(item)
            continue
        covered_url = _covered_by_accepted_source_url(item.text, accepted)
        if not covered_url:
            covered.append(item)
            continue
        source_class, eligibility, classification_reason = _apply_inferred_url(
            url=covered_url,
            audit_root=audit_root,
            source_class=item.source_class,
            eligibility=item.eligibility,
            classification_reason=item.classification_reason,
            reason="covered_by_accepted_source",
        )
        limits = _append_limit(item.limits, "URL covered by accepted same-root evidence in evidence vNext.")
        covered.append(
            SourceObservation(
                observation_id=item.observation_id,
                text=item.text,
                url=covered_url,
                dimension=item.dimension,
                provider=item.provider,
                feature_name=item.feature_name,
                source_class=source_class,
                eligibility=eligibility,
                gate_status=_gate_status(source_class=source_class, eligibility=eligibility, text=item.text),
                classification_reason=classification_reason,
                limits=limits,
            )
        )
    return covered


def _covered_by_accepted_source_url(text: str, accepted: list[SourceObservation]) -> str:
    fragments = _coverage_fragments(text)
    if not fragments:
        return ""
    urls_by_fragment: list[set[str]] = []
    for fragment in fragments:
        urls = {
            item.url
            for item in accepted
            if _coverage_fragment_matches_accepted(fragment, item.text)
        }
        if not urls:
            return ""
        urls_by_fragment.append(urls)
    intersection = set.intersection(*urls_by_fragment)
    if intersection:
        return _choose_inferred_url(intersection)
    return _choose_inferred_url(set().union(*urls_by_fragment))


def _coverage_fragment_matches_accepted(fragment: str, accepted_text: str) -> bool:
    accepted = _source_match_text(accepted_text)
    if not fragment or not accepted:
        return False
    return fragment in accepted or accepted in fragment


def _coverage_fragments(text: str) -> list[str]:
    normalized = _source_match_text(text)
    if len(normalized) < 20:
        return []
    sentence_fragments = [
        _source_match_text(part)
        for part in re.split(r"(?<=[.!?])\s+|\s+-\s+|\s+--\s+", normalized)
    ]
    fragments = [fragment for fragment in sentence_fragments if len(fragment) >= 24 and len(fragment.split()) >= 4]
    if len(fragments) >= 2:
        return _unique(fragments)
    return [normalized]


def _is_internal_analysis_observation(item: dict[str, Any]) -> bool:
    feature_name = str(item.get("feature_name") or "").lower()
    provider = str(item.get("feature_source") or "").lower()
    return feature_name in INTERNAL_ANALYSIS_FEATURES or provider in INTERNAL_ANALYSIS_PROVIDERS


def _correct_exa_visual_false_positive(
    *,
    url: str,
    text: str,
    audit_root: str,
    provider: str,
    source_class: str,
    eligibility: str,
    classification_reason: str,
) -> tuple[str, str, str]:
    if provider.lower() != "exa":
        return source_class, eligibility, classification_reason
    if source_class != "visual_internal_metric" or classification_reason != "visual_or_internal_analysis_not_market_evidence":
        return source_class, eligibility, classification_reason
    if not url or not text.strip():
        return source_class, eligibility, classification_reason
    corrected_source_class = _source_class_for_inferred_url(url, audit_root=audit_root, fallback="external_third_party")
    if corrected_source_class in {"audited_surface", "owned_surface"}:
        return corrected_source_class, "observation_only", "exa_external_product_evidence_not_internal_visual_analysis"
    return "external_third_party", "eligible_for_narrative_finding", "exa_external_product_evidence_not_internal_visual_analysis"


def _dimension_url_hints(dimension_inputs: dict[str, Any]) -> dict[tuple[str, str, str], str]:
    urls_by_group: dict[tuple[str, str, str], set[str]] = {}
    for dimension, items in dimension_inputs.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            key = _dimension_group_key(str(dimension or ""), item)
            urls_by_group.setdefault(key, set()).add(url)
    return {key: next(iter(urls)) for key, urls in urls_by_group.items() if len(urls) == 1}


def _dimension_group_key(dimension: str, item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(dimension or ""),
        str(item.get("feature_name") or ""),
        str(item.get("feature_source") or ""),
    )


def _source_class_for_inferred_url(url: str, *, audit_root: str, fallback: str) -> str:
    host = _host(url)
    root = _root_domain(host)
    if not host:
        return fallback
    if audit_root and root == audit_root:
        return fallback if fallback in {"audited_surface", "owned_surface"} else "owned_surface"
    return "external_third_party"


def _apply_inferred_url(
    *,
    url: str,
    audit_root: str,
    source_class: str,
    eligibility: str,
    classification_reason: str,
    reason: str,
) -> tuple[str, str, str]:
    inferred_source_class = _source_class_for_inferred_url(url, audit_root=audit_root, fallback=source_class)
    if inferred_source_class == "external_third_party" and eligibility in {"requires_human_review", "observation_only"}:
        return inferred_source_class, "eligible_for_narrative_finding", reason
    if inferred_source_class in {"audited_surface", "owned_surface"} and eligibility == "requires_human_review":
        return inferred_source_class, "observation_only", reason
    if classification_reason == "owned_claim_without_url":
        return inferred_source_class, eligibility, reason
    return inferred_source_class, eligibility, classification_reason


def _snapshot_text_url_hints(snapshot: dict[str, Any]) -> list[tuple[str, str, str]]:
    hints: list[tuple[str, str, str]] = []
    for item in snapshot.get("raw_inputs") or []:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "")
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        if source in {"web", "hyperbrowser"}:
            text = _clean_text(
                payload.get("markdown_content")
                or payload.get("content")
                or payload.get("text")
                or ""
            )
            url = str(payload.get("source_url") or payload.get("url") or payload.get("final_url") or "").strip()
            if text and url:
                hints.append((text.lower(), url, source))
        elif source == "exa":
            for collection in ("mentions", "news", "ai_visibility_results", "competitors"):
                entries = payload.get(collection)
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    url = str(entry.get("url") or "").strip()
                    text = _clean_text(
                        " ".join(
                            str(part or "")
                            for part in (
                                entry.get("title"),
                                entry.get("summary"),
                                entry.get("text"),
                                " ".join(str(value) for value in (entry.get("highlights") or [])),
                            )
                        )
                    )
                    if text and url:
                        hints.append((text.lower(), url, f"exa.{collection}"))
    return hints


def _infer_url_for_text(text: str, hints: list[tuple[str, str, str]], *, audit_root: str = "") -> str:
    needle = _source_match_text(text)
    if len(needle) < 20:
        return ""
    inferred = _infer_url_from_audited_source_windows(needle, hints, audit_root=audit_root)
    if inferred:
        return inferred
    matches = {url for haystack, url, _source in hints if needle in _source_match_text(haystack)}
    inferred = _choose_inferred_url(matches)
    if inferred:
        return inferred
    fragment_matches = [
        {url for haystack, url, _source in hints if fragment in _source_match_text(haystack)}
        for fragment in _source_match_fragments(needle)
    ]
    if len(fragment_matches) >= 2 and all(fragment_matches):
        inferred = _choose_inferred_url(set.intersection(*fragment_matches))
        if inferred:
            return inferred
        inferred = _choose_inferred_url(set().union(*fragment_matches))
        if inferred:
            return inferred
    return ""


def _infer_url_from_audited_source_windows(
    needle: str,
    hints: list[tuple[str, str, str]],
    *,
    audit_root: str,
) -> str:
    if not audit_root:
        return ""
    audited_hints = [
        (haystack, url)
        for haystack, url, source in hints
        if source in {"web", "hyperbrowser"} and _root_domain(_host(url)) == audit_root
    ]
    if not audited_hints:
        return ""
    exact_matches = {url for haystack, url in audited_hints if needle in _source_match_text(haystack)}
    inferred = _choose_inferred_url(exact_matches)
    if inferred:
        return inferred

    urls_by_window: list[set[str]] = []
    for window in _source_match_word_windows(needle):
        urls = {url for haystack, url in audited_hints if window in _source_match_text(haystack)}
        if urls:
            urls_by_window.append(urls)
    words = needle.split()
    if len(words) <= 6 and urls_by_window:
        return _choose_inferred_url(set().union(*urls_by_window))
    if len(urls_by_window) < 2:
        return ""
    intersection = set.intersection(*urls_by_window)
    if intersection:
        return _choose_inferred_url(intersection)
    return _choose_inferred_url(set().union(*urls_by_window))


def _source_match_word_windows(text: str) -> list[str]:
    words = _source_match_text(text).split()
    if len(words) < 5:
        return []
    if len(words) <= 6:
        window = " ".join(words)
        return [window] if len(window) >= 20 else []
    windows: list[str] = []
    for size in (9, 7, 5):
        if len(words) < size:
            continue
        for index in range(0, len(words) - size + 1):
            window = " ".join(words[index : index + size])
            if len(window) >= 24:
                windows.append(window)
    return _unique(windows)


def _choose_inferred_url(urls: set[str]) -> str:
    cleaned = {str(url or "").strip() for url in urls if str(url or "").strip()}
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return next(iter(cleaned))
    roots = {_root_domain(_host(url)) for url in cleaned}
    if len(roots) == 1 and next(iter(roots)):
        return sorted(cleaned, key=lambda url: (len(urlparse(url).path or ""), len(url), url))[0]
    return ""


def _source_match_text(value: Any) -> str:
    text = _clean_text(value).lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[*_`>#\[\]{}()]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _source_match_fragments(text: str) -> list[str]:
    fragments: list[str] = []
    for part in re.split(r"[,;|/]+", str(text or "")):
        fragment = _source_match_text(part)
        if len(fragment) < 16 or len(fragment.split()) < 2:
            continue
        fragments.append(fragment)
    return _unique(fragments)


def _gate_status(*, source_class: str, eligibility: str, text: str) -> str:
    if eligibility in REVIEW_ELIGIBILITIES or source_class in REVIEW_SOURCE_CLASSES:
        return "review_required"
    if eligibility in REJECTED_ELIGIBILITIES or source_class in REJECTED_SOURCE_CLASSES:
        return "rejected"
    if eligibility in ACCEPTED_ELIGIBILITIES and source_class in ACCEPTED_SOURCE_CLASSES and text.strip():
        return "accepted"
    if not text.strip():
        return "rejected"
    return "review_required"


def _observation_reason(item: SourceObservation) -> str:
    reason = item.classification_reason.strip()
    if reason:
        return reason
    if item.eligibility:
        return item.eligibility
    if item.source_class:
        return item.source_class
    return "unknown"


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _filter_claims(claims: list[EvidenceClaim], gate: EvidenceVNextPacket) -> list[EvidenceClaim]:
    accepted_url_keys = {_url_key(item.url) for item in gate.accepted if item.url}
    unresolved_profile_url_keys = {
        _url_key(item.url)
        for item in gate.review_required
        if item.url and item.classification_reason == "same_name_external_profile_not_alias"
    }
    review_or_rejected_url_keys = {
        _url_key(item.url)
        for item in (*gate.review_required, *gate.rejected)
        if item.url
    }
    accepted_text_keys = {_text_key(item.text) for item in gate.accepted if item.text}
    accepted_url_by_text_key = {
        _text_key(item.text): item.url
        for item in gate.accepted
        if item.text and item.url
    }
    review_or_rejected_text_keys = {
        _text_key(item.text)
        for item in (*gate.review_required, *gate.rejected)
        if item.text
    }
    filtered: list[EvidenceClaim] = []
    for claim in claims:
        claim = _claim_with_inferred_url(claim, accepted_url_by_text_key)
        if _claim_rejected_by_gate(
            claim,
            accepted_url_keys=accepted_url_keys,
            unresolved_profile_url_keys=unresolved_profile_url_keys,
            review_or_rejected_url_keys=review_or_rejected_url_keys,
            accepted_text_keys=accepted_text_keys,
            review_or_rejected_text_keys=review_or_rejected_text_keys,
        ):
            filtered.append(
                EvidenceClaim(
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type="noise",
                    quote=claim.quote,
                    source_id=claim.source_id,
                    source_url=claim.source_url,
                    source_type="noise",
                    surface_role=claim.surface_role,
                    entity_scope=claim.entity_scope,
                    confidence="low",
                    noise_reason=claim.noise_reason or _claim_noise_reason(claim, unresolved_profile_url_keys),
                    notes=_unique(
                        list(claim.notes)
                        + [_claim_noise_note(claim, unresolved_profile_url_keys)]
                    ),
                )
            )
            continue
        filtered.append(claim)
    return filtered


def _claim_with_inferred_url(claim: EvidenceClaim, accepted_url_by_text_key: dict[str, str]) -> EvidenceClaim:
    if claim.source_url:
        return claim
    inferred_url = accepted_url_by_text_key.get(_text_key(claim.text or claim.quote))
    if not inferred_url:
        return claim
    return EvidenceClaim(
        claim_id=claim.claim_id,
        text=claim.text,
        claim_type=claim.claim_type,
        quote=claim.quote,
        source_id=claim.source_id,
        source_url=inferred_url,
        source_type=claim.source_type,
        surface_role=claim.surface_role,
        entity_scope=claim.entity_scope,
        confidence=claim.confidence,
        freshness_days=claim.freshness_days,
        supports_blocks=list(claim.supports_blocks),
        contradicts=list(claim.contradicts),
        secondary_source_ids=list(claim.secondary_source_ids),
        secondary_source_urls=list(claim.secondary_source_urls),
        secondary_origins=list(claim.secondary_origins),
        noise_reason=claim.noise_reason,
        notes=_unique(list(claim.notes) + ["Source URL inferred by evidence vNext from same feature evidence_url."]),
    )


def _reclassified_to_noise_count(claims: list[EvidenceClaim]) -> int:
    return sum(
        1
        for claim in claims
        if claim.claim_type == "noise"
        and any("Rejected by evidence vNext gate." == note for note in claim.notes)
    )


def _scorecard_status(
    *,
    material_lost: list[str],
    non_material_lost: list[str],
    review_count: int,
    rejected_count: int,
) -> dict[str, Any]:
    reason_codes: list[str] = []
    if material_lost:
        reason_codes.append("material_fields_lost")
    if non_material_lost:
        reason_codes.append("non_material_fields_lost")
    if review_count:
        reason_codes.append("review_required_evidence_present")
    if rejected_count:
        reason_codes.append("rejected_evidence_present")

    if material_lost:
        status = "blocked"
    elif non_material_lost or review_count:
        status = "review_required"
    else:
        status = "promising"

    return {
        "status": status,
        "reason_codes": reason_codes or ["no_material_regressions_detected"],
        "material_lost_fields": list(material_lost),
        "non_material_lost_fields": list(non_material_lost),
    }


def _preview_looks_nonmaterial(value: str) -> bool:
    low = str(value or "").lower()
    return any(
        marker in low
        for marker in (
            "robots.txt",
            "sitemap.xml",
            "local image analysis",
            "whitespace ratio",
            "dominant color",
            "contrast signal",
            "schema.org",
            "key pages found",
        )
    )


def _claim_rejected_by_gate(
    claim: EvidenceClaim,
    *,
    accepted_url_keys: set[str],
    unresolved_profile_url_keys: set[str],
    review_or_rejected_url_keys: set[str],
    accepted_text_keys: set[str],
    review_or_rejected_text_keys: set[str],
) -> bool:
    if claim.claim_type == "noise" or claim.source_type == "noise":
        return False
    claim_url_key = _url_key(claim.source_url)
    claim_text_key = _text_key(claim.text or claim.quote)

    if claim.source_type.startswith("owned_") and claim.claim_type != "feature_evidence":
        return False
    if claim.claim_type == "feature_evidence" and not claim.source_url:
        return True
    if claim_url_key and claim_url_key in unresolved_profile_url_keys:
        return True
    if claim_url_key and claim_url_key in accepted_url_keys:
        return False
    if claim_text_key and claim_text_key in accepted_text_keys:
        return False
    if claim_url_key and claim_url_key in review_or_rejected_url_keys:
        return True
    if claim_text_key and claim_text_key in review_or_rejected_text_keys:
        return True
    if claim.source_type in {"unknown", "third_party_context", "third_party_review", "press_founder"}:
        return claim.claim_type in {"unknown", "feature_evidence"} and not claim.source_url
    return False


def _claim_noise_reason(claim: EvidenceClaim, unresolved_profile_url_keys: set[str]) -> str:
    if _url_key(claim.source_url) in unresolved_profile_url_keys:
        return "unresolved_external_profile_source"
    return "evidence_vnext_gate_rejected"


def _claim_noise_note(claim: EvidenceClaim, unresolved_profile_url_keys: set[str]) -> str:
    if _url_key(claim.source_url) in unresolved_profile_url_keys:
        return "Quarantined by evidence vNext because source URL is an unresolved same-name external profile."
    return "Rejected by evidence vNext gate."


def _vnext_gaps(gate: EvidenceVNextPacket, claims: list[EvidenceClaim]) -> list[str]:
    gaps: list[str] = []
    if gate.review_required:
        gaps.append("Evidence vNext found review-required evidence; excluded from vNext interpretation.")
    if gate.rejected and not any(claim.claim_type != "noise" for claim in claims):
        gaps.append("Evidence vNext rejected all interpretation candidates.")
    return gaps


def _vnext_warnings(gate: EvidenceVNextPacket) -> list[str]:
    warnings: list[str] = []
    if gate.review_required:
        warnings.append("evidence_vnext_review_required")
    if gate.rejected:
        warnings.append("evidence_vnext_rejected_candidates")
    return warnings


def _compare_field(field: str, current_value: Any, vnext_value: Any) -> FieldComparison:
    current_normalized = _normalize_value(current_value)
    vnext_normalized = _normalize_value(vnext_value)
    return FieldComparison(
        field=field,
        legacy_empty=not bool(current_normalized),
        graph_empty=not bool(vnext_normalized),
        changed=current_normalized != vnext_normalized,
        legacy_preview=_preview(current_value),
        graph_preview=_preview(vnext_value),
    )


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split()).strip()
    if isinstance(value, list):
        return "\n".join(_normalize_value(item) for item in value if _normalize_value(item))
    if isinstance(value, dict):
        return " ".join(str(value.get(key) or "") for key in sorted(value))
    return str(value).strip()


def _preview(value: Any, limit: int = 180) -> str:
    if isinstance(value, list):
        parts = []
        for item in value[:3]:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("source_url") or item)[:80])
            else:
                parts.append(str(item)[:80])
        text = " | ".join(parts)
    elif isinstance(value, dict):
        text = str(value)
    else:
        text = str(value or "")
    return " ".join(text.split())[:limit]


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _append_limit(existing: str, addition: str) -> str:
    existing = str(existing or "").strip()
    addition = str(addition or "").strip()
    if not existing:
        return addition
    if not addition or addition in existing:
        return existing
    return f"{existing} {addition}"


def _url_key(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.netloc or parsed.path).strip("/").removeprefix("www.")
    path = parsed.path.strip("/")
    if not parsed.netloc and "/" in parsed.path:
        host, _, path = parsed.path.partition("/")
        host = host.strip("/").removeprefix("www.")
        path = path.strip("/")
    return f"{host}/{path}".rstrip("/")


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _root_domain(host: str) -> str:
    parts = [part for part in str(host or "").split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return str(host or "")


def _text_key(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
