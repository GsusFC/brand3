"""Private helpers for brand_intelligence_core."""

from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from typing import Any
from urllib.parse import urlparse

from src.research.brand_intelligence import (
    BrandEvidenceGraph,
    BrandEvidenceItem,
    BrandIdentityBakeoffCase,
    BrandIdentityBakeoffResult,
    BrandSourceBakeoffCase,
    BrandSourceBakeoffResult,
    BrandSourceObservation,
    BrandSourceInventory,
    BrandSourcePlan,
    BrandSourceRequest,
    BrandEvidenceKind,
    EvidenceStrength,
    SourceChannel,
)
from src.research.brand_intelligence_identity import (
    resolve_brand_identity_from_signals,
)


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


def _search_label(entity) -> str:
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


def _badge_type_from_band(letter: str) -> str:
    if letter in ("A", "B"):
        return "ok"
    if letter in ("D", "F"):
        return "warn"
    return "neutral"


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


def _evaluate_source_case(case: BrandSourceBakeoffCase) -> BrandSourceBakeoffResult:
    from src.research.brand_intelligence_core import build_brand_source_inventory

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
