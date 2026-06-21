"""Public calibration API wrappers for Brand3."""

from __future__ import annotations

from pathlib import Path

from src.config import BRAND3_DB_PATH
from src.services.calibration_state import _build_experiment_summary
from src.services.calibration_workflows import (
    _build_run_audit_context as _build_run_audit_context_impl,
    _default_gate_config as _default_gate_config_impl,
    _evaluate_promotion_gate as _evaluate_promotion_gate_impl,
    _load_gate_config as _load_gate_config_impl,
    _read_calibration_state as _read_calibration_state_impl,
    _restore_calibration_state as _restore_calibration_state_impl,
    apply_candidates as _apply_candidates_impl,
    compare_version as _compare_version_impl,
    get_gate_config as _get_gate_config_impl,
    list_baselines as _list_baselines_impl,
    list_candidates as _list_candidates_impl,
    list_experiments as _list_experiments_impl,
    list_versions as _list_versions_impl,
    promote_baseline as _promote_baseline_impl,
    propose_calibration as _propose_calibration_impl,
    review_candidate as _review_candidate_impl,
    rollback_version as _rollback_version_impl,
    run_experiment as _run_experiment_impl,
    set_gate_config as _set_gate_config_impl,
)
from src.storage.sqlite_store import SQLiteStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIMENSIONS_PATH = (PROJECT_ROOT / "src" / "dimensions.py").resolve()
ENGINE_PATH = (PROJECT_ROOT / "src" / "scoring" / "engine.py").resolve()
BRAND3_PROMOTION_MAX_COMPOSITE_DROP = 4.0
BRAND3_PROMOTION_MAX_DIMENSION_DROPS = {
    "percepcion": 5.0,
    "coherencia": 5.0,
    "diferenciacion": 5.0,
    "presencia": 5.0,
    "vitalidad": 5.0,
}


def _service():
    from src.services import brand_service as service

    return service


def _service_attr(name: str, default):
    return getattr(_service(), name, default)


def _db_path() -> str:
    return _service_attr("BRAND3_DB_PATH", BRAND3_DB_PATH)


def _dimensions_path() -> Path:
    return _service_attr("DIMENSIONS_PATH", DIMENSIONS_PATH)


def _engine_path() -> Path:
    return _service_attr("ENGINE_PATH", ENGINE_PATH)


def _default_composite_drop() -> float:
    return _service_attr("BRAND3_PROMOTION_MAX_COMPOSITE_DROP", BRAND3_PROMOTION_MAX_COMPOSITE_DROP)


def _default_dimension_drops() -> dict:
    return _service_attr("BRAND3_PROMOTION_MAX_DIMENSION_DROPS", BRAND3_PROMOTION_MAX_DIMENSION_DROPS)


def _load_gate_config(store: SQLiteStore | None = None) -> dict:
    return _load_gate_config_impl(
        store,
        db_path=_db_path(),
        default_gate_config=_default_gate_config,
    )


def _default_gate_config() -> dict:
    return _default_gate_config_impl(
        max_composite_drop=_default_composite_drop(),
        max_dimension_drops=_default_dimension_drops(),
    )


def _evaluate_promotion_gate(experiment: dict | None, gate_config: dict | None = None) -> dict:
    return _evaluate_promotion_gate_impl(
        experiment,
        gate_config=gate_config,
        default_gate_config=_default_gate_config,
        default_max_composite_drop=_default_composite_drop(),
        default_max_dimension_drops=_default_dimension_drops(),
    )


def _read_calibration_state(store: SQLiteStore | None = None) -> dict[str, object]:
    return _read_calibration_state_impl(
        store,
        dimensions_path=_dimensions_path(),
        engine_path=_engine_path(),
        load_gate_config=_load_gate_config,
    )


def _restore_calibration_state(version: dict, store: SQLiteStore | None = None) -> None:
    _restore_calibration_state_impl(
        version,
        store,
        db_path=_db_path(),
        dimensions_path=_dimensions_path(),
        engine_path=_engine_path(),
    )


def _build_run_audit_context(
    store: SQLiteStore | None = None,
    calibration_profile: str = "base",
    niche_classification: dict | None = None,
) -> dict:
    return _build_run_audit_context_impl(
        store=store,
        db_path=_db_path(),
        dimensions_path=_dimensions_path(),
        engine_path=_engine_path(),
        load_gate_config=_load_gate_config,
        calibration_profile=calibration_profile,
        niche_classification=niche_classification,
    )


def propose_calibration(brand_name: str, limit: int = 20, persist: bool = False) -> list[dict]:
    return _propose_calibration_impl(
        brand_name,
        db_path=_db_path(),
        limit=limit,
        persist=persist,
    )


def list_candidates(brand_name: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
    return _list_candidates_impl(brand_name, status, limit, db_path=_db_path())


def review_candidate(candidate_id: int, status: str) -> dict:
    return _review_candidate_impl(candidate_id, status, db_path=_db_path())


def apply_candidates(candidate_ids: list[int] | None = None, brand_name: str | None = None) -> list[dict]:
    return _apply_candidates_impl(
        candidate_ids=candidate_ids,
        brand_name=brand_name,
        db_path=_db_path(),
        dimensions_path=_dimensions_path(),
        engine_path=_engine_path(),
        read_calibration_state=_read_calibration_state,
    )


def run_experiment(brand_name: str, candidate_ids: list[int] | None = None) -> dict:
    return _run_experiment_impl(
        brand_name,
        candidate_ids=candidate_ids,
        db_path=_db_path(),
        run_fn=getattr(_service(), "run", None),
        apply_candidates_fn=getattr(_service(), "apply_candidates", None) or apply_candidates,
    )


def list_experiments(brand_name: str | None = None, limit: int = 20) -> list[dict]:
    return _list_experiments_impl(brand_name, limit, db_path=_db_path())


def list_versions(limit: int = 20) -> list[dict]:
    return _list_versions_impl(limit, db_path=_db_path())


def rollback_version(version_id: int) -> dict:
    return _rollback_version_impl(
        version_id,
        db_path=_db_path(),
        read_calibration_state=_read_calibration_state,
        restore_calibration_state=_restore_calibration_state,
    )


def promote_baseline(version_id: int, label: str | None = None, force: bool = False) -> dict:
    return _promote_baseline_impl(
        version_id,
        label=label,
        force=force,
        db_path=_db_path(),
        load_gate_config=_load_gate_config,
        evaluate_promotion_gate=_evaluate_promotion_gate,
    )


def list_baselines(limit: int = 20) -> dict:
    return _list_baselines_impl(limit, db_path=_db_path())


def get_gate_config() -> dict:
    return _get_gate_config_impl(db_path=_db_path(), load_gate_config=_load_gate_config)


def set_gate_config(max_composite_drop: float | None = None, dimension_drops: dict | None = None) -> dict:
    return _set_gate_config_impl(
        max_composite_drop=max_composite_drop,
        dimension_drops=dimension_drops,
        db_path=_db_path(),
        load_gate_config=_load_gate_config,
    )


def compare_version(version_id: int, brand_name: str) -> dict:
    return _compare_version_impl(
        version_id,
        brand_name,
        db_path=_db_path(),
        evaluate_promotion_gate=_evaluate_promotion_gate,
        load_gate_config=_load_gate_config,
    )
