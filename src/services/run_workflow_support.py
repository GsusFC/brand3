"""Helpers for analysis run workflow orchestration."""

from __future__ import annotations


def resolve_brand_name(url: str, brand_name: str | None) -> str:
    if brand_name:
        return brand_name
    return url.replace("https://", "").replace("http://", "").split("/")[0]


def phase_two_kwargs(prepared) -> dict:
    return {
        "web_data": prepared.web_data,
        "content_web": prepared.content_web,
        "exa_data": prepared.exa_data,
        "social_data": prepared.social_data,
        "context_data": prepared.context_data,
        "competitor_data": prepared.competitor_data,
        "llm": prepared.llm,
        "data_quality": prepared.data_quality,
        "content_source": prepared.content_source,
        "research_pack_for_feature_prompts": prepared.research_pack_for_feature_prompts,
        "partial_dimensions": prepared.partial_dimensions,
        "calibration_profile": prepared.calibration_profile,
    }


def finalization_kwargs(
    *,
    prepared,
    phase_two: dict,
    brand_score,
    summary: str,
    brand_name: str,
    url: str,
    use_llm: bool,
    use_social: bool,
    use_competitors: bool,
    skip_visual_analysis: bool,
    llm_provider,
    llm_skipped_reason,
) -> dict:
    return {
        "brand_name": brand_name,
        "url": url,
        "web_data": prepared.web_data,
        "content_web": prepared.content_web,
        "exa_data": prepared.exa_data,
        "content_source": prepared.content_source,
        "data_quality": prepared.data_quality,
        "partial_dimensions": prepared.partial_dimensions,
        "social_data": prepared.social_data,
        "use_llm": use_llm,
        "use_social": use_social,
        "use_competitors": use_competitors,
        "skip_visual_analysis": skip_visual_analysis,
        "llm": prepared.llm,
        "llm_provider": llm_provider,
        "llm_skipped_reason": llm_skipped_reason,
        "calibration_profile": prepared.calibration_profile,
        "niche_classification": prepared.niche_classification,
        "research_pack_for_feature_prompts": prepared.research_pack_for_feature_prompts,
        "entity_discovery": prepared.entity_discovery,
        "discovery_search_plan": prepared.discovery_search_plan,
        "discovery_evidence_preview": prepared.discovery_evidence_preview,
        "discovery_enrichment_payload": prepared.discovery_enrichment_payload,
        "discovery_payload": prepared.discovery_payload,
        "discovery_trust_basis": prepared.discovery_trust_basis,
        "discovery_calibration_hint": prepared.discovery_calibration_hint,
        "discovery_calibration_decision": prepared.discovery_calibration_decision,
        "entity_research_packet": prepared.entity_research_packet,
        "acquisition_provenance": prepared.acquisition_provenance,
        "acquisition_steps": prepared.acquisition_steps,
        "raw_input_cache": prepared.raw_input_cache,
        "screenshot_capture": phase_two["screenshot_capture"],
        "base_data_sources": prepared.data_sources,
        "social_limitation": prepared.social_limitation,
        "context_data": prepared.context_data,
        "features_by_dim": phase_two["features_by_dim"],
        "brand_score": brand_score,
        "summary": summary,
    }


def mark_run_status(service, store, run_id: int | None, status: str) -> None:
    if run_id:
        service._store_safely(store, f"run status {status}", lambda: store.mark_run_status(run_id, status))
