"""Preparation helpers for Brand3 analysis runs."""

from __future__ import annotations

from dataclasses import dataclass

from src.collectors.competitor_collector import CompetitorData
from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData
from src.collectors.web_collector import WebCollector, WebData
from src.services.run_preparation_discovery import (
    DiscoveryArtifacts,
    DiscoveryCalibration,
    DiscoveryPreparation,
    _build_competitor_names,
    _build_niche_exa_texts,
    build_discovery_artifacts,
    build_discovery_calibration,
    build_discovery_preparation,
)


@dataclass
class NicheSelection:
    classification: dict
    calibration_profile: str
    profile_source: str


@dataclass
class ContentPlan:
    content_web: WebData | None
    content_source: str
    data_sources: dict[str, object]
    data_quality: str
    partial_dimensions: list[str]


@dataclass
class LlmSetup:
    llm: object | None
    provider: dict[str, object] | None
    skipped_reason: str | None
def select_niche_profile(
    *,
    brand_name: str,
    url: str,
    web_data: WebData | None,
    exa_data: ExaData | None,
    competitor_data: CompetitorData | None,
    calibration_profile_override: str | None,
    min_confidence: float,
    classify_brand_niche,
    select_calibration_profile,
) -> NicheSelection:
    exa_texts = _build_niche_exa_texts(exa_data)
    competitor_names = _build_competitor_names(competitor_data)

    classification = classify_brand_niche(
        brand_name,
        url,
        web_title=web_data.title if web_data else None,
        web_content=web_data.markdown_content if web_data else None,
        exa_texts=exa_texts,
        competitor_names=competitor_names,
    )
    if calibration_profile_override:
        calibration_profile = calibration_profile_override
        profile_source = "manual"
    else:
        calibration_profile, profile_source = select_calibration_profile(
            classification,
            min_confidence=min_confidence,
        )
    print(
        "  Niche:"
        f" {classification['predicted_niche']}"
        f"/{classification.get('predicted_subtype') or '-'}"
        f" ({classification['confidence']:.2f})"
        f" -> profile {calibration_profile} [{profile_source}]"
    )
    return NicheSelection(
        classification=classification,
        calibration_profile=calibration_profile,
        profile_source=profile_source,
    )


def plan_content(
    *,
    url: str,
    brand_name: str,
    web_data: WebData | None,
    context_data: ContextData | None,
    web_collector: WebCollector,
    exa_data: ExaData | None,
    recover_owned_web_content,
    build_content_web,
    compute_data_quality,
    partial_dimensions: tuple[str, ...],
) -> ContentPlan:
    content_web, content_source, data_sources = build_content_web(
        url,
        brand_name,
        recover_owned_web_content(url, web_data, web_collector, context_data) or web_data,
        exa_data,
    )
    data_quality = compute_data_quality(exa_data, content_source)
    limited_dimensions = list(partial_dimensions) if data_quality == "insufficient" else []

    if content_source == "owned_fallback" and content_web:
        print(
            "  Web fallback:"
            f" using {len(data_sources.get('owned_fallback_urls') or [])} owned same-domain pages"
            f" as content source ({len(content_web.markdown_content)} chars aggregate)"
        )
    elif content_source == "exa_fallback" and content_web:
        print(
            "  Web fallback:"
            f" using {data_sources['exa_fallback_mentions_used']} Exa mentions"
            f" as content source ({len(content_web.markdown_content)} chars aggregate)"
        )
    elif content_source == "none":
        print("  Web fallback: no usable Firecrawl, owned fallback, or Exa content available")
    print(f"  Data quality: {data_quality}")

    return ContentPlan(
        content_web=content_web,
        content_source=content_source,
        data_sources=data_sources,
        data_quality=data_quality,
        partial_dimensions=limited_dimensions,
    )


def _build_llm_setup_result(
    *,
    llm_cls,
    cheap_model: str,
    provider_payload_builder,
    skipped_reason: str | None,
    ) -> LlmSetup:
    llm = llm_cls(model=cheap_model)
    provider = provider_payload_builder(llm)
    if skipped_reason is None and llm.api_key:
        return LlmSetup(llm=llm, provider=provider, skipped_reason=None)
    if skipped_reason is None:
        print("  LLM: disabled (no key found)")
        skipped_reason = "missing_api_key"
    return LlmSetup(llm=None, provider=provider, skipped_reason=skipped_reason)


def setup_llm(
    *,
    use_llm: bool,
    context_data: ContextData | None,
    content_web: WebData | None,
    content_source: str,
    llm_cls,
    cheap_model: str,
    provider_payload_builder,
    should_skip_llm_for_low_context,
) -> LlmSetup:
    if not use_llm:
        return LlmSetup(llm=None, provider=None, skipped_reason=None)

    if should_skip_llm_for_low_context(context_data, content_web, content_source):
        print("  LLM: skipped (insufficient context coverage)")
        return LlmSetup(llm=None, provider=None, skipped_reason="insufficient_context_coverage")

    setup = _build_llm_setup_result(
        llm_cls=llm_cls,
        cheap_model=cheap_model,
        provider_payload_builder=provider_payload_builder,
        skipped_reason=None,
    )
    if setup.llm is not None:
        print(f"  LLM: {setup.llm.model} via {setup.provider['provider']}")
    return setup
