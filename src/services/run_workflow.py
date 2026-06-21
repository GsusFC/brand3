"""End-to-end analysis run orchestration."""

from __future__ import annotations

import json
from time import perf_counter


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

    run_started = perf_counter()
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
        service._check_cancel(cancel_check)
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
        step_started = service._log_timing("phase 1d entity research packet", step_started)
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
            exa_collector=raw_inputs.exa_collector,
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
        discovery_enrichment_payload = discovery_enrichment.payload
        step_started = service._log_timing("phase 1e discovery enrichment", step_started)
        acquisition_provenance = service._acquisition_provenance_summary(
            brand_name=brand_name,
            url=url,
            web_data=web_data,
            exa_data=exa_data,
            context_data=context_data,
            discovery_enrichment_payload=discovery_enrichment_payload,
            raw_input_cache=raw_input_cache,
            content_source=content_source,
            data_quality=data_quality,
        )
        discovery_trust_basis = service.build_discovery_trust_basis(
            entity_discovery,
            discovery_search_plan,
            discovery_evidence_preview,
            discovery_enrichment_payload,
        )
        discovery_calibration_hint = service.build_discovery_calibration_hint(
            entity_discovery,
            discovery_trust_basis,
            niche_classification,
        )
        available_profiles = {item["profile_id"] for item in service.list_calibration_profiles()}
        discovery_calibration_decision = service.apply_discovery_calibration_hint(
            current_profile=calibration_profile,
            current_profile_source=profile_source,
            discovery_calibration_hint=discovery_calibration_hint,
            discovery_evidence_preview=discovery_evidence_preview,
            discovery_enrichment=discovery_enrichment_payload,
            available_profiles=available_profiles,
        )
        calibration_profile = str(discovery_calibration_decision["calibration_profile"])
        profile_source = str(discovery_calibration_decision["profile_source"])
        discovery_payload = {
            "entity_discovery": entity_discovery,
            "discovery_search_plan": discovery_search_plan,
            "discovery_evidence_preview": discovery_evidence_preview,
            "discovery_trust_basis": discovery_trust_basis,
            "discovery_calibration_hint": discovery_calibration_hint,
        }
        research_pack_for_feature_prompts = service._build_research_pack_for_feature_prompts(
            store=store,
            run_id=run_id,
        )
        step_started = service._log_timing("phase 1f provenance+calibration", step_started)

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

        service._emit_progress(progress_cb, "extracting")
        service._check_cancel(cancel_check)
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

        service._emit_progress(progress_cb, "scoring")
        service._check_cancel(cancel_check)
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
        engine = scoring.engine
        brand_score = scoring.brand_score
        print(f"[timing] phase 3 scoring: {(perf_counter() - phase_started):.2f}s")

        service._emit_progress(progress_cb, "finalizing")
        service._check_cancel(cancel_check)
        phase_started = perf_counter()
        step_started = phase_started
        print("[4/4] Generating report...\n")
        summary = engine.generate_summary(brand_score)
        print(summary)
        print("\n".join([""] + service.format_discovery_summary(discovery_payload)))
        service._print_feature_details(brand_score)
        step_started = service._log_timing("phase 4a summary output", step_started)

        dimension_confidence = service._dimension_confidence_summary(
            features_by_dim,
            evidence_items=service._context_evidence_items(context_data),
            data_quality=data_quality,
            context_data=context_data,
        )
        evidence_summary = service.summarize_evidence_from_features(
            features_by_dim,
            evidence_items=service._context_evidence_items(context_data),
        )
        confidence_summary = service._context_confidence_summary(context_data)
        llm_cache = service._llm_cache_summary(llm, llm_skipped_reason)
        public_presence_inventory = service._public_presence_inventory_summary(
            brand_name=brand_score.brand_name,
            url=brand_score.url,
            web_data=web_data,
            content_web=content_web,
            content_source=content_source,
            exa_data=exa_data,
            context_data=context_data,
        )
        context_enrichment_summary = service._context_enrichment_summary(
            public_presence_inventory=public_presence_inventory,
            context_summary=confidence_summary,
        )
        context_effective_readiness = service._context_effective_readiness(
            public_presence_inventory=public_presence_inventory,
            context_summary=confidence_summary,
        )
        trust_summary = service._trust_summary_payload(
            data_quality=data_quality,
            context_summary=confidence_summary,
            evidence_summary=evidence_summary,
            dimension_confidence=dimension_confidence,
            context_enrichment_summary=context_enrichment_summary,
            context_effective_readiness=context_effective_readiness,
        )
        trust_summary["evidence_basis_summary"] = discovery_trust_basis["user_message"]
        step_started = service._log_timing("phase 4b confidence+trust summaries", step_started)
        run_audit_context = (
            service._build_run_audit_context(
                store,
                calibration_profile=calibration_profile,
                niche_classification=niche_classification,
            )
            if store
            else service._build_run_audit_context(
                calibration_profile=calibration_profile,
                niche_classification=niche_classification,
            )
        )
        step_started = service._log_timing("phase 4c audit context", step_started)
        run_audit_context["executive_analysis_v2"] = service.run_brand_audit_analyst_pass(
            llm=service._audit_analyst_llm(llm),
            brand_name=brand_score.brand_name,
            url=brand_score.url,
            research_pack=research_pack_for_feature_prompts,
            dimensions=brand_score.breakdown,
            features_by_dim=features_by_dim,
        )
        step_started = service._log_timing("phase 4d analyst pass", step_started)

        result = {
            "brand": brand_score.brand_name,
            "brand_profile": service._build_brand_profile(brand_score.brand_name, brand_score.url, store),
            "url": brand_score.url,
            "run_id": run_id,
            "entity_discovery": entity_discovery,
            "discovery_search_plan": discovery_search_plan,
            "discovery_evidence_preview": discovery_evidence_preview,
            "discovery_enrichment": discovery_enrichment_payload,
            "entity_research_packet": entity_research_packet,
            "discovery_trust_basis": discovery_trust_basis,
            "discovery_calibration_hint": discovery_calibration_hint,
            "discovery_calibration_decision": discovery_calibration_decision,
            "niche_classification": niche_classification,
            "calibration_profile": calibration_profile,
            "profile_source": profile_source,
            "data_quality": data_quality,
            "data_sources": service._build_run_data_sources_payload(
                base_data_sources=data_sources,
                acquisition_provenance=acquisition_provenance,
                acquisition_steps=acquisition_steps,
                public_presence_inventory=public_presence_inventory,
                screenshot_capture=screenshot_capture,
                social_limitation=social_limitation,
                raw_input_cache=raw_input_cache,
                llm_provider=llm_provider,
                llm_model_roles=service._llm_model_roles_payload(),
                llm_cache=llm_cache,
                cost_policy=service._cost_policy_summary(
                    raw_input_cache=raw_input_cache,
                    llm_cache=llm_cache,
                    use_llm=use_llm,
                    use_social=use_social,
                    social_limitation=social_limitation,
                    use_competitors=use_competitors,
                    skip_visual_analysis=skip_visual_analysis,
                    context_data=context_data,
                    data_quality=data_quality,
                ),
            ),
            "context_readiness": service._to_jsonable(context_data),
            "context_enrichment_summary": context_enrichment_summary,
            "context_effective_readiness": context_effective_readiness,
            "confidence_summary": confidence_summary,
            "dimension_confidence": dimension_confidence,
            "evidence_summary": evidence_summary,
            "trust_summary": trust_summary,
            "composite_score": brand_score.composite_score,
            "composite_reliable": data_quality != "insufficient",
            "partial_score": data_quality == "insufficient",
            "partial_dimensions": partial_dimensions,
            "dimensions": brand_score.breakdown,
            "llm_used": use_llm and llm is not None,
            "social_scraped": social_data is not None and len(social_data.platforms) > 0,
            "audit": run_audit_context,
            "timestamp": service.datetime.now().isoformat(),
        }
        step_started = service._log_timing("phase 4e result assembly", step_started)
        result["audit"].update(
            service._build_run_audit_payload(
                acquisition_provenance=acquisition_provenance,
                acquisition_steps=acquisition_steps,
                raw_input_cache=raw_input_cache,
                screenshot_capture=screenshot_capture,
                data_quality=data_quality,
                content_source=content_source,
                discovery_calibration_decision=discovery_calibration_decision,
            )
        )
        if run_id:
            service._store_safely(store, "run audit save", lambda: store.save_run_audit(run_id, result["audit"]))

        print("\n--- JSON ---")
        print(json.dumps(result, indent=2))
        output_path = service._save_result(result)
        print(f"\nSaved result to: {output_path}")
        step_started = service._log_timing("phase 4f json+output save", step_started)
        if run_id:
            service._store_safely(
                store,
                "visual signature persistence",
                lambda: service.persist_visual_signature_result(store, run_id, result),
            )
        if run_id:
            service._store_safely(
                store,
                "run finalize",
                lambda: store.finalize_run(
                    run_id=run_id,
                    composite_score=brand_score.composite_score,
                    llm_used=use_llm and llm is not None,
                    social_scraped=social_data is not None and len(social_data.platforms) > 0,
                    result_path=str(output_path),
                    summary=summary,
                ),
            )
        step_started = service._log_timing("phase 4g finalize persistence", step_started)
        if run_id:
            service._store_safely(
                store,
                "report readiness persistence",
                lambda: service._persist_report_readiness(store, run_id, result["audit"]),
            )
        if run_id and llm is not None:
            def _persist_report_narrative() -> None:
                from src.reports.dossier import (
                    REPORT_NARRATIVE_SOURCE,
                    build_report_narrative_payload,
                )

                snapshot = store.get_run_snapshot(run_id)
                if not snapshot:
                    return
                store.save_raw_input(
                    run_id,
                    REPORT_NARRATIVE_SOURCE,
                    build_report_narrative_payload(
                        snapshot,
                        analyzer=llm,
                        analyst_pass=run_audit_context.get("executive_analysis_v2"),
                    ),
                )

            service._store_safely(store, "report narrative persistence", _persist_report_narrative)
        service._log_timing("phase 4h report narrative", step_started)
        service._log_timing("phase 4 report+persist", phase_started)
        service._log_timing("total run", run_started)
        return result
    except service.AnalysisJobCancelled:
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
