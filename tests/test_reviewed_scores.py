import json
import tempfile
import unittest
from pathlib import Path

from src.scoring.replay import _compute_scoring_state_fingerprint, DIMENSIONS_PATH, ENGINE_PATH
from src.models.brand import BrandScore, DimensionScore, FeatureValue
from src.scoring.engine import ScoringEngine
from src.storage.sqlite_store import SQLiteStore


def _feature_fixture() -> dict[str, dict[str, FeatureValue]]:
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


def _seed_run(store: SQLiteStore, *, partial_dimensions: list[str] | None = None) -> tuple[int, float]:
    brand_id = store.upsert_brand("Example", "https://example.com")
    run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)
    features_by_dim = _feature_fixture()
    for dim in partial_dimensions or []:
        features_by_dim.pop(dim, None)
    engine = ScoringEngine()
    brand_score = engine.score_brand(
        "https://example.com",
        "Example",
        features_by_dim,
        unavailable_dimensions=set(partial_dimensions or []),
    )
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
        "partial_dimensions": list(partial_dimensions or []),
        "partial_score": False,
    }
    artifact_path = Path(store.db_path).with_name(f"reviewed-{run_id}.json")
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    store.finalize_run(run_id, brand_score.composite_score, True, False, str(artifact_path), "summary")
    return run_id, float(brand_score.composite_score or 0.0)


class ReviewedScoreLayerTests(unittest.TestCase):
    def test_valid_reviewed_score_is_persisted_separately(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, computed = _seed_run(store)

            reviewed_id = store.save_reviewed_score(
                run_id,
                reviewed_composite_score=78.0,
                reason="Reviewer found the brand to be slightly stronger after checking the evidence trail.",
                evidence_refs=["raw_inputs:web", "evidence_items:presencia"],
                reviewer="reviewer-a",
                affected_dimensions=["presencia", "diferenciacion"],
                review_status="adjusted",
            )

            saved = store.get_reviewed_score(run_id)
            store.close()

            self.assertIsNotNone(saved)
            self.assertEqual(reviewed_id, saved["id"])
            self.assertEqual(saved["run_id"], run_id)
            self.assertEqual(saved["computed_composite_score"], computed)
            self.assertEqual(saved["reviewed_composite_score"], 78.0)
            self.assertEqual(saved["score_delta"], round(78.0 - computed, 1))
            self.assertEqual(saved["based_on_score_integrity"], "valid")
            self.assertEqual(saved["review_status"], "adjusted")
            self.assertEqual(saved["reviewer"], "reviewer-a")
            self.assertEqual(saved["affected_dimensions"], ["presencia", "diferenciacion"])
            self.assertTrue(saved["evidence_refs"])
            self.assertEqual(saved["technical_override"], False)

    def test_missing_reason_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store)

            with self.assertRaises(ValueError):
                store.save_reviewed_score(
                    run_id,
                    reviewed_composite_score=78.0,
                    reason="",
                    evidence_refs=["raw_inputs:web"],
                    reviewer="reviewer-a",
                    affected_dimensions=["presencia"],
                    review_status="adjusted",
                )
            store.close()

    def test_missing_evidence_rejects_adjustment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store)

            with self.assertRaises(ValueError):
                store.save_reviewed_score(
                    run_id,
                    reviewed_composite_score=78.0,
                    reason="Adjustment requested without traceable evidence.",
                    evidence_refs=[],
                    reviewer="reviewer-a",
                    affected_dimensions=["presencia"],
                    review_status="adjusted",
                )
            store.close()

    def test_invalid_dimension_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store)

            with self.assertRaises(ValueError):
                store.save_reviewed_score(
                    run_id,
                    reviewed_composite_score=78.0,
                    reason="Invalid dimension should fail.",
                    evidence_refs=["raw_inputs:web"],
                    reviewer="reviewer-a",
                    affected_dimensions=["not_a_dimension"],
                    review_status="adjusted",
                )
            store.close()

    def test_score_integrity_valid_allows_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, computed = _seed_run(store)

            reviewed_id = store.save_reviewed_score(
                run_id,
                reviewed_composite_score=computed,
                reason="No adjustment required after review.",
                evidence_refs=[],
                reviewer="reviewer-a",
                affected_dimensions=["presencia"],
                review_status="approved",
            )

            saved = store.get_reviewed_score(run_id)
            store.close()

            self.assertEqual(reviewed_id, saved["id"])
            self.assertEqual(saved["based_on_score_integrity"], "valid")
            self.assertEqual(saved["score_delta"], 0.0)

    def test_drift_detected_blocks_normal_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store)
            store.conn.execute(
                """
                UPDATE features
                SET value = ?
                WHERE run_id = ? AND dimension_name = ? AND feature_name = ?
                """,
                (5.0, run_id, "presencia", "web_presence"),
            )
            store.conn.commit()

            with self.assertRaises(ValueError):
                store.save_reviewed_score(
                    run_id,
                    reviewed_composite_score=78.0,
                    reason="This should not be allowed while drift is present.",
                    evidence_refs=["raw_inputs:web"],
                    reviewer="reviewer-a",
                    affected_dimensions=["presencia"],
                    review_status="adjusted",
                )
            store.close()

    def test_technical_override_requires_explicit_reason(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store)

            with self.assertRaises(ValueError):
                store.save_reviewed_score(
                    run_id,
                    reviewed_composite_score=78.0,
                    reason="",
                    evidence_refs=["raw_inputs:web"],
                    reviewer="reviewer-a",
                    affected_dimensions=["presencia"],
                    review_status="technical_override",
                    technical_override=True,
                )
            store.close()


if __name__ == "__main__":
    unittest.main()
