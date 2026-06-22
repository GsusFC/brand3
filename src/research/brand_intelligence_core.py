"""Brand Intelligence source planning and evidence helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from urllib.parse import urlparse
import hashlib
import re

from src.research.brand_intelligence import (
    BRAND_EVIDENCE_GRAPH_CONTRACT_VERSION,
    ENTITY_CONTRACT_VERSION,
    IDENTITY_BAKEOFF_VERSION,
    IDENTITY_RESOLUTION_CONTRACT_VERSION,
    SEED_CONTRACT_VERSION,
    SOURCE_INVENTORY_CONTRACT_VERSION,
    SOURCE_OBSERVATION_BAKEOFF_VERSION,
    SOURCE_PLAN_CONTRACT_VERSION,
    BrandEntityType,
    BrandEvidenceGraph,
    BrandEvidenceItem,
    BrandIdentityBakeoffCase,
    BrandIdentityBakeoffResult,
    BrandIdentityCandidate,
    BrandIdentityResolution,
    BrandIdentitySignal,
    BrandSeed,
    BrandSourceBakeoffCase,
    BrandSourceBakeoffResult,
    BrandSourceInventory,
    BrandSourceObservation,
    BrandSourcePlan,
    BrandSourceRequest,
    EvidenceEligibility,
    EvidenceStrength,
    IdentitySignalSource,
    ResolutionStatus,
    ResolvedBrandEntity,
    SeedKind,
    SourceChannel,
    SourceObservationStatus,
    BrandEvidenceKind,
)
from src.research.brand_intelligence_identity import (
    domain_identity_signal,
    identity_signals_for_seed,
    linkedin_identity_signal,
    owned_web_identity_signal,
    resolve_brand_identity,
    resolve_brand_identity_from_signals,
    resolve_brand_seed,
    review_identity_signal,
    search_result_identity_signal,
)

def build_brand_source_plan(entity: ResolvedBrandEntity) -> BrandSourcePlan:
    """Plan multichannel brand evidence before Brand3 interpretation."""
    requests: list[BrandSourceRequest] = []
    missing: list[str] = []
    limitations = list(entity.limitations)

    if entity.canonical_url:
        requests.append(
            BrandSourceRequest(
                channel="owned_web",
                intent="official_brand_claims_and_visual_surface",
                url=entity.canonical_url,
                priority=10,
                reason="Official owned surface is one channel, not the whole brand.",
            )
        )
    else:
        missing.append("canonical_owned_surface")

    if entity.parent_url:
        requests.append(
            BrandSourceRequest(
                channel="parent_owned_web",
                intent="parent_brand_context",
                url=entity.parent_url,
                priority=20,
                reason="Parent brand can change interpretation of product brands.",
            )
        )

    search_entity = _search_label(entity)
    requests.extend(
        [
            BrandSourceRequest("search", "entity_disambiguation", query=f"{search_entity} official brand", priority=30),
            BrandSourceRequest("reviews", "external_perception_and_friction", query=f"{search_entity} reviews", priority=40),
            BrandSourceRequest("news", "reputation_momentum_and_category_context", query=f"{search_entity} news", priority=50, required=False),
            BrandSourceRequest("linkedin", "company_presence_team_and_category", query=f"{search_entity} LinkedIn", priority=60, required=False),
            BrandSourceRequest("social", "performed_voice_and_current_signals", query=f"{search_entity} social profiles", priority=70, required=False),
            BrandSourceRequest("visual", "visual_identity_surface", url=entity.canonical_url, priority=80, required=bool(entity.canonical_url)),
        ]
    )

    if entity.entity_type == "product":
        requests.append(
            BrandSourceRequest("app_store", "app_or_product_distribution_surface", query=f"{search_entity} app", priority=55, required=False)
        )
    if entity.entity_type == "ecosystem":
        requests.extend(
            [
                BrandSourceRequest("docs", "developer_product_reality", query=f"{search_entity} docs", priority=35),
                BrandSourceRequest("community", "ecosystem_adoption_and_participation", query=f"{search_entity} community", priority=65, required=False),
            ]
        )
    if entity.resolution_status != "resolved":
        missing.append("verified_entity_resolution")
        limitations.append("brand_interpretation_must_remain_provisional")

    return BrandSourcePlan(
        resolution_status=entity.resolution_status,
        resolved_name=entity.resolved_name,
        interpretation_ready=entity.resolution_status == "resolved",
        source_requests=sorted(requests, key=lambda item: item.priority),
        required_missing=_unique(missing),
        limitations=_unique(limitations),
    )


def plan_brand_intelligence(seed: BrandSeed) -> tuple[ResolvedBrandEntity, BrandSourcePlan]:
    entity = resolve_brand_seed(seed)
    return entity, build_brand_source_plan(entity)


def build_brand_source_inventory(
    plan: BrandSourcePlan,
    observations: list[BrandSourceObservation],
) -> BrandSourceInventory:
    """Summarize source coverage before evidence extraction or interpretation."""
    required_channels = [request.channel for request in plan.source_requests if request.required]
    observed_eligible = {
        observation.channel
        for observation in observations
        if observation.status == "observed" and observation.evidence_eligibility in {"eligible", "limited"}
    }
    eligible_channels = _unique([channel for channel in required_channels if channel in observed_eligible])
    eligible_channels.extend(
        channel
        for channel in _unique([observation.channel for observation in observations if observation.channel in observed_eligible])
        if channel not in eligible_channels
    )
    missing_required = [
        channel
        for channel in required_channels
        if channel not in observed_eligible
    ]
    deferred_channels = _unique(
        [
            observation.channel
            for observation in observations
            if observation.status == "deferred"
        ]
    )
    duplicate_urls = _duplicate_source_urls(observations)
    conflicting_urls = _conflicting_source_urls(observations)
    limitations = list(plan.limitations)
    if missing_required:
        limitations.append("missing_required_sources")
    if not eligible_channels:
        limitations.append("no_evidence_eligible_sources")
    if plan.required_missing:
        limitations.append("identity_or_source_plan_missing_requirements")
    if duplicate_urls:
        limitations.append("duplicate_source_observations")
    if conflicting_urls:
        limitations.append("conflicting_source_observations")
    return BrandSourceInventory(
        resolved_name=plan.resolved_name,
        observations=observations,
        missing_required_channels=_unique(missing_required),
        deferred_channels=deferred_channels,
        eligible_channels=_unique(eligible_channels),
        duplicate_source_urls=duplicate_urls,
        conflicting_source_urls=conflicting_urls,
        limitations=_unique(limitations),
    )


def search_source_observation(
    result: dict[str, object],
    *,
    provider: str = "exa",
    channel: SourceChannel = "search",
) -> BrandSourceObservation:
    url = str(result.get("url") or "").strip()
    title = str(result.get("title") or "").strip()
    text = str(result.get("text") or result.get("summary") or result.get("snippet") or "").strip()
    score = _coerce_float(result.get("score"), default=0.0)
    freshness = str(result.get("published_date") or result.get("date") or "unknown").strip() or "unknown"
    if not url and not title:
        return BrandSourceObservation(
            channel,
            "not_observed",
            provider=provider,
            freshness=freshness,
            reason="missing_url_and_title",
        )
    if len(text) >= 80:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url) if url else "",
            provider,
            title,
            freshness,
            round(max(0.7, min(0.95, score or 0.74)), 4),
            "eligible",
            "search_result_with_extractable_context",
        )
    return BrandSourceObservation(
        channel,
        "observed",
        _normalize_url(url) if url else "",
        provider,
        title,
        freshness,
        round(max(0.45, min(0.7, score or 0.52)), 4),
        "limited",
        "search_result_without_rich_context",
    )


def scope_external_observation_to_entity(
    observation: BrandSourceObservation,
    result: dict[str, object],
    *,
    entity: ResolvedBrandEntity,
    seed_url: str = "",
    brand: str = "",
) -> BrandSourceObservation:
    """Quarantine external observations that do not prove the URL-resolved entity."""
    if observation.status != "observed" or observation.channel not in {"search", "reviews", "news"}:
        return observation
    from src.research.brand_intelligence_identity import (
        _external_result_matches_entity,
        _external_result_text,
        _near_entity_token_collision,
    )

    text = _external_result_text(result)
    if _external_result_matches_entity(text, entity=entity, seed_url=seed_url, brand=brand):
        return observation
    reason = (
        "external_result_entity_boundary_collision"
        if _near_entity_token_collision(text, entity=entity, brand=brand)
        else "external_result_entity_relevance_not_confirmed"
    )
    return replace(
        observation,
        evidence_eligibility="ineligible",
        confidence=min(observation.confidence, 0.2),
        reason=reason,
    )


def owned_web_source_observation(
    capture: dict[str, object],
    *,
    provider: str = "firecrawl",
    channel: SourceChannel = "owned_web",
) -> BrandSourceObservation:
    url = str(capture.get("url") or capture.get("source_url") or capture.get("canonical_url") or "").strip()
    title = str(capture.get("title") or capture.get("metadata_title") or "").strip()
    text = str(capture.get("markdown") or capture.get("text") or capture.get("content") or "").strip()
    freshness = str(capture.get("captured_at") or capture.get("fetched_at") or "unknown").strip() or "unknown"
    error = str(capture.get("error") or "").strip()
    if error:
        return BrandSourceObservation(
            channel,
            "error",
            _normalize_url(url) if url else "",
            provider,
            title,
            freshness,
            0.0,
            "ineligible",
            "provider_error",
            [error],
        )
    if not url:
        return BrandSourceObservation(
            channel,
            "not_observed",
            provider=provider,
            title=title,
            freshness=freshness,
            reason="missing_source_url",
        )
    if len(text) >= 500:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url),
            provider,
            title,
            freshness,
            0.88,
            "eligible",
            "owned_web_capture_with_extractable_content",
        )
    if len(text) >= 120:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url),
            provider,
            title,
            freshness,
            0.62,
            "limited",
            "owned_web_capture_with_thin_content",
        )
    return BrandSourceObservation(
        channel,
        "observed",
        _normalize_url(url),
        provider,
        title,
        freshness,
        0.25,
        "ineligible",
        "owned_web_capture_too_thin_for_evidence",
    )


def review_source_observation(
    listing: dict[str, object],
    *,
    provider: str = "review-source",
    channel: SourceChannel = "reviews",
) -> BrandSourceObservation:
    name = str(listing.get("name") or listing.get("product_name") or listing.get("title") or "").strip()
    url = str(listing.get("url") or listing.get("source_url") or "").strip()
    review_count = _coerce_float(listing.get("review_count") or listing.get("reviews_count"), default=0.0)
    rating = _coerce_float(listing.get("rating"), default=0.0)
    text = str(listing.get("summary") or listing.get("text") or listing.get("description") or "").strip()
    if not name:
        return BrandSourceObservation(
            channel,
            "not_observed",
            _normalize_url(url) if url else "",
            provider,
            freshness=str(listing.get("updated_at") or "unknown"),
            reason="missing_review_listing_name",
        )
    if review_count >= 10 and len(text) >= 80:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url) if url else "",
            provider,
            name,
            str(listing.get("updated_at") or "unknown"),
            round(min(0.9, max(0.72, (rating / 5) if rating else 0.72)), 4),
            "eligible",
            "review_listing_with_volume_and_context",
        )
    if review_count > 0 or len(text) >= 40:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url) if url else "",
            provider,
            name,
            str(listing.get("updated_at") or "unknown"),
            0.55,
            "limited",
            "review_listing_with_limited_volume_or_context",
        )
    return BrandSourceObservation(
        channel,
        "observed",
        _normalize_url(url) if url else "",
        provider,
        name,
        str(listing.get("updated_at") or "unknown"),
        0.25,
        "ineligible",
        "review_listing_without_review_signal",
    )


def profile_source_observation(
    profile: dict[str, object],
    *,
    provider: str = "profile-source",
    channel: SourceChannel = "social",
) -> BrandSourceObservation:
    name = str(profile.get("name") or profile.get("handle") or profile.get("title") or "").strip()
    url = str(profile.get("url") or profile.get("profile_url") or "").strip()
    description = str(profile.get("description") or profile.get("bio") or profile.get("summary") or "").strip()
    verified = bool(profile.get("verified") or profile.get("is_verified"))
    follower_count = _coerce_float(profile.get("followers") or profile.get("follower_count"), default=0.0)
    freshness = str(profile.get("updated_at") or profile.get("captured_at") or "unknown").strip() or "unknown"
    if not name and not url:
        return BrandSourceObservation(
            channel,
            "not_observed",
            provider=provider,
            freshness=freshness,
            reason="missing_profile_identity",
        )
    if verified and len(description) >= 60:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url) if url else "",
            provider,
            name,
            freshness,
            0.82,
            "eligible",
            "verified_profile_with_context",
        )
    if verified or follower_count >= 1000 or len(description) >= 40:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url) if url else "",
            provider,
            name,
            freshness,
            0.58,
            "limited",
            "profile_with_partial_authority_or_context",
        )
    return BrandSourceObservation(
        channel,
        "observed",
        _normalize_url(url) if url else "",
        provider,
        name,
        freshness,
        0.22,
        "ineligible",
        "profile_without_authority_or_context",
    )


def evidence_item_from_observation(
    observation: BrandSourceObservation,
    text: str,
    *,
    kind: BrandEvidenceKind | None = None,
    supports: list[str] | None = None,
) -> BrandEvidenceItem:
    cleaned = " ".join(str(text or "").split())
    inferred_kind = kind or _evidence_kind_for_channel(observation.channel)
    limitations: list[str] = []
    if observation.evidence_eligibility == "ineligible" or observation.status != "observed":
        strength: EvidenceStrength = "blocked"
        limitations.append("source_not_evidence_eligible")
    elif len(cleaned) < 40:
        strength = "blocked"
        limitations.append("excerpt_too_short_for_evidence")
    elif observation.evidence_eligibility == "limited":
        strength = "weak"
        limitations.append("limited_source_context")
    elif observation.channel in {"owned_web", "parent_owned_web"}:
        strength = "moderate"
        limitations.append("owned_claim_not_external_validation")
    else:
        strength = "strong" if observation.confidence >= 0.75 else "moderate"
    return BrandEvidenceItem(
        evidence_id=_brand_evidence_id(inferred_kind, cleaned, observation.source_url, observation.provider),
        kind=inferred_kind,
        text=cleaned,
        source_channel=observation.channel,
        source_url=observation.source_url,
        provider=observation.provider,
        source_title=observation.title,
        quote=cleaned,
        attribution=_attribution_for_channel(observation.channel),
        strength=strength,
        confidence=observation.confidence,
        supports=_unique(supports or _supports_for_evidence_kind(inferred_kind)),
        limitations=_unique(limitations),
    )


def build_brand_evidence_graph(
    inventory: BrandSourceInventory,
    evidence_items: list[BrandEvidenceItem],
) -> BrandEvidenceGraph:
    accepted: list[BrandEvidenceItem] = []
    rejected: list[BrandEvidenceItem] = []
    seen_ids: set[str] = set()
    for item in evidence_items:
        if item.evidence_id in seen_ids:
            rejected.append(_reject_evidence_item(item, "duplicate_evidence_item"))
            continue
        seen_ids.add(item.evidence_id)
        if item.strength == "blocked":
            rejected.append(item)
            continue
        accepted.append(item)

    gaps = list(inventory.missing_required_channels)
    warnings = list(inventory.limitations)
    if not accepted:
        gaps.append("no_evidence_items")
    if not any(item.kind == "external_perception" for item in accepted):
        warnings.append("external_perception_not_evidenced")
    if not any(item.kind in {"owned_claim", "parent_owned_claim"} for item in accepted):
        warnings.append("owned_claims_not_evidenced")
    if inventory.duplicate_source_urls:
        warnings.append("evidence_graph_has_duplicate_source_risk")
    if inventory.conflicting_source_urls:
        warnings.append("evidence_graph_has_conflicting_source_risk")
    return BrandEvidenceGraph(
        resolved_name=inventory.resolved_name,
        evidence=accepted,
        rejected=rejected,
        gaps=_unique(gaps),
        warnings=_unique(warnings),
    )


def evaluate_brand_identity_bakeoff(cases: list[BrandIdentityBakeoffCase]) -> dict[str, object]:
    results = [_evaluate_identity_case(case) for case in cases]
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    known = [result for result in results if result.known_case]
    unknown = [result for result in results if not result.known_case]
    return {
        "version": IDENTITY_BAKEOFF_VERSION,
        "case_count": total,
        "passed_count": passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "known_case_count": len(known),
        "unknown_case_count": len(unknown),
        "known_accuracy": round(sum(1 for result in known if result.passed) / len(known), 4) if known else 0.0,
        "unknown_accuracy": round(sum(1 for result in unknown if result.passed) / len(unknown), 4) if unknown else 0.0,
        "misresolved_count": sum(1 for result in results if result.misresolved),
        "results": [result.to_dict() for result in results],
    }


def evaluate_brand_source_bakeoff(cases: list[BrandSourceBakeoffCase]) -> dict[str, object]:
    results = [_evaluate_source_case(case) for case in cases]
    provider_observations: dict[str, list[BrandSourceObservation]] = {}
    for case in cases:
        for observation in case.observations:
            provider_observations.setdefault(observation.provider or "unknown", []).append(observation)
    provider_metrics = {
        provider: _source_observation_metrics(observations)
        for provider, observations in sorted(provider_observations.items())
    }
    return {
        "version": SOURCE_OBSERVATION_BAKEOFF_VERSION,
        "case_count": len(results),
        "inventory_ready_count": sum(1 for result in results if result.inventory_ready),
        "provider_count": len(provider_metrics),
        "provider_metrics": provider_metrics,
        "results": [result.to_dict() for result in results],
    }


def _evaluate_source_case(case: BrandSourceBakeoffCase) -> BrandSourceBakeoffResult:
    inventory = build_brand_source_inventory(case.plan, case.observations)
    inventory_ready = not inventory.missing_required_channels and not case.plan.required_missing
    return BrandSourceBakeoffResult(
        case_id=case.case_id,
        inventory_ready=inventory_ready,
        missing_required_channels=inventory.missing_required_channels,
        eligible_channels=inventory.eligible_channels,
        provider_metrics=_provider_metrics_for_case(case.observations),
        inventory=inventory,
    )


def _evaluate_identity_case(case: BrandIdentityBakeoffCase) -> BrandIdentityBakeoffResult:
    resolution = resolve_brand_identity_from_signals(case.seed, case.signals)
    selected = resolution.selected_candidate
    actual_name = selected.name if selected else ""
    status_pass = resolution.status == case.expected_status
    name_pass = not case.expected_name or _normalize_name(actual_name) == _normalize_name(case.expected_name)
    passed = status_pass and name_pass
    misresolved = case.expected_status != "resolved" and resolution.status == "resolved"
    return BrandIdentityBakeoffResult(
        case_id=case.case_id,
        expected_status=case.expected_status,
        actual_status=resolution.status,
        expected_name=case.expected_name,
        actual_name=actual_name,
        passed=passed,
        known_case=case.known_case,
        misresolved=misresolved,
        resolution=resolution,
    )


def _provider_metrics_for_case(observations: list[BrandSourceObservation]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[BrandSourceObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.provider or "unknown", []).append(observation)
    return {
        provider: _source_observation_metrics(items)
        for provider, items in sorted(grouped.items())
    }


def _source_observation_metrics(observations: list[BrandSourceObservation]) -> dict[str, object]:
    eligible_observations = [
        observation
        for observation in observations
        if observation.status == "observed" and observation.evidence_eligibility in {"eligible", "limited"}
    ]
    confidence_values = [observation.confidence for observation in observations if observation.confidence > 0]
    latency_values = [observation.latency_ms for observation in observations if observation.latency_ms > 0]
    cost_values = [observation.cost_estimate for observation in observations if observation.cost_estimate is not None]
    source_class_counts: dict[str, int] = {}
    for observation in observations:
        source_class = observation.source_class or "unknown"
        source_class_counts[source_class] = source_class_counts.get(source_class, 0) + 1
    return {
        "observation_count": len(observations),
        "observed_count": sum(1 for item in observations if item.status == "observed"),
        "eligible_count": sum(1 for item in observations if item.evidence_eligibility == "eligible"),
        "limited_count": sum(1 for item in observations if item.evidence_eligibility == "limited"),
        "ineligible_count": sum(1 for item in observations if item.evidence_eligibility == "ineligible"),
        "error_count": sum(1 for item in observations if item.status == "error"),
        "human_review_count": sum(1 for item in observations if item.requires_human_review),
        "covered_channels": _unique([item.channel for item in eligible_observations]),
        "average_confidence": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
        "average_latency_ms": round(sum(latency_values) / len(latency_values), 1) if latency_values else 0.0,
        "total_cost_estimate": round(sum(cost_values), 8) if cost_values else 0.0,
        "average_cost_estimate": round(sum(cost_values) / len(cost_values), 8) if cost_values else 0.0,
        "source_class_counts": dict(sorted(source_class_counts.items())),
    }


def _reject_evidence_item(item: BrandEvidenceItem, reason: str) -> BrandEvidenceItem:
    return BrandEvidenceItem(
        evidence_id=item.evidence_id,
        kind=item.kind,
        text=item.text,
        source_channel=item.source_channel,
        source_url=item.source_url,
        provider=item.provider,
        source_title=item.source_title,
        quote=item.quote,
        attribution=item.attribution,
        strength="blocked",
        confidence=item.confidence,
        supports=list(item.supports),
        limitations=_unique(list(item.limitations) + [reason]),
    )


def _evidence_kind_for_channel(channel: SourceChannel) -> BrandEvidenceKind:
    return {
        "owned_web": "owned_claim",
        "parent_owned_web": "parent_owned_claim",
        "search": "external_context",
        "news": "external_context",
        "reviews": "external_perception",
        "linkedin": "profile_presence",
        "social": "profile_presence",
        "app_store": "distribution_signal",
        "visual": "visual_signal",
        "docs": "owned_claim",
        "community": "external_context",
        "jobs": "external_context",
    }.get(channel, "unknown")


def _supports_for_evidence_kind(kind: BrandEvidenceKind) -> list[str]:
    return {
        "owned_claim": ["brand_idea", "value_proposition"],
        "parent_owned_claim": ["brand_architecture", "brand_idea"],
        "external_context": ["category_context", "reputation"],
        "external_perception": ["perception", "proof"],
        "profile_presence": ["presence", "credibility"],
        "visual_signal": ["visual_identity"],
        "distribution_signal": ["availability", "product_reality"],
    }.get(kind, [])


def _attribution_for_channel(channel: SourceChannel) -> str:
    if channel in {"owned_web", "parent_owned_web", "docs"}:
        return "owned_self_declaration"
    if channel in {"reviews", "news", "search", "community", "jobs"}:
        return "external_observation"
    if channel in {"linkedin", "social", "app_store"}:
        return "profile_or_distribution_observation"
    if channel == "visual":
        return "observed_visual_surface"
    return "unknown_attribution"


def _duplicate_source_urls(observations: list[BrandSourceObservation]) -> list[str]:
    counts: dict[str, int] = {}
    for observation in observations:
        key = _source_url_key(observation.source_url)
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return sorted([url for url, count in counts.items() if count > 1])


def _conflicting_source_urls(observations: list[BrandSourceObservation]) -> list[str]:
    titles_by_url: dict[str, set[str]] = {}
    for observation in observations:
        key = _source_url_key(observation.source_url)
        title = _title_key(observation.title)
        if not key or not title:
            continue
        titles_by_url.setdefault(key, set()).add(title)
    return sorted([url for url, titles in titles_by_url.items() if len(titles) > 1])


def _normalize_url(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path).lower()
    path = parsed.path if parsed.netloc else ""
    return f"{parsed.scheme or 'https'}://{host}{path}".rstrip("/")


def _source_url_key(value: str) -> str:
    normalized = _normalize_url(value)
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").rstrip("/")
    return f"https://{host}{path}"


def _brand_evidence_id(kind: str, text: str, source_url: str, provider: str) -> str:
    raw = "|".join([kind, text, _source_url_key(source_url), provider])
    return f"brand_ev_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def _host(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _root_domain(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if parts[-2:] == ["co", "uk"] and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _label_from_host(host: str) -> str:
    label = (host or "").split(".")[0].replace("-", " ")
    known = {"chatgpt": "ChatGPT", "langchain": "LangChain", "naturaumana": "Natura Umana"}
    return known.get(label.lower(), label.title() if label else "")


def _clean_candidate_name(value: str) -> str:
    cleaned = str(value or "").strip()
    for separator in (" | ", " - ", " – ", " — "):
        if separator in cleaned:
            cleaned = cleaned.split(separator, 1)[0].strip()
    return cleaned


def _candidate_from_search_title(title: str) -> str:
    value = _clean_candidate_name(title)
    for prefix in ("official ", "about "):
        if value.lower().startswith(prefix):
            value = value[len(prefix):].strip()
    return value


def _parent_from_text(text: str) -> str | None:
    low = (text or "").lower()
    if "openai" in low:
        return "OpenAI"
    if "anthropic" in low:
        return "Anthropic"
    return None


def _known_parent_url(parent: str | None) -> str | None:
    if parent == "OpenAI":
        return "https://openai.com"
    if parent == "Anthropic":
        return "https://anthropic.com"
    return None


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


def _title_key(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _coerce_float(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _search_label(entity: ResolvedBrandEntity) -> str:
    if entity.parent_brand and entity.product_name:
        return f"{entity.parent_brand} {entity.product_name}"
    return entity.resolved_name or entity.requested_value or "Unknown brand"


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
