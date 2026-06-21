"""Run preparation phase for Brand3 analysis runs."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from src.services.analysis_exceptions import AnalysisJobCancelled
from src.services.run_support import _check_cancel
from src.services.run_preparation import build_discovery_preparation


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


def prepare_run(
    *,
    service,
    store,
    run_id: int | None,
    url: str,
    brand_name: str,
    use_llm: bool,
    use_social: bool,
    use_competitors: bool,
    calibration_profile_override: str | None,
    refresh: bool,
    run_input_sources: set[str] | None,
    progress_cb=None,
    cancel_check=None,
) -> PreparedRun:
    _check_cancel(cancel_check, cancel_exc=AnalysisJobCancelled)
    phase_started = perf_counter()
    step_started = phase_started
    print(f"[1/4] Collecting data for {brand_name}...")

    raw_inputs = service.collect_raw_inputs(
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        url=url,
        refresh=refresh,
        use_social=use_social,
        use_competitors=use_competitors,
        effective_brand_url_builder=service._effective_brand_url,
        context_evidence_builder=service._context_evidence_items,
        run_input_sources=run_input_sources,
        social_collector=service._collect_social_with_budget,
        context_collector_cls=service.ContextCollector,
        web_collector_cls=service.WebCollector,
        exa_collector_cls=service.ExaCollector,
    )
    context_data = raw_inputs.context_data
    web_data = raw_inputs.web_data
    effective_brand_url = raw_inputs.effective_brand_url
    exa_data = raw_inputs.exa_data
    social_data = raw_inputs.social_data
    social_limitation = raw_inputs.social_limitation
    competitor_data = raw_inputs.competitor_data
    raw_input_cache = raw_inputs.raw_input_cache
    acquisition_steps = raw_inputs.acquisition_steps
    web_collector = raw_inputs.web_collector
    step_started = service._log_timing("phase 1a raw inputs", step_started)

    niche = service.select_niche_profile(
        brand_name=brand_name,
        url=url,
        web_data=web_data,
        exa_data=exa_data,
        competitor_data=competitor_data,
        calibration_profile_override=calibration_profile_override,
        min_confidence=service.BRAND3_NICHE_AUTO_APPLY_MIN_CONFIDENCE,
        classify_brand_niche=service.classify_brand_niche,
        select_calibration_profile=service.select_calibration_profile,
    )
    niche_classification = niche.classification
    calibration_profile = niche.calibration_profile
    profile_source = niche.profile_source
    if run_id:
        service._store_safely(
            store,
            "run classification",
            lambda: store.update_run_classification(run_id, niche_classification, calibration_profile, profile_source),
        )
    step_started = service._log_timing("phase 1b niche profile", step_started)

    content_plan = service.plan_content(
        url=url,
        brand_name=brand_name,
        web_data=web_data,
        context_data=context_data,
        web_collector=web_collector,
        exa_data=exa_data,
        recover_owned_web_content=service._recover_owned_web_content,
        build_content_web=service._build_content_web,
        compute_data_quality=service._compute_data_quality,
        partial_dimensions=service._PARTIAL_DIMENSIONS,
    )
    content_web = content_plan.content_web
    content_source = content_plan.content_source
    data_sources = content_plan.data_sources
    data_quality = content_plan.data_quality
    partial_dimensions = content_plan.partial_dimensions
    step_started = service._log_timing("phase 1c content plan", step_started)
    discovery = build_discovery_preparation(
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
        exa_collector=raw_inputs.exa_collector,
        raw_input_cache=raw_input_cache,
        content_source=content_source,
        data_quality=data_quality,
        calibration_profile=calibration_profile,
        profile_source=profile_source,
        niche_classification=niche_classification,
    )
    entity_discovery = discovery.entity_discovery
    discovery_search_plan = discovery.discovery_search_plan
    entity_research_packet = discovery.entity_research_packet
    discovery_evidence_preview = discovery.discovery_evidence_preview
    discovery_enrichment_payload = discovery.discovery_enrichment_payload
    acquisition_provenance = discovery.acquisition_provenance
    discovery_trust_basis = discovery.discovery_trust_basis
    discovery_calibration_hint = discovery.discovery_calibration_hint
    discovery_calibration_decision = discovery.discovery_calibration_decision
    discovery_payload = discovery.discovery_payload
    research_pack_for_feature_prompts = discovery.research_pack_for_feature_prompts
    calibration_profile = discovery.calibration_profile
    profile_source = discovery.profile_source
    web_data = discovery.web_data
    exa_data = discovery.exa_data
    content_web = discovery.content_web
    step_started = service._log_timing("phase 1d discovery+calibration", step_started)

    llm_setup = service.setup_llm(
        use_llm=use_llm,
        context_data=context_data,
        content_web=content_web,
        content_source=content_source,
        llm_cls=service.LLMAnalyzer,
        cheap_model=service.LLM_CHEAP_MODEL,
        provider_payload_builder=service._llm_provider_payload,
        should_skip_llm_for_low_context=service._should_skip_llm_for_low_context,
    )
    llm = llm_setup.llm
    llm_provider = llm_setup.provider
    llm_skipped_reason = llm_setup.skipped_reason
    service._log_timing("phase 1g llm setup", step_started)
    service._log_timing("phase 1 collect+prepare", phase_started)

    return PreparedRun(
        context_data=context_data,
        web_data=web_data,
        effective_brand_url=effective_brand_url,
        exa_data=exa_data,
        social_data=social_data,
        social_limitation=social_limitation,
        competitor_data=competitor_data,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        web_collector=web_collector,
        niche_classification=niche_classification,
        calibration_profile=calibration_profile,
        profile_source=profile_source,
        content_web=content_web,
        content_source=content_source,
        data_sources=data_sources,
        data_quality=data_quality,
        partial_dimensions=partial_dimensions,
        entity_discovery=entity_discovery,
        discovery_search_plan=discovery_search_plan,
        entity_research_packet=entity_research_packet,
        discovery_evidence_preview=discovery_evidence_preview,
        discovery_enrichment_payload=discovery_enrichment_payload,
        acquisition_provenance=acquisition_provenance,
        discovery_trust_basis=discovery_trust_basis,
        discovery_calibration_hint=discovery_calibration_hint,
        discovery_calibration_decision=discovery_calibration_decision,
        discovery_payload=discovery_payload,
        research_pack_for_feature_prompts=research_pack_for_feature_prompts,
        llm=llm,
        llm_provider=llm_provider,
        llm_skipped_reason=llm_skipped_reason,
    )
