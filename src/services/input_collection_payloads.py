"""Payload conversion helpers for raw input collection."""

from __future__ import annotations

from dataclasses import asdict

from src.collectors.competitor_collector import ComparisonResult, CompetitorData, CompetitorInfo
from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import EXA_STRATEGY_VERSION, ExaData, ExaResult
from src.collectors.github_proof_collector import GITHUB_PROOF_VERSION, GitHubProofData
from src.collectors.hyperbrowser_collector import HyperbrowserFetchData
from src.collectors.parallel_shadow_collector import ParallelShadowData
from src.collectors.searchapi_collector import SEARCHAPI_STRATEGY_VERSION, SearchApiData
from src.collectors.social_collector import PlatformMetrics, SocialData
from src.collectors.web_collector import WebData


def from_web_payload(payload: dict | None) -> WebData | None:
    if not payload:
        return None
    return WebData(**payload)


def from_exa_payload(payload: dict | None) -> ExaData | None:
    if not payload:
        return None
    diagnostics = payload.get("diagnostics") or {}
    if not isinstance(diagnostics, dict) or diagnostics.get("strategy") != EXA_STRATEGY_VERSION:
        return None
    return ExaData(
        brand_name=payload.get("brand_name", ""),
        mentions=[ExaResult(**item) for item in payload.get("mentions", [])],
        profiles=[ExaResult(**item) for item in payload.get("profiles", [])],
        competitors=[ExaResult(**item) for item in payload.get("competitors", [])],
        ai_visibility_results=[ExaResult(**item) for item in payload.get("ai_visibility_results", [])],
        news=[ExaResult(**item) for item in payload.get("news", [])],
        raw_responses=payload.get("raw_responses", {}),
        diagnostics=diagnostics,
    )


def from_hyperbrowser_payload(payload: dict | None) -> HyperbrowserFetchData | None:
    if not payload:
        return None
    return HyperbrowserFetchData(**payload)


def from_parallel_shadow_payload(payload: dict | None) -> dict | None:
    return payload if isinstance(payload, dict) else None


def from_searchapi_payload(payload: dict | None) -> SearchApiData | None:
    if not payload:
        return None
    if payload.get("version") != SEARCHAPI_STRATEGY_VERSION:
        return None
    return SearchApiData.from_dict(payload)


def from_github_payload(payload: dict | None) -> GitHubProofData | None:
    if not payload:
        return None
    if payload.get("version") != GITHUB_PROOF_VERSION:
        return None
    return GitHubProofData.from_dict(payload)


def from_social_payload(payload: dict | None) -> SocialData | None:
    if not payload:
        return None
    return SocialData(
        brand_name=payload.get("brand_name", ""),
        platforms={
            name: PlatformMetrics(**metrics)
            for name, metrics in payload.get("platforms", {}).items()
        },
        profiles_found=payload.get("profiles_found", []),
        total_followers=payload.get("total_followers", 0),
        avg_post_frequency=payload.get("avg_post_frequency", 0.0),
        most_active_platform=payload.get("most_active_platform", ""),
        error=payload.get("error", ""),
    )


def from_competitor_payload(payload: dict | None) -> CompetitorData | None:
    if not payload:
        return None
    return CompetitorData(
        brand_name=payload.get("brand_name", ""),
        brand_url=payload.get("brand_url", ""),
        competitors=[
            CompetitorInfo(
                name=item.get("name", ""),
                url=item.get("url", ""),
                exa_result=ExaResult(**item["exa_result"]) if item.get("exa_result") else None,
                web_data=WebData(**item["web_data"]) if item.get("web_data") else None,
                error=item.get("error", ""),
            )
            for item in payload.get("competitors", [])
        ],
        comparisons=[ComparisonResult(**item) for item in payload.get("comparisons", [])],
        brand_web=WebData(**payload["brand_web"]) if payload.get("brand_web") else None,
        errors=payload.get("errors", []),
    )


def _competitor_storage_payload(competitor_data: CompetitorData) -> dict:
    """Drop competitor raw HTML before persisting."""
    payload = asdict(competitor_data)
    for competitor in payload.get("competitors") or []:
        web_data = competitor.get("web_data")
        if isinstance(web_data, dict):
            web_data["html"] = ""
    return payload


def from_context_payload(payload: dict | None) -> ContextData | None:
    if not payload:
        return None
    return ContextData(**payload)
