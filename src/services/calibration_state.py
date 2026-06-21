"""Calibration gate, experiment summary, and scoring-state helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from src.niche import get_calibration_profile
from src.storage.sqlite_store import SQLiteStore


def _score_map(snapshot: dict) -> dict[str, float]:
    return {
        item["dimension_name"]: float(item["score"])
        for item in snapshot.get("scores", [])
        if item.get("dimension_name") is not None and item.get("score") is not None
    }


def _build_experiment_summary(
    before_snapshot: dict,
    after_snapshot: dict,
    applied_results: list[dict],
) -> dict:
    before_run = before_snapshot["run"]
    after_run = after_snapshot["run"]
    before_scores = _score_map(before_snapshot)
    after_scores = _score_map(after_snapshot)

    dimensions = {}
    for dimension_name in sorted(set(before_scores) | set(after_scores)):
        before_value = before_scores.get(dimension_name)
        after_value = after_scores.get(dimension_name)
        dimensions[dimension_name] = {
            "before": before_value,
            "after": after_value,
            "delta": None if before_value is None or after_value is None else round(after_value - before_value, 1),
        }

    before_composite = before_run.get("composite_score")
    after_composite = after_run.get("composite_score")
    applied_candidate_ids = [item["candidate_id"] for item in applied_results if item.get("applied")]

    return {
        "brand_name": after_run["brand_name"],
        "url": after_run["url"],
        "before_run_id": before_run["id"],
        "after_run_id": after_run["id"],
        "candidate_ids": applied_candidate_ids,
        "composite": {
            "before": before_composite,
            "after": after_composite,
            "delta": None if before_composite is None or after_composite is None else round(after_composite - before_composite, 1),
        },
        "dimensions": dimensions,
    }


def _default_gate_config(
    *,
    max_composite_drop: float,
    max_dimension_drops: dict[str, float],
) -> dict:
    return {
        "max_composite_drop": max_composite_drop,
        "max_dimension_drops": dict(max_dimension_drops),
    }


def _load_gate_config(
    store: SQLiteStore | None = None,
    *,
    db_path: str,
    default_gate_config: Callable[[], dict],
) -> dict:
    should_close = False
    if store is None:
        store = SQLiteStore(db_path)
        should_close = True
    try:
        return store.get_gate_config() or default_gate_config()
    finally:
        if should_close:
            store.close()


def _read_calibration_state(
    store: SQLiteStore | None = None,
    *,
    dimensions_path: Path,
    engine_path: Path,
    load_gate_config: Callable[[SQLiteStore | None], dict],
) -> dict[str, object]:
    return {
        "dimensions_content": dimensions_path.read_text(encoding="utf-8"),
        "engine_content": engine_path.read_text(encoding="utf-8"),
        "gate_config": load_gate_config(store),
    }


def _restore_calibration_state(
    version: dict,
    store: SQLiteStore | None = None,
    *,
    db_path: str,
    dimensions_path: Path,
    engine_path: Path,
) -> None:
    dimensions_path.write_text(version["dimensions_content"], encoding="utf-8")
    engine_path.write_text(version["engine_content"], encoding="utf-8")
    if version.get("gate_config") is not None:
        should_close = False
        if store is None:
            store = SQLiteStore(db_path)
            should_close = True
        try:
            store.upsert_gate_config(version["gate_config"])
        finally:
            if should_close:
                store.close()


def _evaluate_promotion_gate(
    experiment: dict | None,
    gate_config: dict | None = None,
    *,
    default_gate_config: Callable[[], dict],
    default_max_composite_drop: float,
    default_max_dimension_drops: dict[str, float],
) -> dict:
    gate_config = gate_config or default_gate_config()
    max_composite_drop = float(gate_config.get("max_composite_drop", default_max_composite_drop))
    max_dimension_drops = dict(default_max_dimension_drops)
    max_dimension_drops.update(gate_config.get("max_dimension_drops", {}))
    if not experiment:
        return {
            "allowed": False,
            "reasons": ["No experiment found for this version"],
            "summary": None,
            "thresholds": {
                "max_composite_drop": max_composite_drop,
                "max_dimension_drops": max_dimension_drops,
            },
        }

    summary = experiment.get("summary", {})
    composite = summary.get("composite", {})
    reasons = []

    composite_delta = composite.get("delta")
    if composite_delta is None:
        reasons.append("Experiment is missing composite delta")
    elif composite_delta < -max_composite_drop:
        reasons.append(
            f"Composite regressed by {composite_delta:.1f} points "
            f"(limit {-max_composite_drop:.1f})"
        )

    for dimension_name, payload in summary.get("dimensions", {}).items():
        delta = payload.get("delta")
        max_drop = float(max_dimension_drops.get(dimension_name, 5.0))
        if delta is not None and delta < -max_drop:
            reasons.append(
                f"Dimension {dimension_name} regressed by {delta:.1f} points "
                f"(limit {-max_drop:.1f})"
            )

    return {
        "allowed": len(reasons) == 0,
        "reasons": reasons,
        "summary": summary,
        "experiment_id": experiment.get("id"),
        "thresholds": {
            "max_composite_drop": max_composite_drop,
            "max_dimension_drops": max_dimension_drops,
        },
    }


def _compare_summaries(target_summary: dict | None, baseline_summary: dict | None) -> dict | None:
    if not target_summary or not baseline_summary:
        return None

    target_composite = target_summary.get("composite", {}).get("after")
    baseline_composite = baseline_summary.get("composite", {}).get("after")
    dimensions = {}

    target_dimensions = target_summary.get("dimensions", {})
    baseline_dimensions = baseline_summary.get("dimensions", {})
    for dimension_name in sorted(set(target_dimensions) | set(baseline_dimensions)):
        target_after = target_dimensions.get(dimension_name, {}).get("after")
        baseline_after = baseline_dimensions.get(dimension_name, {}).get("after")
        dimensions[dimension_name] = {
            "target_after": target_after,
            "baseline_after": baseline_after,
            "delta_vs_baseline": None
            if target_after is None or baseline_after is None
            else round(target_after - baseline_after, 1),
        }

    return {
        "composite": {
            "target_after": target_composite,
            "baseline_after": baseline_composite,
            "delta_vs_baseline": None
            if target_composite is None or baseline_composite is None
            else round(target_composite - baseline_composite, 1),
        },
        "dimensions": dimensions,
    }


def _compute_scoring_state_fingerprint(
    dimensions_content: str,
    engine_content: str,
    gate_config: dict,
    calibration_profile: str,
    calibration_profile_config: dict,
) -> str:
    payload = {
        "dimensions_content": dimensions_content,
        "engine_content": engine_content,
        "gate_config": gate_config,
        "calibration_profile": calibration_profile,
        "calibration_profile_config": calibration_profile_config,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return digest[:16]


def _build_run_audit_context(
    *,
    store: SQLiteStore | None,
    db_path: str,
    dimensions_path: Path,
    engine_path: Path,
    load_gate_config: Callable[[SQLiteStore | None], dict],
    calibration_profile: str = "base",
    niche_classification: dict | None = None,
) -> dict:
    should_close = False
    if store is None:
        store = SQLiteStore(db_path)
        should_close = True
    try:
        gate_config = load_gate_config(store)
        dimensions_content = dimensions_path.read_text(encoding="utf-8")
        engine_content = engine_path.read_text(encoding="utf-8")
        calibration_profile_config = get_calibration_profile(calibration_profile)
        return {
            "gate_config": gate_config,
            "active_baseline": store.get_active_baseline(),
            "calibration_profile": calibration_profile,
            "calibration_profile_config": calibration_profile_config,
            "niche_classification": niche_classification,
            "scoring_state_fingerprint": _compute_scoring_state_fingerprint(
                dimensions_content=dimensions_content,
                engine_content=engine_content,
                gate_config=gate_config,
                calibration_profile=calibration_profile,
                calibration_profile_config=calibration_profile_config,
            ),
        }
    finally:
        if should_close:
            store.close()
