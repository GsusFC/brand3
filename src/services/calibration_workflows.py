"""Calibration workflows and experiment helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, TypeVar

from src.services.calibration_state import (
    _build_experiment_summary,
    _build_run_audit_context as _build_run_audit_context_with_paths,
    _compare_summaries,
    _default_gate_config as _build_default_gate_config,
    _evaluate_promotion_gate as _evaluate_promotion_gate_with_defaults,
    _load_gate_config as _load_gate_config_from_db,
    _read_calibration_state as _read_calibration_state_from_paths,
    _restore_calibration_state as _restore_calibration_state_with_paths,
)
from src.services.calibration_candidates import (
    apply_candidates as _apply_candidates_impl,
    list_candidates as _list_candidates_impl,
    propose_calibration as _propose_calibration_impl,
    review_candidate as _review_candidate_impl,
)
from src.services.experiment_workflow import run_experiment as _run_experiment_impl
from src.services.calibration_workflows_reporting import (
    compare_version,
    get_gate_config,
    list_baselines,
    list_experiments,
    list_versions,
    promote_baseline,
    rollback_version,
    set_gate_config,
)
from src.storage.sqlite_store import SQLiteStore


T = TypeVar("T")


def _with_store(db_path: str, action: Callable[[SQLiteStore], T]) -> T:
    store = SQLiteStore(db_path)
    try:
        return action(store)
    finally:
        store.close()


def _load_gate_config(
    store: SQLiteStore | None = None,
    *,
    db_path: str,
    default_gate_config: Callable[[], dict],
) -> dict:
    return _load_gate_config_from_db(
        store,
        db_path=db_path,
        default_gate_config=default_gate_config,
    )


def _default_gate_config(*, max_composite_drop: float, max_dimension_drops: dict[str, float]) -> dict:
    return _build_default_gate_config(
        max_composite_drop=max_composite_drop,
        max_dimension_drops=max_dimension_drops,
    )


def _evaluate_promotion_gate(
    experiment: dict | None,
    gate_config: dict | None = None,
    *,
    default_gate_config: Callable[[], dict],
    default_max_composite_drop: float,
    default_max_dimension_drops: dict[str, float],
) -> dict:
    return _evaluate_promotion_gate_with_defaults(
        experiment,
        gate_config=gate_config,
        default_gate_config=default_gate_config,
        default_max_composite_drop=default_max_composite_drop,
        default_max_dimension_drops=default_max_dimension_drops,
    )


def _read_calibration_state(
    store: SQLiteStore | None = None,
    *,
    dimensions_path: Path,
    engine_path: Path,
    load_gate_config: Callable[[SQLiteStore | None], dict],
) -> dict[str, object]:
    return _read_calibration_state_from_paths(
        store,
        dimensions_path=dimensions_path,
        engine_path=engine_path,
        load_gate_config=load_gate_config,
    )


def _restore_calibration_state(
    version: dict,
    store: SQLiteStore | None = None,
    *,
    db_path: str,
    dimensions_path: Path,
    engine_path: Path,
) -> None:
    _restore_calibration_state_with_paths(
        version,
        store,
        db_path=db_path,
        dimensions_path=dimensions_path,
        engine_path=engine_path,
    )


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
    return _build_run_audit_context_with_paths(
        store=store,
        db_path=db_path,
        dimensions_path=dimensions_path,
        engine_path=engine_path,
        load_gate_config=load_gate_config,
        calibration_profile=calibration_profile,
        niche_classification=niche_classification,
    )


def propose_calibration(
    brand_name: str,
    *,
    db_path: str,
    limit: int = 20,
    persist: bool = False,
) -> list[dict]:
    return _propose_calibration_impl(
        brand_name,
        db_path=db_path,
        limit=limit,
        persist=persist,
    )


def list_candidates(
    brand_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
    *,
    db_path: str,
) -> list[dict]:
    return _list_candidates_impl(
        brand_name,
        status,
        limit,
        db_path=db_path,
    )


def review_candidate(candidate_id: int, status: str, *, db_path: str) -> dict:
    return _review_candidate_impl(candidate_id, status, db_path=db_path)


def apply_candidates(
    candidate_ids: list[int] | None = None,
    brand_name: str | None = None,
    *,
    db_path: str,
    dimensions_path: Path,
    engine_path: Path,
    read_calibration_state: Callable[[SQLiteStore | None], dict[str, object]],
) -> list[dict]:
    return _apply_candidates_impl(
        candidate_ids=candidate_ids,
        brand_name=brand_name,
        db_path=db_path,
        dimensions_path=dimensions_path,
        engine_path=engine_path,
        read_calibration_state=read_calibration_state,
    )


def run_experiment(
    brand_name: str,
    candidate_ids: list[int] | None = None,
    *,
    db_path: str,
    run_fn,
    apply_candidates_fn,
    build_experiment_summary=_build_experiment_summary,
) -> dict:
    return _run_experiment_impl(
        brand_name,
        candidate_ids=candidate_ids,
        db_path=db_path,
        run_fn=run_fn,
        apply_candidates_fn=apply_candidates_fn,
        build_experiment_summary=build_experiment_summary,
    )

