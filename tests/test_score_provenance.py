import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.models.brand import BrandScore, FeatureValue
from src.scoring.engine import ScoringEngine
from src.scoring.provenance import build_score_provenance_report
from src.scoring.replay import DIMENSIONS_PATH, ENGINE_PATH, _compute_scoring_state_fingerprint
from src.storage.sqlite_store import SQLiteStore


def _feature_fixture(*, presence_low: bool = False) -> dict[str, dict]:
    presencia_web = 5.0 if presence_low else 90.0
    presencia_social = 5.0 if presence_low else 75.0
    return {
        "coherencia": {
            "visual_consistency": {"value": 80.0, "confidence": 0.9, "source": "web_scrape"},
            "messaging_consistency": {"value": 60.0, "confidence": 0.8, "source": "llm"},
            "tone_consistency": {"value": 70.0, "confidence": 0.8, "source": "llm"},
            "cross_channel_coherence": {"value": 50.0, "confidence": 0.7, "source": "web_scrape"},
        },
        "presencia": {
            "web_presence": {"value": presencia_web, "confidence": 0.9, "source": "web_scrape"},
            "social_footprint": {"value": presencia_social, "confidence": 0.9, "source": "social_media"},
            "search_visibility": {"value": 80.0, "confidence": 0.8, "source": "exa"},
            "directory_presence": {"value": 30.0, "confidence": 0.8, "source": "exa"},
        },
        "percepcion": {
            "brand_sentiment": {"value": 70.0, "confidence": 0.8, "source": "llm"},
            "mention_volume": {"value": 65.0, "confidence": 0.9, "source": "exa"},
            "sentiment_trend": {"value": 55.0, "confidence": 0.8, "source": "llm"},
            "review_quality": {"value": 50.0, "confidence": 0.8, "source": "exa"},
        },
        "diferenciacion": {
            "positioning_clarity": {"value": 75.0, "confidence": 0.8, "source": "llm"},
            "uniqueness": {"value": 70.0, "confidence": 0.8, "source": "llm"},
            "competitor_distance": {"value": 70.0, "confidence": 0.8, "source": "llm"},
            "content_authenticity": {"value": 85.0, "confidence": 0.8, "source": "content_analysis"},
            "brand_personality": {"value": 80.0, "confidence": 0.8, "source": "content_analysis"},
        },
        "vitalidad": {
            "content_recency": {"value": 90.0, "confidence": 0.9, "source": "exa"},
            "publication_cadence": {"value": 80.0, "confidence": 0.9, "source": "exa"},
            "momentum": {"value": 60.0, "confidence": 0.8, "source": "llm"},
        },
    }


def _seed_run(
    store: SQLiteStore,
    *,
    partial_dimensions: list[str] | None = None,
    unavailable_dimensions: list[str] | None = None,
    artifact_partial_dimensions: list[str] | None = None,
    presence_low: bool = False,
) -> tuple[int, float]:
    brand_id = store.upsert_brand("Example", "https://example.com")
    run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)

    feature_payload = _feature_fixture(presence_low=presence_low)
    features_by_dim: dict[str, dict[str, FeatureValue]] = {}
    for dimension_name, features in feature_payload.items():
        if partial_dimensions and dimension_name in partial_dimensions:
            continue
        features_by_dim[dimension_name] = {
            feature_name: FeatureValue(
                name=feature_name,
                value=feature_data["value"],
                confidence=feature_data["confidence"],
                source=feature_data["source"],
            )
            for feature_name, feature_data in features.items()
        }

    engine = ScoringEngine()
    brand_score = engine.score_brand(
        "https://example.com",
        "Example",
        {
            dimension_name: {
                feature_name: feature
                for feature_name, feature in features.items()
            }
            for dimension_name, features in features_by_dim.items()
        },
        unavailable_dimensions=set(unavailable_dimensions if unavailable_dimensions is not None else (partial_dimensions or [])),
    )

    store.save_features(
        run_id,
        {
            dimension_name: {
                feature_name: feature
                for feature_name, feature in features.items()
            }
            for dimension_name, features in features_by_dim.items()
        },
    )
    store.save_scores(
        run_id,
        BrandScore(
            url="https://example.com",
            brand_name="Example",
            dimensions=brand_score.dimensions,
            composite_score=brand_score.composite_score,
        ),
    )

    gate_config = {
        "max_composite_drop": 0.0,
        "max_dimension_drops": {
            "coherencia": 5.0,
            "presencia": 5.0,
            "percepcion": 5.0,
            "diferenciacion": 5.0,
            "vitalidad": 5.0,
        },
    }
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
        "partial_dimensions": list(
            artifact_partial_dimensions if artifact_partial_dimensions is not None else (partial_dimensions or [])
        ),
        "partial_score": False,
    }
    artifact_path = Path(store.db_path).with_name(f"provenance-{run_id}.json")
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    store.finalize_run(run_id, brand_score.composite_score, True, False, str(artifact_path), "summary")
    return run_id, float(brand_score.composite_score or 0.0)


class ScoreProvenanceReportTests(unittest.TestCase):
    def test_computed_only_valid_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, computed = _seed_run(store)

            with patch.object(store, "get_run_snapshot", wraps=store.get_run_snapshot) as get_snapshot:
                report = build_score_provenance_report(store, run_id)

            store.close()

            self.assertEqual(get_snapshot.call_count, 1)
            self.assertEqual(report["computed_composite_score"], computed)
            self.assertEqual(report["replay_integrity"]["status"], "valid")
            self.assertEqual(report["replay_integrity"]["drift_type"], "none")
            self.assertTrue(report["replay_integrity"]["score_values_match_persisted_data"])
            self.assertIsNone(report["reviewed_score"])
            self.assertEqual(report["display_score_source"], "computed")
            self.assertEqual(report["recommended_display_score"], computed)
            self.assertEqual(report["recommended_action"], "none")

    def test_reviewed_score_valid_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store)
            store.save_reviewed_score(
                run_id,
                reviewed_composite_score=78.0,
                reason="Human reviewer adjusted the score after checking the evidence trail.",
                evidence_refs=["https://example.com", "evidence_items:presencia"],
                reviewer="reviewer-a",
                affected_dimensions=["presencia", "diferenciacion"],
                review_status="adjusted",
            )

            report = build_score_provenance_report(store, run_id)

            store.close()

            self.assertIsNotNone(report["reviewed_score"])
            self.assertEqual(report["display_score_source"], "reviewed")
            self.assertEqual(report["recommended_display_score"], 78.0)
            self.assertEqual(report["reviewed_score"]["reviewed_composite_score"], 78.0)
            self.assertEqual(report["reviewed_score"]["based_on_score_integrity"], "valid")

    def test_drift_blocks_display_score(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store)
            store.save_reviewed_score(
                run_id,
                reviewed_composite_score=78.0,
                reason="Human reviewer adjusted the score before drift was introduced.",
                evidence_refs=["https://example.com"],
                reviewer="reviewer-a",
                affected_dimensions=["presencia"],
                review_status="adjusted",
            )
            store.conn.execute(
                """
                UPDATE features
                SET value = ?
                WHERE run_id = ? AND dimension_name = ? AND feature_name = ?
                """,
                (5.0, run_id, "presencia", "web_presence"),
            )
            store.conn.commit()

            report = build_score_provenance_report(store, run_id)

            store.close()

            self.assertEqual(report["replay_integrity"]["status"], "drift_detected")
            self.assertEqual(report["replay_integrity"]["drift_type"], "feature_score_mismatch")
            self.assertFalse(report["replay_integrity"]["score_values_match_persisted_data"])
            self.assertEqual(report["display_score_source"], "blocked")
            self.assertIsNone(report["recommended_display_score"])
            self.assertTrue(
                any(issue["code"] == "display_blocked_due_to_drift" for issue in report["warnings"])
            )

    def test_missing_reviewed_score(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, computed = _seed_run(store)

            report = build_score_provenance_report(store, run_id)

            store.close()

            self.assertIsNone(report["reviewed_score"])
            self.assertEqual(report["display_score_source"], "computed")
            self.assertEqual(report["recommended_display_score"], computed)

    def test_fallback_flags_included(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(
                store,
                partial_dimensions=["presencia"],
                unavailable_dimensions=[],
                artifact_partial_dimensions=[],
            )

            report = build_score_provenance_report(store, run_id)

            store.close()

            self.assertIn("presencia", report["fallback_flags"]["replay_neutral_fallback_dimensions"])
            self.assertEqual(report["dimension_breakdown"]["presencia"]["score"], 50.0)

    def test_feature_confidence_summarized(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store)

            report = build_score_provenance_report(store, run_id)

            store.close()

            self.assertIn("coherencia", report["confidence_summary"])
            self.assertEqual(report["confidence_summary"]["coherencia"]["confidence_status"], "good")
            self.assertGreater(report["feature_provenance_summary"]["coherencia"]["feature_count"], 0)

    def test_rules_caps_exposed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store, presence_low=True)

            report = build_score_provenance_report(store, run_id)

            store.close()

            self.assertIn(
                "marca_fantasma",
                report["dimension_breakdown"]["presencia"]["rules_applied"],
            )
            self.assertTrue(report["rules_applied"])


if __name__ == "__main__":
    unittest.main()
