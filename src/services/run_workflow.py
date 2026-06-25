"""End-to-end analysis run orchestration implementation."""

from __future__ import annotations

from time import perf_counter

from src.services.analysis_exceptions import AnalysisJobCancelled
from src.services.run_finalization import finalize_run as _finalize_run
from src.services.run_preparation_runtime import prepare_run
from src.services.run_phase_two_runtime import run_phase_two
from src.services.run_support import _check_cancel, _emit_progress


def run(
    url: str,
    brand_name: str = None,
    use_llm: bool = True,
    use_social: bool = True,
    use_competitors: bool = True,
    calibration_profile_override: str | None = None,
    skip_visual_analysis: bool = False,
    enable_visual_signature_shadow_run: bool = False,
    refresh: bool = False,
    run_input_sources: set[str] | None = None,
    progress_cb=None,
    cancel_check=None,
) -> dict:
    from src.services import brand_service as service

    if not brand_name:
        brand_name = url.replace("https://", "").replace("http://", "").split("/")[0]

    storage = service.start_analysis_run(
        brand_name,
        url,
        use_llm=use_llm,
        use_social=use_social,
        db_path=service.BRAND3_DB_PATH,
    )
    store = storage.store
    run_id = storage.run_id

    try:
        phase_started = perf_counter()
        prepared = prepare_run(
            service=service,
            store=store,
            run_id=run_id,
            url=url,
            brand_name=brand_name,
            use_llm=use_llm,
            use_social=use_social,
            use_competitors=use_competitors,
            calibration_profile_override=calibration_profile_override,
            refresh=refresh,
            run_input_sources=run_input_sources,
            progress_cb=progress_cb,
            cancel_check=cancel_check,
        )
        context_data = prepared.context_data
        web_data = prepared.web_data
        exa_data = prepared.exa_data
        social_data = prepared.social_data
        social_limitation = prepared.social_limitation
        competitor_data = prepared.competitor_data
        raw_input_cache = prepared.raw_input_cache
        acquisition_steps = prepared.acquisition_steps
        niche_classification = prepared.niche_classification
        calibration_profile = prepared.calibration_profile
        content_web = prepared.content_web
        content_source = prepared.content_source
        data_sources = prepared.data_sources
        data_quality = prepared.data_quality
        partial_dimensions = prepared.partial_dimensions
        entity_discovery = prepared.entity_discovery
        discovery_search_plan = prepared.discovery_search_plan
        entity_research_packet = prepared.entity_research_packet
        discovery_evidence_preview = prepared.discovery_evidence_preview
        discovery_enrichment_payload = prepared.discovery_enrichment_payload
        acquisition_provenance = prepared.acquisition_provenance
        discovery_trust_basis = prepared.discovery_trust_basis
        discovery_calibration_hint = prepared.discovery_calibration_hint
        discovery_calibration_decision = prepared.discovery_calibration_decision
        discovery_payload = prepared.discovery_payload
        research_pack_for_feature_prompts = prepared.research_pack_for_feature_prompts
        llm = prepared.llm
        llm_provider = prepared.llm_provider
        llm_skipped_reason = prepared.llm_skipped_reason
        service._log_timing("phase 1 collect+prepare", phase_started)

        _emit_progress(progress_cb, "extracting")
        _check_cancel(cancel_check, cancel_exc=AnalysisJobCancelled)
        phase_started = perf_counter()
        phase_two = run_phase_two(
            service=service,
            store=store,
            run_id=run_id,
            url=url,
            brand_name=brand_name,
            web_data=web_data,
            content_web=content_web,
            exa_data=exa_data,
            social_data=social_data,
            context_data=context_data,
            competitor_data=competitor_data,
            llm=llm,
            use_llm=use_llm,
            data_quality=data_quality,
            content_source=content_source,
            research_pack_for_feature_prompts=research_pack_for_feature_prompts,
            partial_dimensions=partial_dimensions,
            calibration_profile=calibration_profile,
            skip_visual_analysis=skip_visual_analysis,
            enable_visual_signature_shadow_run=enable_visual_signature_shadow_run,
        )
        features_by_dim = phase_two["features_by_dim"]
        screenshot_capture = phase_two["screenshot_capture"]
        scoring = phase_two["scoring"]
        engine = scoring.engine
        brand_score = scoring.brand_score

        _emit_progress(progress_cb, "finalizing")
        _check_cancel(cancel_check, cancel_exc=AnalysisJobCancelled)
        phase_started = perf_counter()
        summary = engine.generate_summary(brand_score)
        result = _finalize_run(
            service=service,
            store=store,
            run_id=run_id,
            brand_name=brand_name,
            url=url,
            web_data=web_data,
            content_web=content_web,
            exa_data=exa_data,
            content_source=content_source,
            data_quality=data_quality,
            partial_dimensions=partial_dimensions,
            social_data=social_data,
            use_llm=use_llm,
            use_social=use_social,
            use_competitors=use_competitors,
            skip_visual_analysis=skip_visual_analysis,
            llm=llm,
            llm_provider=llm_provider,
            llm_skipped_reason=llm_skipped_reason,
            calibration_profile=calibration_profile,
            niche_classification=niche_classification,
            research_pack_for_feature_prompts=research_pack_for_feature_prompts,
            entity_discovery=entity_discovery,
            discovery_search_plan=discovery_search_plan,
            discovery_evidence_preview=discovery_evidence_preview,
            discovery_enrichment_payload=discovery_enrichment_payload,
            discovery_payload=discovery_payload,
            discovery_trust_basis=discovery_trust_basis,
            discovery_calibration_hint=discovery_calibration_hint,
            discovery_calibration_decision=discovery_calibration_decision,
            entity_research_packet=entity_research_packet,
            acquisition_provenance=acquisition_provenance,
            acquisition_steps=acquisition_steps,
            raw_input_cache=raw_input_cache,
            screenshot_capture=screenshot_capture,
            base_data_sources=data_sources,
            social_limitation=social_limitation,
            context_data=context_data,
            features_by_dim=features_by_dim,
            brand_score=brand_score,
            summary=summary,
        )
        return result
    except AnalysisJobCancelled:
        if run_id:
            service._store_safely(store, "run status cancelled", lambda: store.mark_run_status(run_id, "cancelled"))
        raise
    except Exception:
        if run_id:
            service._store_safely(store, "run status failed", lambda: store.mark_run_status(run_id, "failed"))
        raise
    finally:
        if store:
            service._store_safely(store, "close", store.close)
