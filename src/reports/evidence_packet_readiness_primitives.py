"""Readiness and relationship helpers for Evidence Packet v0."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import urlparse

from src.reports.evidence_packet_analysis import (
    BROAD_MARKET_NOISE_MARKERS,
    MARKETPLACE_HOST_MARKERS,
    OWNED_CLAIM_MARKERS,
    REPOSITORY_HOST_MARKERS,
    TECHNICAL_FEATURE_MARKERS,
    TECHNICAL_PATH_MARKERS,
    TRUST_SECURITY_HOST_MARKERS,
    USAGE_CLAIM_MARKERS,
    VISUAL_FEATURE_MARKERS,
    _dedupe,
    _host,
    _is_marketplace,
    _is_noise,
    _is_repository,
    _is_same_name_different_root,
    _is_same_name_external_profile,
    _is_technical,
    _is_trust_security,
    _is_usage_or_traction_claim,
    _is_visual_internal,
    _looks_like_owned_claim,
    _root_domain,
)


DIMENSIONS = ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")


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
                "Differenciacion lacks comparative, category-distinctive, or competitor-corpus evidence.",
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

    if eligible:
        return (
            "thin",
            _dedupe_strings(reason_codes + ["general_evidence_thin"]),
            "Usable evidence exists, but it is too limited for a ready-status readout.",
            "Acquire more directly attributable evidence.",
        )
    return _blocked_or_review_status(reason_codes, review, "Usable evidence is missing or review-gated.")


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
