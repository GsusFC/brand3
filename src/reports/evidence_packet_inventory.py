"""Source inventory builder for evidence packets."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.reports.evidence_packet_analysis_support import (
    _first_url,
    _is_http_url,
)


def build_source_inventory(snapshot: dict, classified_candidates: list[dict]) -> list[dict]:
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

def _dedupe(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        key = str(item.get("url") or "") + "\0" + str(item.get("source_type") or "") + "\0" + str(item.get("role") or "")
        key += "\0" + str(item.get("notes") or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
