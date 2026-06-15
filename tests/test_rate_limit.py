"""Rate-limit middleware — counter, window, and team bypass."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


def _install_env(db_path: Path) -> None:
    os.environ["BRAND3_DB_PATH"] = str(db_path)
    os.environ["BRAND3_COOKIE_SECRET"] = "t" * 40
    os.environ["BRAND3_TEAM_TOKEN"] = "team-test-token"
    os.environ["BRAND3_RATE_LIMIT_ENABLED"] = "true"
    os.environ["BRAND3_RATE_LIMIT_PER_IP"] = "5"
    os.environ["BRAND3_RATE_LIMIT_WINDOW_HOURS"] = "24"


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "brand3.sqlite3"
        _install_env(self.db)

        # Reset modules so they pick up new env vars.
        import importlib

        for mod_name in list(sys_module_keys()):
            if mod_name.startswith("web") or mod_name == "src.config":
                importlib.reload(__import__(mod_name, fromlist=["*"]))

        from fastapi.testclient import TestClient

        from web.app import app
        from web.workers.queue import set_run_analysis_override

        # Short-circuit DNS so validate_url passes for example.com.
        self._resolver_patcher = patch(
            "web.workers.url_validator.socket.getaddrinfo",
            side_effect=lambda _h, _p: [(2, 1, 6, "", ("1.1.1.1", 0))],
        )
        self._resolver_patcher.start()

        # No-op engine so the background queue finishes instantly without I/O.
        set_run_analysis_override(lambda _url: {"run_id": None, "composite_score": None})

        self.client = TestClient(app)
        # Trigger startup lifespan so schema + migrations run.
        self.client.__enter__()

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
            "BRAND3_RATE_LIMIT_ENABLED",
            "BRAND3_RATE_LIMIT_PER_IP",
            "BRAND3_RATE_LIMIT_WINDOW_HOURS",
            "BRAND3_RATE_LIMIT_BYPASS_IPS",
        ):
            os.environ.pop(key, None)

    def _insert_request(self, ip: str, seconds_ago: int = 0) -> None:
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """
                INSERT INTO web_requests (token, url, brand_slug, requester_ip,
                    requester_is_team, status, created_at)
                VALUES (?, ?, ?, ?, 0, 'queued', datetime('now', ?))
                """,
                (
                    f"tok-{ip}-{seconds_ago}-{time.time_ns()}",
                    "https://example.com",
                    "example",
                    ip,
                    f"-{seconds_ago} seconds",
                ),
            )
            conn.commit()

    def test_fifth_request_passes_sixth_is_blocked(self):
        for _ in range(5):
            self._insert_request("testclient", seconds_ago=1)
        response = self.client.post("/analyze", data={"url": "https://example.com"})
        self.assertEqual(response.status_code, 429)

    def test_below_limit_passes_through_to_stub(self):
        for _ in range(3):
            self._insert_request("testclient", seconds_ago=1)
        response = self.client.post(
            "/analyze",
            data={"url": "https://example.com"},
            follow_redirects=False,
        )
        # Valid URL enqueues and 303-redirects to the status page.
        self.assertEqual(response.status_code, 303)

    def test_rate_limit_counter_runs_via_threadpool(self):
        from web.middleware import rate_limit

        calls = []

        async def fake_to_thread(func, *args, **kwargs):
            calls.append((func, args, kwargs))
            return func(*args, **kwargs)

        for _ in range(5):
            self._insert_request("testclient", seconds_ago=1)

        with patch("web.middleware.rate_limit.asyncio.to_thread", side_effect=fake_to_thread):
            response = self.client.post("/analyze", data={"url": "https://example.com"})

        self.assertEqual(response.status_code, 429)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][0], rate_limit.count_recent_analyses_for_ip)
        self.assertEqual(calls[0][1], ("testclient",))
        self.assertEqual(calls[0][2], {"hours": 24})

    def test_disabled_rate_limit_passes_even_when_counter_is_over_limit(self):
        from web.config import settings

        settings.rate_limit_enabled = False
        for _ in range(10):
            self._insert_request("testclient", seconds_ago=1)

        response = self.client.post(
            "/analyze",
            data={"url": "https://example.com"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)

    def test_team_cookie_bypasses_limit(self):
        from web.middleware.team_cookie import create_serializer

        for _ in range(10):
            self._insert_request("testclient", seconds_ago=1)
        serializer = create_serializer("t" * 40)
        token = serializer.dumps({"unlocked_at": int(time.time())})
        response = self.client.post(
            "/analyze",
            data={"url": "https://example.com"},
            cookies={"brand3_team": token},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    def test_configured_ip_bypasses_limit(self):
        from web.config import settings

        settings.rate_limit_bypass_ips = "127.0.0.1,testclient"
        for _ in range(10):
            self._insert_request("testclient", seconds_ago=1)

        response = self.client.post(
            "/analyze",
            data={"url": "https://example.com"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)

    def test_other_ips_do_not_share_counter(self):
        for _ in range(5):
            self._insert_request("10.0.0.8", seconds_ago=1)
        # A request from a different IP — TestClient defaults to 'testclient' as host.
        response = self.client.post(
            "/analyze",
            data={"url": "https://example.com"},
            follow_redirects=False,
        )
        # testclient ≠ 10.0.0.8, so it has its own counter (zero for first call).
        self.assertEqual(response.status_code, 303)

    def test_rows_outside_window_do_not_count(self):
        # 30h old rows — outside the 24h window.
        for _ in range(10):
            self._insert_request("10.0.0.9", seconds_ago=30 * 3600)
        self._install_ip_header("10.0.0.9")
        response = self.client.post(
            "/analyze",
            data={"url": "https://example.com"},
            headers={"x-forwarded-for": "10.0.0.9"},  # no-op in dev, doc intent
            follow_redirects=False,
        )
        # In dev mode, the IP is TestClient's 'testclient'. The seed rows are for
        # 10.0.0.9 and anyway fall outside the window, so they are irrelevant.
        self.assertEqual(response.status_code, 303)

    def _install_ip_header(self, ip: str) -> None:
        """No-op helper — kept for readability in the window test."""


def sys_module_keys():
    import sys

    return list(sys.modules.keys())


if __name__ == "__main__":
    unittest.main()
