"""Phase 6 — /_health endpoint + JSON logging smoke."""

from __future__ import annotations

import importlib
import io
import json
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path


def _install_env(db_path: Path) -> None:
    os.environ["BRAND3_DB_PATH"] = str(db_path)
    os.environ["BRAND3_COOKIE_SECRET"] = "t" * 40
    os.environ["BRAND3_TEAM_TOKEN"] = "team"
    os.environ["BRAND3_MAX_CONCURRENT_ANALYSES"] = "1"


class HealthTests(unittest.TestCase):
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

    def test_health_returns_ok_shape(self):
        r = self.client.get("/_health")
        self.assertEqual(r.status_code, 200)
        payload = r.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIsInstance(payload["queue_size"], int)
        self.assertIsInstance(payload["running"], int)
        self.assertEqual(set(payload.keys()), {"status", "queue_size", "running"})

    def test_health_fields_survive_serialization(self):
        r = self.client.get("/_health")
        # Idempotent: calling twice must not change the shape.
        payload_a = r.json()
        payload_b = self.client.get("/_health").json()
        self.assertEqual(set(payload_a.keys()), set(payload_b.keys()))

    def test_health_does_not_depend_on_db_probe(self):
        from unittest.mock import patch

        from web.routes import health as health_route

        with patch.object(health_route, "get_queue") as get_queue:
            get_queue.return_value.stats.return_value.queued = 3
            get_queue.return_value.stats.return_value.running = 1
            r = self.client.get("/_health")

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok", "queue_size": 3, "running": 1})


class JsonFormatterTests(unittest.TestCase):
    def test_formatter_emits_valid_json_with_extras(self):
        from web.logging_setup import JsonFormatter

        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(JsonFormatter())
        log = logging.getLogger("brand3.test.json")
        log.handlers.clear()
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        log.info("request", extra={"method": "GET", "status": 200, "duration_ms": 12})
        line = buf.getvalue().strip()
        payload = json.loads(line)
        self.assertEqual(payload["msg"], "request")
        self.assertEqual(payload["level"], "info")
        self.assertEqual(payload["logger"], "brand3.test.json")
        self.assertEqual(payload["extra"]["method"], "GET")
        self.assertEqual(payload["extra"]["status"], 200)


if __name__ == "__main__":
    unittest.main()
