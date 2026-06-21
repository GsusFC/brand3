"""Shared experiment workflow for Brand3 calibration runs."""

from __future__ import annotations

import json

from src.services.calibration_state import _build_experiment_summary
from src.storage.sqlite_store import SQLiteStore


def run_experiment(
    brand_name: str,
    candidate_ids: list[int] | None = None,
    *,
    db_path: str,
    run_fn,
    apply_candidates_fn,
    build_experiment_summary=_build_experiment_summary,
    store_factory=SQLiteStore,
    printer=print,
) -> dict:
    store = store_factory(db_path)
    try:
        before_run_id = store.get_latest_run_id(brand_name=brand_name)
        if not before_run_id:
            raise ValueError(f"No runs found for brand {brand_name}")
        before_snapshot = store.get_run_snapshot(before_run_id)
        if not before_snapshot:
            raise ValueError(f"Run {before_run_id} not found")
        baseline = before_snapshot["run"]
    finally:
        store.close()

    applied_results = apply_candidates_fn(candidate_ids=candidate_ids, brand_name=brand_name)
    applied_candidate_ids = [item["candidate_id"] for item in applied_results if item.get("applied")]
    if not applied_candidate_ids:
        raise ValueError("No approved candidates were applied; experiment aborted")
    applied_version_before_id = next(
        (item["version_before_id"] for item in applied_results if item.get("applied") and item.get("version_before_id")),
        None,
    )
    applied_version_after_id = None
    for item in applied_results:
        if item.get("applied") and item.get("version_after_id"):
            applied_version_after_id = item["version_after_id"]

    rerun_result = run_fn(
        baseline["url"],
        brand_name=baseline["brand_name"],
        use_llm=bool(baseline["use_llm"]),
        use_social=bool(baseline["use_social"]),
    )
    after_run_id = rerun_result.get("run_id")
    if not after_run_id:
        raise ValueError("Rerun did not produce a persisted run_id")

    store = store_factory(db_path)
    try:
        after_snapshot = store.get_run_snapshot(after_run_id)
        if not after_snapshot:
            raise ValueError(f"Run {after_run_id} not found after rerun")

        summary = build_experiment_summary(before_snapshot, after_snapshot, applied_results)
        experiment_id = store.save_experiment(
            brand_name=baseline["brand_name"],
            url=baseline["url"],
            before_run_id=before_run_id,
            after_run_id=after_run_id,
            candidate_ids=applied_candidate_ids,
            summary=summary,
            version_before_id=applied_version_before_id,
            version_after_id=applied_version_after_id,
            before_scoring_state_fingerprint=before_snapshot["run"].get("scoring_state_fingerprint"),
            after_scoring_state_fingerprint=after_snapshot["run"].get("scoring_state_fingerprint"),
        )
        payload = {
            "experiment_id": experiment_id,
            "apply_results": applied_results,
            "summary": summary,
        }
        printer(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()
