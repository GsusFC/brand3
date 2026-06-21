"""Offline Evidence Packet v0 builder.

This module compiles a conservative evidence-ordering packet from an existing
Brand3 run snapshot. It is intentionally offline: no collectors, LLMs, network,
rendering, scoring, or runtime integration.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any
from urllib.parse import urlparse

from src.reports.evidence_packet_analysis import (
    _apply_exa_metadata_hints as _apply_exa_metadata_hints_impl,
    _build_exa_url_metadata as _build_exa_url_metadata_impl,
    _classify_candidate as _classify_candidate_impl,
    _map_exa_source_class_to_packet as _map_exa_source_class_to_packet_impl,
)
from src.reports.evidence_packet_readiness import (
    _add_entity_ambiguity as _add_entity_ambiguity_impl,
    _add_missing as _add_missing_impl,
    _add_review as _add_review_impl,
    _allows_ambiguity_competitor_override as _allows_ambiguity_competitor_override_impl,
    _base_readiness_reason_codes as _base_readiness_reason_codes_impl,
    _blocked_or_review_status as _blocked_or_review_status_impl,
    _cross_dimension_evidence as _cross_dimension_evidence_impl,
    _dedupe_strings as _dedupe_strings_impl,
    _dimension_readiness as _dimension_readiness_impl,
    _entity_resolution as _entity_resolution_impl,
    _has_differentiation_basis as _has_differentiation_basis_impl,
    _has_temporal_activity_signal as _has_temporal_activity_signal_impl,
    _merge_related_surfaces as _merge_related_surfaces_impl,
    _public_related_evidence as _public_related_evidence_impl,
    _readiness_decision as _readiness_decision_impl,
    _related_surfaces as _related_surfaces_impl,
)
from src.reports.evidence_packet_inventory import build_source_inventory as _source_inventory
from src.reports.evidence_packet_candidates import build_evidence_candidates as _evidence_candidates


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

DIMENSIONS = ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")

TRUST_SECURITY_HOST_MARKERS = (
    "scamadviser",
    "joesandbox",
    "any.run",
    "blacklist",
    "virustotal",
    "urlscan",
    "malware",
    "phish",
    "threat",
    "abuse",
)

TECHNICAL_PATH_MARKERS = (
    "robots.txt",
    "sitemap",
    "llms.txt",
    "schema",
    "whois",
    "dns",
)

TECHNICAL_FEATURE_MARKERS = (
    "context",
    "site_structure",
    "context_readiness",
    "activity_surface",
    "review_surface",
    "structured_identity",
    "content_depth_signal",
)

VISUAL_FEATURE_MARKERS = (
    "visual",
    "screenshot",
    "color",
    "contrast",
    "whitespace",
    "typography",
)

OWNED_CLAIM_MARKERS = (
    "the brand describes itself",
    "brand describes itself",
    "the brand claims",
    "states",
    "make email your most valuable channel",
    "email-first operating system",
    "content feels original",
)

BROAD_MARKET_NOISE_MARKERS = (
    "ssl adoption statistics",
    "market share",
    "competitors similar",
    "pricing tiers",
    "perishablenews",
    "honey watermelons",
    "fresh-pro announces",
    "brand refresh new mascot",
)

REPOSITORY_HOST_MARKERS = (
    "github.com",
    "gitlab.com",
    "bitbucket.org",
)

MARKETPLACE_HOST_MARKERS = (
    "producthunt.com",
    "peerpush.net",
    "uneed.best",
    "devhunt.org",
    "sourceforge.net",
    "slashdot.org",
    "softwaresuggest.com",
)

USAGE_CLAIM_MARKERS = (
    "daily users",
    "users",
    "installs",
    "downloads",
    "contributors",
    "followers",
    "stars",
    "forks",
    "upvotes",
)


def build_evidence_packet_v0(snapshot: dict) -> dict:
    """Build an offline local Evidence Packet v0 from an existing run snapshot."""
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
    seen_eligible: set[tuple[str, str]] = set()

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
            _add_entity_ambiguity(packet, classified, seen_ambiguities)
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
            key = (entry.get("text", ""), entry.get("url", ""))
            if key not in seen_eligible:
                packet["finding_eligible_evidence"].append(entry)
                seen_eligible.add(key)
        else:
            key = (entry.get("text", ""), entry.get("url", ""), eligibility)
            if key not in seen_not_eligible:
                packet["evidence_not_eligible_for_findings"].append({**entry, "eligibility": eligibility})
                seen_not_eligible.add(key)

    packet["audited_surface"]["evidence"] = _dedupe(packet["audited_surface"]["evidence"])
    for field in (
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
    ):
        packet[field] = _dedupe(packet[field])

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


def _dimension_readiness(packet: dict, classified_candidates: list[dict]) -> dict:
    readiness: dict[str, dict] = {}
    ambiguity_count = len(packet.get("entity_ambiguity") or [])
    ambiguity_surfaces = [str(item.get("surface") or "") for item in (packet.get("entity_ambiguity") or [])]
    audit_url = str(packet.get("audit_url") or "")

    for dimension in DIMENSIONS:
        items = [item for item in classified_candidates if (item.get("dimension") or "") == dimension]
        eligible = [item for item in items if _counts_for_readiness(item)]
        blocked = [item for item in items if not _counts_for_readiness(item)]
        review = [item for item in items if _requires_review_for_readiness(item)]
        missing = [item for item in items if not str(item.get("url") or "").strip() or not str(item.get("text") or "").strip()]

        context = {
            "items": items,
            "eligible": eligible,
            "blocked": blocked,
            "review": review,
            "missing": missing,
            "ambiguity_count": ambiguity_count,
            "ambiguity_surfaces": ambiguity_surfaces,
            "audit_url": audit_url,
        }
        status, reason_codes, reason, action = _readiness_decision(dimension, context)
        readiness[dimension] = {
            "status": status,
            "eligible_count": len(eligible),
            "blocked_count": len(blocked),
            "review_required_count": len(review),
            "missing_evidence_count": len(missing),
            "reason_codes": reason_codes,
            "readiness_reason": reason,
            "recommended_action": action,
        }
    return readiness


def _counts_for_readiness(item: dict) -> bool:
    if item.get("eligibility") != "eligible_for_narrative_finding":
        return False
    if not str(item.get("text") or "").strip():
        return False
    if _requires_review_for_readiness(item):
        return False
    if item.get("source_class") in {"technical_internal", "visual_internal_metric", "trust_security", "noise"}:
        return False
    return True


def _requires_review_for_readiness(item: dict) -> bool:
    return item.get("eligibility") in {"requires_human_review", "trust_security_review_only"} or item.get(
        "source_class"
    ) in {"related_unresolved", "marketplace_listing", "trust_security"}


def _readiness_decision(dimension: str, context: dict) -> tuple[str, list[str], str, str]:
    items = context["items"]
    eligible = context["eligible"]
    review = context["review"]
    missing = context["missing"]
    ambiguity_count = context["ambiguity_count"]
    reason_codes = _base_readiness_reason_codes(items, eligible, review, missing)

    if not items and dimension == "diferenciacion":
        return (
            "abstain",
            _dedupe_strings(reason_codes + ["no_dimension_evidence", "insufficient_comparative_evidence", "competitor_corpus_required"]),
            "Diferenciacion has no comparative, category-distinctive, or competitor-corpus evidence.",
            "Collect comparative evidence or a competitor corpus before generating differentiation prose.",
        )

    if not items:
        return (
            "abstain",
            _dedupe_strings(reason_codes + ["no_dimension_evidence"]),
            "No usable evidence reached this dimension in the local packet.",
            "Acquire dimension-specific evidence before prompt use.",
        )

    if ambiguity_count >= 3 and not eligible:
        return (
            "blocked",
            _dedupe_strings(reason_codes + ["entity_ambiguity_blocks_readiness"]),
            "Evidence is dominated by unresolved entity or surface ambiguity.",
            "Resolve entity boundaries before narrative generation.",
        )

    if dimension == "diferenciacion":
        comparison = [item for item in eligible if item.get("source_class") == "competitor_comparison"]
        if ambiguity_count >= 2 and not comparison:
            return (
                "blocked",
                _dedupe_strings(reason_codes + ["entity_ambiguity_blocks_readiness", "competitor_comparison_requires_resolved_entity"]),
                "Differentiation evidence is dominated by unresolved entity ambiguity and lacks bounded competitor comparison anchors.",
                "Resolve the audited entity boundary or add bounded competitor comparison evidence before use.",
            )
        if ambiguity_count >= 2 and comparison and not _allows_ambiguity_competitor_override(context):
            return (
                "blocked",
                _dedupe_strings(reason_codes + ["entity_ambiguity_blocks_readiness", "competitor_comparison_requires_resolved_entity"]),
                "Competitor comparison evidence exists, but unresolved entity ambiguity is too strong for safe differentiation readiness.",
                "Resolve audited-entity boundaries before enabling differentiation from comparison evidence.",
            )
        if not _has_differentiation_basis(eligible):
            return (
                "abstain",
                _dedupe_strings(reason_codes + ["insufficient_comparative_evidence", "competitor_corpus_required"]),
                "Differentiacion lacks comparative, category-distinctive, or competitor-corpus evidence.",
                "Collect comparative evidence or a competitor corpus before generating differentiation prose.",
            )
        if ambiguity_count >= 2 and comparison:
            return (
                "ready" if len(comparison) >= 2 else "thin",
                _dedupe_strings(
                    reason_codes
                    + [
                        "entity_ambiguity_present",
                        "competitor_corpus_present",
                        "bounded_comparison_evidence",
                        "no_strategy_inference",
                    ]
                ),
                "Differentiation has bounded competitor comparison evidence, but unresolved entity ambiguity must remain visible.",
                "Use only bounded comparison language and preserve explicit ambiguity caveats.",
            )
        return (
            "ready" if len(comparison) >= 2 else "thin",
            _dedupe_strings(reason_codes + ["competitor_corpus_present", "bounded_comparison_evidence", "no_strategy_inference"]),
            "Comparative or category-distinctive evidence is present, but should remain bounded to the cited sources.",
            "Use only the cited comparative evidence; do not infer category leadership.",
        )

    if dimension == "percepcion":
        external = [item for item in eligible if item.get("source_class") == "external_third_party"]
        if len(eligible) >= 2 and external:
            return (
                "ready",
                _dedupe_strings(reason_codes),
                "Percepcion has non-empty eligible evidence and at least one external perception source.",
                "Proceed only with source-bounded perception language.",
            )
        if eligible:
            return (
                "thin",
                _dedupe_strings(reason_codes + ["insufficient_external_sentiment_evidence"]),
                "Percepcion has usable evidence, but external sentiment coverage is thin.",
                "Acquire more independent perception sources or keep prose heavily qualified.",
            )
        if review:
            return (
                "review_required",
                _dedupe_strings(reason_codes + ["review_gated_evidence_not_ready"]),
                "Perception-like evidence is present but review-gated or not independently attributable.",
                "Verify source relationship and sentiment provenance before use.",
            )
        return (
            "abstain",
            _dedupe_strings(reason_codes + ["observable_absence_conditions_not_met"]),
            "No external sentiment evidence is available, and observable-absence conditions are not documented.",
            "Document search coverage or acquire external perception evidence.",
        )

    if dimension == "coherencia":
        owned_text = [
            item
            for item in items
            if item.get("source_class") in {"audited_surface", "owned_surface"}
            and str(item.get("text") or "").strip()
            and item.get("source_class") != "visual_internal_metric"
        ]
        if len(owned_text) >= 2 and len(eligible) >= 1:
            return (
                "ready",
                _dedupe_strings(reason_codes),
                "Coherencia has multiple owned textual surfaces and at least one usable non-review-gated evidence item.",
                "Proceed with intra-entity consistency language only.",
            )
        if owned_text or eligible:
            return (
                "thin",
                _dedupe_strings(reason_codes + ["owned_textual_surface_coverage_thin"]),
                "Coherencia has some owned textual evidence, but not enough distinct surfaces for ready status.",
                "Collect additional owned textual surfaces before stronger coherence prose.",
            )
        return _blocked_or_review_status(reason_codes, review, "Coherencia evidence is technical, visual-metric, missing, or review-gated.")

    if dimension == "presencia":
        owned = [item for item in items if item.get("source_class") in {"audited_surface", "owned_surface"} and str(item.get("text") or item.get("url") or "").strip()]
        external = [item for item in eligible if item.get("source_class") in {"external_third_party", "repository"}]
        if owned and external:
            return (
                "ready" if len(external) >= 2 else "thin",
                _dedupe_strings(reason_codes),
                "Presencia has owned-surface evidence plus external channel evidence.",
                "Proceed with discoverability language bounded to detected channels.",
            )
        if owned:
            return (
                "thin",
                _dedupe_strings(reason_codes + ["external_channel_coverage_thin"]),
                "Presencia has owned-surface evidence, but external channel evidence is insufficient.",
                "Verify official profiles and collect external channel evidence.",
            )
        return _blocked_or_review_status(reason_codes, review, "Presencia lacks a usable owned surface or external channel evidence.")

    if dimension == "vitalidad":
        temporal = [item for item in eligible if _has_temporal_activity_signal(item)]
        if len(temporal) >= 2:
            return (
                "ready",
                _dedupe_strings(reason_codes),
                "Vitalidad has multiple non-empty temporal activity signals.",
                "Proceed with activity language without inferring traction or growth.",
            )
        if temporal or eligible:
            return (
                "thin",
                _dedupe_strings(reason_codes + ["temporal_activity_coverage_thin"]),
                "Vitalidad has activity evidence, but the temporal basis is thin.",
                "Acquire changelog, release, news, or repository recency evidence.",
            )
        return _blocked_or_review_status(reason_codes, review, "Vitalidad lacks usable temporal activity evidence.")

    return _blocked_or_review_status(reason_codes, review, "Dimension evidence is not ready for narrative use.")


def _blocked_or_review_status(reason_codes: list[str], review: list[dict], reason: str) -> tuple[str, list[str], str, str]:
    if review:
        return (
            "review_required",
            _dedupe_strings(reason_codes + ["review_gated_evidence_not_ready"]),
            reason,
            "Resolve review-gated evidence before prompt use.",
        )
    return (
        "blocked",
        _dedupe_strings(reason_codes),
        reason,
        "Acquire suitable non-technical evidence or abstain.",
    )


def _base_readiness_reason_codes(items: list[dict], eligible: list[dict], review: list[dict], missing: list[dict]) -> list[str]:
    codes: list[str] = []
    if any(not str(item.get("text") or "").strip() for item in items):
        codes.append("empty_text_evidence_blocked")
    if items and all(item.get("source_class") == "technical_internal" for item in items):
        codes.append("technical_internal_only")
    if any(item.get("source_class") == "visual_internal_metric" for item in items):
        codes.append("visual_technical_metric_blocked")
    if any(item.get("source_class") == "visual_internal_metric" for item in items) and eligible:
        codes.append("visual_brand_support_only")
    if any(item.get("source_class") in {"audited_surface", "owned_surface"} for item in items) and not any(
        item.get("source_class") == "external_third_party" for item in eligible
    ):
        codes.append("owned_claim_without_external_corroboration")
    if any("social" in str(item.get("feature_name") or item.get("feature_source") or "").lower() for item in items):
        codes.append("official_profile_requires_link_verification")
    if review:
        codes.append("review_gated_evidence_not_ready")
    if missing:
        codes.append("empty_text_evidence_blocked" if any(not str(item.get("text") or "").strip() for item in missing) else "missing_evidence_url")
    return _dedupe_strings(codes)


def _has_differentiation_basis(items: list[dict]) -> bool:
    for item in items:
        if item.get("source_class") == "competitor_comparison":
            return True
        haystack = " ".join(
            [
                str(item.get("text") or ""),
                str(item.get("url") or ""),
                str(item.get("feature_name") or ""),
            ]
        ).lower()
        if any(marker in haystack for marker in (" vs ", "versus", "alternative to", "compared to", "competitor", "unlike", "differenti")):
            return True
        if any(marker in haystack for marker in ("category", "unique", "distinct", "only", "first")) and item.get(
            "source_class"
        ) == "external_third_party":
            return True
    return False


def _allows_ambiguity_competitor_override(context: dict) -> bool:
    audit_url = str(context.get("audit_url") or "")
    audit_host = _host(audit_url)
    audit_root = _root_domain(audit_host)
    if not audit_root:
        return False
    audit_token = audit_root.split(".")[0]
    if not audit_token:
        return False

    supporting_variants = 0
    for surface in context.get("ambiguity_surfaces") or []:
        surface_host = _host(surface)
        surface_root = _root_domain(surface_host)
        if not surface_root or not surface_root.startswith(audit_token):
            continue
        if not surface_root.endswith(".com"):
            continue
        path = ""
        try:
            path = (urlparse(surface if "://" in surface else f"https://{surface}").path or "").lower()
        except Exception:
            path = ""
        if any(marker in path for marker in ("/about", "/blog", "/release", "/product", "/docs")):
            supporting_variants += 1

    return supporting_variants >= 2


def _has_temporal_activity_signal(item: dict) -> bool:
    haystack = " ".join(
        [
            str(item.get("text") or ""),
            str(item.get("url") or ""),
            str(item.get("feature_name") or ""),
            str(item.get("feature_source") or ""),
        ]
    ).lower()
    return any(
        marker in haystack
        for marker in (
            "202",
            "recent",
            "launch",
            "launched",
            "release",
            "released",
            "changelog",
            "update",
            "updated",
            "activity",
            "news",
            "blog",
        )
    )


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _add_entity_ambiguity(packet: dict, item: dict, seen: set[tuple[str, str]]) -> None:
    key = (item.get("host") or "", item.get("url") or item.get("text") or "")
    if key in seen:
        return
    seen.add(key)
    packet["entity_ambiguity"].append(
        {
            "ambiguity": "same_name_different_root",
            "surface": item.get("url") or item.get("host") or "",
            "text": item.get("text") or "",
            "reason": "Name/token overlap with audited surface does not prove alias, ownership, or entity relationship.",
            "requires_human_review": True,
        }
    )
    _add_review(packet, item, set(), "same_name_different_root_requires_review")


def _entity_resolution(packet: dict) -> dict:
    audited_surface = packet["audited_surface"]
    related_surfaces = _related_surfaces(packet)
    ambiguities = [
        {
            "surface": item.get("surface") or "",
            "reason": item.get("reason") or "",
            "requires_human_review": item.get("requires_human_review", True),
        }
        for item in packet["entity_ambiguity"]
    ]
    return {
        "primary_entity": audited_surface.get("host") or "",
        "confidence": audited_surface.get("confidence") or "unknown",
        "evidence": audited_surface.get("evidence") or [],
        "related_surfaces": related_surfaces,
        "ambiguities": ambiguities,
    }


def _related_surfaces(packet: dict) -> list[dict]:
    related: list[dict] = []
    for entry in packet["owned_claims"] + packet["related_surface_evidence"] + packet["external_evidence"]:
        url = str(entry.get("url") or "").strip()
        if not url:
            continue
        source_class = entry.get("source_class") or ""
        if source_class not in {
            "owned_surface",
            "related_unresolved",
            "repository",
            "marketplace_listing",
        }:
            continue
        relation_type = {
            "owned_surface": "same_root_surface",
            "related_unresolved": "ambiguous_name_match",
            "repository": "repository",
            "marketplace_listing": "marketplace_listing",
        }.get(source_class, "unresolved")
        relationship = "explicitly_related" if source_class == "owned_surface" else "unresolved"
        requires_review = source_class != "owned_surface"
        related.append(
            {
                "surface": url,
                "relation_type": relation_type,
                "relationship": relationship,
                "confidence": "medium" if source_class == "owned_surface" else "unresolved",
                "evidence": [_public_related_evidence(entry)],
                "requires_human_review": requires_review,
            }
        )
    return _merge_related_surfaces(related)


def _merge_related_surfaces(items: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for item in items:
        surface = item["surface"]
        existing = merged.get(surface)
        if not existing:
            merged[surface] = item
            continue
        existing["requires_human_review"] = existing["requires_human_review"] or item["requires_human_review"]
        existing["evidence"].extend(item.get("evidence") or [])
        if existing["relationship"] == "unresolved" and item["relationship"] == "explicitly_related":
            existing["relationship"] = "explicitly_related"
    for item in merged.values():
        item["evidence"] = _dedupe(item["evidence"])
    return list(merged.values())


def _public_related_evidence(entry: dict) -> dict:
    return {
        "text": entry.get("text") or "",
        "url": entry.get("url") or "",
        "classification_reason": entry.get("classification_reason") or "",
        "eligibility": entry.get("eligibility") or "",
    }


def _cross_dimension_evidence(packet: dict, classified_candidates: list[dict]) -> dict:
    return {
        "owned_claims": packet["owned_claims"],
        "external_validation": [
            item
            for item in packet["external_evidence"]
            if item.get("eligibility") == "eligible_for_narrative_finding"
        ],
        "technical_only": packet["technical_signals"] + packet["visual_or_internal_signals"],
        "trust_or_security": packet["trust_or_security_signals"],
        "excluded_noise": packet["excluded_noise"],
        "entity_ambiguity": packet["entity_ambiguity"],
        "contradiction_candidates": _contradiction_candidates(packet, classified_candidates),
    }


def _contradiction_candidates(packet: dict, classified_candidates: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    for item in packet["entity_ambiguity"]:
        candidates.append(
            {
                "type": "same_name_different_root_ambiguity",
                "surface": item.get("surface") or "",
                "evidence": item.get("text") or "",
                "reason": "Same-name or token overlap can create false entity coherence.",
                "requires_human_review": True,
            }
        )

    by_feature: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in classified_candidates:
        by_feature[(item.get("dimension") or "", item.get("feature_name") or "")].append(item)
    for (_dimension, feature_name), items in by_feature.items():
        owned = [item for item in items if item.get("source_class") in {"audited_surface", "owned_surface"}]
        external = [
            item
            for item in items
            if item.get("source_class")
            in {"external_third_party", "related_unresolved", "repository", "marketplace_listing"}
        ]
        if owned and external:
            candidates.append(
                {
                    "type": "owned_claim_vs_external_source_mismatch",
                    "surface": "",
                    "feature_name": feature_name,
                    "owned_evidence": [_public_related_evidence(item) for item in owned[:3]],
                    "external_evidence": [_public_related_evidence(item) for item in external[:3]],
                    "reason": "Owned and external/related evidence appear in the same feature pool and must not be smoothed into one entity story.",
                    "requires_human_review": True,
                }
            )

    numeric_claims = [
        item for item in classified_candidates if any(marker in str(item.get("text") or "").lower() for marker in USAGE_CLAIM_MARKERS)
    ]
    if len(numeric_claims) > 1:
        candidates.append(
            {
                "type": "count_or_activity_claims_require_support",
                "surface": "",
                "evidence": [_public_related_evidence(item) for item in numeric_claims[:5]],
                "reason": "Usage, install, follower, contributor, star, fork, and upvote counts require independent support before narrative use.",
                "requires_human_review": True,
            }
        )
    return _dedupe(candidates)


def _add_review(packet: dict, item: dict, seen: set[tuple[str, str]], reason: str) -> None:
    key = (item.get("url") or "", reason)
    if key in seen:
        return
    seen.add(key)
    packet["requires_human_review"].append(
        {
            "text": item.get("text") or "",
            "url": item.get("url") or "",
            "reason": reason,
            "source_class": item.get("source_class") or "",
        }
    )


def _add_missing(packet: dict, item: dict, seen: set[tuple[str, str]]) -> None:
    key = (item.get("text") or "", item.get("feature_name") or "")
    if key in seen:
        return
    seen.add(key)
    packet["missing_evidence"].append(
        {
            "text": item.get("text") or "",
            "dimension": item.get("dimension") or "",
            "feature_name": item.get("feature_name") or "",
            "reason": "evidence_has_no_url",
            "eligibility": item.get("eligibility") or "requires_human_review",
        }
    )


def _is_visual_internal(feature_name: str, feature_source: str, raw_key: str, haystack: str) -> bool:
    return (
        "visual" in feature_source
        or "visual" in feature_name
        or raw_key == "evidence_insights"
        or any(marker in haystack for marker in VISUAL_FEATURE_MARKERS)
    )


def _is_technical(feature_name: str, feature_source: str, raw_key: str, haystack: str, url: str) -> bool:
    return (
        "context" in feature_source
        or any(marker in feature_name for marker in TECHNICAL_FEATURE_MARKERS)
        or any(marker in haystack for marker in ("robots_found", "sitemap_found", "schema_types", "crawl", "technical site"))
        or any(marker in url.lower() for marker in TECHNICAL_PATH_MARKERS)
        or raw_key == "evidence_item" and any(marker in haystack for marker in TECHNICAL_PATH_MARKERS)
    )


def _is_trust_security(host: str, haystack: str) -> bool:
    return any(marker in host or marker in haystack for marker in TRUST_SECURITY_HOST_MARKERS)


def _is_repository(host: str) -> bool:
    return any(marker == host or host.endswith(f".{marker}") for marker in REPOSITORY_HOST_MARKERS)


def _is_marketplace(host: str) -> bool:
    return any(marker in host for marker in MARKETPLACE_HOST_MARKERS)


def _is_usage_or_traction_claim(haystack: str) -> bool:
    return any(marker in haystack for marker in USAGE_CLAIM_MARKERS)


def _is_noise(haystack: str) -> bool:
    return any(marker in haystack for marker in BROAD_MARKET_NOISE_MARKERS)


def _looks_like_owned_claim(candidate: dict) -> bool:
    text = str(candidate.get("text") or "").lower()
    source = str(candidate.get("feature_source") or "").lower()
    raw_key = str(candidate.get("raw_key") or "").lower()
    return (
        "web_scrape" in source
        or raw_key in {"evidence_snippet", "gap_self_says"}
        or any(marker in text for marker in OWNED_CLAIM_MARKERS)
    )


def _is_same_name_different_root(host: str, audit_host: str, root: str, audit_root: str) -> bool:
    if not host or not audit_host or root == audit_root:
        return False
    audit_tokens = [part for part in audit_host.split(".") if len(part) >= 4]
    return any(token in host for token in audit_tokens)


def _is_same_name_external_profile(text: str, url: str, audit_host: str, audit_root: str) -> bool:
    host = _host(url)
    if not url or not audit_host or not host or _root_domain(host) == audit_root:
        return False
    audit_tokens = [part for part in audit_host.split(".") if len(part) >= 5]
    haystack = f"{text} {url}".lower()
    profile_hosts = (
        "crunchbase.com",
        "linkedin.com",
        "producthunt.com",
        "softwaresuggest.com",
        "sourceforge.net",
        "slashdot.org",
    )
    if not any(marker in host for marker in profile_hosts):
        return False
    return any(token in haystack for token in audit_tokens)


def _dedupe(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _host(url: str | None) -> str:
    candidate = (url or "").strip()
    if not candidate:
        return ""
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _root_domain(host: str | None) -> str:
    host = (host or "").strip(".").lower()
    if not host:
        return ""
    parts = [part for part in host.split(".") if part]
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])
