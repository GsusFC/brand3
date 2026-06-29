from __future__ import annotations

import importlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from src.storage.sqlite_store import SQLiteStore


def _install_env(db_path: Path) -> None:
    os.environ["BRAND3_DB_PATH"] = str(db_path)
    os.environ["BRAND3_COOKIE_SECRET"] = "t" * 40
    os.environ["BRAND3_TEAM_TOKEN"] = "team-token"
    os.environ["BRAND3_MAX_CONCURRENT_ANALYSES"] = "1"


class ScannerStabilityAuditRouteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "brand3.sqlite3"
        _install_env(self.db)
        store = SQLiteStore(str(self.db))
        store.close()
        self._seed_scans()

        for mod_name in list(sys.modules):
            if mod_name.startswith("web") or mod_name == "src.config":
                importlib.reload(sys.modules[mod_name])

        from fastapi.testclient import TestClient

        from web.app import app
        from web.workers.queue import set_run_analysis_override

        set_run_analysis_override(lambda _u: {"run_id": None})
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        from web.workers.queue import set_run_analysis_override

        set_run_analysis_override(None)
        self._tmp.cleanup()
        for key in (
            "BRAND3_DB_PATH",
            "BRAND3_COOKIE_SECRET",
            "BRAND3_TEAM_TOKEN",
            "BRAND3_MAX_CONCURRENT_ANALYSES",
        ):
            os.environ.pop(key, None)

    def test_internal_audit_requires_team_token(self):
        response = self.client.get("/internal/scanner-stability-audit")

        self.assertEqual(response.status_code, 403)

    def test_internal_audit_returns_compact_json_by_default(self):
        response = self.client.get(
            "/internal/scanner-stability-audit?days=365&limit_groups=5",
            headers={"x-brand3-team-token": "team-token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schema_version"], "scanner-stability-audit-v2")
        self.assertEqual(payload["sample_count"], 2)
        self.assertEqual(payload["repeated_group_count"], 1)
        group = payload["groups"][0]
        self.assertEqual(group["diagnosis_stage"], "interpretation_drift")
        self.assertEqual(group["example_scan_ids"], [1, 2])
        self.assertNotIn("examples", group)

    def test_internal_audit_can_return_full_json_and_markdown(self):
        full = self.client.get(
            "/internal/scanner-stability-audit?days=365&full=true",
            headers={"authorization": "Bearer team-token"},
        )
        markdown = self.client.get(
            "/internal/scanner-stability-audit?days=365&format=md",
            headers={"x-brand3-team-token": "team-token"},
        )

        self.assertEqual(full.status_code, 200)
        self.assertIn("examples", full.json()["groups"][0])
        self.assertEqual(markdown.status_code, 200)
        self.assertIn("Scanner stability audit", markdown.text)
        self.assertEqual(markdown.headers["content-type"].split(";", 1)[0], "text/plain")

    def _seed_scans(self):
        payload_a = _payload("A")
        payload_b = _payload("B")
        with sqlite3.connect(self.db) as conn:
            conn.executemany(
                """
                INSERT INTO magnetism_scans (
                    id, brand_name, url, magnetism_score, coherence_score,
                    quadrant, raw_payload, created_at, status
                ) VALUES (?, 'Example', 'https://example.com', ?, 70, 'steady', ?, ?, 'ready')
                """,
                [
                    (1, 62, json.dumps(payload_a), "2026-06-29T00:00:00+00:00"),
                    (2, 72, json.dumps(payload_b), "2026-06-29T01:00:00+00:00"),
                ],
            )


def _payload(answer: str) -> dict:
    return {
        "scanner_version": "SV9",
        "magnetism_score": 62 if answer == "A" else 72,
        "coherence_score": 70,
        "quadrant": "steady",
        "debug": {
            "raw_inputs": {"homepage": "same"},
            "normalized_payload": {
                "research_pack": {"claims": ["same"]},
                "analyst_tldr_validated": {"magnetism": {"answer": answer}},
            },
        },
        "tldr_brand3": {"magnetism": {"answer": answer}},
    }


if __name__ == "__main__":
    unittest.main()
