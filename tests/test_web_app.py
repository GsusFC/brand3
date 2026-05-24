"""End-to-end web flow: /analyze → queue → /r/{token}/status → /r/{token}."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch


def _install_env(db_path: Path) -> None:
    os.environ["BRAND3_DB_PATH"] = str(db_path)
    os.environ["BRAND3_COOKIE_SECRET"] = "t" * 40
    os.environ["BRAND3_TEAM_TOKEN"] = "team-token"
    os.environ["BRAND3_MAX_CONCURRENT_ANALYSES"] = "1"
    os.environ["BRAND3_ANALYSIS_TIMEOUT_SECONDS"] = "30"


class WebAppFlowTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "brand3.sqlite3"
        _install_env(self.db)

        # Reload the web package to pick up env.
        for mod_name in list(sys.modules):
            if mod_name.startswith("web") or mod_name == "src.config":
                importlib.reload(sys.modules[mod_name])

        from fastapi.testclient import TestClient

        from web.app import app
        from web.workers.queue import set_run_analysis_override

        self._resolver_patcher = patch(
            "web.workers.url_validator.socket.getaddrinfo",
            side_effect=lambda _h, _p: [(2, 1, 6, "", ("1.1.1.1", 0))],
        )
        self._resolver_patcher.start()

        # Override the engine entry: synthesize a fake run inserted into the DB.
        def _fake_engine(url: str) -> dict:
            with sqlite3.connect(self.db) as conn:
                cur = conn.execute(
                    "INSERT INTO brands (brand_name, url, domain, created_at, "
                    "last_seen_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
                    ("Fake Brand", url, "example.com"),
                )
                brand_id = int(cur.lastrowid)
                cur = conn.execute(
                    "INSERT INTO runs (brand_id, brand_name, url, started_at, "
                    "completed_at, use_llm, use_social, composite_score) "
                    "VALUES (?, ?, ?, datetime('now'), datetime('now'), 1, 1, ?)",
                    (brand_id, "Fake Brand", url, 72.5),
                )
                run_id = int(cur.lastrowid)
                conn.execute(
                    "INSERT INTO scores (run_id, dimension_name, score, insights_json, "
                    "rules_json, created_at) "
                    "VALUES (?, 'coherencia', 70, '[]', '[]', datetime('now'))",
                    (run_id,),
                )
                conn.commit()
            return {"run_id": run_id, "composite_score": 72.5}

        set_run_analysis_override(_fake_engine)

        self.client = TestClient(app)
        self.client.__enter__()

    def _create_ready_run(self) -> tuple[str, int]:
        response = self.client.post(
            "/analyze",
            data={"url": "https://example.com"},
            follow_redirects=False,
        )
        token = response.headers["location"].split("/")[2]
        row = None
        for _ in range(30):
            with sqlite3.connect(self.db) as conn:
                row = conn.execute(
                    "SELECT status, run_id FROM web_requests WHERE token = ?",
                    (token,),
                ).fetchone()
            if row and row[0] == "ready":
                break
            time.sleep(0.2)
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "ready")
        self.assertIsNotNone(row[1])
        return token, int(row[1])

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self._resolver_patcher.stop()

        from web.workers.queue import set_run_analysis_override

        set_run_analysis_override(None)
        self._tmp.cleanup()
        for key in (
            "BRAND3_DB_PATH",
            "BRAND3_COOKIE_SECRET",
            "BRAND3_TEAM_TOKEN",
            "BRAND3_MAX_CONCURRENT_ANALYSES",
            "BRAND3_ANALYSIS_TIMEOUT_SECONDS",
        ):
            os.environ.pop(key, None)

    def test_analyze_rejects_invalid_url(self):
        response = self.client.post("/analyze", data={"url": "http://localhost"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("localhost", response.text)

    def test_homepage_prioritizes_brand_audit_and_lab_is_secondary(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("brand3 — brand audit", response.text)
        self.assertIn("run brand audit", response.text)
        self.assertIn("dimension scores", response.text)
        self.assertIn("Visual Signature Lab", response.text)
        self.assertIn("Brand3 Lab", response.text)
        self.assertIn("Brand3 Scoring is the working audit product", response.text)
        self.assertIn("brand3-theme", response.text)
        self.assertIn('data-theme-toggle', response.text)
        self.assertIn("brand3-lab-mono-density-20260516", response.text)

    def test_perceptual_narrative_comparison_lab_renders_static_pairs(self):
        response = self.client.get("/brand3-lab/perceptual-narrative-comparison")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Perceptual Narrative Comparison", response.text)
        self.assertIn("aggregate index", response.text)
        self.assertIn("Compared Brand Cases", response.text)
        self.assertIn("open case review", response.text)
        self.assertIn("Aggregate Assessment", response.text)
        self.assertIn("Recommendation", response.text)
        self.assertIn("Overreach Taxonomy", response.text)
        for brand in ("Apple", "Linear", "Stripe Docs", "Headspace", "Notion", "Example Company"):
            self.assertIn(brand, response.text)
        self.assertIn("/brand3-lab/cases/apple#case-comparison", response.text)
        self.assertNotIn("Reviewer notes", response.text)
        self.assertNotIn("Export local draft JSON", response.text)
        self.assertNotIn('method="post"', response.text.lower())

    def test_brand3_lab_home_renders_lab_audit_input_and_latest(self):
        response = self.client.get("/brand3-lab")

        self.assertEqual(response.status_code, 200)
        self.assertIn("brand3 lab — audit", response.text.lower())
        self.assertIn('action="/brand3-lab/analyze"', response.text)
        self.assertIn("run lab analysis", response.text)
        self.assertIn("latest_lab_audits", response.text)

    def test_brand3_lab_analyze_flow_redirects_to_lab_case(self):
        response = self.client.post(
            "/brand3-lab/analyze",
            data={"url": "https://example.com"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        location = response.headers["location"]
        self.assertTrue(location.startswith("/brand3-lab/r/"))
        self.assertTrue(location.endswith("/status"))
        token = location.split("/")[3]

        row = None
        for _ in range(30):
            with sqlite3.connect(self.db) as conn:
                row = conn.execute(
                    "SELECT status, run_id FROM web_requests WHERE token = ?",
                    (token,),
                ).fetchone()
            if row and row[0] == "ready":
                break
            time.sleep(0.2)
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "ready")
        self.assertIsNotNone(row[1])
        run_id = int(row[1])

        status_response = self.client.get(f"/brand3-lab/r/{token}/status", follow_redirects=False)
        self.assertEqual(status_response.status_code, 303)
        self.assertEqual(status_response.headers["location"], f"/brand3-lab/r/{token}")

        report_response = self.client.get(f"/brand3-lab/r/{token}")
        self.assertEqual(report_response.status_code, 200)
        self.assertIn("brand3", report_response.text.lower())

    def test_lab_payload_uses_explicit_abstention_and_generation_unavailable(self):
        from web.routes import brand3_lab as lab_routes

        snapshot = {"run": {"id": 999}}
        packet = {
            "dimension_readiness": {
                "coherencia": {
                    "status": "ready",
                    "reason_codes": ["external_channel_coverage_thin"],
                    "readiness_reason": "Some evidence exists but remains thin.",
                    "recommended_action": "Collect stronger corroboration.",
                },
                "presencia": {
                    "status": "blocked",
                    "reason_codes": ["entity_ambiguity_unresolved"],
                    "readiness_reason": "Entity relation is unresolved.",
                    "recommended_action": "Resolve canonical ownership before prose.",
                },
            }
        }
        candidate = {
            "case_id": "fake_brand",
            "dimensions": {
                "coherencia": {
                    "readiness_status": "ready",
                    "prompt_constraints": [],
                    "evidence": [{"text": "owned claim", "url": "https://example.com"}],
                },
                "presencia": {
                    "readiness_status": "blocked",
                    "prompt_constraints": [],
                    "evidence": [],
                },
            },
        }

        class _StubAnalyzer:
            def __init__(self, *args, **kwargs):
                pass

            def _call_json(self, *args, **kwargs):
                return {}

        with patch.object(lab_routes, "build_evidence_packet_v0", return_value=packet), patch.object(
            lab_routes, "build_prompt_input_candidate_v0", return_value=candidate
        ), patch.object(lab_routes, "LLMAnalyzer", _StubAnalyzer):
            payload, error = lab_routes._build_lab_report_narrative_payload(snapshot)

        self.assertIsNone(error)
        self.assertIsNotNone(payload)
        findings = payload["findings_by_dimension"]
        self.assertIn("coherencia", findings)
        self.assertIn("presencia", findings)
        self.assertIn("Lab generation unavailable", findings["coherencia"][0]["title"])
        self.assertIn("Lab abstention (blocked)", findings["presencia"][0]["title"])
        self.assertIn("reason_codes", findings["presencia"][0]["observation"])
        self.assertIn("Lab narrative scope: ready/thin dimensions only", payload["summary"])

    def test_brand3_lab_detail_routes_render_explanatory_pages(self):
        experiment = self.client.get("/brand3-lab/experiments/perceptual-grammar")
        self.assertEqual(experiment.status_code, 200)
        self.assertIn("What it reads", experiment.text)
        self.assertIn("What it adds to each case", experiment.text)
        self.assertIn("How the LLM should use it", experiment.text)
        self.assertIn("Evidence Base", experiment.text)
        self.assertIn("lab-experiment-work-grid", experiment.text)
        self.assertIn("lab-evidence-grid", experiment.text)
        self.assertIn("Applied To Cases", experiment.text)
        for artifact in (
            "Pattern audit",
            "Perceptual Pattern Registry",
            "Perceptual Reading Semantics",
        ):
            self.assertIn(artifact, experiment.text)

        signal_depth = self.client.get("/brand3-lab/signal-depth/rich_perceptual_signal")
        self.assertEqual(signal_depth.status_code, 200)
        self.assertIn("Why It Exists", signal_depth.text)
        self.assertIn("Observable Markers", signal_depth.text)
        self.assertIn("LLM Flow", signal_depth.text)
        self.assertIn("Valid Reading Posture", signal_depth.text)

        case = self.client.get("/brand3-lab/cases/apple")
        self.assertEqual(case.status_code, 200)
        self.assertIn("Classification Evidence", case.text)
        self.assertIn("Applied Layers", case.text)
        self.assertIn("Narrative Evidence", case.text)
        self.assertIn("Comparison Signals", case.text)
        self.assertNotIn("Comparison Viewer", case.text)
        self.assertNotIn("Open the complete baseline/perceptual comparison", case.text)
        self.assertNotIn("Reviewer Decision", case.text)
        self.assertNotIn("Reviewer notes", case.text)
        self.assertNotIn("Export local draft JSON", case.text)
        self.assertNotIn("data-case-comparison-form", case.text)
        self.assertIn("lab-narrative-grid", case.text)
        self.assertIn("lab-signal-summary", case.text)
        self.assertIn("lab-layer-card-row", case.text)
        self.assertIn('id="case-comparison"', case.text)
        self.assertNotIn('method="post"', case.text.lower())

    def test_brand3_lab_shadow_adapter_route_renders_ui(self):
        response = self.client.get("/brand3-lab/narrative-shadow-adapter")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Narrative Shadow Adapter Trial", response.text)
        self.assertIn("Run Trial", response.text)
        self.assertIn('method="post"', response.text.lower())
        self.assertIn("run shadow trial", response.text)
        self.assertIn('name="source_mode"', response.text)
        self.assertIn("benchmark matrix", response.text)
        self.assertIn("single audited run_id", response.text)
        self.assertIn("By Dimension", response.text)
        self.assertIn("Findings (Human Read)", response.text)
        self.assertIn("Reading Summary", response.text)

    def test_per_audit_brand3_lab_route_renders_without_report_narrative(self):
        token, run_id = self._create_ready_run()

        response = self.client.get(f"/brand3-lab/cases/run/{run_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Applied Reading Candidates", response.text)
        self.assertIn("Lab-only", response.text)
        self.assertIn("read-only", response.text)
        self.assertIn("diagnostic", response.text)
        self.assertIn("Fake Brand", response.text)
        self.assertIn(f"/r/{token}", response.text)
        self.assertIn("Official Result", response.text)
        self.assertIn(f"/brand3-lab/cases/run/{run_id}/review", response.text)
        self.assertIn("Dimension scores", response.text)
        self.assertIn("Lab-Applied Reading Candidate", response.text)
        self.assertIn("No safe Lab-applied reading candidate yet", response.text)
        self.assertIn("Report Narrative", response.text)
        self.assertIn("available</span>=<span class=\"v\">False", response.text)
        self.assertIn("Narrative Harness is unavailable", response.text)
        self.assertIn("Render-aware diagnostics", response.text)
        self.assertIn("EntityNarrativeState", response.text)
        self.assertIn("State-aware findings experiment", response.text)
        self.assertIn("Signal Depth Model", response.text)
        self.assertIn("Perceptual Pattern Registry", response.text)
        self.assertIn("Overreach Taxonomy", response.text)
        self.assertIn("Editorial Discipline Gate", response.text)
        self.assertNotIn('method="post"', response.text.lower())

    def test_per_audit_brand3_lab_review_route_renders_unavailable_state(self):
        _token, run_id = self._create_ready_run()

        response = self.client.get(f"/brand3-lab/cases/run/{run_id}/review")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Lab Review Input", response.text)
        self.assertIn("draft-only", response.text)
        self.assertIn("not_persisted", response.text)
        self.assertIn("No safe Lab candidate to review", response.text)
        self.assertIn("Export local draft JSON", response.text)
        self.assertIn("data-lab-review-form", response.text)
        self.assertIn("brand3_lab_review.js", response.text)
        self.assertNotIn('method="post"', response.text.lower())

        post_response = self.client.post(f"/brand3-lab/cases/run/{run_id}/review")
        self.assertEqual(post_response.status_code, 405)

    def test_per_audit_brand3_lab_route_runs_harness_for_report_narrative(self):
        _token, run_id = self._create_ready_run()
        payload = {
            "version": 1,
            "source": "report_narrative",
            "synthesis_prose": "The brand describes itself as a focused platform.",
            "tensions_prose": "There is no external corroboration in the evidence pool.",
            "findings_by_dimension": {
                "presencia": [
                    {
                        "title": "Repeated owned claim",
                        "observation": (
                            "The brand describes itself as a focused platform. "
                            "This is based only on self-description; no external corroboration "
                            "in the evidence pool."
                        ),
                        "implication": "This suggests a positioning claim that needs evidence.",
                        "typical_decision": "Teams in this position typically choose between options.",
                        "evidence_urls": [],
                    },
                    {
                        "title": "Linked finding",
                        "observation": "Third party evidence is available.",
                        "implication": "This anchors part of the finding.",
                        "typical_decision": "Specific decision framing.",
                        "evidence_urls": ["https://example.com/source"],
                    },
                ]
            },
        }
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """
                INSERT INTO raw_inputs (run_id, source, payload_json, created_at)
                VALUES (?, 'report_narrative', ?, datetime('now'))
                """,
                (run_id, json.dumps(payload)),
            )
            before_score = conn.execute(
                "SELECT composite_score FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()[0]
            conn.commit()

        response = self.client.get(f"/brand3-lab/cases/run/{run_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Official Brand Audit finding", response.text)
        self.assertIn("Lab-applied reading", response.text)
        self.assertIn("recomposed candidate", response.text)
        self.assertIn("experimental", response.text)
        self.assertIn("lab-only", response.text)
        self.assertIn("not official", response.text)
        self.assertIn("not persisted", response.text)
        self.assertIn("deterministic_recomposition", response.text)
        self.assertIn("Repeated owned claim", response.text)
        self.assertIn("The brand describes itself as a focused platform.", response.text)
        self.assertIn("Generic Decision Space is demoted", response.text)
        self.assertIn("Change notes", response.text)
        self.assertIn("Evidence & risk", response.text)
        self.assertIn("confidence=low", response.text)
        self.assertIn("human_review=True", response.text)
        self.assertNotIn("Decision space: Teams in this position typically", response.text)
        self.assertIn("Narrative Harness", response.text)
        self.assertIn("generated_offline", response.text)
        self.assertIn("EntityNarrativeState", response.text)
        self.assertIn("Evidence URL coverage", response.text)
        self.assertIn("without_urls", response.text)
        self.assertIn("observation_repetition_families", response.text)
        self.assertIn("missing_evidence_urls", response.text)
        self.assertIn("no report mutation", response.text)
        with sqlite3.connect(self.db) as conn:
            after_score = conn.execute(
                "SELECT composite_score FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()[0]
            raw_count = conn.execute(
                "SELECT COUNT(*) FROM raw_inputs WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]
        self.assertEqual(after_score, before_score)
        self.assertEqual(raw_count, 1)

    def test_per_audit_brand3_lab_review_route_renders_controls_for_candidates(self):
        _token, run_id = self._create_ready_run()
        payload = {
            "version": 1,
            "source": "report_narrative",
            "synthesis_prose": "The brand describes itself as a focused platform.",
            "tensions_prose": "There is no external corroboration in the evidence pool.",
            "findings_by_dimension": {
                "presencia": [
                    {
                        "title": "Repeated owned claim",
                        "observation": (
                            "The brand describes itself as a focused platform. "
                            "This is based only on self-description; no external corroboration "
                            "in the evidence pool."
                        ),
                        "implication": "This suggests a positioning claim that needs evidence.",
                        "typical_decision": "Teams in this position typically choose between options.",
                        "evidence_urls": [],
                    },
                    {
                        "title": "Linked finding",
                        "observation": "Third party evidence is available.",
                        "implication": "This anchors part of the finding.",
                        "typical_decision": "Specific decision framing.",
                        "evidence_urls": ["https://example.com/source"],
                    },
                ]
            },
        }
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """
                INSERT INTO raw_inputs (run_id, source, payload_json, created_at)
                VALUES (?, 'report_narrative', ?, datetime('now'))
                """,
                (run_id, json.dumps(payload)),
            )
            before_score = conn.execute(
                "SELECT composite_score FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()[0]
            conn.commit()

        response = self.client.get(f"/brand3-lab/cases/run/{run_id}/review")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Official Brand Audit finding", response.text)
        self.assertIn("Lab-applied candidate", response.text)
        self.assertIn("Repeated owned claim", response.text)
        self.assertIn("Linked finding", response.text)
        self.assertIn("Reviewer decision", response.text)
        self.assertIn("baseline better", response.text)
        self.assertIn("lab better", response.text)
        self.assertIn("unsafe overreach", response.text)
        self.assertIn("Reason tags", response.text)
        self.assertIn("stronger evidence binding", response.text)
        self.assertIn("reduced caveat repetition", response.text)
        self.assertIn("requires human review", response.text)
        self.assertIn("Overall Review", response.text)
        self.assertIn("baseline wins", response.text)
        self.assertIn("needs more evidence", response.text)
        self.assertIn("Export local draft JSON", response.text)
        self.assertIn("draft_only", response.text)
        self.assertIn("not_persisted", response.text)
        self.assertIn("data-review-schema-version", response.text)
        self.assertIn("data-dimension-review", response.text)
        self.assertIn('name="overall_decision"', response.text)
        self.assertIn('name="overall_notes"', response.text)
        self.assertNotIn('method="post"', response.text.lower())
        with sqlite3.connect(self.db) as conn:
            after_score = conn.execute(
                "SELECT composite_score FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()[0]
            raw_count = conn.execute(
                "SELECT COUNT(*) FROM raw_inputs WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]
        self.assertEqual(after_score, before_score)
        self.assertEqual(raw_count, 1)

    def test_per_audit_brand3_lab_missing_run_returns_404(self):
        response = self.client.get("/brand3-lab/cases/run/999999")

        self.assertEqual(response.status_code, 404)

    def test_perceptual_narrative_comparison_export_script_is_draft_only(self):
        response = self.client.get("/static/perceptual_narrative_comparison.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn("draft_only", response.text)
        self.assertIn("not_persisted", response.text)
        self.assertIn("case_id", response.text)
        self.assertIn("comparison_source_metadata", response.text)
        self.assertIn("not_persisted", response.text)
        self.assertIn("No review is persisted", response.text)

    def test_brand3_lab_review_export_script_is_draft_only(self):
        response = self.client.get("/static/brand3_lab_review.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn("draft_only", response.text)
        self.assertIn("not_persisted", response.text)
        self.assertIn("run_id", response.text)
        self.assertIn("case_id", response.text)
        self.assertIn("source_artifacts", response.text)
        self.assertIn("dimension_reviews", response.text)
        self.assertIn("overall_decision", response.text)
        self.assertIn("reviewer_notes", response.text)

    def test_analyze_valid_url_redirects_and_persists_row(self):
        response = self.client.post(
            "/analyze",
            data={"url": "https://example.com"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["location"].startswith("/r/"))
        self.assertTrue(response.headers["location"].endswith("/status"))

        token = response.headers["location"].split("/")[2]
        with sqlite3.connect(self.db) as conn:
            row = conn.execute(
                "SELECT * FROM web_requests WHERE token = ?", (token,)
            ).fetchone()
        self.assertIsNotNone(row)

    def test_full_flow_queued_to_ready(self):
        response = self.client.post(
            "/analyze",
            data={"url": "https://example.com"},
            follow_redirects=False,
        )
        token = response.headers["location"].split("/")[2]

        # Let the worker drain. The fake engine is synchronous, so one loop cycle
        # plus the worker poll interval (1s) is enough.
        for _ in range(30):
            with sqlite3.connect(self.db) as conn:
                row = conn.execute(
                    "SELECT status, run_id FROM web_requests WHERE token = ?",
                    (token,),
                ).fetchone()
            if row and row[0] == "ready":
                break
            time.sleep(0.2)

        self.assertEqual(row[0], "ready")
        self.assertIsNotNone(row[1])  # run_id populated

        # status endpoint now redirects to the report.
        status_resp = self.client.get(f"/r/{token}/status", follow_redirects=False)
        self.assertEqual(status_resp.status_code, 303)
        self.assertEqual(status_resp.headers["location"], f"/r/{token}")

        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """
                INSERT INTO raw_inputs (run_id, source, payload_json, created_at)
                VALUES (?, 'report_narrative', ?, datetime('now'))
                """,
                (
                    row[1],
                    json.dumps(
                        {
                            "version": 1,
                            "source": "report_narrative",
                            "synthesis_prose": "Persisted public narrative.",
                            "tensions_prose": "Persisted public tension.",
                            "findings_by_dimension": {
                                "presencia": [
                                    {
                                        "title": "Persisted public finding",
                                        "observation": "Persisted public observation.",
                                        "implication": "Persisted public implication.",
                                        "typical_decision": "Persisted public decision space.",
                                        "evidence_urls": [],
                                    }
                                ]
                            },
                        }
                    ),
                ),
            )
            conn.commit()

        # report endpoint renders HTML without live LLM narrative work.
        with patch(
            "src.features.llm_analyzer.LLMAnalyzer",
            side_effect=AssertionError("web report detail must not call LLM"),
        ):
            report_resp = self.client.get(f"/r/{token}")
        self.assertEqual(report_resp.status_code, 200)
        self.assertIn("Fake Brand", report_resp.text)
        self.assertIn("Reports", report_resp.text)
        self.assertIn("Brand history", report_resp.text)
        self.assertIn("Persisted public narrative.", report_resp.text)
        self.assertIn("Persisted public finding", report_resp.text)
        self.assertIn("Persisted public tension.", report_resp.text)

    def test_status_page_shows_live_phase_checklist(self):
        from web.workers.queue import set_run_analysis_override

        release = threading.Event()

        def _slow_engine(url: str, progress_cb=None) -> dict:
            if progress_cb is not None:
                progress_cb("scoring")
            release.wait(timeout=5)
            with sqlite3.connect(self.db) as conn:
                cur = conn.execute(
                    "INSERT INTO brands (brand_name, url, domain, created_at, "
                    "last_seen_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
                    ("Phase Brand", url, "example.com"),
                )
                brand_id = int(cur.lastrowid)
                cur = conn.execute(
                    "INSERT INTO runs (brand_id, brand_name, url, started_at, "
                    "completed_at, use_llm, use_social, composite_score) "
                    "VALUES (?, ?, ?, datetime('now'), datetime('now'), 1, 1, ?)",
                    (brand_id, "Phase Brand", url, 72.5),
                )
                run_id = int(cur.lastrowid)
                conn.commit()
            return {"run_id": run_id, "composite_score": 72.5}

        set_run_analysis_override(_slow_engine)
        try:
            response = self.client.post(
                "/analyze",
                data={"url": "https://example.com"},
                follow_redirects=False,
            )
            token = response.headers["location"].split("/")[2]

            row = None
            for _ in range(30):
                with sqlite3.connect(self.db) as conn:
                    row = conn.execute(
                        "SELECT status, phase FROM web_requests WHERE token = ?",
                        (token,),
                    ).fetchone()
                if row and row[0] == "running" and row[1] == "scoring":
                    break
                time.sleep(0.2)

            self.assertEqual(row[0], "running")
            self.assertEqual(row[1], "scoring")

            status_resp = self.client.get(f"/r/{token}/status")
            self.assertEqual(status_resp.status_code, 200)
            self.assertIn("Scoring dimensions", status_resp.text)
            self.assertIn("[active]", status_resp.text)
            self.assertIn("This checklist reflects pipeline phase", status_resp.text)
        finally:
            release.set()

    def test_unknown_token_returns_404(self):
        response = self.client.get("/r/nope-nope/status")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
