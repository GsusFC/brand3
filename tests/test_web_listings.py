"""Phase 4 — /, /reports, /brand/{domain} listings and filters."""

from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path


def _install_env(db_path: Path) -> None:
    os.environ["BRAND3_DB_PATH"] = str(db_path)
    os.environ["BRAND3_COOKIE_SECRET"] = "t" * 40
    os.environ["BRAND3_TEAM_TOKEN"] = "team"
    os.environ["BRAND3_MAX_CONCURRENT_ANALYSES"] = "1"


class ListingsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "brand3.sqlite3"
        _install_env(self.db)

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

    def _seed_ready_run(
        self,
        brand_slug: str,
        composite: float | None,
        days_ago: int = 0,
        is_public: int = 1,
        takedown: int = 0,
    ) -> str:
        """Insert an engine run + a ready web_request row. Returns the token."""
        token = f"tok-{brand_slug}-{time.time_ns()}"
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO brands (brand_name, url, domain, created_at, "
                "last_seen_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
                (brand_slug, f"https://{brand_slug}.com", f"{brand_slug}.com"),
            )
            brand_id = int(
                conn.execute(
                    "SELECT id FROM brands WHERE brand_name = ? AND url = ?",
                    (brand_slug, f"https://{brand_slug}.com"),
                ).fetchone()[0]
            )
            cur = conn.execute(
                "INSERT INTO runs (brand_id, brand_name, url, started_at, "
                "completed_at, use_llm, use_social, composite_score) "
                "VALUES (?, ?, ?, datetime('now', ?), datetime('now', ?), 1, 1, ?)",
                (
                    brand_id,
                    brand_slug,
                    f"https://{brand_slug}.com",
                    f"-{days_ago} days",
                    f"-{days_ago} days",
                    composite,
                ),
            )
            run_id = int(cur.lastrowid)
            conn.execute(
                """
                INSERT INTO web_requests
                  (token, url, brand_slug, requester_ip, status, run_id,
                   is_public, takedown_requested, created_at, completed_at)
                VALUES (?, ?, ?, '127.0.0.1', 'ready', ?, ?, ?,
                        datetime('now', ?), datetime('now', ?))
                """,
                (
                    token,
                    f"https://{brand_slug}.com",
                    brand_slug,
                    run_id,
                    is_public,
                    takedown,
                    f"-{days_ago} days",
                    f"-{days_ago} days",
                ),
            )
            conn.commit()
        return token

    def _seed_ready_scan(
        self,
        brand_name: str,
        magnetism_score: int,
        coherence_score: int,
        days_ago: int = 0,
    ) -> int:
        with sqlite3.connect(self.db) as conn:
            cur = conn.execute(
                """
                INSERT INTO magnetism_scans
                  (brand_name, url, magnetism_score, coherence_score, quadrant, raw_payload,
                   created_at, status, token, phase, phase_updated_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', ?), 'ready', ?, 'ready',
                        datetime('now', ?), datetime('now', ?))
                """,
                (
                    brand_name,
                    f"https://{brand_name}.com",
                    magnetism_score,
                    coherence_score,
                    "quadrant",
                    "{}",
                    f"-{days_ago} days",
                    f"scan-{brand_name}-{time.time_ns()}",
                    f"-{days_ago} days",
                    f"-{days_ago} days",
                ),
            )
            conn.commit()
        return int(cur.lastrowid)

    def test_index_empty_shows_placeholder(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Magnetism Scanner", r.text)
        self.assertIn(">Brand Audit<", r.text)
        self.assertIn('href="/brand-audit"', r.text)
        self.assertIn("no analyses yet", r.text)

    def test_index_limits_to_ten(self):
        for i in range(20):
            self._seed_ready_run(f"brand{i:02d}", composite=50.0 + i, days_ago=i)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        rendered = r.text.count("<tr>")
        self.assertEqual(rendered, 16)  # header + 15 rows
        self.assertIn("brand00", r.text)  # newest
        self.assertNotIn("brand15", r.text)  # 16th excluded

    def test_index_merges_scanners_and_audits(self):
        self._seed_ready_run("auditco", composite=66.0, days_ago=1)
        self._seed_ready_scan("scanco", magnetism_score=83, coherence_score=72, days_ago=0)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("score", r.text)
        self.assertIn("band", r.text)
        self.assertIn("Scanner", r.text)
        self.assertIn("Audit", r.text)
        self.assertIn('class="home-kind home-kind-scanner"', r.text)
        self.assertIn('class="home-kind home-kind-audit"', r.text)
        self.assertIn("/magnetism-scanner/scan/", r.text)
        self.assertIn("/r/tok-", r.text)

    def test_index_dedupes_repeated_scans_per_brand(self):
        self._seed_ready_scan("dupco", magnetism_score=81, coherence_score=70, days_ago=0)
        self._seed_ready_scan("dupco", magnetism_score=82, coherence_score=71, days_ago=1)
        self._seed_ready_scan("dupco", magnetism_score=83, coherence_score=72, days_ago=2)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text.count("dupco"), 1)
        self.assertEqual(r.text.count("<tr>"), 2)  # header + 1 row
        self.assertIn("81", r.text)
        self.assertIn("[", r.text)

    def test_brand_page_shows_all_history(self):
        for i in range(3):
            self._seed_ready_run("a16z", composite=60.0 + i, days_ago=i)
        r = self.client.get("/brand/a16z")
        self.assertEqual(r.status_code, 200)
        self.assertIn("a16z", r.text)
        # Header + 3 rows = 4 <tr>
        self.assertEqual(r.text.count("<tr>"), 4)

    def test_brand_page_accepts_full_domain(self):
        self._seed_ready_run("a16z", composite=70.0)
        r = self.client.get("/brand/a16z.com")
        self.assertEqual(r.status_code, 200)
        self.assertIn("a16z", r.text)

    def test_reports_filter_by_query(self):
        self._seed_ready_run("airbnb", composite=65.0)
        self._seed_ready_run("uber", composite=72.0)
        r = self.client.get("/reports?q=air")
        self.assertEqual(r.status_code, 200)
        self.assertIn("airbnb", r.text)
        self.assertNotIn(">uber<", r.text)

    def test_reports_sort_score_desc(self):
        self._seed_ready_run("low", composite=40.0, days_ago=1)
        self._seed_ready_run("high", composite=90.0, days_ago=2)
        r = self.client.get("/reports?sort=score_desc")
        self.assertEqual(r.status_code, 200)
        idx_high = r.text.find(">high<")
        idx_low = r.text.find(">low<")
        self.assertGreater(idx_low, idx_high)  # high appears before low

    def test_taken_down_row_is_hidden(self):
        self._seed_ready_run("hidden", composite=50.0, takedown=1)
        r = self.client.get("/reports")
        self.assertNotIn(">hidden<", r.text)
        r2 = self.client.get("/brand/hidden")
        self.assertNotIn("view</a>", r2.text)

    def test_non_public_row_is_hidden(self):
        self._seed_ready_run("privateco", composite=50.0, is_public=0)
        r = self.client.get("/reports")
        self.assertNotIn(">privateco<", r.text)


if __name__ == "__main__":
    unittest.main()
