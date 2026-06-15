"""Score replay and integrity checks for persisted Brand3 runs.

This module compares persisted analysis data against a recomputation using the
current scoring code, weights, and gate configuration.

It does not mutate persisted state and it does not define a new scoring model.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.config import BRAND3_PROMOTION_MAX_COMPOSITE_DROP, BRAND3_PROMOTION_MAX_DIMENSION_DROPS
from src.models.brand import FeatureValue
from src.niche.profiles import get_calibration_profile
from src.scoring.engine import ScoringEngine
from src.storage.sqlite_store import SQLiteStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIMENSIONS_PATH = (PROJECT_ROOT / "src" / "dimensions.py").resolve()
ENGINE_PATH = (PROJECT_ROOT / "src" / "scoring" / "engine.py").resolve()
_SNAPSHOT_UNSET = object()


def _default_gate_config() -> dict[str, Any]:
    return {
        "max_composite_drop": BRAND3_PROMOTION_MAX_COMPOSITE_DROP,
        "max_dimension_drops": dict(BRAND3_PROMOTION_MAX_DIMENSION_DROPS),
    }


def _load_gate_config(store: SQLiteStore | None = None) -> dict[str, Any]:
    should_close = False
    if store is None:
        store = SQLiteStore()
        should_close = True
    try:
        return store.get_gate_config() or _default_gate_config()
    finally:
        if should_close:
            store.close()


def _compute_scoring_state_fingerprint(
    *,
    dimensions_content: str,
    engine_content: str,
    gate_config: dict[str, Any],
    calibration_profile: str,
    calibration_profile_config: dict[str, Any],
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


def _to_float(value: Any | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _issue(
    code: str,
    message: str,
    *,
    severity: str = "error",
    dimension: str | None = None,
    **details: Any,
) -> dict[str, Any]:
    issue = {"code": code, "message": message, "severity": severity}
    if dimension is not None:
        issue["dimension"] = dimension
    if details:
        issue["details"] = details
    return issue


def _load_result_artifact(path: str | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not path:
        return None, _issue(
            "result_artifact_missing",
            "The run has no persisted result artifact path.",
        )

    artifact_path = Path(path)
    try:
        raw = artifact_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, _issue(
            "result_artifact_missing",
            "The persisted result artifact file does not exist.",
            path=str(artifact_path),
        )

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, _issue(
            "result_artifact_invalid_json",
            "The persisted result artifact contains malformed JSON.",
            path=str(artifact_path),
            raw_json=raw,
            error=str(exc),
        )

    if not isinstance(payload, dict):
        return None, _issue(
            "result_artifact_invalid_shape",
            "The persisted result artifact is not a JSON object.",
            path=str(artifact_path),
            raw_type=type(payload).__name__,
        )

    return payload, None


def _build_features_by_dim(snapshot: dict[str, Any]) -> dict[str, dict[str, FeatureValue]]:
    features_by_dim: dict[str, dict[str, FeatureValue]] = {}
    for row in snapshot.get("features", []):
        dimension_name = str(row.get("dimension_name") or "")
        feature_name = str(row.get("feature_name") or "")
        if not dimension_name or not feature_name:
            continue
        features_by_dim.setdefault(dimension_name, {})[feature_name] = FeatureValue(
            name=feature_name,
            value=float(row.get("value") or 0.0),
            raw_value=None if row.get("raw_value") is None else str(row.get("raw_value")),
            confidence=float(row.get("confidence") or 0.0),
            source=str(row.get("source") or ""),
        )
    return features_by_dim


def _serialize_features_by_dim(features_by_dim: dict[str, dict[str, FeatureValue]]) -> dict[str, dict[str, Any]]:
    serialized: dict[str, dict[str, Any]] = {}
    for dimension_name, features in features_by_dim.items():
        serialized[dimension_name] = {}
        for feature_name, feature in features.items():
            serialized[dimension_name][feature_name] = {
                "value": feature.value,
                "raw_value": feature.raw_value,
                "confidence": feature.confidence,
                "source": feature.source,
            }
    return serialized


def _compare_dimension_scores(
    *,
    dimension_name: str,
    persisted_score: float | None,
    recomputed_score: float | None,
    source: str,
) -> dict[str, Any] | None:
    if persisted_score is None and recomputed_score is None:
        return None
    if persisted_score is None or recomputed_score is None:
        return _issue(
            f"{source}_dimension_missing_score",
            "One side of the dimension score comparison is missing.",
            dimension=dimension_name,
            persisted=persisted_score,
            recomputed=recomputed_score,
        )
    if round(abs(persisted_score - recomputed_score), 1) != 0.0:
        return _issue(
            f"{source}_dimension_mismatch",
            "The dimension score differs between persisted data and replay.",
            dimension=dimension_name,
            persisted=persisted_score,
            recomputed=recomputed_score,
            difference=round(recomputed_score - persisted_score, 1),
        )
    return None


def _classify_drift(
    *,
    score_integrity: str,
    fingerprint_status: str,
    issues: list[dict[str, Any]],
) -> tuple[str, bool | None]:
    if score_integrity == "unverifiable":
        return "unverifiable", None

    error_codes = {
        str(issue.get("code") or "")
        for issue in issues
        if issue.get("severity") != "info"
    }

    artifact_codes = {
        "artifact_composite_mismatch",
        "artifact_composite_missing",
        "artifact_vs_db_dimension_mismatch",
        "artifact_dimension_missing_score",
    }
    score_codes = {
        "persisted_vs_recomputed_dimension_mismatch",
        "persisted_composite_mismatch",
        "persisted_vs_recomputed_dimension_missing_score",
        "persisted_composite_missing",
    }

    if error_codes & artifact_codes:
        return "artifact_mismatch", True
    if error_codes & {"persisted_vs_recomputed_dimension_mismatch"}:
        return "feature_score_mismatch", False
    if error_codes & score_codes:
        return "score_data_mismatch", False
    if fingerprint_status == "mismatch":
        return "fingerprint_only_mismatch", True
    return "none", True


def build_score_replay_audit(
    store: SQLiteStore,
    run_id: int,
    *,
    snapshot: dict[str, Any] | None | object = _SNAPSHOT_UNSET,
) -> dict[str, Any]:
    if snapshot is _SNAPSHOT_UNSET:
        snapshot = store.get_run_snapshot(run_id)
    if not snapshot:
        return {
            "run_id": run_id,
            "score_integrity": "unverifiable",
            "persisted_composite": None,
            "recomputed_composite": None,
            "difference": None,
            "fingerprint_status": "missing",
            "issues": [
                _issue(
                    "snapshot_missing",
                    "The persisted snapshot for this run could not be loaded.",
                )
            ],
            "recommended_action": "config_check",
        }

    run = snapshot.get("run") or {}
    calibration_profile = str(run.get("calibration_profile") or "base")
    persisted_composite = _to_float(run.get("composite_score"))
    persisted_fingerprint = str(run.get("scoring_state_fingerprint") or "").strip() or None
    run_result_path = run.get("result_path")

    result_artifact, artifact_load_issue = _load_result_artifact(run_result_path if isinstance(run_result_path, str) else None)
    artifact_partial_dimensions: list[str] = []
    artifact_partial_score = False
    artifact_composite = None
    artifact_dimensions: dict[str, Any] = {}
    if result_artifact:
        artifact_composite = _to_float(result_artifact.get("composite_score"))
        artifact_dimensions = result_artifact.get("dimensions") if isinstance(result_artifact.get("dimensions"), dict) else {}
        artifact_partial_score = bool(result_artifact.get("partial_score"))
        raw_partial_dimensions = result_artifact.get("partial_dimensions")
        if isinstance(raw_partial_dimensions, list):
            artifact_partial_dimensions = [str(item) for item in raw_partial_dimensions if str(item).strip()]
        elif artifact_partial_score:
            artifact_load_issue = _issue(
                "artifact_missing_partial_dimensions",
                "The persisted result artifact does not record partial dimensions for a partial run.",
            )

    issues: list[dict[str, Any]] = []
    if artifact_load_issue:
        issues.append(artifact_load_issue)

    if result_artifact is not None:
        if persisted_composite is None or artifact_composite is None:
            if persisted_composite != artifact_composite:
                issues.append(
                    _issue(
                        "artifact_composite_missing",
                        "The persisted result artifact does not expose the same composite score shape as the DB snapshot.",
                        persisted=persisted_composite,
                        artifact=artifact_composite,
                    )
                )
        elif round(abs(persisted_composite - artifact_composite), 1) != 0.0:
            issues.append(
                _issue(
                    "artifact_composite_mismatch",
                    "The persisted result artifact composite score differs from the DB snapshot.",
                    persisted=persisted_composite,
                    artifact=artifact_composite,
                    difference=round(artifact_composite - persisted_composite, 1),
                )
            )

    gate_config = _load_gate_config(store)
    current_profile_config = get_calibration_profile(calibration_profile)
    current_fingerprint = _compute_scoring_state_fingerprint(
        dimensions_content=DIMENSIONS_PATH.read_text(encoding="utf-8"),
        engine_content=ENGINE_PATH.read_text(encoding="utf-8"),
        gate_config=gate_config,
        calibration_profile=calibration_profile,
        calibration_profile_config=current_profile_config,
    )
    if not persisted_fingerprint:
        fingerprint_status = "missing"
        issues.append(
            _issue(
                "fingerprint_missing",
                "The persisted scoring fingerprint is missing.",
            )
        )
    elif persisted_fingerprint == current_fingerprint:
        fingerprint_status = "match"
    else:
        fingerprint_status = "mismatch"
        issues.append(
            _issue(
                "fingerprint_mismatch",
                "The persisted scoring fingerprint differs from the current scoring config.",
                persisted=persisted_fingerprint,
                current=current_fingerprint,
            )
        )

    features_by_dim = _build_features_by_dim(snapshot)
    engine = ScoringEngine(calibration_profile=calibration_profile)
    all_dimension_names = sorted(engine.dimensions.keys())
    recomputed_brand = engine.score_brand(
        url=str(run.get("url") or ""),
        brand_name=str(run.get("brand_name") or ""),
        features_by_dim=features_by_dim,
        unavailable_dimensions=set(artifact_partial_dimensions),
    )
    recomputed_composite = recomputed_brand.composite_score
    if artifact_partial_score:
        recomputed_composite = None

    if persisted_composite is None or recomputed_composite is None:
        if persisted_composite != recomputed_composite:
            issues.append(
                _issue(
                    "persisted_composite_missing",
                    "The persisted composite score cannot be compared with the recomputed score.",
                    persisted=persisted_composite,
                    recomputed=recomputed_composite,
                )
            )
    elif round(abs(persisted_composite - recomputed_composite), 1) != 0.0:
        issues.append(
            _issue(
                "persisted_composite_mismatch",
                "The persisted composite score differs from the recomputed score.",
                persisted=persisted_composite,
                recomputed=recomputed_composite,
                difference=round(recomputed_composite - persisted_composite, 1),
            )
        )

    persisted_dimension_scores = {name: None for name in all_dimension_names}
    for row in snapshot.get("scores", []):
        dimension_name = str(row.get("dimension_name") or "")
        if dimension_name in persisted_dimension_scores:
            persisted_dimension_scores[dimension_name] = _to_float(row.get("score"))
    for dimension_name in all_dimension_names:
        persisted_score = persisted_dimension_scores.get(dimension_name)
        recomputed_score = recomputed_brand.dimensions.get(dimension_name).score if dimension_name in recomputed_brand.dimensions else None
        if artifact_partial_score and dimension_name in artifact_partial_dimensions:
            recomputed_score = None

        diff_issue = _compare_dimension_scores(
            dimension_name=dimension_name,
            persisted_score=persisted_score,
            recomputed_score=recomputed_score,
            source="persisted_vs_recomputed",
        )
        if diff_issue:
            issues.append(diff_issue)

        artifact_score = _to_float(artifact_dimensions.get(dimension_name))
        artifact_compare_issue = _compare_dimension_scores(
            dimension_name=dimension_name,
            persisted_score=persisted_score,
            recomputed_score=artifact_score,
            source="artifact_vs_db",
        )
        if artifact_compare_issue:
            issues.append(artifact_compare_issue)

        feature_count = len(features_by_dim.get(dimension_name, {}))
        if recomputed_score == 50.0 and feature_count == 0 and dimension_name not in artifact_partial_dimensions:
            issues.append(
                _issue(
                    "neutral_fallback_dimension",
                    "A 50.0 dimension score was produced without persisted features and should be interpreted as a neutral fallback, not an average-quality measurement.",
                    severity="info",
                    dimension=dimension_name,
                    persisted=persisted_score,
                    recomputed=recomputed_score,
                )
            )

    artifact_dimension_scores = {
        name: _to_float(artifact_dimensions.get(name))
        for name in all_dimension_names
    }
    recomputed_dimension_scores = {
        name: (score.score if score.score is not None else None)
        for name, score in recomputed_brand.dimensions.items()
    }

    error_issues = [issue for issue in issues if issue.get("severity") != "info"]
    info_issues = [issue for issue in issues if issue.get("severity") == "info"]
    if fingerprint_status == "missing" or artifact_load_issue or not snapshot.get("run"):
        score_integrity = "unverifiable"
    elif error_issues:
        score_integrity = "drift_detected"
    else:
        score_integrity = "valid"

    drift_type, score_values_match_persisted_data = _classify_drift(
        score_integrity=score_integrity,
        fingerprint_status=fingerprint_status,
        issues=issues,
    )

    if score_integrity == "unverifiable":
        recommended_action = "config_check"
    elif error_issues:
        recommended_action = "config_check" if fingerprint_status == "mismatch" else "rerun"
    elif info_issues:
        recommended_action = "human_review"
    else:
        recommended_action = "none"

    difference = None
    if persisted_composite is not None and recomputed_composite is not None:
        difference = round(recomputed_composite - persisted_composite, 1)

    return {
        "run_id": run_id,
        "score_integrity": score_integrity,
        "persisted_composite": persisted_composite,
        "recomputed_composite": recomputed_composite,
        "difference": difference,
        "fingerprint_status": fingerprint_status,
        "drift_type": drift_type,
        "score_values_match_persisted_data": score_values_match_persisted_data,
        "persisted_scoring_state_fingerprint": persisted_fingerprint,
        "current_scoring_state_fingerprint": current_fingerprint,
        "persisted_features": _serialize_features_by_dim(features_by_dim),
        "persisted_dimension_scores": persisted_dimension_scores,
        "artifact_dimension_scores": artifact_dimension_scores,
        "recomputed_dimension_scores": recomputed_dimension_scores,
        "dimensions": {
            name: {
                "persisted": persisted_dimension_scores.get(name),
                "artifact": artifact_dimension_scores.get(name),
                "recomputed": recomputed_dimension_scores.get(name),
                "feature_count": len(features_by_dim.get(name, {})),
                "unavailable": name in artifact_partial_dimensions,
            }
            for name in all_dimension_names
        },
        "issues": issues,
        "recommended_action": recommended_action,
    }
