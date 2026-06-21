"""Feature extraction and scoring phase for Brand3 analysis runs."""

from __future__ import annotations

from time import perf_counter


def run_phase_two(
    *,
    service,
    store,
    run_id: int | None,
    url: str,
    brand_name: str,
    web_data,
    content_web,
    exa_data,
    social_data,
    context_data,
    competitor_data,
    llm,
    use_llm: bool,
    data_quality: str,
    content_source: str,
    research_pack_for_feature_prompts,
    partial_dimensions,
    calibration_profile: str,
    skip_visual_analysis: bool,
    enable_visual_signature_shadow_run: bool,
) -> dict:
    phase_started = perf_counter()
    print("[2/4] Extracting features...")

    feature_result = service.run_feature_pipeline(
        url=url,
        skip_visual_analysis=skip_visual_analysis,
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
        research_pack=research_pack_for_feature_prompts,
        take_screenshot_with_budget=service._take_screenshot_with_budget,
        screenshot_capture_diagnostic=service._screenshot_capture_diagnostic,
        presencia_cls=service.PresenciaExtractor,
        vitalidad_cls=service.VitalidadExtractor,
        coherencia_cls=service.CoherenciaExtractor,
        diferenciacion_cls=service.DiferenciacionExtractor,
        percepcion_cls=service.PercepcionExtractor,
        annotate_content_source=service._annotate_content_source,
    )
    features_by_dim = feature_result.features_by_dim
    screenshot_capture = feature_result.screenshot_capture
    if run_id:
        service._store_safely(
            store,
            "screenshot capture raw input save",
            lambda: store.save_raw_input(
                run_id,
                "screenshot_capture",
                {
                    "version": "screenshot_capture_v1",
                    "url": url,
                    "content_source": content_source,
                    "skip_visual_analysis": skip_visual_analysis,
                    "capture": screenshot_capture,
                },
            ),
        )
    service._run_visual_signature_shadow(
        enabled=enable_visual_signature_shadow_run,
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        url=url,
        web_data=web_data,
        content_web=content_web,
        screenshot_capture=screenshot_capture,
    )
    print(f"[timing] phase 2 features: {(perf_counter() - phase_started):.2f}s")

    phase_started = perf_counter()
    print("[3/4] Scoring...")
    scoring = service.score_features(
        url=url,
        brand_name=brand_name,
        features_by_dim=features_by_dim,
        partial_dimensions=partial_dimensions,
        data_quality=data_quality,
        calibration_profile=calibration_profile,
        store=store,
        run_id=run_id,
        scoring_engine_cls=service.ScoringEngine,
        store_safely=service._store_safely,
    )
    print(f"[timing] phase 3 scoring: {(perf_counter() - phase_started):.2f}s")

    return {
        "features_by_dim": features_by_dim,
        "screenshot_capture": screenshot_capture,
        "scoring": scoring,
    }
