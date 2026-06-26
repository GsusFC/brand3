"""Snapshot hydration helpers for Visual Signature runtime."""

from __future__ import annotations


def require_snapshot(store, run_id: int) -> dict:
    snapshot = store.get_run_snapshot(run_id)
    if not snapshot:
        raise ValueError(f"run {run_id} not found")
    return snapshot


def snapshot_identity(snapshot: dict, *, run_id: int) -> tuple[str, str]:
    run_payload = snapshot.get("run") or {}
    brand_name = str(run_payload.get("brand_name") or "")
    url = str(run_payload.get("url") or "")
    if not url:
        raise ValueError(f"run {run_id} has no url")
    return brand_name, url
