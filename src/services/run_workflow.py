"""End-to-end analysis run orchestration."""

from __future__ import annotations

from src.services.run_workflow_impl import run as _run_workflow_impl


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
    return _run_workflow_impl(
        url=url,
        brand_name=brand_name,
        use_llm=use_llm,
        use_social=use_social,
        use_competitors=use_competitors,
        calibration_profile_override=calibration_profile_override,
        skip_visual_analysis=skip_visual_analysis,
        enable_visual_signature_shadow_run=enable_visual_signature_shadow_run,
        refresh=refresh,
        run_input_sources=run_input_sources,
        progress_cb=progress_cb,
        cancel_check=cancel_check,
    )


# Backward-compatible alias.
run_workflow = run
