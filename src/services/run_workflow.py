"""End-to-end analysis run orchestration implementation."""

from __future__ import annotations

from time import perf_counter

from src.services.analysis_exceptions import AnalysisJobCancelled
from src.services.run_finalization import finalize_run as _finalize_run
from src.services.run_preparation_runtime import prepare_run
from src.services.run_phase_two_runtime import run_phase_two
from src.services.run_support import _check_cancel, _emit_progress
from src.services.run_workflow_support import (
    finalization_kwargs,
    mark_run_status,
    phase_two_kwargs,
    resolve_brand_name,
)


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

    brand_name = resolve_brand_name(url, brand_name)

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
            use_llm=use_llm,
            skip_visual_analysis=skip_visual_analysis,
            enable_visual_signature_shadow_run=enable_visual_signature_shadow_run,
            **phase_two_kwargs(prepared),
        )
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
            **finalization_kwargs(
                prepared=prepared,
                phase_two=phase_two,
                brand_score=brand_score,
                summary=summary,
                brand_name=brand_name,
                url=url,
                use_llm=use_llm,
                use_social=use_social,
                use_competitors=use_competitors,
                skip_visual_analysis=skip_visual_analysis,
                llm_provider=prepared.llm_provider,
                llm_skipped_reason=prepared.llm_skipped_reason,
            ),
        )
        return result
    except AnalysisJobCancelled:
        mark_run_status(service, store, run_id, "cancelled")
        raise
    except Exception:
        mark_run_status(service, store, run_id, "failed")
        raise
    finally:
        if store:
            service._store_safely(store, "close", store.close)
