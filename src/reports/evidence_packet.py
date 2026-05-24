"""Offline Evidence Packet v0 builder.

This module compiles a conservative evidence-ordering packet from an existing
Brand3 run snapshot. It is intentionally offline: no collectors, LLMs, network,
rendering, scoring, or runtime integration.
"""

from __future__ import annotations

import ast
import json
from collections import defaultdict
from typing import Any
from urllib.parse import urlparse


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
    exa_url_metadata = _build_exa_url_metadata(snapshot)

    packet = _empty_packet(case_id=case_id, audit_url=audit_url, audit_host=audit_host, audit_root=audit_root)

    candidates = _evidence_candidates(snapshot)
    classified_candidates: list[dict] = []

    seen_ambiguities: set[tuple[str, str]] = set()
    seen_reviews: set[tuple[str, str]] = set()
    seen_missing: set[tuple[str, str]] = set()
    seen_not_eligible: set[tuple[str, str, str]] = set()
    seen_eligible: set[tuple[str, str]] = set()

    for candidate in candidates:
        classified = _classify_candidate(
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
            _add_review(packet, classified, seen_reviews, "trust_or_security_signal_requires_review")
        elif source_class == "visual_internal_metric":
            packet["visual_or_internal_signals"].append(entry)
        elif source_class == "noise":
            packet["excluded_noise"].append(entry)
        else:
            packet["external_evidence"].append(entry)

        if not classified.get("url"):
            _add_missing(packet, classified, seen_missing)

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

    packet["entity_resolution"] = _entity_resolution(packet)
    packet["source_inventory"] = _source_inventory(snapshot, classified_candidates)
    packet["dimension_readiness"] = _dimension_readiness(packet, classified_candidates)
    packet["cross_dimension_evidence"] = _cross_dimension_evidence(packet, classified_candidates)
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


def _source_inventory(snapshot: dict, classified_candidates: list[dict]) -> list[dict]:
    inventory: list[dict] = []
    seen_urls: set[str] = set()

    for item in classified_candidates:
        url = str(item.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        inventory.append(
            {
                "url": url,
                "source_type": _inventory_source_type(item),
                "source_quality": _source_quality(item),
                "role": _source_role(item),
                "notes": item.get("classification_reason") or "",
            }
        )

    for item in snapshot.get("raw_inputs") or []:
        payload = item.get("payload")
        source_url = _first_url(payload)
        inventory.append(
            {
                "url": source_url,
                "source_type": str(item.get("source") or "unknown"),
                "source_quality": "unknown",
                "role": "raw_input",
                "notes": f"available={payload is not None}; payload_type={type(payload).__name__ if payload is not None else 'none'}",
            }
        )
    feature_sources: dict[str, int] = defaultdict(int)
    for feature in snapshot.get("features") or []:
        feature_sources[str(feature.get("source") or "unknown")] += 1
    for source, count in sorted(feature_sources.items()):
        inventory.append(
            {
                "url": "",
                "source_type": f"features:{source}",
                "source_quality": "unknown",
                "role": "feature_source_summary",
                "notes": f"count={count}",
            }
        )
    if snapshot.get("evidence_items"):
        inventory.append(
            {
                "url": "",
                "source_type": "evidence_items",
                "source_quality": "unknown",
                "role": "evidence_item_summary",
                "notes": f"count={len(snapshot['evidence_items'])}",
            }
        )
    return _dedupe(inventory)


def _evidence_candidates(snapshot: dict) -> list[dict]:
    candidates: list[dict] = []
    for feature in snapshot.get("features") or []:
        raw = _parse_raw_value(feature.get("raw_value"))
        base = {
            "origin": "feature",
            "dimension": feature.get("dimension_name") or "",
            "feature_name": feature.get("feature_name") or "",
            "feature_source": feature.get("source") or "",
            "feature_confidence": feature.get("confidence"),
        }
        candidates.extend(_candidates_from_raw(raw, base))

    for item in snapshot.get("evidence_items") or []:
        candidates.append(
            {
                "origin": "evidence_item",
                "dimension": item.get("dimension_name") or "",
                "feature_name": item.get("feature_name") or "",
                "feature_source": item.get("source") or "",
                "feature_confidence": item.get("confidence"),
                "text": str(item.get("quote") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "raw_key": "evidence_item",
            }
        )
    return [candidate for candidate in candidates if candidate.get("text") or candidate.get("url")]


def _candidates_from_raw(raw: Any, base: dict) -> list[dict]:
    if not isinstance(raw, dict):
        return []
    if (
        str(base.get("dimension") or "") == "diferenciacion"
        and str(base.get("feature_source") or "") == "competitor_web_comparison"
    ):
        return _competitor_comparison_candidates(raw, base)

    out: list[dict] = []

    def add(*, text: str = "", url: str = "", raw_key: str, extra: dict | None = None) -> None:
        text = " ".join(str(text or "").split())
        url = str(url or "").strip()
        if text or url:
            out.append({**base, "text": text, "url": url, "raw_key": raw_key, "extra": extra or {}})

    for key in ("evidence", "quotes", "examples", "messaging_gaps", "tone_examples"):
        items = raw.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                text = item.get("quote") or item.get("snippet") or item.get("text") or item.get("example") or item.get("title") or ""
                source_value = item.get("source") or ""
                source_url = source_value if _is_http_url(source_value) else ""
                url = item.get("source_url") or item.get("url") or source_url
                add(text=text, url=url, raw_key=key, extra={k: v for k, v in item.items() if k not in {"quote", "snippet", "text", "example", "title", "source_url", "url", "source"}})
            elif isinstance(item, str):
                add(text=item, raw_key=key)

    for gap in raw.get("gaps") or []:
        if not isinstance(gap, dict):
            continue
        self_says = str(gap.get("self_says") or "").strip()
        third_party = str(gap.get("third_party_says") or "").strip()
        url = str(gap.get("source_url") or gap.get("url") or "").strip()
        if self_says:
            add(text=self_says, raw_key="gap_self_says", extra={"gap_url": url})
        if third_party or url:
            add(text=third_party, url=url, raw_key="gap_third_party_says")

    if isinstance(raw.get("evidence_url"), str):
        add(url=raw["evidence_url"], raw_key="evidence_url")
    if isinstance(raw.get("evidence_snippet"), str):
        add(text=raw["evidence_snippet"], raw_key="evidence_snippet")
    for snippet in raw.get("evidence_snippets") or []:
        if isinstance(snippet, str):
            add(text=snippet, raw_key="evidence_snippets")
    for insight in raw.get("evidence_insights") or []:
        if isinstance(insight, str):
            add(text=insight, raw_key="evidence_insights")

    for platform in raw.get("platforms") or []:
        if isinstance(platform, dict):
            add(
                text=f"{platform.get('name') or 'social'} profile candidate",
                url=platform.get("url") or "",
                raw_key="platforms",
                extra={"verified": platform.get("verified"), "followers": platform.get("followers")},
            )
    return out


def _competitor_comparison_candidates(raw: dict, base: dict) -> list[dict]:
    candidates: list[dict] = []
    avg_distance = raw.get("avg_distance")
    competitors_analyzed = raw.get("competitors_analyzed")
    source_url = "snapshot://feature/competitor_web_comparison"

    def add(label: str, payload: dict, relation: str) -> None:
        name = str(payload.get("name") or "").strip()
        distance = payload.get("distance")
        if not name or distance is None:
            return
        text = (
            f"Existing Brand3 competitor comparison identifies {name} as the audited brand's {label} "
            f"with measured distance {distance}; avg_distance={avg_distance}; "
            f"competitors_analyzed={competitors_analyzed}."
        )
        candidates.append(
            {
                **base,
                "text": text,
                "url": source_url,
                "raw_key": f"competitor_{relation}",
                "extra": {
                    "competitor_name": name,
                    "distance": distance,
                    "avg_distance": avg_distance,
                    "competitors_analyzed": competitors_analyzed,
                    "limits": (
                        "Snapshot comparison can support relative positioning distance only; "
                        "it does not prove superiority, product quality, adoption, customer choice, "
                        "durable defensibility, or planning direction."
                    ),
                },
            }
        )

    closest = raw.get("closest_competitor")
    if isinstance(closest, dict):
        add("closest measured competitor", closest, "closest")
    most_different = raw.get("most_different")
    if isinstance(most_different, dict):
        add("most different measured competitor", most_different, "most_different")
    return candidates


def _classify_candidate(
    candidate: dict,
    *,
    audit_host: str,
    audit_root: str,
    exa_url_metadata: dict[str, dict] | None = None,
) -> dict:
    url = str(candidate.get("url") or "").strip()
    text = str(candidate.get("text") or "").strip()
    host = _host(url)
    root = _root_domain(host)
    feature_name = str(candidate.get("feature_name") or "").lower()
    feature_source = str(candidate.get("feature_source") or "").lower()
    raw_key = str(candidate.get("raw_key") or "").lower()
    haystack = " ".join([text, url, feature_name, feature_source, raw_key]).lower()

    source_class = "external_third_party"
    eligibility = "eligible_for_narrative_finding"
    reason = "source_classified_external_candidate"

    if feature_source == "competitor_web_comparison" and raw_key.startswith("competitor_"):
        source_class = "competitor_comparison"
        eligibility = "eligible_for_narrative_finding"
        reason = "bounded_competitor_comparison_snapshot"
    elif _is_visual_internal(feature_name, feature_source, raw_key, haystack):
        source_class = "visual_internal_metric"
        eligibility = "technical_only"
        reason = "visual_or_internal_analysis_not_market_evidence"
    elif _is_technical(feature_name, feature_source, raw_key, haystack, url):
        source_class = "technical_internal"
        eligibility = "technical_only"
        reason = "technical_context_not_brand_narrative_evidence"
    elif _is_trust_security(host, haystack):
        source_class = "trust_security"
        eligibility = "trust_security_review_only"
        reason = "trust_or_security_source_requires_review"
    elif _is_repository(host):
        source_class = "repository"
        eligibility = "observation_only"
        reason = "repository_activity_not_adoption"
    elif _is_marketplace(host):
        source_class = "marketplace_listing"
        eligibility = "requires_human_review"
        reason = "marketplace_listing_not_automatic_external_validation"
    elif _is_noise(haystack):
        source_class = "noise"
        eligibility = "reject_noise"
        reason = "off_topic_or_broad_market_noise"
    elif _is_same_name_external_profile(text, url, audit_host, audit_root):
        source_class = "related_unresolved"
        eligibility = "requires_human_review"
        reason = "same_name_external_profile_not_alias"
    elif raw_key == "platforms" or "social" in feature_name or "social" in feature_source:
        source_class = "external_third_party"
        eligibility = "observation_only"
        reason = "social_profile_candidate_not_external_validation"
    elif host and host == audit_host:
        source_class = "audited_surface"
        eligibility = "observation_only" if _looks_like_owned_claim(candidate) else "eligible_for_narrative_finding"
        reason = "audited_surface_evidence"
    elif host and root and root == audit_root:
        source_class = "owned_surface"
        eligibility = "observation_only"
        reason = "same_root_or_subdomain_not_external_validation"
    elif _is_same_name_different_root(host, audit_host, root, audit_root):
        source_class = "related_unresolved"
        eligibility = "requires_human_review"
        reason = "same_name_different_root_not_alias"
    elif not url and _looks_like_owned_claim(candidate):
        source_class = "owned_surface"
        eligibility = "observation_only"
        reason = "owned_claim_without_url"
    elif not url:
        source_class = "external_third_party"
        eligibility = "requires_human_review"
        reason = "missing_evidence_url"

    if not url and eligibility == "eligible_for_narrative_finding":
        eligibility = "requires_human_review"
        reason = "missing_evidence_url"
    if not text and eligibility == "eligible_for_narrative_finding":
        eligibility = "blocked_empty_text"
        reason = "empty_text_evidence_blocked"
    if _is_usage_or_traction_claim(haystack) and source_class in {"audited_surface", "owned_surface"}:
        eligibility = "observation_only"
        reason = "owned_usage_or_traction_claim_requires_independent_support"

    exa_meta = (exa_url_metadata or {}).get(url) if url else None
    source_class, eligibility, reason = _apply_exa_metadata_hints(
        source_class=source_class,
        eligibility=eligibility,
        reason=reason,
        exa_meta=exa_meta,
        host=host,
        root=root,
        audit_host=audit_host,
        audit_root=audit_root,
    )

    return {
        **candidate,
        "host": host,
        "root_domain": root,
        "source_class": source_class,
        "eligibility": eligibility,
        "classification_reason": reason,
    }


def _apply_exa_metadata_hints(
    *,
    source_class: str,
    eligibility: str,
    reason: str,
    exa_meta: dict | None,
    host: str,
    root: str,
    audit_host: str,
    audit_root: str,
) -> tuple[str, str, str]:
    if not exa_meta:
        return source_class, eligibility, reason

    mapped_class = _map_exa_source_class_to_packet(
        exa_source_class=str(exa_meta.get("source_class") or ""),
        exa_relation=str(exa_meta.get("relation") or ""),
        host=host,
        root=root,
        audit_host=audit_host,
        audit_root=audit_root,
    )
    mapped_review = bool(exa_meta.get("requires_human_review"))
    mapped_reason = str(exa_meta.get("classification_reason") or "").strip()

    if mapped_class in {"noise", "technical_internal", "marketplace_listing", "related_unresolved"}:
        source_class = mapped_class
    elif mapped_class in {"audited_surface", "owned_surface"} and source_class not in {
        "trust_security",
        "technical_internal",
        "visual_internal_metric",
        "noise",
        "related_unresolved",
        "marketplace_listing",
    }:
        source_class = mapped_class
    elif mapped_class == "external_third_party" and source_class in {"external_third_party", "repository"}:
        source_class = mapped_class

    if mapped_class == "related_unresolved":
        eligibility = "requires_human_review"
        reason = mapped_reason or "exa_related_surface_unresolved"
    elif mapped_class == "marketplace_listing":
        eligibility = "requires_human_review"
        reason = mapped_reason or "exa_marketplace_listing_review_gated"
    elif mapped_class == "technical_internal":
        eligibility = "technical_only"
        reason = mapped_reason or "exa_technical_internal_signal"
    elif mapped_class == "noise":
        eligibility = "reject_noise"
        reason = mapped_reason or "exa_noise_source"
    elif mapped_review and eligibility == "eligible_for_narrative_finding":
        eligibility = "requires_human_review"
        reason = mapped_reason or "exa_requires_human_review"

    return source_class, eligibility, reason


def _map_exa_source_class_to_packet(
    *,
    exa_source_class: str,
    exa_relation: str,
    host: str,
    root: str,
    audit_host: str,
    audit_root: str,
) -> str:
    base = exa_source_class.strip().lower()
    relation = exa_relation.strip().lower()

    if base == "owned":
        if relation == "audited_surface" or host == audit_host:
            return "audited_surface"
        if relation == "same_root_surface" or (root and root == audit_root):
            return "owned_surface"
        return "owned_surface"
    if base == "external":
        return "external_third_party"
    if base == "related_unresolved":
        return "related_unresolved"
    if base == "marketplace_listing":
        return "marketplace_listing"
    if base == "technical_internal":
        return "technical_internal"
    if base == "noise":
        return "noise"
    return ""


def _build_exa_url_metadata(snapshot: dict) -> dict[str, dict]:
    metadata: dict[str, dict] = {}
    for item in snapshot.get("raw_inputs") or []:
        if str(item.get("source") or "") != "exa":
            continue
        payload = item.get("payload") if isinstance(item, dict) else None
        if not isinstance(payload, dict):
            continue
        for field in ("mentions", "news", "competitors", "ai_visibility_results"):
            entries = payload.get(field)
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                url = str(entry.get("url") or "").strip()
                if not url:
                    continue
                existing = metadata.get(url)
                candidate = {
                    "source_class": str(entry.get("source_class") or ""),
                    "relation": str(entry.get("relation") or ""),
                    "classification_reason": str(entry.get("classification_reason") or ""),
                    "requires_human_review": bool(entry.get("requires_human_review")),
                }
                if not existing:
                    metadata[url] = candidate
                    continue
                if _exa_meta_priority(candidate) > _exa_meta_priority(existing):
                    metadata[url] = candidate
    return metadata


def _exa_meta_priority(meta: dict) -> int:
    source_class = str(meta.get("source_class") or "")
    if source_class == "noise":
        return 100
    if source_class == "related_unresolved":
        return 90
    if source_class == "marketplace_listing":
        return 80
    if source_class == "technical_internal":
        return 70
    if source_class == "owned":
        return 50
    if source_class == "external":
        return 40
    return 10


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


def _parse_raw_value(raw: Any) -> Any:
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        return raw
    stripped = raw.strip()
    try:
        return ast.literal_eval(stripped)
    except (ValueError, SyntaxError, MemoryError):
        pass
    try:
        return json.loads(stripped)
    except (ValueError, TypeError):
        return raw


def _host(url: str | None) -> str:
    candidate = (url or "").strip()
    if not candidate:
        return ""
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _is_http_url(value: Any) -> bool:
    candidate = str(value or "").strip()
    return candidate.startswith("http://") or candidate.startswith("https://")


def _root_domain(host: str | None) -> str:
    host = (host or "").strip(".").lower()
    if not host:
        return ""
    parts = [part for part in host.split(".") if part]
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def _first_url(value: Any) -> str:
    if isinstance(value, str):
        return value if _is_http_url(value) else ""
    if isinstance(value, dict):
        for key in ("url", "source_url", "homepage", "target_url"):
            found = value.get(key)
            if _is_http_url(found):
                return str(found)
        for item in value.values():
            found = _first_url(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _first_url(item)
            if found:
                return found
    return ""


def _inventory_source_type(item: dict) -> str:
    source_class = item.get("source_class") or "unknown"
    return {
        "audited_surface": "owned",
        "owned_surface": "owned",
        "external_third_party": "external",
        "related_unresolved": "unknown",
        "technical_internal": "technical",
        "trust_security": "trust_security",
        "visual_internal_metric": "technical",
        "competitor_comparison": "comparison",
        "repository": "repository",
        "marketplace_listing": "marketplace",
        "noise": "unknown",
    }.get(source_class, "unknown")


def _source_quality(item: dict) -> str:
    source_class = item.get("source_class") or ""
    if source_class in {"audited_surface", "owned_surface", "repository"}:
        return "high"
    if source_class in {"external_third_party", "marketplace_listing", "trust_security", "competitor_comparison"}:
        return "medium"
    if source_class in {"related_unresolved", "noise"}:
        return "low"
    return "unknown"


def _source_role(item: dict) -> str:
    source_class = item.get("source_class") or ""
    return {
        "audited_surface": "audited_surface",
        "owned_surface": "same_root_or_subdomain_surface",
        "external_third_party": "external_evidence_candidate",
        "related_unresolved": "related_surface_unresolved",
        "technical_internal": "technical_signal",
        "trust_security": "trust_or_security_signal",
        "visual_internal_metric": "visual_or_internal_signal",
        "competitor_comparison": "bounded_competitor_comparison",
        "repository": "repository_or_developer_surface",
        "marketplace_listing": "marketplace_or_directory_listing",
        "noise": "excluded_noise_candidate",
    }.get(source_class, "unknown")
