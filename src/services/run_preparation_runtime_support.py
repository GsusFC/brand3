"""Support helpers for run preparation orchestration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PreparedRun:
    context_data: object
    web_data: object
    effective_brand_url: str | None
    exa_data: object
    social_data: object
    social_limitation: str | None
    competitor_data: object
    raw_input_cache: dict
    acquisition_steps: dict
    web_collector: object
    niche_classification: dict
    calibration_profile: str
    profile_source: str
    content_web: object
    content_source: str
    data_sources: dict
    data_quality: str
    partial_dimensions: list[str]
    entity_discovery: dict
    discovery_search_plan: dict
    entity_research_packet: dict
    discovery_evidence_preview: dict
    discovery_enrichment_payload: dict
    acquisition_provenance: dict
    discovery_trust_basis: dict
    discovery_calibration_hint: dict
    discovery_calibration_decision: dict
    discovery_payload: dict
    research_pack_for_feature_prompts: object
    llm: object | None
    llm_provider: dict | None
    llm_skipped_reason: str | None


def raw_inputs_state(raw_inputs) -> dict:
    return {
        "context_data": raw_inputs.context_data,
        "web_data": raw_inputs.web_data,
        "effective_brand_url": raw_inputs.effective_brand_url,
        "exa_data": raw_inputs.exa_data,
        "social_data": raw_inputs.social_data,
        "social_limitation": raw_inputs.social_limitation,
        "competitor_data": raw_inputs.competitor_data,
        "raw_input_cache": raw_inputs.raw_input_cache,
        "acquisition_steps": raw_inputs.acquisition_steps,
        "web_collector": raw_inputs.web_collector,
        "exa_collector": raw_inputs.exa_collector,
    }


def discovery_state(discovery) -> dict:
    return {
        "entity_discovery": discovery.entity_discovery,
        "discovery_search_plan": discovery.discovery_search_plan,
        "entity_research_packet": discovery.entity_research_packet,
        "discovery_evidence_preview": discovery.discovery_evidence_preview,
        "discovery_enrichment_payload": discovery.discovery_enrichment_payload,
        "acquisition_provenance": discovery.acquisition_provenance,
        "discovery_trust_basis": discovery.discovery_trust_basis,
        "discovery_calibration_hint": discovery.discovery_calibration_hint,
        "discovery_calibration_decision": discovery.discovery_calibration_decision,
        "discovery_payload": discovery.discovery_payload,
        "research_pack_for_feature_prompts": discovery.research_pack_for_feature_prompts,
        "calibration_profile": discovery.calibration_profile,
        "profile_source": discovery.profile_source,
        "web_data": discovery.web_data,
        "exa_data": discovery.exa_data,
        "content_web": discovery.content_web,
    }


def build_prepared_run(
    *,
    raw_state: dict,
    discovery_state: dict,
    llm_setup,
    niche_classification: dict,
    content_plan,
) -> PreparedRun:
    return PreparedRun(
        context_data=raw_state["context_data"],
        web_data=discovery_state["web_data"],
        effective_brand_url=raw_state["effective_brand_url"],
        exa_data=discovery_state["exa_data"],
        social_data=raw_state["social_data"],
        social_limitation=raw_state["social_limitation"],
        competitor_data=raw_state["competitor_data"],
        raw_input_cache=raw_state["raw_input_cache"],
        acquisition_steps=raw_state["acquisition_steps"],
        web_collector=raw_state["web_collector"],
        niche_classification=niche_classification,
        calibration_profile=discovery_state["calibration_profile"],
        profile_source=discovery_state["profile_source"],
        content_web=discovery_state["content_web"],
        content_source=content_plan.content_source,
        data_sources=content_plan.data_sources,
        data_quality=content_plan.data_quality,
        partial_dimensions=content_plan.partial_dimensions,
        entity_discovery=discovery_state["entity_discovery"],
        discovery_search_plan=discovery_state["discovery_search_plan"],
        entity_research_packet=discovery_state["entity_research_packet"],
        discovery_evidence_preview=discovery_state["discovery_evidence_preview"],
        discovery_enrichment_payload=discovery_state["discovery_enrichment_payload"],
        acquisition_provenance=discovery_state["acquisition_provenance"],
        discovery_trust_basis=discovery_state["discovery_trust_basis"],
        discovery_calibration_hint=discovery_state["discovery_calibration_hint"],
        discovery_calibration_decision=discovery_state["discovery_calibration_decision"],
        discovery_payload=discovery_state["discovery_payload"],
        research_pack_for_feature_prompts=discovery_state["research_pack_for_feature_prompts"],
        llm=llm_setup.llm,
        llm_provider=llm_setup.provider,
        llm_skipped_reason=llm_setup.skipped_reason,
    )
