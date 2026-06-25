"""Discovery preparation helpers for Brand3 analysis runs."""

from __future__ import annotations

from dataclasses import dataclass

from src.collectors.competitor_collector import CompetitorData
from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData
from src.collectors.web_collector import WebCollector, WebData


@dataclass
class DiscoveryArtifacts:
    entity_discovery: dict
    discovery_search_plan: dict
    entity_research_packet: dict
    discovery_evidence_preview: dict
    discovery_enrichment_payload: dict
    acquisition_provenance: dict
    web_data: WebData | None
    exa_data: ExaData | None
    content_web: WebData | None


@dataclass
class DiscoveryCalibration:
    discovery_trust_basis: dict
    discovery_calibration_hint: dict
    discovery_calibration_decision: dict
    discovery_payload: dict
    research_pack_for_feature_prompts: object
    calibration_profile: str
    profile_source: str


@dataclass
class DiscoveryPreparation:
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
    calibration_profile: str
    profile_source: str
    web_data: WebData | None
    exa_data: ExaData | None
    content_web: WebData | None


def _build_niche_exa_texts(exa_data: ExaData | None) -> list[str]:
    exa_texts: list[str] = []
    if not exa_data:
        return exa_texts

    # Keep niche classification high-precision: full mention bodies are noisy
    # and regularly include unrelated keywords from long-form pages.
    exa_texts.extend([item.title for item in exa_data.mentions if item.title])
    exa_texts.extend([item.summary for item in exa_data.mentions if item.summary])
    for item in exa_data.mentions:
        if not item.highlights:
            continue
        exa_texts.extend(
            str(highlight).strip()
            for highlight in item.highlights[:2]
            if str(highlight).strip()
        )
    exa_texts.extend([item.title for item in exa_data.news if item.title])
    return exa_texts


def _build_competitor_names(competitor_data: CompetitorData | None) -> list[str]:
    if not competitor_data:
        return []
    return [item.name for item in competitor_data.competitors if item.name]


def build_discovery_artifacts(
    *,
    service,
    store,
    run_id: int | None,
    brand_name: str,
    url: str,
    web_data: WebData | None,
    content_web: WebData | None,
    exa_data: ExaData | None,
    context_data: ContextData | None,
    web_collector: WebCollector,
    exa_collector,
    raw_input_cache: dict,
    content_source: str,
    data_quality: str,
) -> DiscoveryArtifacts:
    entity_discovery = service._entity_discovery_payload(
        brand_name=brand_name,
        url=url,
        web_data=content_web or web_data,
        exa_data=exa_data,
        context_data=context_data,
    )
    discovery_search_plan = service._discovery_search_plan_payload(
        entity_discovery=entity_discovery,
        brand_name=brand_name,
        url=url,
    )
    entity_research_packet = service.build_entity_research_packet(
        input_url=url,
        brand_name=brand_name,
        entity_discovery=entity_discovery,
        discovery_search_plan=discovery_search_plan,
        web_data=content_web or web_data,
        exa_data=exa_data,
    ).to_dict()
    if run_id:
        service._store_safely(
            store,
            "entity research packet save",
            lambda: store.save_raw_input(run_id, "entity_research_packet", entity_research_packet),
        )
    discovery_evidence_preview = service._to_jsonable(
        service.build_discovery_evidence_preview(
            discovery_search_plan,
            exa_data=exa_data,
            web_data=content_web or web_data,
            context_data=context_data,
        )
    )
    discovery_enrichment = service.build_discovery_enrichment(
        discovery_search_plan,
        discovery_evidence_preview,
        exa_data=exa_data,
        web_data=content_web or web_data,
        web_collector=web_collector,
        exa_collector=exa_collector,
        entity_research_packet=entity_research_packet,
    )
    raw_web_data = web_data
    exa_data = discovery_enrichment.exa_data
    content_web = discovery_enrichment.web_data or content_web
    web_data = discovery_enrichment.web_data or web_data
    if run_id and service._web_content_changed(raw_web_data, content_web):
        effective_web_payload = service._to_jsonable(content_web)
        if isinstance(effective_web_payload, dict):
            effective_web_payload["derived"] = "discovery_enrichment"
        service._store_safely(
            store,
            "effective web input save",
            lambda: store.save_raw_input(run_id, "web", effective_web_payload),
        )
    acquisition_provenance = service._acquisition_provenance_summary(
        brand_name=brand_name,
        url=url,
        web_data=web_data,
        exa_data=exa_data,
        context_data=context_data,
        discovery_enrichment_payload=discovery_enrichment.payload,
        raw_input_cache=raw_input_cache,
        content_source=content_source,
        data_quality=data_quality,
    )
    return DiscoveryArtifacts(
        entity_discovery=entity_discovery,
        discovery_search_plan=discovery_search_plan,
        entity_research_packet=entity_research_packet,
        discovery_evidence_preview=discovery_evidence_preview,
        discovery_enrichment_payload=discovery_enrichment.payload,
        acquisition_provenance=acquisition_provenance,
        web_data=web_data,
        exa_data=exa_data,
        content_web=content_web,
    )


def build_discovery_calibration(
    *,
    service,
    store,
    run_id: int | None,
    artifacts: DiscoveryArtifacts,
    calibration_profile: str,
    profile_source: str,
    niche_classification: dict,
) -> DiscoveryCalibration:
    discovery_trust_basis = service.build_discovery_trust_basis(
        artifacts.entity_discovery,
        artifacts.discovery_search_plan,
        artifacts.discovery_evidence_preview,
        artifacts.discovery_enrichment_payload,
    )
    discovery_calibration_hint = service.build_discovery_calibration_hint(
        artifacts.entity_discovery,
        discovery_trust_basis,
        niche_classification,
    )
    available_profiles = {item["profile_id"] for item in service.list_calibration_profiles()}
    discovery_calibration_decision = service.apply_discovery_calibration_hint(
        current_profile=calibration_profile,
        current_profile_source=profile_source,
        discovery_calibration_hint=discovery_calibration_hint,
        discovery_evidence_preview=artifacts.discovery_evidence_preview,
        discovery_enrichment=artifacts.discovery_enrichment_payload,
        available_profiles=available_profiles,
    )
    calibration_profile = str(discovery_calibration_decision["calibration_profile"])
    profile_source = str(discovery_calibration_decision["profile_source"])
    discovery_payload = {
        "entity_discovery": artifacts.entity_discovery,
        "discovery_search_plan": artifacts.discovery_search_plan,
        "discovery_evidence_preview": artifacts.discovery_evidence_preview,
        "discovery_trust_basis": discovery_trust_basis,
        "discovery_calibration_hint": discovery_calibration_hint,
    }
    research_pack_for_feature_prompts = service._build_research_pack_for_feature_prompts(
        store=store,
        run_id=run_id,
    )
    return DiscoveryCalibration(
        discovery_trust_basis=discovery_trust_basis,
        discovery_calibration_hint=discovery_calibration_hint,
        discovery_calibration_decision=discovery_calibration_decision,
        discovery_payload=discovery_payload,
        research_pack_for_feature_prompts=research_pack_for_feature_prompts,
        calibration_profile=calibration_profile,
        profile_source=profile_source,
    )


def build_discovery_preparation(
    *,
    service,
    store,
    run_id: int | None,
    brand_name: str,
    url: str,
    web_data: WebData | None,
    content_web: WebData | None,
    exa_data: ExaData | None,
    context_data: ContextData | None,
    web_collector: WebCollector,
    exa_collector,
    raw_input_cache: dict,
    content_source: str,
    data_quality: str,
    calibration_profile: str,
    profile_source: str,
    niche_classification: dict,
) -> DiscoveryPreparation:
    artifacts = build_discovery_artifacts(
        service=service,
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        url=url,
        web_data=web_data,
        content_web=content_web,
        exa_data=exa_data,
        context_data=context_data,
        web_collector=web_collector,
        exa_collector=exa_collector,
        raw_input_cache=raw_input_cache,
        content_source=content_source,
        data_quality=data_quality,
    )
    calibration = build_discovery_calibration(
        service=service,
        store=store,
        run_id=run_id,
        artifacts=artifacts,
        calibration_profile=calibration_profile,
        profile_source=profile_source,
        niche_classification=niche_classification,
    )
    return DiscoveryPreparation(
        entity_discovery=artifacts.entity_discovery,
        discovery_search_plan=artifacts.discovery_search_plan,
        entity_research_packet=artifacts.entity_research_packet,
        discovery_evidence_preview=artifacts.discovery_evidence_preview,
        discovery_enrichment_payload=artifacts.discovery_enrichment_payload,
        acquisition_provenance=artifacts.acquisition_provenance,
        discovery_trust_basis=calibration.discovery_trust_basis,
        discovery_calibration_hint=calibration.discovery_calibration_hint,
        discovery_calibration_decision=calibration.discovery_calibration_decision,
        discovery_payload=calibration.discovery_payload,
        research_pack_for_feature_prompts=calibration.research_pack_for_feature_prompts,
        calibration_profile=calibration.calibration_profile,
        profile_source=calibration.profile_source,
        web_data=artifacts.web_data,
        exa_data=artifacts.exa_data,
        content_web=artifacts.content_web,
    )
