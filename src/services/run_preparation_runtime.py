"""Run preparation phase implementation for Brand3 analysis runs."""

from __future__ import annotations

from time import perf_counter

from src.services.analysis_exceptions import AnalysisJobCancelled
from src.services.run_support import _check_cancel
from src.services.run_preparation import build_discovery_preparation
from src.services.run_preparation_runtime_support import (
    PreparedRun,
    build_prepared_run,
    discovery_state,
    raw_inputs_state,
)


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
    raw_state = raw_inputs_state(raw_inputs)
    step_started = service._log_timing("phase 1a raw inputs", step_started)

    niche = service.select_niche_profile(
        brand_name=brand_name,
        url=url,
        web_data=raw_state["web_data"],
        exa_data=raw_state["exa_data"],
        competitor_data=raw_state["competitor_data"],
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
        web_data=raw_state["web_data"],
        context_data=raw_state["context_data"],
        web_collector=raw_state["web_collector"],
        exa_data=raw_state["exa_data"],
        recover_owned_web_content=service._recover_owned_web_content,
        build_content_web=service._build_content_web,
        compute_data_quality=service._compute_data_quality,
        partial_dimensions=service._PARTIAL_DIMENSIONS,
    )
    step_started = service._log_timing("phase 1c content plan", step_started)
    discovery = build_discovery_preparation(
        service=service,
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        url=url,
        web_data=raw_state["web_data"],
        content_web=content_plan.content_web,
        exa_data=raw_state["exa_data"],
        context_data=raw_state["context_data"],
        web_collector=raw_state["web_collector"],
        exa_collector=raw_state["exa_collector"],
        raw_input_cache=raw_state["raw_input_cache"],
        content_source=content_plan.content_source,
        data_quality=content_plan.data_quality,
        calibration_profile=calibration_profile,
        profile_source=profile_source,
        niche_classification=niche_classification,
    )
    prepared_discovery = discovery_state(discovery)
    step_started = service._log_timing("phase 1d discovery+calibration", step_started)

    llm_setup = service.setup_llm(
        use_llm=use_llm,
        context_data=raw_state["context_data"],
        content_web=prepared_discovery["content_web"],
        content_source=content_plan.content_source,
        llm_cls=service.LLMAnalyzer,
        cheap_model=service.LLM_CHEAP_MODEL,
        provider_payload_builder=service._llm_provider_payload,
        should_skip_llm_for_low_context=service._should_skip_llm_for_low_context,
    )
    service._log_timing("phase 1g llm setup", step_started)
    service._log_timing("phase 1 collect+prepare", phase_started)

    return build_prepared_run(
        raw_state=raw_state,
        discovery_state=prepared_discovery,
        llm_setup=llm_setup,
        niche_classification=niche_classification,
        content_plan=content_plan,
    )
