import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
from src.services import brand_service
from src.learning.applier import apply_candidate
from src.learning.calibration import CalibrationAnalyzer
from src.models.brand import BrandScore, DimensionScore
from src.storage.sqlite_store import SQLiteStore


class LearningTests(unittest.TestCase):
    def test_calibration_recommendations_from_annotations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, True)
            brand_score = BrandScore(
                url="https://example.com",
                brand_name="Example",
                dimensions={
                    "diferenciacion": DimensionScore(
                        name="diferenciacion",
                        score=25.0,
                        features={},
                        insights=["Lenguaje excesivamente generico"],
                        rules_applied=["lenguaje_generico"],
                    )
                },
                composite_score=40.0,
            )
            store.save_features(
                run_id,
                {
                    "diferenciacion": {
                        "generic_language_score": __import__("src.models.brand", fromlist=["FeatureValue"]).FeatureValue(
                            "generic_language_score", 88.0, confidence=0.4, source="web_scrape"
                        )
                    }
                },
            )
            store.save_scores(run_id, brand_score)
            store.add_annotation(
                run_id=run_id,
                dimension_name="diferenciacion",
                feature_name="generic_language_score",
                expected_score=55.0,
                actual_score=25.0,
                note="Demasiado castigada para una marca con lenguaje propio",
            )

            snapshot = store.get_run_snapshot(run_id)
            annotations = store.list_annotations("Example")
            store.close()

            analyzer = CalibrationAnalyzer()
            recs = analyzer.analyze_snapshot(snapshot)
            recs.extend(analyzer.analyze_annotations(annotations))

            messages = "\n".join(rec.message for rec in recs)
            self.assertTrue(any(rec.target == "diferenciacion" for rec in recs))
            self.assertIn("generic language cap", messages.lower())

    def test_propose_candidates_from_history(self):
        analyzer = CalibrationAnalyzer()
        report = {
            "brand_name": "Example",
            "runs": [{"id": 3}, {"id": 2}, {"id": 1}],
            "dimension_series": {
                "diferenciacion": [
                    {"run_id": 3, "dimension_name": "diferenciacion", "score": 70.0},
                    {"run_id": 2, "dimension_name": "diferenciacion", "score": 35.0},
                    {"run_id": 1, "dimension_name": "diferenciacion", "score": 30.0},
                ]
            },
            "annotations": [
                {
                    "dimension_name": "diferenciacion",
                    "feature_name": "generic_language_score",
                    "expected_score": 60.0,
                    "actual_score": 25.0,
                }
            ],
        }

        candidates = analyzer.propose_candidates(report, report["annotations"])
        targets = {candidate.target for candidate in candidates}
        scopes = {candidate.scope for candidate in candidates}

        self.assertIn("diferenciacion", targets)
        self.assertIn("diferenciacion.lenguaje_generico", targets)
        self.assertIn("dimension_weight", scopes)
        self.assertIn("rule_threshold", scopes)

    def test_apply_dimension_weight_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dimensions_path = Path(tmpdir) / "dimensions.py"
            dimensions_path.write_text(
                'DIMENSIONS = {"coherencia": {"weight": 0.20}, "presencia": {"weight": 0.20}}\n',
                encoding="utf-8",
            )
            result = apply_candidate(
                str(dimensions_path),
                str(dimensions_path),
                {
                    "scope": "dimension_weight",
                    "target": "coherencia",
                    "proposal": {"proposed_weight": 0.22},
                },
            )
            updated = dimensions_path.read_text(encoding="utf-8")
            self.assertTrue(result["applied"])
            self.assertIn('"coherencia": {"weight": 0.22}', updated)

    def test_apply_rule_threshold_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dimensions_path = Path(tmpdir) / "dimensions.py"
            engine_path = Path(tmpdir) / "engine.py"
            dimensions_path.write_text('DIMENSIONS = {}\n', encoding="utf-8")
            engine_path.write_text(
                'ScoringRule(condition="lenguaje_generico", check=lambda f: f.get("generic_language_score", FeatureValue("", 0)).value > 80, cap=25, insight="x")\n',
                encoding="utf-8",
            )
            result = apply_candidate(
                str(dimensions_path),
                str(engine_path),
                {
                    "scope": "rule_threshold",
                    "target": "diferenciacion.lenguaje_generico",
                    "proposal": {"proposed_threshold": 85},
                },
            )
            updated = engine_path.read_text(encoding="utf-8")
            self.assertTrue(result["applied"])
            self.assertIn('.value > 85', updated)

    def test_candidate_status_can_be_updated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            candidate_id = store.save_calibration_candidate(
                brand_name="Example",
                scope="dimension_weight",
                target="coherencia",
                proposal={"current_weight": 0.2, "proposed_weight": 0.22},
                rationale="test",
            )
            store.update_calibration_candidate_status(candidate_id, "approved")
            candidate = store.get_calibration_candidate(candidate_id)
            store.close()
            self.assertEqual(candidate["status"], "approved")

    def test_apply_candidates_records_versions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            dimensions_path = Path(tmpdir) / "dimensions.py"
            engine_path = Path(tmpdir) / "engine.py"
            dimensions_path.write_text(
                'DIMENSIONS = {"coherencia": {"weight": 0.20}, "presencia": {"weight": 0.20}}\n',
                encoding="utf-8",
            )
            engine_path.write_text(
                'ScoringRule(condition="lenguaje_generico", check=lambda f: f.get("generic_language_score", FeatureValue("", 0)).value > 80, cap=25, insight="x")\n',
                encoding="utf-8",
            )

            store = SQLiteStore(str(db_path))
            candidate_id = store.save_calibration_candidate(
                brand_name="Example",
                scope="dimension_weight",
                target="coherencia",
                proposal={"current_weight": 0.20, "proposed_weight": 0.22},
                rationale="test",
            )
            store.update_calibration_candidate_status(candidate_id, "approved")
            store.close()

            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                with patch.object(main, "DIMENSIONS_PATH", dimensions_path):
                    with patch.object(main, "ENGINE_PATH", engine_path):
                        result = main.apply_candidates(candidate_ids=[candidate_id])

            verify = SQLiteStore(str(db_path))
            try:
                versions = verify.list_calibration_versions(limit=10)
                applied = verify.list_applied_calibrations(limit=10)
            finally:
                verify.close()

            self.assertTrue(result[0]["applied"])
            self.assertGreaterEqual(len(versions), 2)
            self.assertEqual(len(applied), 1)
            self.assertEqual(applied[0]["candidate_id"], candidate_id)

    def test_rollback_version_restores_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            dimensions_path = Path(tmpdir) / "dimensions.py"
            engine_path = Path(tmpdir) / "engine.py"
            dimensions_path.write_text('DIMENSIONS = {"coherencia": {"weight": 0.20}}\n', encoding="utf-8")
            engine_path.write_text("cap=25\n", encoding="utf-8")

            store = SQLiteStore(str(db_path))
            store.upsert_gate_config(
                {"max_composite_drop": 0.0, "max_dimension_drops": {"diferenciacion": 5.0}}
            )
            version_id = store.save_calibration_version(
                label="baseline",
                dimensions_content='DIMENSIONS = {"coherencia": {"weight": 0.20}}\n',
                engine_content="cap=25\n",
                gate_config={"max_composite_drop": 1.0, "max_dimension_drops": {"diferenciacion": 7.0}},
            )
            store.close()

            dimensions_path.write_text('DIMENSIONS = {"coherencia": {"weight": 0.30}}\n', encoding="utf-8")
            engine_path.write_text("cap=35\n", encoding="utf-8")

            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                with patch.object(main, "DIMENSIONS_PATH", dimensions_path):
                    with patch.object(main, "ENGINE_PATH", engine_path):
                        payload = main.rollback_version(version_id)

            self.assertTrue(payload["rolled_back"])
            self.assertIn('"weight": 0.20', dimensions_path.read_text(encoding="utf-8"))
            self.assertEqual(engine_path.read_text(encoding="utf-8"), "cap=25\n")
            verify = SQLiteStore(str(db_path))
            try:
                gate = verify.get_gate_config()
            finally:
                verify.close()
            self.assertEqual(gate["max_composite_drop"], 1.0)
            self.assertEqual(gate["max_dimension_drops"]["diferenciacion"], 7.0)

    def test_promote_baseline_replaces_previous_active_one(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            version_a = store.save_calibration_version("v1", "dims-a", "eng-a")
            version_b = store.save_calibration_version("v2", "dims-b", "eng-b")
            run_1 = store.create_run(brand_id, "Example", "https://example.com", True, True)
            run_2 = store.create_run(brand_id, "Example", "https://example.com", True, True)
            run_3 = store.create_run(brand_id, "Example", "https://example.com", True, True)
            store.save_experiment(
                brand_name="Example",
                url="https://example.com",
                before_run_id=run_1,
                after_run_id=run_2,
                candidate_ids=[1],
                summary={
                    "composite": {"before": 50.0, "after": 55.0, "delta": 5.0},
                    "dimensions": {"coherencia": {"before": 50.0, "after": 54.0, "delta": 4.0}},
                },
                version_before_id=version_a,
                version_after_id=version_a,
            )
            store.save_experiment(
                brand_name="Example",
                url="https://example.com",
                before_run_id=run_2,
                after_run_id=run_3,
                candidate_ids=[2],
                summary={
                    "composite": {"before": 55.0, "after": 58.0, "delta": 3.0},
                    "dimensions": {"coherencia": {"before": 54.0, "after": 56.0, "delta": 2.0}},
                },
                version_before_id=version_a,
                version_after_id=version_b,
            )
            store.close()

            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                first = main.promote_baseline(version_a, label="stable-a")
                second = main.promote_baseline(version_b, label="stable-b")
                baselines = main.list_baselines(limit=10)

            self.assertTrue(first["promoted"])
            self.assertTrue(second["promoted"])
            self.assertEqual(baselines["active"]["version_id"], version_b)
            active_rows = [item for item in baselines["history"] if item["is_active"] == 1]
            self.assertEqual(len(active_rows), 1)
            self.assertEqual(active_rows[0]["label"], "stable-b")

    def test_promote_baseline_blocks_regressive_version_without_force(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            before_run = store.create_run(brand_id, "Example", "https://example.com", True, True)
            after_run = store.create_run(brand_id, "Example", "https://example.com", True, True)
            version_before = store.save_calibration_version("before", "dims-a", "eng-a")
            version_after = store.save_calibration_version("after", "dims-b", "eng-b")
            store.save_experiment(
                brand_name="Example",
                url="https://example.com",
                before_run_id=before_run,
                after_run_id=after_run,
                candidate_ids=[1],
                summary={
                    "composite": {"before": 70.0, "after": 63.0, "delta": -7.0},
                    "dimensions": {
                        "diferenciacion": {"before": 60.0, "after": 50.0, "delta": -10.0},
                    },
                },
                version_before_id=version_before,
                version_after_id=version_after,
            )
            store.close()

            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                payload = main.promote_baseline(version_after, label="blocked")
                baselines = main.list_baselines(limit=10)

            self.assertFalse(payload["promoted"])
            self.assertFalse(payload["gate"]["allowed"])
            self.assertEqual(baselines["active"], None)

    def test_promote_baseline_can_force_override_gate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            before_run = store.create_run(brand_id, "Example", "https://example.com", True, True)
            after_run = store.create_run(brand_id, "Example", "https://example.com", True, True)
            version_before = store.save_calibration_version("before", "dims-a", "eng-a")
            version_after = store.save_calibration_version("after", "dims-b", "eng-b")
            store.save_experiment(
                brand_name="Example",
                url="https://example.com",
                before_run_id=before_run,
                after_run_id=after_run,
                candidate_ids=[1],
                summary={
                    "composite": {"before": 70.0, "after": 63.0, "delta": -7.0},
                    "dimensions": {
                        "diferenciacion": {"before": 60.0, "after": 50.0, "delta": -10.0},
                    },
                },
                version_before_id=version_before,
                version_after_id=version_after,
            )
            store.close()

            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                payload = main.promote_baseline(version_after, label="forced", force=True)
                baselines = main.list_baselines(limit=10)

            self.assertTrue(payload["promoted"])
            self.assertTrue(payload["forced"])
            self.assertEqual(baselines["active"]["version_id"], version_after)

    def test_promote_baseline_respects_configured_dimension_drop_thresholds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            before_run = store.create_run(brand_id, "Example", "https://example.com", True, True)
            after_run = store.create_run(brand_id, "Example", "https://example.com", True, True)
            version_before = store.save_calibration_version("before", "dims-a", "eng-a")
            version_after = store.save_calibration_version("after", "dims-b", "eng-b")
            store.save_experiment(
                brand_name="Example",
                url="https://example.com",
                before_run_id=before_run,
                after_run_id=after_run,
                candidate_ids=[1],
                summary={
                    "composite": {"before": 70.0, "after": 70.0, "delta": 0.0},
                    "dimensions": {
                        "diferenciacion": {"before": 60.0, "after": 54.0, "delta": -6.0},
                    },
                },
                version_before_id=version_before,
                version_after_id=version_after,
            )
            store.close()

            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                with patch.object(main, "BRAND3_PROMOTION_MAX_DIMENSION_DROPS", {"diferenciacion": 7.0}):
                    payload = main.promote_baseline(version_after, label="threshold-ok")

            self.assertTrue(payload["promoted"])
            self.assertEqual(payload["gate"]["thresholds"]["max_dimension_drops"]["diferenciacion"], 7.0)

    def test_set_gate_config_persists_active_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                payload = main.set_gate_config(
                    max_composite_drop=2.0,
                    dimension_drops={"percepcion": 3.0},
                )
                current = main.get_gate_config()

            self.assertEqual(payload["max_composite_drop"], 2.0)
            self.assertEqual(current["max_dimension_drops"]["percepcion"], 3.0)

    def test_build_run_audit_context_includes_gate_config_and_active_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            store.upsert_gate_config(
                {
                    "max_composite_drop": 1.0,
                    "max_dimension_drops": {"diferenciacion": 6.0},
                }
            )
            version_id = store.save_calibration_version(
                "stable",
                "dims",
                "eng",
                gate_config={
                    "max_composite_drop": 1.0,
                    "max_dimension_drops": {"diferenciacion": 6.0},
                },
            )
            store.promote_baseline(version_id, "stable")
            store.close()

            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                payload = main._build_run_audit_context()

            self.assertEqual(payload["gate_config"]["max_composite_drop"], 1.0)
            self.assertEqual(payload["active_baseline"]["version_id"], version_id)
            self.assertEqual(payload["calibration_profile"], "base")
            self.assertEqual(len(payload["scoring_state_fingerprint"]), 16)

    def test_scoring_state_fingerprint_changes_with_gate_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                main.set_gate_config(max_composite_drop=1.0)
                first = main._build_run_audit_context(calibration_profile="base")["scoring_state_fingerprint"]
                second = main._build_run_audit_context(
                    calibration_profile="frontier_ai"
                )["scoring_state_fingerprint"]

            self.assertNotEqual(first, second)

    def test_compare_version_uses_active_baseline_for_same_brand(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            baseline_version = store.save_calibration_version("baseline", "dims-a", "eng-a")
            target_version = store.save_calibration_version("target", "dims-b", "eng-b")
            run_1 = store.create_run(brand_id, "Example", "https://example.com", True, True)
            run_2 = store.create_run(brand_id, "Example", "https://example.com", True, True)
            run_3 = store.create_run(brand_id, "Example", "https://example.com", True, True)
            run_4 = store.create_run(brand_id, "Example", "https://example.com", True, True)
            store.save_experiment(
                brand_name="Example",
                url="https://example.com",
                before_run_id=run_1,
                after_run_id=run_2,
                candidate_ids=[1],
                summary={
                    "composite": {"before": 50.0, "after": 56.0, "delta": 6.0},
                    "dimensions": {"coherencia": {"before": 48.0, "after": 55.0, "delta": 7.0}},
                },
                version_before_id=baseline_version,
                version_after_id=baseline_version,
            )
            store.save_experiment(
                brand_name="Example",
                url="https://example.com",
                before_run_id=run_3,
                after_run_id=run_4,
                candidate_ids=[2],
                summary={
                    "composite": {"before": 56.0, "after": 60.0, "delta": 4.0},
                    "dimensions": {"coherencia": {"before": 55.0, "after": 59.0, "delta": 4.0}},
                },
                version_before_id=baseline_version,
                version_after_id=target_version,
            )
            store.promote_baseline(baseline_version, "stable")
            store.close()

            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                payload = main.compare_version(target_version, "Example")

            self.assertEqual(payload["active_baseline"]["version_id"], baseline_version)
            self.assertTrue(payload["target_gate"]["allowed"])
            self.assertEqual(payload["comparison"]["composite"]["delta_vs_baseline"], 4.0)
            self.assertEqual(payload["comparison"]["dimensions"]["coherencia"]["delta_vs_baseline"], 4.0)

    def test_brand_report_exposes_scoring_state_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_a = store.create_run(brand_id, "Example", "https://example.com", True, True)
            run_b = store.create_run(brand_id, "Example", "https://example.com", True, True)
            for run_id, score, fingerprint, niche in (
                (run_a, 50.0, "fp-a", "enterprise_ai"),
                (run_b, 60.0, "fp-b", "frontier_ai"),
            ):
                store.save_scores(
                    run_id,
                    BrandScore(
                        url="https://example.com",
                        brand_name="Example",
                        dimensions={
                            "presencia": DimensionScore(
                                name="presencia",
                                score=score,
                                insights=[],
                                rules_applied=[],
                                features={},
                            )
                        },
                        composite_score=score,
                    ),
                )
                store.finalize_run(run_id, score, True, True, f"/tmp/{run_id}.json", "summary")
                store.save_run_audit(
                    run_id,
                    {
                        "gate_config": {},
                        "active_baseline": None,
                        "scoring_state_fingerprint": fingerprint,
                    },
                )
                store.update_run_classification(
                    run_id,
                    {"predicted_niche": niche, "predicted_subtype": "model_lab" if niche == "frontier_ai" else "ai_governance", "confidence": 0.8, "evidence": [], "alternatives": []},
                    calibration_profile=niche,
                    profile_source="auto",
                )
            store.close()

            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                payload = main.brand_report("Example", limit=10)

            self.assertEqual(payload["brand_profile"]["domain"], "example.com")
            self.assertEqual(payload["latest_predicted_niche"], "frontier_ai")
            self.assertEqual(payload["latest_predicted_subtype"], "model_lab")
            self.assertEqual(payload["latest_calibration_profile"], "frontier_ai")
            self.assertEqual(payload["latest_scoring_state_fingerprint"], "fp-b")
            self.assertEqual(payload["scoring_states"]["fp-a"], 1)
            self.assertEqual(payload["scoring_states"]["fp-b"], 1)

    def test_execute_analysis_job_runs_pipeline_and_marks_done(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            job_id = store.create_analysis_job(
                url="https://example.com",
                brand_name="Example",
                use_llm=True,
                use_social=False,
            )
            store.close()

            with patch.object(brand_service, "BRAND3_DB_PATH", str(db_path)):
                with patch.object(
                    brand_service,
                    "run",
                    return_value={
                        "brand": "Example",
                        "url": "https://example.com",
                        "run_id": 33,
                        "composite_score": 88.0,
                    },
                ):
                    payload = brand_service.execute_analysis_job(job_id)

            self.assertEqual(payload["status"], "done")
            self.assertEqual(payload["phase"], "done")
            self.assertEqual(payload["attempt_count"], 1)
            self.assertEqual(payload["brand_profile"]["domain"], "example.com")
            self.assertTrue(any(event["phase"] == "collecting" for event in payload["events"]))
            self.assertTrue(any(event["phase"] == "done" for event in payload["events"]))
            self.assertEqual(payload["run_id"], 33)
            self.assertEqual(payload["result"]["composite_score"], 88.0)

    def test_cancel_and_retry_analysis_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            job_id = store.create_analysis_job(
                url="https://example.com",
                brand_name="Example",
                use_llm=True,
                use_social=False,
            )
            store.close()

            with patch.object(brand_service, "BRAND3_DB_PATH", str(db_path)):
                cancelled = brand_service.cancel_analysis_job(job_id)
                self.assertEqual(cancelled["status"], "cancelled")

                queued = brand_service.retry_analysis_job(job_id)
                self.assertEqual(queued["status"], "queued")
                self.assertEqual(queued["cancel_requested"], 0)

                with patch.object(
                    brand_service,
                    "run",
                    return_value={
                        "brand": "Example",
                        "url": "https://example.com",
                        "run_id": 44,
                        "composite_score": 82.0,
                    },
                ):
                    payload = brand_service.execute_analysis_job(job_id)

            self.assertEqual(payload["status"], "done")
            self.assertEqual(payload["attempt_count"], 1)
            self.assertEqual(payload["run_id"], 44)

    def test_execute_analysis_job_marks_cancelled_when_pipeline_stops(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            job_id = store.create_analysis_job(
                url="https://example.com",
                brand_name="Example",
                use_llm=True,
                use_social=False,
            )
            store.close()

            def _cancelled_run(*args, **kwargs):
                kwargs["progress_cb"]("extracting")
                raise brand_service.AnalysisJobCancelled("Cancelled by user")

            with patch.object(brand_service, "BRAND3_DB_PATH", str(db_path)):
                with patch.object(brand_service, "run", side_effect=_cancelled_run):
                    payload = brand_service.execute_analysis_job(job_id)

            self.assertEqual(payload["status"], "cancelled")
            self.assertEqual(payload["phase"], "cancelled")
            self.assertEqual(payload["error"], "Cancelled by user")

    def test_benchmark_profiles_compares_auto_and_manual_profiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "benchmark.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "name": "startup-sample",
                        "brands": [
                            {
                                "brand_name": "Example Devtool",
                                "url": "https://example.dev",
                                "expected_niche": "frontier_ai",
                                "expected_subtype": "model_lab",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            def fake_run(url, brand_name=None, use_llm=True, use_social=True, calibration_profile_override=None, **kwargs):
                profile = calibration_profile_override or "frontier_ai"
                source = "manual" if calibration_profile_override else "auto"
                score = 78.0 if profile == "base" else 84.0
                return {
                    "brand": brand_name,
                    "url": url,
                    "run_id": 1 if source == "auto" else 2,
                    "composite_score": score,
                    "dimensions": {"diferenciacion": 85.0},
                    "niche_classification": {
                        "predicted_niche": "frontier_ai",
                        "predicted_subtype": "model_lab",
                        "confidence": 0.82,
                    },
                    "calibration_profile": profile,
                    "profile_source": source,
                }

            with patch.object(brand_service, "PROJECT_ROOT", Path(tmpdir)):
                with patch.object(brand_service, "run", side_effect=fake_run):
                    payload = brand_service.benchmark_profiles(
                        str(spec_path),
                        profiles=["base", "frontier_ai"],
                        include_auto=True,
                    )

            self.assertEqual(payload["benchmark_name"], "startup-sample")
            self.assertEqual(len(payload["brands"]), 1)
            self.assertEqual(len(payload["brands"][0]["results"]), 3)
            self.assertEqual(payload["summary"]["variants"]["base"]["average_composite"], 78.0)
            self.assertEqual(payload["summary"]["variants"]["frontier_ai"]["average_composite"], 84.0)
            self.assertEqual(payload["summary"]["niche_matches"]["matched"], 3)
            self.assertEqual(payload["summary"]["subtype_matches"]["matched"], 3)
            self.assertTrue(Path(payload["output_path"]).exists())

    def test_compare_benchmarks_reports_variant_deltas(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            before_path = Path(tmpdir) / "before.json"
            after_path = Path(tmpdir) / "after.json"
            before_path.write_text(
                json.dumps(
                    {
                        "benchmark_name": "before-run",
                        "brands": [
                            {
                                "brand_name": "Example",
                                "url": "https://example.com",
                                "results": [
                                    {
                                        "variant": "auto",
                                        "composite_score": 50.0,
                                        "dimensions": {"diferenciacion": 40.0},
                                        "predicted_niche": "base",
                                        "predicted_subtype": "startup_studio",
                                        "niche_match": False,
                                        "subtype_match": False,
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            after_path.write_text(
                json.dumps(
                    {
                        "benchmark_name": "after-run",
                        "brands": [
                            {
                                "brand_name": "Example",
                                "url": "https://example.com",
                                "results": [
                                    {
                                        "variant": "auto",
                                        "composite_score": 58.0,
                                        "dimensions": {"diferenciacion": 47.0},
                                        "predicted_niche": "frontier_ai",
                                        "predicted_subtype": "model_lab",
                                        "niche_match": True,
                                        "subtype_match": True,
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(brand_service, "PROJECT_ROOT", Path(tmpdir)):
                payload = brand_service.compare_benchmarks(str(before_path), str(after_path))

            self.assertEqual(payload["summary"]["shared_brands"], 1)
            self.assertEqual(payload["summary"]["variant_deltas"]["auto"]["average_composite_delta"], 8.0)
            self.assertEqual(payload["summary"]["variant_deltas"]["auto"]["niche_match_improved"], 1)
            self.assertEqual(payload["summary"]["variant_deltas"]["auto"]["subtype_match_improved"], 1)
            self.assertTrue(Path(payload["output_path"]).exists())


if __name__ == "__main__":
    unittest.main()
