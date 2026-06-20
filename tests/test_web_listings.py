"""Phase 4 — /, /reports, /brand/{domain} listings and filters."""

from __future__ import annotations

import importlib
import json
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
        raw_payload: dict | None = None,
        source_run_id: int | None = None,
    ) -> int:
        payload_json = "{}"
        if raw_payload is not None:
            payload_json = json.dumps(raw_payload, ensure_ascii=False)
        with sqlite3.connect(self.db) as conn:
            cur = conn.execute(
                """
                INSERT INTO magnetism_scans
                  (brand_name, url, magnetism_score, coherence_score, quadrant, raw_payload,
                   created_at, status, token, phase, phase_updated_at, completed_at, source_run_id)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', ?), 'ready', ?, 'ready',
                        datetime('now', ?), datetime('now', ?), ?)
                """,
                (
                    brand_name,
                    f"https://{brand_name}.com",
                    magnetism_score,
                    coherence_score,
                    "quadrant",
                    payload_json,
                    f"-{days_ago} days",
                    f"scan-{brand_name}-{time.time_ns()}",
                    f"-{days_ago} days",
                    f"-{days_ago} days",
                    source_run_id,
                ),
            )
            conn.commit()
        return int(cur.lastrowid)

    def _seed_sv9_scan(self, source_run_id: int, brand_name: str) -> int:
        from src.sv9.models import ComponentResult, Sv9ScanResult, STATUS_SCORED
        from src.sv9.store import Sv9Store

        store = Sv9Store(str(self.db))
        try:
            return int(
                store.save_scan(
                    Sv9ScanResult(
                        brand_name=brand_name,
                        url=f"https://{brand_name}.com",
                        source_run_id=source_run_id,
                        brand3_score=71,
                        components={
                            "mission": ComponentResult(
                                component="mission",
                                status=STATUS_SCORED,
                                score=2,
                                detected_content="Clear mission.",
                            )
                        },
                    )
                )
            )
        finally:
            store.close()

    def test_index_empty_shows_placeholder(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Brand3 Scanner", r.text)
        self.assertNotIn("SV9 Brand Score", r.text)
        self.assertNotIn('href="/brand-audit"', r.text)
        self.assertIn("todavía no hay análisis", r.text)
        self.assertIn("scanner de marca", r.text)

    def test_index_lists_first_paginated_page(self):
        for i in range(20):
            self._seed_ready_run(f"brand{i:02d}", composite=50.0 + i, days_ago=i)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        rendered = r.text.count("<tr>")
        self.assertEqual(rendered, 21)  # header + 20 rows
        self.assertIn("brand00", r.text)  # newest
        self.assertIn("brand19", r.text)

    def test_index_paginates_all_brands(self):
        for i in range(30):
            self._seed_ready_run(f"brand{i:02d}", composite=50.0 + i, days_ago=i)

        first = self.client.get("/")
        second = self.client.get("/?page=2")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertIn("30 marcas", first.text)
        self.assertIn("page 1/2", first.text)
        self.assertIn("brand00", first.text)
        self.assertNotIn("brand25", first.text)
        self.assertIn("page 2/2", second.text)
        self.assertIn("brand25", second.text)

    def test_index_searches_unified_observatory(self):
        self._seed_ready_run("airbnb", composite=65.0)
        self._seed_ready_scan("linear", magnetism_score=83, coherence_score=72)

        r = self.client.get("/?q=line")

        self.assertEqual(r.status_code, 200)
        self.assertIn(">Linear<", r.text)
        self.assertNotIn(">Airbnb<", r.text)

    def test_index_filters_by_accepted_market_classification(self):
        self._seed_ready_run("airbnb", composite=65.0)
        self._seed_ready_scan("linear", magnetism_score=83, coherence_score=72)
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """
                INSERT INTO brand_market_classifications
                  (brand_key, classification_json, confidence, source,
                   requires_human_review, updated_at)
                VALUES (?, ?, 'high', 'manual_review', 0, datetime('now'))
                """,
                (
                    "linear.com",
                    json.dumps(
                        {
                            "accepted": {
                                "business_model": ["SaaS"],
                                "sector_industry": ["project management"],
                            },
                            "primary_category": "SaaS",
                        }
                    ),
                ),
            )
            conn.commit()

        all_rows = self.client.get("/")
        filtered = self.client.get("/?category=saas")
        tagged = self.client.get("/?tag=project-management")
        reports_tagged = self.client.get("/reports?tag=project-management")
        scanner_tagged = self.client.get("/magnetism-scanner?tag=project-management")

        self.assertEqual(all_rows.status_code, 200)
        self.assertIn('<option value="saas">SaaS</option>', all_rows.text)
        self.assertIn('name="tag"', all_rows.text)
        self.assertIn('<option value="project-management">project management</option>', all_rows.text)
        self.assertEqual(filtered.status_code, 200)
        self.assertIn(">Linear<", filtered.text)
        self.assertNotIn(">Airbnb<", filtered.text)
        self.assertEqual(tagged.status_code, 200)
        self.assertIn(">Linear<", tagged.text)
        self.assertNotIn(">Airbnb<", tagged.text)
        self.assertEqual(reports_tagged.status_code, 200)
        self.assertIn(">Linear<", reports_tagged.text)
        self.assertNotIn(">Airbnb<", reports_tagged.text)
        self.assertEqual(scanner_tagged.status_code, 200)
        self.assertIn(">Linear<", scanner_tagged.text)
        self.assertNotIn(">Airbnb<", scanner_tagged.text)

    def test_brand_page_renders_market_classification_context(self):
        self._seed_ready_scan("linear", magnetism_score=83, coherence_score=72)
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """
                INSERT INTO brand_market_classifications
                  (brand_key, classification_json, confidence, source,
                   requires_human_review, updated_at)
                VALUES (?, ?, 'high', 'manual_review', 0, datetime('now'))
                """,
                (
                    "linear.com",
                    json.dumps(
                        {
                            "accepted": {
                                "business_model": ["SaaS"],
                                "sector_industry": ["project management"],
                            },
                            "proposed": {
                                "technology_capability": ["automation"],
                            },
                            "primary_category": "project management",
                        }
                    ),
                ),
            )
            conn.commit()

        response = self.client.get("/brand/linear.com")

        self.assertEqual(response.status_code, 200)
        self.assertIn("clasificación_mercado", response.text)
        self.assertIn("project management", response.text)
        self.assertIn("SaaS", response.text)
        self.assertNotIn("automation", response.text)
        self.assertIn("No modifica el score", response.text)

    def test_index_merges_scanners_and_audits(self):
        self._seed_ready_run("auditco", composite=66.0, days_ago=1)
        self._seed_ready_scan("scanco", magnetism_score=83, coherence_score=72, days_ago=0)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn('class="home-recent-table"', r.text)
        self.assertIn("score", r.text)
        self.assertIn("cat.", r.text)
        self.assertNotIn('<th class="col-bar">bar</th>', r.text)
        self.assertNotIn('<th class="col-band">band</th>', r.text)
        self.assertNotIn('class="col-type"', r.text)
        self.assertNotIn('class="home-kind', r.text)
        self.assertIn("/magnetism-scanner/scan/", r.text)
        self.assertIn("/r/tok-", r.text)

    def test_index_displays_company_name_instead_of_url(self):
        self._seed_ready_scan("www.sklum.com", magnetism_score=83, coherence_score=72, days_ago=0)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(">Sklum<", r.text)
        self.assertNotIn(">www.sklum.com<", r.text)

    def test_home_recent_scanner_link_prefers_sv9_when_available(self):
        source_run_id = 321
        self._seed_ready_scan(
            "sv9home",
            magnetism_score=83,
            coherence_score=72,
            source_run_id=source_run_id,
            raw_payload={
                "brand_name": "sv9home",
                "url": "https://sv9home.com",
                "magnetism_score": 83,
                "coherence_score": 72,
                "quadrant": "quadrant",
                "source_run_id": source_run_id,
                "source": "brand_audit_snapshot",
            },
        )
        sv9_id = self._seed_sv9_scan(source_run_id, "sv9home")

        r = self.client.get("/")

        self.assertEqual(r.status_code, 200)
        self.assertIn(f'href="/sv9/scan/{sv9_id}?lang=es"', r.text)
        self.assertIn('<span class="score-compact">71</span>', r.text)

    def test_scanner_recent_list_prefers_sv9_when_available(self):
        source_run_id = 322
        self._seed_ready_scan(
            "sv9scanner",
            magnetism_score=83,
            coherence_score=72,
            source_run_id=source_run_id,
            raw_payload={
                "brand_name": "sv9scanner",
                "url": "https://sv9scanner.com",
                "magnetism_score": 83,
                "coherence_score": 72,
                "quadrant": "quadrant",
                "source_run_id": source_run_id,
                "source": "brand_audit_snapshot",
            },
        )
        sv9_id = self._seed_sv9_scan(source_run_id, "sv9scanner")

        r = self.client.get("/magnetism-scanner")

        self.assertEqual(r.status_code, 200)
        self.assertIn(f'href="/sv9/scan/{sv9_id}?lang=es"', r.text)

    def test_scanner_recent_list_uses_compact_date_and_company_name(self):
        self._seed_ready_scan("www.sklum.com", magnetism_score=83, coherence_score=72, days_ago=0)
        r = self.client.get("/magnetism-scanner?lang=es")
        self.assertEqual(r.status_code, 200)
        self.assertIn(">Sklum<", r.text)
        self.assertNotIn(">www.sklum.com<", r.text)
        self.assertIn("26/", r.text)
        self.assertNotIn("2026 ·", r.text)

    def test_index_dedupes_repeated_scans_per_brand(self):
        self._seed_ready_scan("dupco", magnetism_score=81, coherence_score=70, days_ago=0)
        self._seed_ready_scan("dupco", magnetism_score=82, coherence_score=71, days_ago=1)
        self._seed_ready_scan("dupco", magnetism_score=83, coherence_score=72, days_ago=2)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text.count(">Dupco<"), 1)
        self.assertEqual(r.text.count("<tr>"), 2)  # header + 1 row
        self.assertIn("81", r.text)
        self.assertIn("26/", r.text)

    def test_scanner_recent_list_prefers_magnetism_payload_when_columns_are_stale(self):
        self._seed_ready_scan(
            "stale",
            magnetism_score=0,
            coherence_score=52,
            days_ago=0,
            raw_payload={
                "brand_name": "stale",
                "url": "https://stale.com",
                "magnetism_score": 64,
                "coherence_score": 74,
                "quadrant": "Canonical quadrant",
                "source_run_id": 160,
                "source": "brand_audit_snapshot",
            },
        )
        from web.storage import list_magnetism_scans

        row = list_magnetism_scans(limit=1)[0]
        self.assertNotIn("raw_payload", row)
        self.assertEqual(row["magnetism_score"], 64)
        self.assertEqual(row["coherence_score"], 74)
        self.assertEqual(row["quadrant"], "Canonical quadrant")
        self.assertEqual(row["source_run_id"], 160)
        self.assertEqual(row["scan_mode"]["mode"], "from_audit_run")
        self.assertTrue(row["scan_mode"]["comparable"])

        r = self.client.get("/magnetism-scanner")
        self.assertEqual(r.status_code, 200)
        self.assertIn("64", r.text)
        self.assertIn("Canonical quadrant", r.text)

    def test_brand_page_shows_all_history(self):
        for i in range(3):
            self._seed_ready_run("a16z", composite=60.0 + i, days_ago=i)
        r = self.client.get("/brand/a16z")
        self.assertEqual(r.status_code, 200)
        self.assertIn("A16z", r.text)
        # Header + 3 rows = 4 <tr>
        self.assertEqual(r.text.count("<tr>"), 4)

    def test_brand_page_accepts_full_domain(self):
        self._seed_ready_run("a16z", composite=70.0)
        r = self.client.get("/brand/a16z.com")
        self.assertEqual(r.status_code, 200)
        self.assertIn("A16z", r.text)

    def test_brand_page_shows_unified_scan_history(self):
        source_run_id = 789
        self._seed_ready_run("histco", composite=65.0, days_ago=2)
        self._seed_ready_scan(
            "histco",
            magnetism_score=83,
            coherence_score=72,
            days_ago=1,
            source_run_id=source_run_id,
        )
        sv9_id = self._seed_sv9_scan(source_run_id, "histco")

        r = self.client.get("/brand/histco")

        self.assertEqual(r.status_code, 200)
        self.assertIn("Histco", r.text)
        self.assertIn("audit", r.text)
        self.assertIn("magnetism", r.text)
        self.assertIn("sv9", r.text)
        self.assertIn(f"/sv9/scan/{sv9_id}?lang=es", r.text)
        self.assertIn("/magnetism-scanner/scan/", r.text)
        self.assertIn("/r/tok-histco", r.text)

    def test_brand_page_renders_generated_profile_from_evidence(self):
        token = self._seed_ready_run("profileco", composite=65.0)
        with sqlite3.connect(self.db) as conn:
            run_id = int(
                conn.execute(
                    "SELECT run_id FROM web_requests WHERE token = ?",
                    (token,),
                ).fetchone()[0]
            )
            conn.execute(
                "INSERT INTO raw_inputs (run_id, source, payload_json, created_at) VALUES (?, ?, ?, datetime('now'))",
                (
                    run_id,
                    "web",
                    json.dumps(
                        {
                            "url": "https://profileco.com",
                            "html": (
                                '<link rel="apple-touch-icon" href="/apple-touch-icon.png">'
                                '<a href="https://www.linkedin.com/company/profileco">LinkedIn</a>'
                                '<a href="https://x.com/intent/user?screen_name=profileco">X</a>'
                            ),
                        }
                    ),
                ),
            )
            conn.commit()
        sv9_id = self._seed_sv9_scan(run_id, "profileco")

        r = self.client.get("/brand/profileco")

        self.assertEqual(r.status_code, 200)
        self.assertIn("business_model", r.text)
        self.assertIn("sin clasificar", r.text)
        self.assertIn('href="https://profileco.com"', r.text)
        self.assertIn('src="https://profileco.com/apple-touch-icon.png"', r.text)
        self.assertNotIn("logo=brand_profile", r.text)
        self.assertIn("LinkedIn", r.text)
        self.assertIn('href="https://x.com/profileco"', r.text)
        self.assertIn("capa_visual", r.text)
        self.assertIn("moodboard.js", r.text)
        self.assertIn("https://profileco.com/apple-touch-icon.png", r.text)
        self.assertIn(f"/sv9/scan/{sv9_id}?lang=es", r.text)
        self.assertIn("ver SV9", r.text)

    def test_brand_page_ignores_social_links_not_found_in_owned_html(self):
        token = self._seed_ready_run("wronglinks", composite=65.0)
        with sqlite3.connect(self.db) as conn:
            run_id = int(
                conn.execute(
                    "SELECT run_id FROM web_requests WHERE token = ?",
                    (token,),
                ).fetchone()[0]
            )
            conn.execute(
                "INSERT INTO raw_inputs (run_id, source, payload_json, created_at) VALUES (?, ?, ?, datetime('now'))",
                (
                    run_id,
                    "web",
                    json.dumps(
                        {
                            "url": "https://wronglinks.com",
                            "html": (
                                "<main>"
                                '<a href="https://www.linkedin.com/posts/unrelatedco-launch">Post</a>'
                                '<a href="https://www.instagram.com/reel/abc123">Reel</a>'
                                "</main>"
                            ),
                            "markdown_content": (
                                "Search candidate: https://linkedin.com/company/unrelatedco "
                                "and generated handle https://x.com/wwwwronglinkscom"
                            ),
                        }
                    ),
                ),
            )
            conn.commit()

        r = self.client.get("/brand/wronglinks")

        self.assertEqual(r.status_code, 200)
        self.assertIn("sin perfiles oficiales detectados", r.text)

        payload = self.client.get("/api/brands/wronglinks.com/profile")
        self.assertEqual(payload.status_code, 200)
        self.assertEqual(payload.json()["profile"]["social_links"], [])

    def test_brand_page_renders_visual_signature_scan_when_available(self):
        token = self._seed_ready_run("visualco", composite=65.0)
        with sqlite3.connect(self.db) as conn:
            run_id = int(
                conn.execute(
                    "SELECT run_id FROM web_requests WHERE token = ?",
                    (token,),
                ).fetchone()[0]
            )
            conn.execute(
                "INSERT INTO raw_inputs (run_id, source, payload_json, created_at) VALUES (?, ?, ?, datetime('now'))",
                (
                    run_id,
                    "visual_signature",
                    json.dumps(
                        {
                            "schema_version": "visual-signature-persistence-1",
                            "visual_signature_scan": {
                                "schema_version": "visual-signature-scan-v1",
                                "brand_name": "VisualCo",
                                "website_url": "https://visualco.com",
                                "status": "review_required",
                                "score": 73.5,
                                "dimensions": {
                                    "capture_quality": {"score": 62.8},
                                    "identity_clarity": {"score": 75.3},
                                },
                                "capture": {
                                    "available": True,
                                    "type": "viewport",
                                    "obstruction": {"present": True, "type": "cookie_banner"},
                                },
                                "evidence": [
                                    {
                                        "key": "capture",
                                        "text": "Viewport screenshot available for visual evaluation.",
                                        "polarity": "positive",
                                    }
                                ],
                                "limitations": ["first_viewport_obstructed"],
                            },
                        }
                    ),
                ),
            )
            conn.commit()

        r = self.client.get("/brand/visualco")
        self.assertEqual(r.status_code, 200)
        self.assertIn("visual_signature", r.text)
        self.assertIn("73.5", r.text)
        self.assertIn("cookie_banner", r.text)

        payload = self.client.get("/api/brands/visualco.com/profile")
        self.assertEqual(payload.status_code, 200)
        scan = payload.json()["profile"]["visual_signature_scan"]
        self.assertTrue(scan["available"])
        self.assertEqual(scan["schema_version"], "visual-signature-scan-v1")
        self.assertEqual(scan["score"], 73.5)

    def test_brand_profile_cache_reuses_generated_profile(self):
        self._seed_ready_run("cacheco", composite=65.0)
        import web.observatory_index as observatory_index

        original = observatory_index.build_recommended_research_pack
        calls = 0

        def counting_builder(snapshot):
            nonlocal calls
            calls += 1
            return original(snapshot)

        observatory_index.build_recommended_research_pack = counting_builder
        try:
            first = self.client.get("/brand/cacheco")
            second = self.client.get("/brand/cacheco")
        finally:
            observatory_index.build_recommended_research_pack = original

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(calls, 1)
        with sqlite3.connect(self.db) as conn:
            row = conn.execute(
                "SELECT schema_version, profile_json FROM brand_profile_cache WHERE brand_key = ?",
                ("cacheco.com",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "brand-profile-cache-v4")
        self.assertIn("cacheco.com", row[1])

    def test_brand_profile_cache_invalidates_when_run_evidence_changes(self):
        token = self._seed_ready_run("cachechange", composite=65.0)
        with sqlite3.connect(self.db) as conn:
            run_id = int(
                conn.execute(
                    "SELECT run_id FROM web_requests WHERE token = ?",
                    (token,),
                ).fetchone()[0]
            )

        first = self.client.get("/brand/cachechange")
        self.assertEqual(first.status_code, 200)
        with sqlite3.connect(self.db) as conn:
            before = conn.execute(
                "SELECT source_fingerprint FROM brand_profile_cache WHERE brand_key = ?",
                ("cachechange.com",),
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO raw_inputs (run_id, source, payload_json, created_at) VALUES (?, ?, ?, datetime('now'))",
                (
                    run_id,
                    "web",
                    json.dumps({"url": "https://cachechange.com", "html": "changed evidence"}),
                ),
            )
            conn.commit()

        import web.observatory_index as observatory_index

        original = observatory_index.build_recommended_research_pack
        calls = 0

        def counting_builder(snapshot):
            nonlocal calls
            calls += 1
            return original(snapshot)

        observatory_index.build_recommended_research_pack = counting_builder
        try:
            second = self.client.get("/brand/cachechange")
        finally:
            observatory_index.build_recommended_research_pack = original

        self.assertEqual(second.status_code, 200)
        self.assertEqual(calls, 1)
        with sqlite3.connect(self.db) as conn:
            after = conn.execute(
                "SELECT source_fingerprint FROM brand_profile_cache WHERE brand_key = ?",
                ("cachechange.com",),
            ).fetchone()[0]
        self.assertNotEqual(before, after)

    def test_brand_profile_edit_requires_team_and_applies_overrides(self):
        self._seed_ready_run("editco", composite=65.0)

        locked = self.client.get("/brand/editco.com/edit")
        self.assertEqual(locked.status_code, 403)
        public_before = self.client.get("/brand/editco.com")
        self.assertEqual(public_before.status_code, 200)
        self.assertNotIn("editar</a>", public_before.text)

        unlocked = self.client.get(
            "/team/unlock", params={"token": "team"}, follow_redirects=False
        )
        self.assertEqual(unlocked.status_code, 303)
        form = self.client.get("/brand/editco.com/edit")
        self.assertEqual(form.status_code, 200)
        self.assertIn("edición_ficha", form.text)

        saved = self.client.post(
            "/brand/editco.com/edit",
            data={
                "name": "EditCo Manual",
                "domain": "editco.com",
                "canonical_url": "https://editco.com",
                "logo_url": "https://editco.com/logo.png",
                "category": "Fintech",
                "summary": "Ficha corregida manualmente.",
                "offer": "Plataforma financiera para equipos.",
                "audience": "Finance teams",
                "outcome": "Mejor control de tesorería.",
                "official_links": "https://editco.com\nhttps://editco.com/pricing",
                "social_links": "https://linkedin.com/company/editco",
                "updated_by": "sergio",
            },
            follow_redirects=False,
        )
        self.assertEqual(saved.status_code, 303)
        self.assertEqual(saved.headers["location"], "/brand/editco.com?lang=es")

        page = self.client.get("/brand/editco.com")
        self.assertEqual(page.status_code, 200)
        self.assertIn("EditCo Manual", page.text)
        self.assertIn("Ficha corregida manualmente.", page.text)
        self.assertIn('src="https://editco.com/logo.png"', page.text)
        self.assertIn("Fintech", page.text)
        self.assertIn("https://editco.com/pricing", page.text)
        self.assertIn("LinkedIn", page.text)
        self.assertIn("editar</a>", page.text)

        with sqlite3.connect(self.db) as conn:
            row = conn.execute(
                "SELECT display_name, logo_url, profile_overrides_json FROM brand_profiles WHERE brand_key = ?",
                ("editco.com",),
            ).fetchone()
        self.assertEqual(row[0], "EditCo Manual")
        self.assertEqual(row[1], "https://editco.com/logo.png")
        self.assertIn("Ficha corregida manualmente.", row[2])

    def test_brand_profile_api_patch_requires_team_and_applies_partial_overrides(self):
        self._seed_ready_run("apieditco", composite=65.0)

        profile = self.client.get("/api/brands/apieditco.com/profile")
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["brand_key"], "apieditco.com")
        self.assertIn("profile", profile.json())
        self.assertIn("scans", profile.json())

        locked = self.client.patch(
            "/api/brands/apieditco.com/profile",
            json={"summary": "No deberia guardarse."},
        )
        self.assertEqual(locked.status_code, 403)

        saved = self.client.patch(
            "/api/brands/apieditco.com/profile",
            headers={"x-brand3-team-token": "team"},
            json={
                "name": "API EditCo",
                "summary": "Ficha editada desde API.",
                "logo_url": "https://apieditco.com/logo.png",
                "official_links": ["https://apieditco.com", "https://apieditco.com/pricing"],
                "updated_by": "api",
            },
        )
        self.assertEqual(saved.status_code, 200)
        payload = saved.json()
        self.assertEqual(payload["brand_key"], "apieditco.com")
        self.assertEqual(payload["profile"]["name"], "API EditCo")
        self.assertEqual(payload["profile"]["summary"], "Ficha editada desde API.")
        self.assertEqual(payload["profile"]["logo_url"], "https://apieditco.com/logo.png")
        self.assertIn("https://apieditco.com/pricing", payload["profile"]["official_links"])

        page = self.client.get("/brand/apieditco.com")
        self.assertEqual(page.status_code, 200)
        self.assertIn("API EditCo", page.text)
        self.assertIn("Ficha editada desde API.", page.text)

    def test_brand_market_classification_api_exposes_taxonomy_and_persists_controlled_tags(self):
        self._seed_ready_run("apitaxoco", composite=65.0)

        taxonomy = self.client.get("/api/brands/market-taxonomy")
        self.assertEqual(taxonomy.status_code, 200)
        self.assertIn("business_model", taxonomy.json()["groups"])
        self.assertTrue(
            any(
                item["tag"] == "SaaS"
                for item in taxonomy.json()["groups"]["business_model"]
            )
        )

        locked = self.client.patch(
            "/api/brands/apitaxoco.com/market-classification",
            json={"business_model": ["B2B"]},
        )
        self.assertEqual(locked.status_code, 403)

        saved = self.client.patch(
            "/api/brands/apitaxoco.com/market-classification",
            headers={"authorization": "Bearer team"},
            json={
                "business_model": ["B2B", "SaaS"],
                "sector_industry": ["fintech"],
                "technology_capability": ["API", "not controlled"],
                "primary_category": "fintech",
                "updated_by": "api",
            },
        )
        self.assertEqual(saved.status_code, 200)
        market = saved.json()["market_classification"]
        self.assertEqual(market["primary_category"], "fintech")
        self.assertEqual(market["accepted"]["business_model"], ["B2B", "SaaS"])
        self.assertEqual(market["accepted"]["technology_capability"], ["API"])
        self.assertNotIn("not controlled", market["accepted"]["technology_capability"])

        partial = self.client.patch(
            "/api/brands/apitaxoco.com/market-classification",
            headers={"x-brand3-team-token": "team"},
            json={"market_signals": ["public customer logos"]},
        )
        self.assertEqual(partial.status_code, 200)
        partial_market = partial.json()["market_classification"]
        self.assertEqual(partial_market["accepted"]["business_model"], ["B2B", "SaaS"])
        self.assertEqual(partial_market["accepted"]["market_signals"], ["public customer logos"])

    def test_llm_openapi_exposes_scanner_and_brand_tools(self):
        response = self.client.get("/api/llm/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/v1/scanner", paths)
        self.assertIn("/api/v1/scanner/{scan_id}/evidence", paths)
        self.assertIn("/api/brands/{domain}/profile", paths)
        self.assertIn("/api/brands/{domain}/market-classification", paths)

    def test_brand_market_classification_edit_persists_controlled_tags(self):
        self._seed_ready_run("taxoco", composite=65.0)
        unlocked = self.client.get(
            "/team/unlock", params={"token": "team"}, follow_redirects=False
        )
        self.assertEqual(unlocked.status_code, 303)

        form = self.client.get("/brand/taxoco.com/edit")
        self.assertEqual(form.status_code, 200)
        self.assertIn("business_model", form.text)
        self.assertIn("technology_capability", form.text)

        saved = self.client.post(
            "/brand/taxoco.com/market-classification",
            data={
                "business_model": ["B2B", "SaaS"],
                "sector_industry": ["fintech"],
                "technology_capability": ["API", "not a controlled tag"],
                "primary_category": "fintech",
                "updated_by": "sergio",
            },
            follow_redirects=False,
        )
        self.assertEqual(saved.status_code, 303)
        self.assertEqual(saved.headers["location"], "/brand/taxoco.com?lang=es")

        page = self.client.get("/brand/taxoco.com")
        self.assertEqual(page.status_code, 200)
        self.assertIn("clasificación_mercado", page.text)
        self.assertIn("fintech", page.text)
        self.assertIn("B2B", page.text)
        self.assertIn("SaaS", page.text)
        self.assertIn("API", page.text)
        self.assertNotIn("not a controlled tag", page.text)

        with sqlite3.connect(self.db) as conn:
            payload = json.loads(
                conn.execute(
                    "SELECT classification_json FROM brand_market_classifications WHERE brand_key = ?",
                    ("taxoco.com",),
                ).fetchone()[0]
            )
        self.assertEqual(payload["primary_category"], "fintech")
        self.assertEqual(payload["accepted"]["business_model"], ["B2B", "SaaS"])
        self.assertEqual(payload["accepted"]["technology_capability"], ["API"])
        self.assertFalse(payload["requires_human_review"])

    def test_reports_filter_by_query(self):
        self._seed_ready_run("airbnb", composite=65.0)
        self._seed_ready_run("uber", composite=72.0)
        r = self.client.get("/reports?q=air")
        self.assertEqual(r.status_code, 200)
        self.assertIn(">Airbnb<", r.text)
        self.assertNotIn(">Uber<", r.text)

    def test_reports_sort_score_desc(self):
        self._seed_ready_run("low", composite=40.0, days_ago=1)
        self._seed_ready_run("high", composite=90.0, days_ago=2)
        r = self.client.get("/reports?sort=score_desc")
        self.assertEqual(r.status_code, 200)
        idx_high = r.text.find(">High<")
        idx_low = r.text.find(">LOW<")
        self.assertGreater(idx_low, idx_high)  # high appears before low

    def test_reports_preserves_ui_language_and_links(self):
        self._seed_ready_run("langco", composite=77.0)
        r = self.client.get("/reports?lang=en")
        self.assertEqual(r.status_code, 200)
        self.assertIn('<html lang="en">', r.text)
        self.assertIn('href="/r/tok-langco', r.text)
        self.assertIn("?lang=en", r.text)
        self.assertIn('lang=en', r.text)

    def test_reports_advanced_observatory_includes_scanners(self):
        self._seed_ready_run("auditco", composite=66.0)
        self._seed_ready_scan("linear", magnetism_score=83, coherence_score=72)

        r = self.client.get("/reports")

        self.assertEqual(r.status_code, 200)
        self.assertIn("observatorio_avanzado", r.text)
        self.assertIn(">Auditco<", r.text)
        self.assertIn(">Linear<", r.text)
        self.assertIn("/magnetism-scanner/scan/", r.text)
        self.assertIn("magnetism", r.text)

    def test_grouped_listing_links_brand_to_full_history(self):
        self._seed_ready_run("histco", composite=66.0)
        self._seed_ready_scan("histco", magnetism_score=83, coherence_score=72)

        r = self.client.get("/reports")

        self.assertEqual(r.status_code, 200)
        self.assertIn('href="/brand/histco.com?lang=es">Histco</a>', r.text)
        self.assertIn('href="/brand/histco.com?lang=es">2</a>', r.text)

    def test_taken_down_row_is_hidden(self):
        self._seed_ready_run("hidden", composite=50.0, takedown=1)
        r = self.client.get("/reports")
        self.assertNotIn(">Hidden<", r.text)
        r2 = self.client.get("/brand/hidden")
        self.assertNotIn("view</a>", r2.text)

    def test_non_public_row_is_hidden(self):
        self._seed_ready_run("privateco", composite=50.0, is_public=0)
        r = self.client.get("/reports")
        self.assertNotIn(">Privateco<", r.text)


if __name__ == "__main__":
    unittest.main()
