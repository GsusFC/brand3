import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import main
from src.models.brand import BrandScore, DimensionScore
from src.storage.sqlite_store import SQLiteStore


class MainExperimentTests(unittest.TestCase):
    def test_analyze_refresh_flag_is_passed_to_service(self):
        with patch.object(main, "run", return_value={}) as run_mock:
            main.main(["brand3", "analyze", "https://claude.ai", "Claude", "--refresh"])

        run_mock.assert_called_once_with(
            "https://claude.ai",
            "Claude",
            True,
            True,
            refresh=True,
        )

    def test_render_report_without_diagnostic_flag_uses_existing_render_path(self):
        stdout = io.StringIO()

        with patch("src.reports.renderer.render_run", return_value=Path("/tmp/report.html")) as render_run:
            with patch.object(main, "_render_report_with_readiness_diagnostic") as debug_render:
                with redirect_stdout(stdout):
                    main.main(["brand3", "render-report", "--run-id", "7"])

        render_run.assert_called_once_with(7, theme="dark")
        debug_render.assert_not_called()
        self.assertIn("Rendered HTML report: /tmp/report.html", stdout.getvalue())

    def test_render_report_diagnostic_flag_sets_context_ui_flag(self):
        captured = {}

        class FakeStore:
            def get_latest_run_id(self):
                return 99

            def get_run_snapshot(self, run_id):
                captured["run_id"] = run_id
                return {
                    "run": {
                        "id": run_id,
                        "brand_name": "Example",
                        "url": "https://example.com",
                    }
                }

            def close(self):
                captured["closed"] = True

        class FakeTemplate:
            def render(self, **context):
                captured["context"] = context
                return "<html>debug</html>"

        class FakeEnv:
            def get_template(self, name):
                captured["template"] = name
                return FakeTemplate()

        class FakeRenderer:
            env = FakeEnv()

        context = {"ui": {}, "brand": {"name": "Example"}}
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            with patch("src.storage.sqlite_store.SQLiteStore", return_value=FakeStore()):
                with patch("src.reports.dossier.build_brand_dossier", return_value=context):
                    with patch("src.reports.renderer.ReportRenderer", return_value=FakeRenderer()):
                        with patch("src.reports.renderer._resolve_output_path", return_value=output_path):
                            path = main._render_report_with_readiness_diagnostic(
                                run_id=7,
                                latest=False,
                                theme="dark",
                            )

            self.assertEqual(path, output_path)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "<html>debug</html>")

        self.assertEqual(captured["run_id"], 7)
        self.assertTrue(captured["closed"])
        self.assertEqual(captured["template"], "report.html.j2")
        self.assertTrue(captured["context"]["ui"]["show_readiness_diagnostic"])

    def test_readiness_command_prints_processed_json_readiness(self):
        snapshot = {
            "brand": "Legacy Brand",
            "url": "https://legacy.example",
            "composite_score": 73.0,
            "dimensions": {
                "coherencia": 80.0,
                "presencia": 75.0,
                "percepcion": 70.0,
                "diferenciacion": 78.0,
                "vitalidad": 62.0,
            },
            "partial_dimensions": [],
            "audit": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "legacy.json"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                main.main(["brand3", "readiness", str(path)])

        output = stdout.getvalue()
        self.assertIn(f"path: {path}", output)
        self.assertIn("brand: Legacy Brand", output)
        self.assertIn("report_mode: insufficient_evidence", output)
        self.assertIn("diagnostic_summary:", output)
        self.assertIn("input_limitations:", output)
        self.assertIn("blockers:", output)
        self.assertIn("warnings:", output)
        self.assertIn("dimension_states:", output)
        self.assertIn("fallback_detected:", output)
        self.assertIn("missing_high_weight_features:", output)

    def test_readiness_batch_command_prints_one_row_per_snapshot(self):
        snapshots = [
            {"brand": "Alpha", "readiness_fixture": "alpha"},
            {"brand": "Beta", "readiness_fixture": "beta"},
        ]

        def fake_build_report_context(snapshot, theme="dark"):
            if snapshot["readiness_fixture"] == "alpha":
                readiness = {
                    "report_mode": "technical_diagnostic",
                    "blockers": ["core_dimensions_not_evaluable"],
                    "dimension_states": {
                        "coherencia": "not_evaluable",
                        "diferenciacion": "observation_only",
                        "presencia": "ready",
                    },
                    "input_limitations": ["legacy_score_only_snapshot"],
                }
            else:
                readiness = {
                    "report_mode": "publishable_brand_report",
                    "blockers": [],
                    "dimension_states": {
                        "coherencia": "ready",
                        "diferenciacion": "ready",
                        "presencia": "ready",
                    },
                    "input_limitations": [],
                }
            return {"brand": snapshot["brand"], "readiness": readiness}

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for index, snapshot in enumerate(snapshots):
                path = Path(tmpdir) / f"snapshot-{index}.json"
                path.write_text(json.dumps(snapshot), encoding="utf-8")
                paths.append(path)

            stdout = io.StringIO()
            with patch.object(main, "_load_build_report_context", return_value=fake_build_report_context):
                with redirect_stdout(stdout):
                    main.main(["brand3", "readiness-batch", *(str(path) for path in paths)])

        lines = stdout.getvalue().splitlines()
        self.assertEqual(
            lines[0],
            "brand\treport_mode\tblockers\tnot_evaluable_dimensions\t"
            "observation_only_dimensions\tinput_limitations",
        )
        self.assertEqual(
            lines[1],
            "Alpha\ttechnical_diagnostic\tcore_dimensions_not_evaluable\t"
            "coherencia\tdiferenciacion\tlegacy_score_only_snapshot",
        )
        self.assertEqual(
            lines[2],
            "Beta\tpublishable_brand_report\t-\t-\t-\t-",
        )

    def test_run_experiment_applies_candidates_reruns_and_persists_delta(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            before_run = store.create_run(brand_id, "Example", "https://example.com", True, False)
            store.save_scores(
                before_run,
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
            store.finalize_run(before_run, 50.0, True, False, "/tmp/before.json", "before")
            store.save_run_audit(
                before_run,
                {
                    "gate_config": {"max_composite_drop": 0.0, "max_dimension_drops": {}},
                    "active_baseline": None,
                    "scoring_state_fingerprint": "before-fingerprint",
                },
            )
            store.close()

            def fake_run(url, brand_name=None, use_llm=True, use_social=True):
                inner = SQLiteStore(str(db_path))
                try:
                    brand_key = inner.upsert_brand(brand_name, url)
                    run_id = inner.create_run(brand_key, brand_name, url, use_llm, use_social)
                    inner.save_scores(
                        run_id,
                        BrandScore(
                            url=url,
                            brand_name=brand_name,
                            dimensions={
                                "presencia": DimensionScore(name="presencia", score=66.0, insights=[], rules_applied=[], features={}),
                                "diferenciacion": DimensionScore(name="diferenciacion", score=48.0, insights=[], rules_applied=[], features={}),
                            },
                            composite_score=57.0,
                        ),
                    )
                    inner.finalize_run(run_id, 57.0, use_llm, use_social, "/tmp/after.json", "after")
                    inner.save_run_audit(
                        run_id,
                        {
                            "gate_config": {"max_composite_drop": 0.0, "max_dimension_drops": {}},
                            "active_baseline": None,
                            "scoring_state_fingerprint": "after-fingerprint",
                        },
                    )
                    return {
                        "brand": brand_name,
                        "url": url,
                        "run_id": run_id,
                        "composite_score": 57.0,
                    }
                finally:
                    inner.close()

            with patch.object(main, "BRAND3_DB_PATH", str(db_path)):
                with patch.object(main, "apply_candidates", return_value=[{"candidate_id": 9, "applied": True}]):
                    with patch.object(main, "run", side_effect=fake_run):
                        payload = main.run_experiment("Example")

            self.assertEqual(payload["summary"]["composite"]["before"], 50.0)
            self.assertEqual(payload["summary"]["composite"]["after"], 57.0)
            self.assertEqual(payload["summary"]["composite"]["delta"], 7.0)
            self.assertEqual(payload["summary"]["dimensions"]["diferenciacion"]["delta"], 8.0)

            verify = SQLiteStore(str(db_path))
            try:
                experiments = verify.list_experiments("Example", limit=10)
            finally:
                verify.close()

            self.assertEqual(len(experiments), 1)
            self.assertEqual(experiments[0]["candidate_ids"], [9])
            self.assertEqual(experiments[0]["summary"]["after_run_id"], payload["summary"]["after_run_id"])
            self.assertEqual(experiments[0]["before_scoring_state_fingerprint"], "before-fingerprint")
            self.assertEqual(experiments[0]["after_scoring_state_fingerprint"], "after-fingerprint")


if __name__ == "__main__":
    unittest.main()
