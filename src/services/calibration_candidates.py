"""Calibration candidate lifecycle helpers."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable, TypeVar

from src.learning.applier import CandidateApplyError, apply_candidate
from src.learning.calibration import CalibrationAnalyzer
from src.storage.sqlite_store import SQLiteStore


T = TypeVar("T")


def _with_store(db_path: str, action: Callable[[SQLiteStore], T]) -> T:
    store = SQLiteStore(db_path)
    try:
        return action(store)
    finally:
        store.close()


def propose_calibration(
    brand_name: str,
    *,
    db_path: str,
    limit: int = 20,
    persist: bool = False,
) -> list[dict]:
    def _action(store: SQLiteStore) -> list[dict]:
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

    return _with_store(db_path, _action)


def list_candidates(
    brand_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
    *,
    db_path: str,
) -> list[dict]:
    def _action(store: SQLiteStore) -> list[dict]:
        candidates = store.list_calibration_candidates(brand_name=brand_name, status=status, limit=limit)
        print(json.dumps(candidates, indent=2))
        return candidates

    return _with_store(db_path, _action)


def review_candidate(candidate_id: int, status: str, *, db_path: str) -> dict:
    if status not in {"approved", "rejected", "proposed", "applied"}:
        raise ValueError("Status must be one of: proposed, approved, rejected, applied")

    def _action(store: SQLiteStore) -> dict:
        candidate = store.get_calibration_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")
        store.update_calibration_candidate_status(candidate_id, status)
        candidate["status"] = status
        print(json.dumps(candidate, indent=2))
        return candidate

    return _with_store(db_path, _action)


def apply_candidates(
    candidate_ids: list[int] | None = None,
    brand_name: str | None = None,
    *,
    db_path: str,
    dimensions_path,
    engine_path,
    read_calibration_state: Callable[[SQLiteStore | None], dict[str, object]],
) -> list[dict]:
    def _action(store: SQLiteStore) -> list[dict]:
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

    return _with_store(db_path, _action)
