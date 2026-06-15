import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import BRAND3_PROMOTION_MAX_COMPOSITE_DROP, BRAND3_PROMOTION_MAX_DIMENSION_DROPS
from src.models.brand import BrandScore, DimensionScore, FeatureValue
from src.scoring.engine import ScoringEngine
from src.scoring.replay import (
    DIMENSIONS_PATH,
    ENGINE_PATH,
    _compute_scoring_state_fingerprint,
    build_score_replay_audit,
)
from src.storage.sqlite_store import SQLiteStore


def _default_gate_config() -> dict:
    return {
        "max_composite_drop": BRAND3_PROMOTION_MAX_COMPOSITE_DROP,
        "max_dimension_drops": dict(BRAND3_PROMOTION_MAX_DIMENSION_DROPS),
    }


def _build_feature_set() -> dict[str, dict[str, FeatureValue]]:
    return {
        "coherencia": {
            "visual_consistency": FeatureValue("visual_consistency", 80.0, confidence=0.9, source="web_scrape"),
            "messaging_consistency": FeatureValue("messaging_consistency", 60.0, confidence=0.8, source="llm"),
            "tone_consistency": FeatureValue("tone_consistency", 70.0, confidence=0.8, source="llm"),
            "cross_channel_coherence": FeatureValue("cross_channel_coherence", 50.0, confidence=0.7, source="web_scrape"),
        },
        "presencia": {
            "web_presence": FeatureValue("web_presence", 90.0, confidence=0.9, source="web_scrape"),
            "social_footprint": FeatureValue("social_footprint", 75.0, confidence=0.9, source="social_media"),
            "search_visibility": FeatureValue("search_visibility", 80.0, confidence=0.8, source="exa"),
            "directory_presence": FeatureValue("directory_presence", 30.0, confidence=0.8, source="exa"),
        },
        "percepcion": {
            "brand_sentiment": FeatureValue("brand_sentiment", 70.0, confidence=0.8, source="llm"),
            "mention_volume": FeatureValue("mention_volume", 65.0, confidence=0.9, source="exa"),
            "sentiment_trend": FeatureValue("sentiment_trend", 55.0, confidence=0.8, source="llm"),
            "review_quality": FeatureValue("review_quality", 50.0, confidence=0.8, source="exa"),
        },
        "diferenciacion": {
            "positioning_clarity": FeatureValue("positioning_clarity", 75.0, confidence=0.8, source="llm"),
            "uniqueness": FeatureValue("uniqueness", 70.0, confidence=0.8, source="llm"),
            "competitor_distance": FeatureValue("competitor_distance", 70.0, confidence=0.8, source="llm"),
            "content_authenticity": FeatureValue("content_authenticity", 85.0, confidence=0.8, source="content_analysis"),
            "brand_personality": FeatureValue("brand_personality", 80.0, confidence=0.8, source="content_analysis"),
        },
        "vitalidad": {
            "content_recency": FeatureValue("content_recency", 90.0, confidence=0.9, source="exa"),
            "publication_cadence": FeatureValue("publication_cadence", 80.0, confidence=0.9, source="exa"),
            "momentum": FeatureValue("momentum", 60.0, confidence=0.8, source="llm"),
        },
    }


def _persist_fixture_run(
    store: SQLiteStore,
    *,
    partial_dimensions: list[str] | None = None,
    partial_score: bool = False,
) -> tuple[int, dict, Path]:
    brand_id = store.upsert_brand("Example", "https://example.com")
    run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)
    features_by_dim = _build_feature_set()

    if partial_dimensions:
        for dim_name in partial_dimensions:
            features_by_dim.pop(dim_name, None)

    engine = ScoringEngine()
    brand_score = engine.score_brand(
        "https://example.com",
        "Example",
        features_by_dim,
        unavailable_dimensions=set(partial_dimensions or []),
    )
    if partial_score:
        brand_score.composite_score = None

    store.save_features(run_id, features_by_dim)
    store.save_scores(run_id, brand_score)

    gate_config = _default_gate_config()
    store.upsert_gate_config(gate_config)
    fingerprint = _compute_scoring_state_fingerprint(
        dimensions_content=DIMENSIONS_PATH.read_text(encoding="utf-8"),
        engine_content=ENGINE_PATH.read_text(encoding="utf-8"),
        gate_config=gate_config,
        calibration_profile="base",
        calibration_profile_config=engine.profile_config,
    )
    store.save_run_audit(
        run_id,
        {
            "gate_config": gate_config,
            "active_baseline": None,
            "scoring_state_fingerprint": fingerprint,
        },
    )

    artifact = {
        "run_id": run_id,
        "brand_name": "Example",
        "url": "https://example.com",
        "composite_score": brand_score.composite_score,
        "dimensions": brand_score.breakdown,
        "partial_dimensions": list(partial_dimensions or []),
        "partial_score": partial_score,
    }
    artifact_path = Path(store.db_path).with_name(f"result-{run_id}.json")
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    store.finalize_run(
        run_id,
        brand_score.composite_score,
        True,
        False,
        str(artifact_path),
        "summary",
    )
    return run_id, artifact, artifact_path


class ScoreReplayAuditTests(unittest.TestCase):
    def test_valid_replay_matches_persisted_score_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _, _ = _persist_fixture_run(store)

            report = build_score_replay_audit(store, run_id)

            store.close()

            self.assertEqual(report["score_integrity"], "valid")
            self.assertEqual(report["fingerprint_status"], "match")
            self.assertEqual(report["drift_type"], "none")
            self.assertTrue(report["score_values_match_persisted_data"])
            self.assertEqual(report["difference"], 0.0)
            self.assertEqual(report["recommended_action"], "none")
            self.assertEqual(report["persisted_composite"], report["recomputed_composite"])

    def test_replay_uses_provided_snapshot_without_reloading(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _, _ = _persist_fixture_run(store)
            snapshot = store.get_run_snapshot(run_id)

            with patch.object(store, "get_run_snapshot", side_effect=AssertionError("snapshot should be reused")):
                report = build_score_replay_audit(store, run_id, snapshot=snapshot)

            store.close()

            self.assertEqual(report["score_integrity"], "valid")

    def test_tampered_composite_score_is_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _, _ = _persist_fixture_run(store)
            store.conn.execute("UPDATE runs SET composite_score = ? WHERE id = ?", (99.0, run_id))
            store.conn.commit()

            report = build_score_replay_audit(store, run_id)

            store.close()

            self.assertEqual(report["score_integrity"], "drift_detected")
            self.assertEqual(report["fingerprint_status"], "match")
            self.assertEqual(report["recommended_action"], "rerun")
            self.assertTrue(
                any(issue["code"] == "persisted_composite_mismatch" for issue in report["issues"])
            )
            self.assertTrue(
                any(issue["code"] == "artifact_composite_mismatch" for issue in report["issues"])
            )

    def test_tampered_feature_value_is_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _, _ = _persist_fixture_run(store)
            store.conn.execute(
                """
                UPDATE features
                SET value = ?
                WHERE run_id = ? AND dimension_name = ? AND feature_name = ?
                """,
                (5.0, run_id, "presencia", "web_presence"),
            )
            store.conn.commit()

            report = build_score_replay_audit(store, run_id)

            store.close()

            self.assertEqual(report["score_integrity"], "drift_detected")
            self.assertEqual(report["recommended_action"], "rerun")
            self.assertEqual(report["drift_type"], "feature_score_mismatch")
            self.assertFalse(report["score_values_match_persisted_data"])
            self.assertTrue(
                any(
                    issue["code"] == "persisted_vs_recomputed_dimension_mismatch"
                    and issue.get("dimension") == "presencia"
                    for issue in report["issues"]
                )
            )

    def test_tampered_artifact_json_is_classified_separately(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, artifact, artifact_path = _persist_fixture_run(store)
            artifact["composite_score"] = 88.0
            artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")

            report = build_score_replay_audit(store, run_id)

            store.close()

            self.assertEqual(report["score_integrity"], "drift_detected")
            self.assertEqual(report["drift_type"], "artifact_mismatch")
            self.assertTrue(report["score_values_match_persisted_data"])
            self.assertEqual(report["recommended_action"], "rerun")
            self.assertTrue(
                any(issue["code"] == "artifact_composite_mismatch" for issue in report["issues"])
            )

    def test_changed_weights_are_detected_as_score_data_drift(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _, _ = _persist_fixture_run(store)

            altered_profile = {
                "dimension_weights": {
                    "coherencia": 0.10,
                    "presencia": 0.10,
                    "percepcion": 0.60,
                    "diferenciacion": 0.10,
                    "vitalidad": 0.10,
                },
                "rule_overrides": {},
            }

            with (
                patch("src.scoring.engine.get_calibration_profile", return_value=altered_profile),
                patch("src.scoring.replay.get_calibration_profile", return_value=altered_profile),
            ):
                report = build_score_replay_audit(store, run_id)

            store.close()

            self.assertEqual(report["score_integrity"], "drift_detected")
            self.assertEqual(report["fingerprint_status"], "mismatch")
            self.assertEqual(report["drift_type"], "score_data_mismatch")
            self.assertFalse(report["score_values_match_persisted_data"])
            self.assertEqual(report["recommended_action"], "config_check")
            self.assertTrue(
                any(issue["code"] == "fingerprint_mismatch" for issue in report["issues"])
            )

    def test_fingerprint_only_mismatch_keeps_score_values_matching(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _, _ = _persist_fixture_run(store)
            store.conn.execute(
                "UPDATE run_audits SET scoring_state_fingerprint = ? WHERE run_id = ?",
                ("legacy-stale-fingerprint", run_id),
            )
            store.conn.commit()

            report = build_score_replay_audit(store, run_id)

            store.close()

            self.assertEqual(report["score_integrity"], "drift_detected")
            self.assertEqual(report["fingerprint_status"], "mismatch")
            self.assertEqual(report["drift_type"], "fingerprint_only_mismatch")
            self.assertTrue(report["score_values_match_persisted_data"])
            self.assertEqual(report["recommended_action"], "config_check")
            self.assertTrue(
                any(issue["code"] == "fingerprint_mismatch" for issue in report["issues"])
            )

    def test_missing_fingerprint_is_unverifiable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _, _ = _persist_fixture_run(store)
            store.conn.execute("DELETE FROM run_audits WHERE run_id = ?", (run_id,))
            store.conn.commit()

            report = build_score_replay_audit(store, run_id)

            store.close()

            self.assertEqual(report["score_integrity"], "unverifiable")
            self.assertEqual(report["fingerprint_status"], "missing")
            self.assertEqual(report["drift_type"], "unverifiable")
            self.assertIsNone(report["score_values_match_persisted_data"])
            self.assertEqual(report["recommended_action"], "config_check")
            self.assertTrue(any(issue["code"] == "fingerprint_missing" for issue in report["issues"]))

    def test_unavailable_dimensions_replay_cleanly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _, _ = _persist_fixture_run(
                store,
                partial_dimensions=["coherencia", "diferenciacion"],
            )

            report = build_score_replay_audit(store, run_id)

            store.close()

            self.assertEqual(report["score_integrity"], "valid")
            self.assertEqual(report["fingerprint_status"], "match")
            self.assertEqual(report["recommended_action"], "none")
            self.assertIsNone(report["persisted_dimension_scores"]["coherencia"])
            self.assertIsNone(report["recomputed_dimension_scores"]["coherencia"])
            self.assertTrue(report["dimensions"]["coherencia"]["unavailable"])

    def test_neutral_fallback_fifty_is_flagged_as_fallback_not_quality(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)

            engine = ScoringEngine()
            features_by_dim = {
                "coherencia": {
                    "visual_consistency": FeatureValue("visual_consistency", 80.0, confidence=0.9, source="web_scrape"),
                    "messaging_consistency": FeatureValue("messaging_consistency", 60.0, confidence=0.8, source="llm"),
                    "tone_consistency": FeatureValue("tone_consistency", 70.0, confidence=0.8, source="llm"),
                    "cross_channel_coherence": FeatureValue("cross_channel_coherence", 50.0, confidence=0.7, source="web_scrape"),
                },
                "presencia": {
                    "web_presence": FeatureValue("web_presence", 90.0, confidence=0.9, source="web_scrape"),
                    "social_footprint": FeatureValue("social_footprint", 75.0, confidence=0.9, source="social_media"),
                    "search_visibility": FeatureValue("search_visibility", 80.0, confidence=0.8, source="exa"),
                    "directory_presence": FeatureValue("directory_presence", 30.0, confidence=0.8, source="exa"),
                },
                "percepcion": {},
                "diferenciacion": {
                    "positioning_clarity": FeatureValue("positioning_clarity", 75.0, confidence=0.8, source="llm"),
                    "uniqueness": FeatureValue("uniqueness", 70.0, confidence=0.8, source="llm"),
                    "competitor_distance": FeatureValue("competitor_distance", 70.0, confidence=0.8, source="llm"),
                    "content_authenticity": FeatureValue("content_authenticity", 85.0, confidence=0.8, source="content_analysis"),
                    "brand_personality": FeatureValue("brand_personality", 80.0, confidence=0.8, source="content_analysis"),
                },
                "vitalidad": {
                    "content_recency": FeatureValue("content_recency", 90.0, confidence=0.9, source="exa"),
                    "publication_cadence": FeatureValue("publication_cadence", 80.0, confidence=0.9, source="exa"),
                    "momentum": FeatureValue("momentum", 60.0, confidence=0.8, source="llm"),
                },
            }
            brand_score = engine.score_brand("https://example.com", "Example", features_by_dim)
            store.save_features(run_id, features_by_dim)
            store.save_scores(
                run_id,
                BrandScore(
                    url="https://example.com",
                    brand_name="Example",
                    dimensions=brand_score.dimensions,
                    composite_score=brand_score.composite_score,
                ),
            )
            gate_config = _default_gate_config()
            store.upsert_gate_config(gate_config)
            fingerprint = _compute_scoring_state_fingerprint(
                dimensions_content=DIMENSIONS_PATH.read_text(encoding="utf-8"),
                engine_content=ENGINE_PATH.read_text(encoding="utf-8"),
                gate_config=gate_config,
                calibration_profile="base",
                calibration_profile_config=engine.profile_config,
            )
            store.save_run_audit(
                run_id,
                {
                    "gate_config": gate_config,
                    "active_baseline": None,
                    "scoring_state_fingerprint": fingerprint,
                },
            )
            artifact = {
                "run_id": run_id,
                "brand_name": "Example",
                "url": "https://example.com",
                "composite_score": brand_score.composite_score,
                "dimensions": brand_score.breakdown,
                "partial_dimensions": [],
                "partial_score": False,
            }
            artifact_path = Path(store.db_path).with_name(f"result-{run_id}.json")
            artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
            store.finalize_run(
                run_id,
                brand_score.composite_score,
                True,
                False,
                str(artifact_path),
                "summary",
            )

            report = build_score_replay_audit(store, run_id)

            store.close()

            self.assertEqual(report["score_integrity"], "valid")
            self.assertEqual(report["recommended_action"], "human_review")
            self.assertTrue(
                any(
                    issue["code"] == "neutral_fallback_dimension"
                    and issue["dimension"] == "percepcion"
                    for issue in report["issues"]
                )
            )


if __name__ == "__main__":
    unittest.main()
