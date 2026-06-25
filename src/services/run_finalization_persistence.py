"""Post-result persistence implementation for Brand3 runs."""

from __future__ import annotations


def _persist_report_narrative(
    *,
    service,
    store,
    run_id: int,
    llm,
    run_audit_context: dict,
) -> None:
    from src.reports.dossier import REPORT_NARRATIVE_SOURCE, build_report_narrative_payload

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


def persist_finalization_artifacts(
    *,
    service,
    store,
    run_id: int | None,
    result: dict,
    social_data,
    use_llm: bool,
    llm,
    summary: str,
    brand_score,
    run_audit_context: dict,
    step_started: float,
    phase_started: float,
) -> tuple[float, float]:
    if run_id:
        service._store_safely(store, "run audit save", lambda: store.save_run_audit(run_id, result["audit"]))

    output_path = service._save_result(result)
    print(f"\nSaved result to: {output_path}")
    step_started = service._log_timing("phase 4f json+output save", step_started)

    if run_id:
        service._store_safely(
            store,
            "visual signature persistence",
            lambda: service.persist_visual_signature_result(store, run_id, result),
        )
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
        service._store_safely(
            store,
            "report narrative persistence",
            lambda: _persist_report_narrative(
                service=service,
                store=store,
                run_id=run_id,
                llm=llm,
                run_audit_context=run_audit_context,
            ),
        )
    service._log_timing("phase 4h report narrative", step_started)
    service._log_timing("phase 4 report+persist", phase_started)
    return step_started, phase_started
