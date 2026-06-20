"""Feature and score persistence helpers for SQLiteStore."""

from __future__ import annotations

from datetime import datetime

from ..models.brand import BrandScore, FeatureValue
from .json_payloads import json_dumps as _json_dumps


class FeaturesScoresStoreMixin:
    """Persists extracted feature values and computed dimension scores."""

    def save_features(self, run_id: int, features_by_dim: dict[str, dict[str, FeatureValue]]) -> None:
        rows = []
        now = datetime.now().isoformat()
        for dimension_name, features in features_by_dim.items():
            for feature_name, feature in features.items():
                rows.append(
                    (
                        run_id,
                        dimension_name,
                        feature_name,
                        float(feature.value),
                        None if feature.raw_value is None else str(feature.raw_value),
                        float(feature.confidence),
                        feature.source,
                        now,
                    )
                )
        self.conn.executemany(
            """
            INSERT INTO features (
                run_id, dimension_name, feature_name, value,
                raw_value, confidence, source, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def save_scores(self, run_id: int, brand_score: BrandScore) -> None:
        rows = []
        now = datetime.now().isoformat()
        for dimension_name, dimension_score in brand_score.dimensions.items():
            if dimension_score.score is None:
                continue
            rows.append(
                (
                    run_id,
                    dimension_name,
                    float(dimension_score.score),
                    _json_dumps(dimension_score.insights),
                    _json_dumps(dimension_score.rules_applied),
                    now,
                )
            )
        if rows:
            self.conn.executemany(
                """
                INSERT INTO scores (run_id, dimension_name, score, insights_json, rules_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        self.conn.commit()
