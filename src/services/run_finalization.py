"""Persist and finalize the final pieces of an analysis run."""

from __future__ import annotations

from src.services.run_finalization_impl import finalize_run as _finalize_run_impl


def finalize_run(*, service, store, run_id: int | None, **kwargs):
    return _finalize_run_impl(
        service=service,
        store=store,
        run_id=run_id,
        **kwargs,
    )
