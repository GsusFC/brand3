import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from src.models.brand import BrandScore, DimensionScore, FeatureValue
from src.storage.sqlite_store import SQLiteStore, _MalformedJSONPayload


class SQLiteStoreTests(unittest.TestCase):
    def test_store_configures_busy_timeout_per_connection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            try:
                timeout_ms = store.conn.execute("PRAGMA busy_timeout").fetchone()[0]
            finally:
                store.close()

            self.assertEqual(timeout_ms, 5000)

    def test_schema_initialization_runs_once_for_same_database_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            SQLiteStore.reset_schema_init_metrics()

            first = SQLiteStore(str(db_path))
            first.close()
            second = SQLiteStore(str(db_path))
            second.close()

            metrics = SQLiteStore.schema_init_metrics()
            self.assertEqual(metrics["runs"], 1)
            self.assertEqual(metrics["skips"], 1)

    def test_schema_initialization_cache_survives_database_writes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            SQLiteStore.reset_schema_init_metrics()

            first = SQLiteStore(str(db_path))
            brand_id = first.upsert_brand("Example", "https://example.com")
            first.create_run(brand_id, "Example", "https://example.com", True, False)
            first.close()
            second = SQLiteStore(str(db_path))
            second.close()

            metrics = SQLiteStore.schema_init_metrics()
            self.assertEqual(metrics["runs"], 1)
            self.assertEqual(metrics["skips"], 1)

    def test_schema_initialization_runs_for_recreated_database_at_same_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            SQLiteStore.reset_schema_init_metrics()

            first = SQLiteStore(str(db_path))
            first.close()
            for suffix in ("", "-wal", "-shm"):
                Path(f"{db_path}{suffix}").unlink(missing_ok=True)

            second = SQLiteStore(str(db_path))
            brand_id = second.upsert_brand("Example", "https://example.com")
            second.create_run(brand_id, "Example", "https://example.com", True, False)
            second.close()

            metrics = SQLiteStore.schema_init_metrics()
            self.assertEqual(metrics["runs"], 2)
            self.assertEqual(metrics["skips"], 0)

    def test_schema_initialization_runs_when_cached_database_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            SQLiteStore.reset_schema_init_metrics()

            first = SQLiteStore(str(db_path))
            first.conn.execute("DROP TABLE runs")
            first.conn.commit()
            first.close()

            second = SQLiteStore(str(db_path))
            brand_id = second.upsert_brand("Example", "https://example.com")
            second.create_run(brand_id, "Example", "https://example.com", True, False)
            second.close()

            metrics = SQLiteStore.schema_init_metrics()
            self.assertEqual(metrics["runs"], 2)
            self.assertEqual(metrics["skips"], 0)

    def test_core_run_read_indexes_are_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))

            rows = store.conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                  AND name IN (
                      'idx_runs_brand_started',
                      'idx_runs_brand_name_url_started',
                      'idx_scores_run',
                      'idx_features_run',
                      'idx_annotations_run_created',
                      'idx_raw_inputs_run_created',
                      'idx_raw_inputs_source_created'
                  )
                """
            ).fetchall()
            store.close()

            self.assertEqual(
                {row["name"] for row in rows},
                {
                    "idx_runs_brand_started",
                    "idx_runs_brand_name_url_started",
                    "idx_scores_run",
                    "idx_features_run",
                    "idx_annotations_run_created",
                    "idx_raw_inputs_run_created",
                    "idx_raw_inputs_source_created",
                },
            )

    def test_core_run_read_queries_use_indexes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))

            plans = {
                "features": store.conn.execute(
                    "EXPLAIN QUERY PLAN SELECT dimension_name FROM features WHERE run_id = ?",
                    (1,),
                ).fetchall(),
                "scores": store.conn.execute(
                    "EXPLAIN QUERY PLAN SELECT dimension_name FROM scores WHERE run_id = ?",
                    (1,),
                ).fetchall(),
                "raw_inputs": store.conn.execute(
                    """
                    EXPLAIN QUERY PLAN
                    SELECT source FROM raw_inputs
                    WHERE run_id = ?
                    ORDER BY created_at ASC
                    """,
                    (1,),
                ).fetchall(),
                "annotations": store.conn.execute(
                    """
                    EXPLAIN QUERY PLAN
                    SELECT note FROM annotations
                    WHERE run_id = ?
                    ORDER BY created_at ASC
                    """,
                    (1,),
                ).fetchall(),
                "latest_run": store.conn.execute(
                    """
                    EXPLAIN QUERY PLAN
                    SELECT id FROM runs
                    WHERE brand_name = ? AND url = ?
                    ORDER BY started_at DESC
                    LIMIT 1
                    """,
                    ("Example", "https://example.com"),
                ).fetchall(),
            }
            store.close()

            self.assertIn("idx_features_run", self._query_plan_text(plans["features"]))
            self.assertIn("idx_scores_run", self._query_plan_text(plans["scores"]))
            self.assertIn("idx_raw_inputs_run_created", self._query_plan_text(plans["raw_inputs"]))
            self.assertIn("idx_annotations_run_created", self._query_plan_text(plans["annotations"]))
            self.assertIn("idx_runs_brand_name_url_started", self._query_plan_text(plans["latest_run"]))

    @staticmethod
    def _query_plan_text(rows):
        return "\n".join(str(row["detail"]) for row in rows)

    def test_store_persists_run_inputs_features_and_scores(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))

            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)
            store.save_raw_input(run_id, "web", {"url": "https://example.com", "title": "Example"})
            store.save_features(
                run_id,
                {
                    "presencia": {
                        "web_presence": FeatureValue(
                            "web_presence", 80.0, raw_value="real website", confidence=0.9, source="web_scrape"
                        )
                    }
                },
            )

            brand_score = BrandScore(
                url="https://example.com",
                brand_name="Example",
                dimensions={
                    "presencia": DimensionScore(
                        name="presencia",
                        score=80.0,
                        features={},
                        insights=["Strong website"],
                        rules_applied=[],
                    )
                },
                composite_score=80.0,
            )
            store.save_scores(run_id, brand_score)
            store.finalize_run(run_id, 80.0, True, False, "/tmp/example.json", "summary")
            store.close()

            conn = sqlite3.connect(db_path)
            runs = conn.execute("SELECT composite_score, llm_used, social_scraped, result_path FROM runs").fetchall()
            raw_inputs = conn.execute("SELECT source FROM raw_inputs").fetchall()
            features = conn.execute("SELECT dimension_name, feature_name, value FROM features").fetchall()
            scores = conn.execute("SELECT dimension_name, score FROM scores").fetchall()
            conn.close()

            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0][0], 80.0)
            self.assertEqual(runs[0][1], 1)
            self.assertEqual(runs[0][2], 0)
            self.assertEqual(runs[0][3], "/tmp/example.json")
            self.assertEqual(raw_inputs[0][0], "web")
            self.assertEqual(features[0], ("presencia", "web_presence", 80.0))
            self.assertEqual(scores[0], ("presencia", 80.0))

    def test_get_run_summary_loads_run_metadata_without_snapshot_payloads(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))

            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)
            store.save_raw_input(run_id, "web", {"large": "payload"})
            store.finalize_run(run_id, 80.0, True, False, "/tmp/example.json", "summary")

            summary = store.get_run_summary(run_id)
            snapshot = store.get_run_snapshot(run_id)
            store.close()

            self.assertEqual(summary["id"], run_id)
            self.assertEqual(summary["brand_name"], "Example")
            self.assertEqual(summary["url"], "https://example.com")
            self.assertEqual(summary["brand_profile"]["domain"], "example.com")
            self.assertNotIn("raw_inputs", summary)
            self.assertNotIn("features", summary)
            self.assertEqual(snapshot["raw_inputs"][0]["payload"], {"large": "payload"})

    def test_get_latest_raw_input_respects_ttl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)
            store.save_raw_input(run_id, "web", {"url": "https://example.com", "title": "Fresh"})

            payload = store.get_latest_raw_input("Example", "https://example.com", "web", max_age_hours=24)
            self.assertEqual(payload["title"], "Fresh")

            with patch("src.storage.raw_inputs.datetime") as mock_datetime:
                from datetime import datetime as real_datetime
                mock_datetime.now.return_value = real_datetime(2030, 1, 1, 0, 0, 0)
                mock_datetime.fromtimestamp.side_effect = real_datetime.fromtimestamp
                expired = store.get_latest_raw_input("Example", "https://example.com", "web", max_age_hours=1)
            self.assertIsNone(expired)

            store.close()

    def test_get_latest_raw_input_handles_malformed_payload_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)

            store.save_raw_input(run_id, "web", {"url": "https://example.com", "title": "Fresh"})
            valid = store.get_latest_raw_input("Example", "https://example.com", "web", max_age_hours=24)
            self.assertEqual(valid["title"], "Fresh")

            store.conn.execute(
                "UPDATE raw_inputs SET payload_json = ? WHERE run_id = ? AND source = ?",
                ("{", run_id, "web"),
            )
            store.conn.commit()

            malformed = store.get_latest_raw_input("Example", "https://example.com", "web", max_age_hours=24)
            store.close()

            self.assertIsInstance(malformed, _MalformedJSONPayload)
            self.assertEqual(malformed.field, "raw_inputs.payload_json")
            self.assertEqual(malformed.raw_json, "{")
            self.assertIn("Expecting", malformed.error)

    def test_store_persists_evidence_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)

            store.save_evidence_items(
                run_id,
                [
                    {
                        "source": "context",
                        "url": "https://example.com/sitemap.xml",
                        "quote": "sitemap.xml found with 12 URLs",
                        "feature_name": "site_structure",
                        "dimension_name": "presencia",
                        "confidence": 0.8,
                        "freshness_days": 0,
                    },
                    {
                        "source": "exa",
                        "url": "https://news.example.com/article",
                        "quote": "Example mentioned in press",
                        "feature_name": "mentions",
                        "dimension_name": "percepcion",
                        "confidence": 0.6,
                    },
                ],
            )
            evidence = store.get_run_evidence(run_id)
            context_evidence = store.get_run_evidence(run_id, source="context")
            presencia_evidence = store.get_run_evidence(run_id, dimension_name="presencia")
            missing_evidence = store.get_run_evidence(run_id, dimension_name="vitalidad")
            snapshot = store.get_run_snapshot(run_id)
            store.close()

            self.assertEqual(len(evidence), 2)
            self.assertEqual(evidence[0]["source"], "context")
            self.assertEqual(evidence[0]["dimension_name"], "presencia")
            self.assertEqual(len(context_evidence), 1)
            self.assertEqual(context_evidence[0]["quote"], "sitemap.xml found with 12 URLs")
            self.assertEqual(len(presencia_evidence), 1)
            self.assertEqual(presencia_evidence[0]["source"], "context")
            self.assertEqual(missing_evidence, [])
            self.assertEqual(snapshot["evidence_items"][0]["quote"], "sitemap.xml found with 12 URLs")

    def test_get_run_snapshot_handles_malformed_snapshot_json_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)
            store.save_raw_input(run_id, "report_narrative", {"version": 1, "summary": "ok"})
            store.save_run_audit(
                run_id,
                {
                    "gate_config": {},
                    "active_baseline": None,
                    "scoring_state_fingerprint": "state-a",
                },
            )
            store.update_run_classification(
                run_id,
                {
                    "predicted_niche": "enterprise_ai",
                    "predicted_subtype": "ai_governance",
                    "confidence": 0.72,
                    "evidence": [],
                    "alternatives": [],
                },
                calibration_profile="enterprise_ai",
                profile_source="auto",
            )
            store.finalize_run(run_id, 81.0, True, False, "/tmp/example.json", "summary")

            baseline = store.get_run_snapshot(run_id)
            self.assertEqual(baseline["run"]["audit"]["scoring_state_fingerprint"], "state-a")
            self.assertEqual(baseline["raw_inputs"][0]["payload"]["version"], 1)

            store.conn.execute("UPDATE run_audits SET audit_json = ? WHERE run_id = ?", ("{", run_id))
            store.conn.execute(
                "UPDATE runs SET niche_evidence_json = ?, niche_alternatives_json = ? WHERE id = ?",
                ("{", "[", run_id),
            )
            store.conn.execute(
                "UPDATE raw_inputs SET payload_json = ? WHERE run_id = ? AND source = ?",
                ("{", run_id, "report_narrative"),
            )
            store.conn.commit()

            snapshot = store.get_run_snapshot(run_id)
            store.close()

            self.assertIsNone(snapshot["run"]["audit"])
            self.assertEqual(snapshot["run"]["audit_error"]["field"], "run_audits.audit_json")
            self.assertEqual(snapshot["run"]["audit_error"]["raw_json"], "{")
            self.assertEqual(snapshot["run"]["niche_evidence"], [])
            self.assertEqual(snapshot["run"]["niche_evidence_error"]["field"], "runs.niche_evidence_json")
            self.assertEqual(snapshot["run"]["niche_alternatives"], [])
            self.assertEqual(snapshot["run"]["niche_alternatives_error"]["field"], "runs.niche_alternatives_json")
            self.assertIsNone(snapshot["raw_inputs"][0]["payload"])
            self.assertEqual(snapshot["raw_inputs"][0]["payload_error"]["field"], "raw_inputs.payload_json")
            self.assertEqual(snapshot["raw_inputs"][0]["payload_error"]["raw_json"], "{")

    def test_store_allows_null_dimension_and_composite_scores(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)

            store.save_scores(
                run_id,
                BrandScore(
                    url="https://example.com",
                    brand_name="Example",
                    dimensions={
                        "coherencia": DimensionScore(
                            name="coherencia",
                            score=None,
                            insights=["Datos insuficientes para evaluar esta dimensión"],
                            rules_applied=[],
                            features={},
                        )
                    },
                    composite_score=None,
                ),
            )
            store.finalize_run(run_id, None, True, False, "/tmp/example.json", "summary")
            store.close()

            conn = sqlite3.connect(db_path)
            run_row = conn.execute("SELECT composite_score FROM runs WHERE id=?", (run_id,)).fetchone()
            score_row = conn.execute("SELECT score FROM scores WHERE run_id=? AND dimension_name='coherencia'", (run_id,)).fetchone()
            conn.close()

            self.assertIsNone(run_row[0])
            self.assertIsNone(score_row)

    def test_list_runs_and_snapshot_include_persisted_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, True)
            store.save_raw_input(run_id, "web", {"url": "https://example.com"})
            store.save_features(
                run_id,
                {"presencia": {"web_presence": FeatureValue("web_presence", 90.0, source="web_scrape")}},
            )
            store.save_scores(
                run_id,
                BrandScore(
                    url="https://example.com",
                    brand_name="Example",
                    dimensions={
                        "presencia": DimensionScore(
                            name="presencia",
                            score=90.0,
                            insights=["Great site"],
                            rules_applied=[],
                            features={},
                        )
                    },
                    composite_score=90.0,
                ),
            )
            store.finalize_run(run_id, 90.0, True, True, "/tmp/example.json", "summary")
            store.save_run_audit(
                run_id,
                {
                    "gate_config": {"max_composite_drop": 0.0, "max_dimension_drops": {}},
                    "active_baseline": None,
                    "scoring_state_fingerprint": "fingerprint-a",
                },
            )
            store.update_run_classification(
                run_id,
                {
                    "predicted_niche": "enterprise_ai",
                    "predicted_subtype": "ai_governance",
                    "confidence": 0.77,
                    "evidence": ["Matched keyword 'platform'"],
                    "alternatives": [{"niche": "frontier_ai", "score": 3.0}],
                },
                calibration_profile="enterprise_ai",
                profile_source="auto",
            )
            store.add_annotation(run_id, "Looks correct", dimension_name="presencia", actual_score=90.0)

            runs = store.list_runs("Example")
            snapshot = store.get_run_snapshot(run_id)
            annotations = store.list_annotations("Example")
            store.close()

            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["id"], run_id)
            self.assertEqual(runs[0]["scoring_state_fingerprint"], "fingerprint-a")
            self.assertEqual(runs[0]["brand_profile"]["domain"], "example.com")
            self.assertEqual(runs[0]["brand_profile"]["logo_key"], "example")
            self.assertEqual(runs[0]["predicted_niche"], "enterprise_ai")
            self.assertEqual(runs[0]["predicted_subtype"], "ai_governance")
            self.assertEqual(runs[0]["calibration_profile"], "enterprise_ai")
            self.assertEqual(snapshot["run"]["id"], run_id)
            self.assertEqual(snapshot["run"]["scoring_state_fingerprint"], "fingerprint-a")
            self.assertEqual(snapshot["run"]["audit"]["scoring_state_fingerprint"], "fingerprint-a")
            self.assertEqual(snapshot["run"]["brand_profile"]["domain"], "example.com")
            self.assertEqual(snapshot["run"]["niche_evidence"][0], "Matched keyword 'platform'")
            self.assertEqual(snapshot["scores"][0]["dimension_name"], "presencia")
            self.assertEqual(snapshot["features"][0]["feature_name"], "web_presence")
            self.assertEqual(len(annotations), 1)

    def test_brand_report_aggregates_runs_scores_and_annotations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")

            run_a = store.create_run(brand_id, "Example", "https://example.com", True, True)
            store.save_scores(
                run_a,
                BrandScore(
                    url="https://example.com",
                    brand_name="Example",
                    dimensions={
                        "presencia": DimensionScore(name="presencia", score=60.0, insights=[], rules_applied=[], features={}),
                        "diferenciacion": DimensionScore(name="diferenciacion", score=40.0, insights=[], rules_applied=[], features={}),
                    },
                    composite_score=50.0,
                ),
            )
            store.finalize_run(run_a, 50.0, True, True, "/tmp/a.json", "a")
            store.save_run_audit(
                run_a,
                {"gate_config": {}, "active_baseline": None, "scoring_state_fingerprint": "state-a"},
            )
            store.update_run_classification(
                run_a,
                {"predicted_niche": "enterprise_ai", "predicted_subtype": "ai_governance", "confidence": 0.72, "evidence": [], "alternatives": []},
                calibration_profile="enterprise_ai",
                profile_source="auto",
            )
            store.add_annotation(run_a, "too low", dimension_name="diferenciacion", actual_score=40.0, expected_score=55.0)

            run_b = store.create_run(brand_id, "Example", "https://example.com", True, True)
            store.save_scores(
                run_b,
                BrandScore(
                    url="https://example.com",
                    brand_name="Example",
                    dimensions={
                        "presencia": DimensionScore(name="presencia", score=80.0, insights=[], rules_applied=[], features={}),
                        "diferenciacion": DimensionScore(name="diferenciacion", score=65.0, insights=[], rules_applied=[], features={}),
                    },
                    composite_score=72.0,
                ),
            )
            store.finalize_run(run_b, 72.0, True, True, "/tmp/b.json", "b")
            store.save_run_audit(
                run_b,
                {"gate_config": {}, "active_baseline": None, "scoring_state_fingerprint": "state-b"},
            )
            store.update_run_classification(
                run_b,
                {"predicted_niche": "frontier_ai", "predicted_subtype": "model_lab", "confidence": 0.81, "evidence": [], "alternatives": []},
                calibration_profile="frontier_ai",
                profile_source="auto",
            )

            report = store.get_brand_report("Example", limit=10)
            store.close()

            self.assertEqual(report["brand_name"], "Example")
            self.assertEqual(report["brand_profile"]["domain"], "example.com")
            self.assertEqual(len(report["runs"]), 2)
            self.assertIn("presencia", report["dimension_series"])
            self.assertEqual(len(report["annotations"]), 1)
            self.assertEqual(report["runs"][0]["scoring_state_fingerprint"], "state-b")
            self.assertEqual(report["runs"][0]["predicted_niche"], "frontier_ai")
            self.assertEqual(report["runs"][0]["predicted_subtype"], "model_lab")

    def test_list_brands_returns_brand_identity_and_latest_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Stripe", "https://stripe.com")
            run_id = store.create_run(brand_id, "Stripe", "https://stripe.com", True, False)
            store.finalize_run(run_id, 81.0, True, False, "/tmp/stripe.json", "stripe")
            store.save_run_audit(
                run_id,
                {"gate_config": {}, "active_baseline": None, "scoring_state_fingerprint": "stripe-fp"},
            )
            store.update_run_classification(
                run_id,
                {"predicted_niche": "enterprise_ai", "predicted_subtype": "ai_governance", "confidence": 0.79, "evidence": [], "alternatives": []},
                calibration_profile="enterprise_ai",
                profile_source="auto",
            )

            brands = store.list_brands(limit=10)
            store.close()

            self.assertEqual(len(brands), 1)
            self.assertEqual(brands[0]["brand_name"], "Stripe")
            self.assertEqual(brands[0]["brand_profile"]["domain"], "stripe.com")
            self.assertEqual(brands[0]["brand_profile"]["logo_key"], "stripe")
            self.assertEqual(brands[0]["latest_composite_score"], 81.0)
            self.assertEqual(brands[0]["latest_scoring_state_fingerprint"], "stripe-fp")
            self.assertEqual(brands[0]["latest_predicted_niche"], "enterprise_ai")
            self.assertEqual(brands[0]["latest_predicted_subtype"], "ai_governance")
            self.assertEqual(brands[0]["latest_calibration_profile"], "enterprise_ai")

    def test_experiments_are_persisted_with_summary_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")

            before_run = store.create_run(brand_id, "Example", "https://example.com", True, True)
            store.finalize_run(before_run, 55.0, True, True, "/tmp/before.json", "before")

            after_run = store.create_run(brand_id, "Example", "https://example.com", True, True)
            store.finalize_run(after_run, 61.0, True, True, "/tmp/after.json", "after")

            experiment_id = store.save_experiment(
                brand_name="Example",
                url="https://example.com",
                before_run_id=before_run,
                after_run_id=after_run,
                candidate_ids=[3, 5],
                summary={
                    "composite": {"before": 55.0, "after": 61.0, "delta": 6.0},
                    "dimensions": {"presencia": {"before": 50.0, "after": 60.0, "delta": 10.0}},
                },
                before_scoring_state_fingerprint="fp-before",
                after_scoring_state_fingerprint="fp-after",
            )

            experiments = store.list_experiments("Example", limit=10)
            store.close()

            self.assertEqual(len(experiments), 1)
            self.assertEqual(experiments[0]["id"], experiment_id)
            self.assertEqual(experiments[0]["candidate_ids"], [3, 5])
            self.assertEqual(experiments[0]["summary"]["composite"]["delta"], 6.0)
            self.assertEqual(experiments[0]["before_scoring_state_fingerprint"], "fp-before")
            self.assertEqual(experiments[0]["after_scoring_state_fingerprint"], "fp-after")

    def test_experiment_can_link_before_and_after_versions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            before_run = store.create_run(brand_id, "Example", "https://example.com", True, True)
            after_run = store.create_run(brand_id, "Example", "https://example.com", True, True)
            version_before_id = store.save_calibration_version("before", "a", "b")
            version_after_id = store.save_calibration_version("after", "c", "d")

            experiment_id = store.save_experiment(
                brand_name="Example",
                url="https://example.com",
                before_run_id=before_run,
                after_run_id=after_run,
                candidate_ids=[1],
                summary={"composite": {"before": 50.0, "after": 55.0, "delta": 5.0}},
                version_before_id=version_before_id,
                version_after_id=version_after_id,
            )
            experiments = store.list_experiments("Example", limit=10)
            store.close()

            self.assertEqual(experiments[0]["id"], experiment_id)
            self.assertEqual(experiments[0]["version_before_id"], version_before_id)
            self.assertEqual(experiments[0]["version_after_id"], version_after_id)

    def test_get_latest_experiment_for_version_can_filter_by_brand(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            version_id = store.save_calibration_version("target", "dims", "eng")

            brand_a = store.upsert_brand("BrandA", "https://a.com")
            brand_b = store.upsert_brand("BrandB", "https://b.com")
            a_before = store.create_run(brand_a, "BrandA", "https://a.com", True, True)
            a_after = store.create_run(brand_a, "BrandA", "https://a.com", True, True)
            b_before = store.create_run(brand_b, "BrandB", "https://b.com", True, True)
            b_after = store.create_run(brand_b, "BrandB", "https://b.com", True, True)

            store.save_experiment(
                brand_name="BrandA",
                url="https://a.com",
                before_run_id=a_before,
                after_run_id=a_after,
                candidate_ids=[1],
                summary={"composite": {"before": 40.0, "after": 45.0, "delta": 5.0}},
                version_before_id=version_id,
                version_after_id=version_id,
            )
            store.save_experiment(
                brand_name="BrandB",
                url="https://b.com",
                before_run_id=b_before,
                after_run_id=b_after,
                candidate_ids=[2],
                summary={"composite": {"before": 50.0, "after": 55.0, "delta": 5.0}},
                version_before_id=version_id,
                version_after_id=version_id,
            )

            filtered = store.get_latest_experiment_for_version(version_id, brand_name="BrandA")
            store.close()

            self.assertEqual(filtered["brand_name"], "BrandA")

    def test_gate_config_can_be_persisted_and_versioned(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            gate_config = {
                "max_composite_drop": 2.0,
                "max_dimension_drops": {"diferenciacion": 7.0},
            }
            store.upsert_gate_config(gate_config)
            version_id = store.save_calibration_version(
                "with-gate",
                "dims",
                "eng",
                gate_config=gate_config,
            )
            active = store.get_gate_config()
            version = store.get_calibration_version(version_id)
            store.close()

            self.assertEqual(active["max_composite_drop"], 2.0)
            self.assertEqual(version["gate_config"]["max_dimension_drops"]["diferenciacion"], 7.0)

    def test_analysis_job_lifecycle_is_persisted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            job_id = store.create_analysis_job(
                url="https://example.com",
                brand_name="Example",
                use_llm=True,
                use_social=False,
            )
            store.start_analysis_job(job_id)
            store.update_analysis_job_phase(job_id, "scoring")
            store.complete_analysis_job(job_id, 12, {"run_id": 12, "composite_score": 77.0})
            job = store.get_analysis_job(job_id)
            jobs = store.list_analysis_jobs("Example", status="done", limit=10)
            store.close()

            self.assertEqual(job["status"], "done")
            self.assertEqual(job["phase"], "done")
            self.assertEqual(job["attempt_count"], 1)
            self.assertEqual(job["brand_profile"]["domain"], "example.com")
            self.assertIsNotNone(job["queue_duration_seconds"])
            self.assertIsNotNone(job["run_duration_seconds"])
            self.assertIsNotNone(job["total_duration_seconds"])
            self.assertTrue(any(event["phase"] == "queued" for event in job["events"]))
            self.assertTrue(any(event["phase"] == "done" for event in job["events"]))
            self.assertEqual(job["run_id"], 12)
            self.assertEqual(job["result"]["composite_score"], 77.0)
            self.assertEqual(len(jobs), 1)

    def test_analysis_job_readback_handles_malformed_result_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            job_id = store.create_analysis_job(
                url="https://example.com",
                brand_name="Example",
                use_llm=True,
                use_social=False,
            )
            store.start_analysis_job(job_id)
            store.complete_analysis_job(job_id, 12, {"run_id": 12, "composite_score": 77.0})
            baseline = store.get_analysis_job(job_id)
            self.assertEqual(baseline["result"]["composite_score"], 77.0)

            store.conn.execute(
                "UPDATE analysis_jobs SET result_json = ? WHERE id = ?",
                ("{", job_id),
            )
            store.conn.commit()

            job = store.get_analysis_job(job_id)
            jobs = store.list_analysis_jobs("Example", status="done", limit=10)
            store.close()

            self.assertIsNone(job["result"])
            self.assertEqual(job["result_error"]["field"], "analysis_jobs.result_json")
            self.assertEqual(job["result_error"]["raw_json"], "{")
            self.assertIsNone(jobs[0]["result"])
            self.assertEqual(jobs[0]["result_error"]["field"], "analysis_jobs.result_json")

    def test_analysis_job_cancel_and_retry_are_persisted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            job_id = store.create_analysis_job(
                url="https://example.com",
                brand_name="Example",
                use_llm=True,
                use_social=False,
            )
            store.request_analysis_job_cancel(job_id)
            cancelled = store.get_analysis_job(job_id)

            store.requeue_analysis_job(job_id)
            queued = store.get_analysis_job(job_id)

            store.start_analysis_job(job_id)
            running = store.get_analysis_job(job_id)
            store.request_analysis_job_cancel(job_id)
            cancellation_requested = store.get_analysis_job(job_id)
            store.cancel_analysis_job(job_id)
            final = store.get_analysis_job(job_id)
            store.close()

            self.assertEqual(cancelled["status"], "cancelled")
            self.assertEqual(cancelled["phase"], "cancelled")
            self.assertEqual(cancelled["cancel_requested"], 1)
            self.assertEqual(cancelled["brand_profile"]["logo_key"], "example")
            self.assertEqual(queued["status"], "queued")
            self.assertEqual(queued["phase"], "queued")
            self.assertEqual(queued["cancel_requested"], 0)
            self.assertEqual(running["attempt_count"], 1)
            self.assertEqual(cancellation_requested["status"], "running")
            self.assertEqual(cancellation_requested["cancel_requested"], 1)
            self.assertEqual(final["status"], "cancelled")
            self.assertTrue(any(event["level"] == "warning" for event in final["events"]))

    def test_run_durations_are_exposed_in_run_lists_and_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, True)
            store.finalize_run(run_id, 80.0, True, True, "/tmp/example.json", "summary")

            runs = store.list_runs("Example", limit=10)
            snapshot = store.get_run_snapshot(run_id)
            store.close()

            self.assertIsNotNone(runs[0]["run_duration_seconds"])
            self.assertIsNotNone(snapshot["run"]["run_duration_seconds"])


if __name__ == "__main__":
    unittest.main()
