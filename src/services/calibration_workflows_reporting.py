"""Calibration reporting and version management helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable, TypeVar

from src.services.calibration_state import _compare_summaries
from src.storage.sqlite_store import SQLiteStore


T = TypeVar("T")


def _with_store(db_path: str, action: Callable[[SQLiteStore], T]) -> T:
    store = SQLiteStore(db_path)
    try:
        return action(store)
    finally:
        store.close()


def list_experiments(brand_name: str | None = None, limit: int = 20, *, db_path: str) -> list[dict]:
    def _action(store: SQLiteStore) -> list[dict]:
        experiments = store.list_experiments(brand_name=brand_name, limit=limit)
        print(json.dumps(experiments, indent=2))
        return experiments

    return _with_store(db_path, _action)


def list_versions(limit: int = 20, *, db_path: str) -> list[dict]:
    def _action(store: SQLiteStore) -> list[dict]:
        versions = store.list_calibration_versions(limit=limit)
        print(json.dumps(versions, indent=2))
        return versions

    return _with_store(db_path, _action)


def rollback_version(version_id: int, *, db_path: str, read_calibration_state, restore_calibration_state) -> dict:
    def _action(store: SQLiteStore) -> dict:
        version = store.get_calibration_version(version_id)
        if not version:
            raise ValueError(f"Calibration version {version_id} not found")
        current_state = read_calibration_state(store)
        rollback_source_id = store.save_calibration_version(
            label=f"pre-rollback-{datetime.now().isoformat()}",
            dimensions_content=current_state["dimensions_content"],
            engine_content=current_state["engine_content"],
            gate_config=current_state["gate_config"],
        )
        restore_calibration_state(version, store)
        restored_state = read_calibration_state(store)
        restored_version_id = store.save_calibration_version(
            label=f"rollback-to-{version_id}",
            dimensions_content=restored_state["dimensions_content"],
            engine_content=restored_state["engine_content"],
            gate_config=restored_state["gate_config"],
        )
        payload = {
            "rolled_back": True,
            "target_version_id": version_id,
            "rollback_source_version_id": rollback_source_id,
            "restored_version_id": restored_version_id,
            "label": version["label"],
        }
        print(json.dumps(payload, indent=2))
        return payload

    return _with_store(db_path, _action)


def promote_baseline(
    version_id: int,
    label: str | None = None,
    force: bool = False,
    *,
    db_path: str,
    load_gate_config,
    evaluate_promotion_gate,
) -> dict:
    def _action(store: SQLiteStore) -> dict:
        version = store.get_calibration_version(version_id)
        if not version:
            raise ValueError(f"Calibration version {version_id} not found")
        experiment = store.get_latest_experiment_for_version(version_id)
        gate = evaluate_promotion_gate(experiment, gate_config=version.get("gate_config"))
        if not gate["allowed"] and not force:
            payload = {
                "promoted": False,
                "version_id": version_id,
                "label": label or version["label"],
                "gate": gate,
            }
            print(json.dumps(payload, indent=2))
            return payload
        if version.get("gate_config") is not None:
            store.upsert_gate_config(version["gate_config"])
        baseline_id = store.promote_baseline(version_id=version_id, label=label or version["label"])
        payload = {
            "baseline_id": baseline_id,
            "version_id": version_id,
            "label": label or version["label"],
            "promoted": True,
            "forced": force,
            "gate": gate,
        }
        print(json.dumps(payload, indent=2))
        return payload

    return _with_store(db_path, _action)


def list_baselines(limit: int = 20, *, db_path: str) -> dict:
    def _action(store: SQLiteStore) -> dict:
        payload = {
            "active": store.get_active_baseline(),
            "history": store.list_baselines(limit=limit),
        }
        print(json.dumps(payload, indent=2))
        return payload

    return _with_store(db_path, _action)


def get_gate_config(*, db_path: str, load_gate_config) -> dict:
    def _action(store: SQLiteStore) -> dict:
        payload = load_gate_config(store)
        print(json.dumps(payload, indent=2))
        return payload

    return _with_store(db_path, _action)


def set_gate_config(
    max_composite_drop: float | None = None,
    dimension_drops: dict | None = None,
    *,
    db_path: str,
    load_gate_config,
) -> dict:
    def _action(store: SQLiteStore) -> dict:
        current = load_gate_config(store)
        if max_composite_drop is not None:
            current["max_composite_drop"] = float(max_composite_drop)
        if dimension_drops:
            merged = dict(current.get("max_dimension_drops", {}))
            merged.update({key: float(value) for key, value in dimension_drops.items()})
            current["max_dimension_drops"] = merged
        store.upsert_gate_config(current)
        print(json.dumps(current, indent=2))
        return current

    return _with_store(db_path, _action)


def compare_version(
    version_id: int,
    brand_name: str,
    *,
    db_path: str,
    evaluate_promotion_gate,
    load_gate_config,
) -> dict:
    def _action(store: SQLiteStore) -> dict:
        version = store.get_calibration_version(version_id)
        if not version:
            raise ValueError(f"Calibration version {version_id} not found")

        target_experiment = store.get_latest_experiment_for_version(version_id, brand_name=brand_name)
        active_baseline = store.get_active_baseline()
        baseline_experiment = None
        if active_baseline:
            baseline_experiment = store.get_latest_experiment_for_version(
                active_baseline["version_id"],
                brand_name=brand_name,
            )

        payload = {
            "brand_name": brand_name,
            "target_version": {
                "id": version["id"],
                "label": version["label"],
            },
            "target_gate": evaluate_promotion_gate(
                target_experiment,
                gate_config=version.get("gate_config") or load_gate_config(store),
            ),
            "target_experiment": target_experiment,
            "active_baseline": active_baseline,
            "baseline_experiment": baseline_experiment,
            "comparison": _compare_summaries(
                target_experiment.get("summary") if target_experiment else None,
                baseline_experiment.get("summary") if baseline_experiment else None,
            ),
        }
        print(json.dumps(payload, indent=2))
        return payload

    return _with_store(db_path, _action)
