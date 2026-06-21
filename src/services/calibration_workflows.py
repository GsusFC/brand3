"""Calibration workflows, experiments, and version management helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.learning.applier import CandidateApplyError, apply_candidate
from src.learning.calibration import CalibrationAnalyzer
from src.niche import get_calibration_profile
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
from src.services.serialization import _to_jsonable
from src.storage.sqlite_store import SQLiteStore


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
    store = SQLiteStore(db_path)
    try:
        report = store.get_brand_report(brand_name, limit=limit)
        analyzer = CalibrationAnalyzer()
        candidates = analyzer.propose_candidates(report, report.get("annotations", []))

        payload = []
        for candidate in candidates:
            item = {
                "scope": candidate.scope,
                "target": candidate.target,
                "proposal": candidate.proposal,
                "rationale": candidate.rationale,
                "severity": candidate.severity,
                "evidence": candidate.evidence,
            }
            if persist:
                item["candidate_id"] = store.save_calibration_candidate(
                    brand_name=brand_name,
                    scope=candidate.scope,
                    target=candidate.target,
                    proposal=candidate.proposal,
                    rationale=candidate.rationale,
                )
            payload.append(item)

        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def list_candidates(
    brand_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
    *,
    db_path: str,
) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        candidates = store.list_calibration_candidates(brand_name=brand_name, status=status, limit=limit)
        print(json.dumps(candidates, indent=2))
        return candidates
    finally:
        store.close()


def review_candidate(candidate_id: int, status: str, *, db_path: str) -> dict:
    if status not in {"approved", "rejected", "proposed", "applied"}:
        raise ValueError("Status must be one of: proposed, approved, rejected, applied")
    store = SQLiteStore(db_path)
    try:
        candidate = store.get_calibration_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")
        store.update_calibration_candidate_status(candidate_id, status)
        candidate["status"] = status
        print(json.dumps(candidate, indent=2))
        return candidate
    finally:
        store.close()


def apply_candidates(
    candidate_ids: list[int] | None = None,
    brand_name: str | None = None,
    *,
    db_path: str,
    dimensions_path: Path,
    engine_path: Path,
    read_calibration_state: Callable[[SQLiteStore | None], dict[str, object]],
) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        if candidate_ids:
            candidates = []
            for candidate_id in candidate_ids:
                candidate = store.get_calibration_candidate(candidate_id)
                if not candidate:
                    raise ValueError(f"Candidate {candidate_id} not found")
                candidates.append(candidate)
        else:
            candidates = store.list_calibration_candidates(brand_name=brand_name, status="approved", limit=100)

        version_before_id = None
        version_after_id = None
        results = []
        for candidate in candidates:
            if candidate["status"] != "approved":
                results.append(
                    {
                        "candidate_id": candidate["id"],
                        "applied": False,
                        "reason": f"Candidate status is {candidate['status']}, not approved",
                    }
                )
                continue
            try:
                if version_before_id is None:
                    state_before = read_calibration_state(store)
                    version_before_id = store.save_calibration_version(
                        label=f"before-apply-{datetime.now().isoformat()}",
                        dimensions_content=state_before["dimensions_content"],
                        engine_content=state_before["engine_content"],
                        gate_config=state_before["gate_config"],
                    )
                applied = apply_candidate(dimensions_path, engine_path, candidate)
                applied["candidate_id"] = candidate["id"]
                results.append(applied)
                if applied["applied"]:
                    state_after = read_calibration_state(store)
                    version_after_id = store.save_calibration_version(
                        label=f"after-apply-{datetime.now().isoformat()}",
                        dimensions_content=state_after["dimensions_content"],
                        engine_content=state_after["engine_content"],
                        gate_config=state_after["gate_config"],
                    )
                    applied["version_before_id"] = version_before_id
                    applied["version_after_id"] = version_after_id
                    store.update_calibration_candidate_status(candidate["id"], "applied")
                    store.save_applied_calibration(candidate["id"], version_before_id, version_after_id)
            except CandidateApplyError as e:
                results.append(
                    {
                        "candidate_id": candidate["id"],
                        "applied": False,
                        "reason": str(e),
                    }
                )

        print(json.dumps(results, indent=2))
        return results
    finally:
        store.close()


def run_experiment(
    brand_name: str,
    candidate_ids: list[int] | None = None,
    *,
    db_path: str,
    run_fn,
    apply_candidates_fn,
    build_experiment_summary=_build_experiment_summary,
) -> dict:
    store = SQLiteStore(db_path)
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

    store = SQLiteStore(db_path)
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
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def list_experiments(brand_name: str | None = None, limit: int = 20, *, db_path: str) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        experiments = store.list_experiments(brand_name=brand_name, limit=limit)
        print(json.dumps(experiments, indent=2))
        return experiments
    finally:
        store.close()


def list_versions(limit: int = 20, *, db_path: str) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        versions = store.list_calibration_versions(limit=limit)
        print(json.dumps(versions, indent=2))
        return versions
    finally:
        store.close()


def rollback_version(version_id: int, *, db_path: str, read_calibration_state, restore_calibration_state) -> dict:
    store = SQLiteStore(db_path)
    try:
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
    finally:
        store.close()


def promote_baseline(
    version_id: int,
    label: str | None = None,
    force: bool = False,
    *,
    db_path: str,
    load_gate_config,
    evaluate_promotion_gate,
) -> dict:
    store = SQLiteStore(db_path)
    try:
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
    finally:
        store.close()


def list_baselines(limit: int = 20, *, db_path: str) -> dict:
    store = SQLiteStore(db_path)
    try:
        payload = {
            "active": store.get_active_baseline(),
            "history": store.list_baselines(limit=limit),
        }
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def get_gate_config(*, db_path: str, load_gate_config) -> dict:
    store = SQLiteStore(db_path)
    try:
        payload = load_gate_config(store)
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def set_gate_config(
    max_composite_drop: float | None = None,
    dimension_drops: dict | None = None,
    *,
    db_path: str,
    load_gate_config,
) -> dict:
    store = SQLiteStore(db_path)
    try:
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
    finally:
        store.close()


def compare_version(
    version_id: int,
    brand_name: str,
    *,
    db_path: str,
    evaluate_promotion_gate,
    load_gate_config,
) -> dict:
    store = SQLiteStore(db_path)
    try:
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
    finally:
        store.close()
