"""Small run orchestration helpers shared by Brand3 services."""

from __future__ import annotations

def _emit_progress(progress_cb, phase: str) -> None:
    if progress_cb is None:
        return
    progress_cb(phase)


def _build_research_pack_for_feature_prompts(
    *,
    store,
    run_id: int | None,
    build_recommended_research_pack_fn=None,
):
    if not store or run_id is None:
        return None
    try:
        if build_recommended_research_pack_fn is None:
            from src.research.research_pack_facade import build_recommended_research_pack as build_recommended_research_pack_fn

        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            return None
        return build_recommended_research_pack_fn(snapshot).pack
    except Exception as exc:
        print(f"  Research pack prompt input: skipped ({exc})")
        return None


def _check_cancel(cancel_check, *, cancel_exc) -> None:
    if cancel_check is not None and cancel_check():
        raise cancel_exc("Cancelled by user")
