"""Scoring orchestration for Brand3 analysis runs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScoringResult:
    engine: object
    brand_score: object


def score_features(
    *,
    url: str,
    brand_name: str,
    features_by_dim: dict[str, dict],
    partial_dimensions: list[str],
    data_quality: str,
    calibration_profile: str,
    store,
    run_id: int | None,
    scoring_engine_cls,
    store_safely,
) -> ScoringResult:
    engine = scoring_engine_cls(calibration_profile=calibration_profile)
    brand_score = engine.score_brand(
        url,
        brand_name,
        features_by_dim,
        unavailable_dimensions=set(partial_dimensions),
    )
    if data_quality == "insufficient":
        brand_score.composite_score = None
    if run_id:
        store_safely(store, "feature save", lambda: store.save_features(run_id, features_by_dim))
        store_safely(store, "score save", lambda: store.save_scores(run_id, brand_score))
    return ScoringResult(engine=engine, brand_score=brand_score)
