"""Support helpers for the offline Evidence Packet v0 builder."""

from __future__ import annotations

from typing import Any

from src.reports.evidence_packet_analysis import (
    _build_exa_url_metadata as _build_exa_url_metadata_impl,
    _classify_candidate as _classify_candidate_impl,
    _dedupe as _dedupe_impl,
    _host as _host_impl,
    _looks_like_owned_claim as _looks_like_owned_claim_impl,
    _map_exa_source_class_to_packet as _map_exa_source_class_to_packet_impl,
    _root_domain as _root_domain_impl,
)
from src.reports.evidence_packet_candidates import build_evidence_candidates as _evidence_candidates
from src.reports.evidence_packet_inventory import build_source_inventory as _source_inventory
from src.reports.evidence_packet_readiness import (
    _add_entity_ambiguity as _add_entity_ambiguity_impl,
    _add_missing as _add_missing_impl,
    _add_review as _add_review_impl,
    _cross_dimension_evidence as _cross_dimension_evidence_impl,
    _dimension_readiness as _dimension_readiness_impl,
    _entity_resolution as _entity_resolution_impl,
)

_dedupe = _dedupe_impl
_host = _host_impl
_root_domain = _root_domain_impl
_looks_like_owned_claim = _looks_like_owned_claim_impl

VERSION = 0

OUTPUT_FIELDS = (
    "version",
    "case_id",
    "audit_url",
    "audited_surface",
    "entity_resolution",
    "source_inventory",
    "owned_claims",
    "external_evidence",
    "related_surface_evidence",
    "technical_signals",
    "trust_or_security_signals",
    "visual_or_internal_signals",
    "entity_ambiguity",
    "excluded_noise",
    "missing_evidence",
    "finding_eligible_evidence",
    "evidence_not_eligible_for_findings",
    "requires_human_review",
    "dimension_evidence_inputs",
    "dimension_readiness",
    "cross_dimension_evidence",
    "metadata",
)


def build_evidence_packet_v0(snapshot: dict) -> dict:
    run = snapshot.get("run") or {}
    audit_url = str(run.get("url") or "").strip()
    audit_host = _host(audit_url)
    audit_root = _root_domain(audit_host)
    case_id = _case_id(run, audit_host)
    exa_url_metadata = _build_exa_url_metadata_impl(snapshot)

    packet = _empty_packet(case_id=case_id, audit_url=audit_url, audit_host=audit_host, audit_root=audit_root)

    candidates = _evidence_candidates(snapshot)
    classified_candidates: list[dict] = []

    seen_ambiguities: set[tuple[str, str]] = set()
    seen_reviews: set[tuple[str, str]] = set()
    seen_missing: set[tuple[str, str]] = set()
    seen_not_eligible: set[tuple[str, str, str]] = set()

    for candidate in candidates:
        classified = _classify_candidate_impl(
            candidate,
            audit_host=audit_host,
            audit_root=audit_root,
            exa_url_metadata=exa_url_metadata,
        )
        classified_candidates.append(classified)
        dimension = classified.get("dimension") or "unknown"
        packet["dimension_evidence_inputs"].setdefault(dimension, []).append(_dimension_input(classified))

        source_class = classified["source_class"]
        eligibility = classified["eligibility"]
        entry = _public_entry(classified)

        if source_class == "audited_surface":
            packet["audited_surface"]["evidence"].append(entry)
            if _looks_like_owned_claim(classified):
                packet["owned_claims"].append(entry)
        elif source_class == "owned_surface":
            packet["owned_claims"].append(entry)
        elif source_class == "related_unresolved":
            packet["related_surface_evidence"].append({**entry, "relationship": "unresolved"})
            _add_entity_ambiguity_impl(packet, classified, seen_ambiguities)
        elif source_class == "technical_internal":
            packet["technical_signals"].append(entry)
        elif source_class == "trust_security":
            packet["trust_or_security_signals"].append(entry)
            _add_review_impl(packet, classified, seen_reviews, "trust_or_security_signal_requires_review")
        elif source_class == "visual_internal_metric":
            packet["visual_or_internal_signals"].append(entry)
        elif source_class == "noise":
            packet["excluded_noise"].append(entry)
        else:
            packet["external_evidence"].append(entry)

        if not classified.get("url"):
            _add_missing_impl(packet, classified, seen_missing)
        if eligibility == "eligible_for_narrative_finding":
            packet["finding_eligible_evidence"].append(entry)
        else:
            packet["evidence_not_eligible_for_findings"].append(entry)
            if eligibility != "blocked_empty_text":
                _add_review_impl(packet, classified, seen_reviews, eligibility or "requires_review")

    packet["entity_resolution"] = _entity_resolution_impl(packet)
    packet["source_inventory"] = _source_inventory(snapshot, classified_candidates)
    packet["dimension_readiness"] = _dimension_readiness_impl(packet, classified_candidates)
    packet["cross_dimension_evidence"] = _cross_dimension_evidence_impl(packet, classified_candidates)
    packet["metadata"]["counts"] = {
        field: len(packet[field])
        for field in OUTPUT_FIELDS
        if isinstance(packet.get(field), list)
    }
    return packet


def _empty_packet(*, case_id: str, audit_url: str, audit_host: str, audit_root: str) -> dict:
    return {
        "version": VERSION,
        "case_id": case_id,
        "audit_url": audit_url,
        "audited_surface": {
            "url": audit_url,
            "host": audit_host,
            "root_domain": audit_root,
            "evidence": [],
            "confidence": "medium" if audit_url else "unknown",
        },
        "entity_resolution": {
            "primary_entity": audit_host or "",
            "confidence": "medium" if audit_url else "unknown",
            "evidence": [],
            "related_surfaces": [],
            "ambiguities": [],
        },
        "source_inventory": [],
        "owned_claims": [],
        "external_evidence": [],
        "related_surface_evidence": [],
        "technical_signals": [],
        "trust_or_security_signals": [],
        "visual_or_internal_signals": [],
        "entity_ambiguity": [],
        "excluded_noise": [],
        "missing_evidence": [],
        "finding_eligible_evidence": [],
        "evidence_not_eligible_for_findings": [],
        "requires_human_review": [],
        "dimension_evidence_inputs": {},
        "dimension_readiness": {},
        "cross_dimension_evidence": {
            "owned_claims": [],
            "external_validation": [],
            "technical_only": [],
            "trust_or_security": [],
            "excluded_noise": [],
            "entity_ambiguity": [],
            "contradiction_candidates": [],
        },
        "metadata": {
            "source": "existing_exa_web_pipeline",
            "llm_required": False,
            "deep_research_required": False,
            "runtime_effect": False,
            "scoring_effect": False,
            "prompt_effect": False,
            "render_effect": False,
            "visual_signature_effect": False,
            "network_required": False,
            "builder": "build_evidence_packet_v0",
        },
    }


def _case_id(run: dict, audit_host: str) -> str:
    brand = str(run.get("brand_name") or audit_host or "brand").strip()
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in brand)
    return "_".join(part for part in cleaned.split("_") if part) or "brand"


def _public_entry(item: dict) -> dict:
    return {
        "text": item.get("text") or "",
        "url": item.get("url") or "",
        "dimension": item.get("dimension") or "",
        "feature_name": item.get("feature_name") or "",
        "feature_source": item.get("feature_source") or "",
        "source_class": item.get("source_class") or "",
        "eligibility": item.get("eligibility") or "",
        "classification_reason": item.get("classification_reason") or "",
        "limits": (item.get("extra") or {}).get("limits", ""),
    }


def _dimension_input(item: dict) -> dict:
    return {
        "text": item.get("text") or "",
        "url": item.get("url") or "",
        "feature_name": item.get("feature_name") or "",
        "feature_source": item.get("feature_source") or "",
        "source_class": item.get("source_class") or "",
        "eligibility": item.get("eligibility") or "",
        "classification_reason": item.get("classification_reason") or "",
        "limits": (item.get("extra") or {}).get("limits", ""),
    }
