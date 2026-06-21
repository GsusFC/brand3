"""Public feedback API wrappers for Brand3."""

from __future__ import annotations

from src.config import BRAND3_DB_PATH
from src.storage.sqlite_store import SQLiteStore


def add_feedback(
    note: str,
    run_id: int | None = None,
    brand_name: str | None = None,
    url: str | None = None,
    dimension_name: str | None = None,
    feature_name: str | None = None,
    expected_score: float | None = None,
    actual_score: float | None = None,
) -> int:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        target_run_id = run_id or store.get_latest_run_id(brand_name=brand_name, url=url)
        if not target_run_id:
            raise ValueError("No matching run found for feedback")
        annotation_id = store.add_annotation(
            run_id=target_run_id,
            note=note,
            dimension_name=dimension_name,
            feature_name=feature_name,
            expected_score=expected_score,
            actual_score=actual_score,
        )
        print(f"Saved annotation {annotation_id} for run {target_run_id}")
        return annotation_id
    finally:
        store.close()
