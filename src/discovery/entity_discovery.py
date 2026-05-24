"""Deterministic entity discovery metadata.

This module is intentionally isolated from scoring, collection, calibration,
prompts, cache keys, and report rendering. It performs no network calls and
only returns structured metadata from deterministic local heuristics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlparse


EntityType = Literal[
    "company",
    "product",
    "protocol",
    "project",
    "nonprofit",
    "marketplace",
    "unknown",
]
AnalysisScope = Literal[
    "company_brand",
    "product_brand",
    "product_with_parent",
    "ecosystem",
    "url_only",
]


@dataclass(frozen=True)
class EntityDiscoveryResult:
    input_name: str
    input_url: str
    entity_name: str
    entity_type: EntityType
    analysis_scope: AnalysisScope
    canonical_brand_name: str
    canonical_url: str
    parent_brand_name: str | None = None
    parent_url: str | None = None
    product_name: str | None = None
    product_url: str | None = None
    confidence: float = 0.0
    evidence: list[dict[str, object]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def discover_entity(
    brand_name: str,
    url: str,
    web_data=None,
    exa_data=None,
    context_data=None,
) -> EntityDiscoveryResult:
    """Return deterministic entity-discovery metadata for a brand input."""
    input_name = (brand_name or "").strip()
    input_url = (url or "").strip()
    normalized_name = _normalize_name(input_name)
    canonical_input_url = _normalize_url(input_url)
    domain = _root_domain(_host(canonical_input_url))
    evidence = [_evidence("input", "brand_name", input_name, 0.5)]
    warnings: list[str] = []
    if canonical_input_url:
        evidence.append(_evidence("input", "url_domain", domain or canonical_input_url, 0.5))
    else:
        warnings.append("input_url_missing")

    # Known product-parent patterns.
    if normalized_name == "chatgpt" or domain == "chatgpt.com":
        evidence.append(_evidence("rule", "known_product_parent", "ChatGPT -> OpenAI", 0.95))
        return EntityDiscoveryResult(
            input_name=input_name,
            input_url=input_url,
            entity_name="ChatGPT",
            entity_type="product",
            analysis_scope="product_with_parent",
            canonical_brand_name="ChatGPT",
            canonical_url=canonical_input_url or "https://chatgpt.com",
            parent_brand_name="OpenAI",
            parent_url="https://openai.com",
            product_name="ChatGPT",
            product_url=canonical_input_url or "https://chatgpt.com",
            confidence=0.95,
            evidence=evidence,
            warnings=warnings,
        )

    if normalized_name == "claude" or domain == "claude.ai":
        evidence.append(_evidence("rule", "known_product_parent", "Claude -> Anthropic", 0.95))
        return EntityDiscoveryResult(
            input_name=input_name,
            input_url=input_url,
            entity_name="Claude",
            entity_type="product",
            analysis_scope="product_with_parent",
            canonical_brand_name="Claude",
            canonical_url=canonical_input_url or "https://claude.ai",
            parent_brand_name="Anthropic",
            parent_url="https://anthropic.com",
            product_name="Claude",
            product_url=canonical_input_url or "https://claude.ai",
            confidence=0.95,
            evidence=evidence,
            warnings=warnings,
        )

    # Known company mode.
    if normalized_name == "openai" or domain == "openai.com":
        evidence.append(_evidence("rule", "known_company", "OpenAI company brand", 0.95))
        return EntityDiscoveryResult(
            input_name=input_name,
            input_url=input_url,
            entity_name="OpenAI",
            entity_type="company",
            analysis_scope="company_brand",
            canonical_brand_name="OpenAI",
            canonical_url="https://openai.com",
            confidence=0.95,
            evidence=evidence,
            warnings=warnings,
        )

    if normalized_name == "anthropic" or domain == "anthropic.com":
        evidence.append(_evidence("rule", "known_company", "Anthropic company brand", 0.95))
        return EntityDiscoveryResult(
            input_name=input_name,
            input_url=input_url,
            entity_name="Anthropic",
            entity_type="company",
            analysis_scope="company_brand",
            canonical_brand_name="Anthropic",
            canonical_url="https://anthropic.com",
            confidence=0.95,
            evidence=evidence,
            warnings=warnings,
        )

    # Known protocol/ecosystem mode.
    if normalized_name == "base" or domain == "base.org":
        evidence.append(_evidence("rule", "known_protocol_ecosystem", "Base/base.org ecosystem", 0.9))
        return EntityDiscoveryResult(
            input_name=input_name,
            input_url=input_url,
            entity_name="Base",
            entity_type="protocol",
            analysis_scope="ecosystem",
            canonical_brand_name="Base",
            canonical_url="https://base.org",
            confidence=0.9,
            evidence=evidence,
            warnings=warnings,
        )

    # Generic fallback.
    if _domain_matches_brand(domain, normalized_name):
        evidence.append(_evidence("heuristic", "brand_domain_match", domain or "", 0.72))
        canonical_name = _title_from_input(input_name, domain)
        return EntityDiscoveryResult(
            input_name=input_name,
            input_url=input_url,
            entity_name=canonical_name,
            entity_type="company",
            analysis_scope="company_brand",
            canonical_brand_name=canonical_name,
            canonical_url=canonical_input_url,
            confidence=0.72,
            evidence=evidence,
            warnings=warnings,
        )

    warnings.append("no_parent_or_product_relation_found")
    warnings.append("brand_domain_match_failed")
    return EntityDiscoveryResult(
        input_name=input_name,
        input_url=input_url,
        entity_name=input_name or domain or "Unknown",
        entity_type="unknown",
        analysis_scope="url_only",
        canonical_brand_name=input_name or domain or "Unknown",
        canonical_url=canonical_input_url,
        confidence=0.2 if input_name or canonical_input_url else 0.0,
        evidence=evidence,
        warnings=warnings,
    )


def _evidence(source: str, signal: str, value: str, confidence: float) -> dict[str, object]:
    return {
        "source": source,
        "signal": signal,
        "value": value,
        "confidence": confidence,
    }


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


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
    return ".".join(parts[-2:])


def _domain_matches_brand(domain: str, normalized_name: str) -> bool:
    if not domain or not normalized_name:
        return False
    domain_label = _normalize_name(domain.split(".")[0])
    return bool(domain_label and (domain_label == normalized_name or normalized_name in domain_label))


def _title_from_input(input_name: str, domain: str) -> str:
    if input_name:
        return input_name
    return (domain.split(".")[0] if domain else "Unknown").replace("-", " ").title()
