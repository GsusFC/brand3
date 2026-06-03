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

from web.app import app
from web.templates_env import STATIC_ASSET_VERSION


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

    def test_homepage_prioritizes_brand_audit_and_supported_surfaces(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Brand3 Scanner", response.text)
        self.assertIn("Analizar marca", response.text)
        self.assertIn("Auditoría de Marca", response.text)
        self.assertNotIn("home-secondary-actions", response.text)
        self.assertNotIn("abre Brand Audit", response.text)
        self.assertIn("Auditoría, evidencia y TLDR estratégico de una marca pública.", response.text)
        self.assertIn("Resultado incluido", response.text)
        self.assertIn("TLDR Brand3", response.text)
        self.assertIn("Metodología", response.text)
        self.assertIn("brand3-theme", response.text)
        self.assertIn('data-theme-toggle', response.text)
        self.assertIn(f"/static/main.css?v={STATIC_ASSET_VERSION}", response.text)
        self.assertNotIn("Brand3 Lab", response.text)
        self.assertNotIn("/brand3-lab", response.text)

    def test_homepage_preserves_ui_language_for_navigation(self):
        response = self.client.get("/?lang=en")
        self.assertEqual(response.status_code, 200)
        self.assertIn('<html lang="en">', response.text)
        self.assertNotIn('href="/brand-audit?lang=en"', response.text)
        self.assertIn('href="/visual-signature?lang=en"', response.text)
        self.assertIn('href="/magnetism-scanner?lang=en"', response.text)
        self.assertIn('href="/takedown?lang=en"', response.text)

    def test_brand_audit_landing_page_is_dedicated_route(self):
        response = self.client.get("/brand-audit")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Auditoría de Marca", response.text)
        self.assertIn("Introduce la URL de una marca para ejecutar una auditoría", response.text)
        self.assertIn('action="/analyze"', response.text)
        self.assertIn("ejecutar auditoría", response.text)
        self.assertIn("Brand3 Scanner", response.text)
        self.assertIn("Laboratorio de firma visual", response.text)
        self.assertIn("auditorías_recientes", response.text)
        self.assertIn('href="/reports"', response.text)

    def test_brand3_lab_surface_is_removed(self):
        for path in (
            "/brand3-lab",
            "/brand3-lab/perceptual-narrative-comparison",
            "/brand3-lab/cases/apple",
            "/brand3-lab/narrative-shadow-adapter",
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404, path)

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
        self.assertIn("brand3", report_resp.text)
        self.assertIn("Historial de marca", report_resp.text)
        self.assertIn('class="term-actions"', report_resp.text)
        self.assertIn('class="lang-toggle"', report_resp.text)
        self.assertIn('class="source-link badge-ready" href="?theme=light&lang=es"', report_resp.text)
        self.assertIn('class="source-link" href="?theme=light&lang=en"', report_resp.text)
        self.assertIn('class="theme-toggle theme-toggle-term"', report_resp.text)
        self.assertNotIn('class="main-nav-link is-active" href="/reports"', report_resp.text)
        self.assertNotIn('aria-label="Brand3 primary navigation"', report_resp.text)
        self.assertIn("Persisted public narrative.", report_resp.text)
        self.assertIn("Persisted public finding", report_resp.text)
        self.assertIn("Persisted public tension.", report_resp.text)

        en_resp = self.client.get(f"/r/{token}?lang=en")
        self.assertEqual(en_resp.status_code, 200)
        self.assertIn("Brand history", en_resp.text)
        self.assertNotIn('aria-label="Brand3 primary navigation"', en_resp.text)

    def test_report_uses_cached_spanish_translation_without_rerunning_audit(self):
        token, run_id = self._create_ready_run()
        translated_payload = {
            "version": 1,
            "source": "report_narrative",
            "translation_version": 1,
            "translation_source": "report_translation",
            "target_lang": "es",
            "synthesis_prose": "Narrativa traducida persistida.",
            "summary": "Narrativa traducida persistida.",
            "tensions_prose": "Tensión traducida persistida.",
            "findings_by_dimension": {
                "coherencia": [
                    {
                        "title": "Hallazgo traducido",
                        "observation": "Observación traducida.",
                        "implication": "Implicación traducida.",
                        "typical_decision": "Decisión traducida.",
                        "evidence_urls": [],
                    }
                ]
            },
        }
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """
                INSERT INTO raw_inputs (run_id, source, payload_json, created_at)
                VALUES (?, 'report_translation', ?, datetime('now'))
                """,
                (run_id, json.dumps(translated_payload)),
            )
            conn.commit()

        with patch(
            "src.features.llm_analyzer.LLMAnalyzer",
            side_effect=AssertionError("cached translation must not call LLM"),
        ):
            report_resp = self.client.get(f"/r/{token}?lang=es")

        self.assertEqual(report_resp.status_code, 200)
        self.assertIn("Narrativa traducida persistida.", report_resp.text)
        self.assertIn("Hallazgo traducido", report_resp.text)
        self.assertIn("Tensión traducida persistida.", report_resp.text)

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
