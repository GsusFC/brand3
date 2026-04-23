import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


FASTAPI_AVAILABLE = bool(importlib.util.find_spec("fastapi")) and bool(importlib.util.find_spec("starlette"))


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi not installed")
class ApiTests(unittest.TestCase):
    def test_health_endpoint_returns_ok(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_runs_endpoint_delegates_to_service(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        expected = [{"id": 1, "brand_name": "Example"}]
        with patch("src.api.app.brand_service.list_runs", return_value=expected):
            response = client.get("/api/runs", params={"brand_name": "Example", "limit": 5})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_brands_endpoint_delegates_to_service(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        expected = [{"brand_name": "Stripe", "brand_profile": {"domain": "stripe.com"}}]
        with patch("src.api.app.brand_service.list_brands", return_value=expected):
            response = client.get("/api/brands", params={"limit": 10})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_profiles_endpoint_delegates_to_service(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        expected = [{"profile_id": "base", "label": "Base"}]
        with patch("src.api.app.brand_service.list_profiles", return_value=expected):
            response = client.get("/api/profiles")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_analyze_rejects_invalid_url_before_service_call(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        with patch("src.api.app.brand_service.run") as run_mock:
            response = client.post("/api/analyze", json={"url": "http://127.0.0.1"})

        self.assertEqual(response.status_code, 400)
        run_mock.assert_not_called()

    def test_analyze_response_includes_context_fields(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        payload = {
            "brand": "Example",
            "brand_profile": {"name": "Example"},
            "url": "https://example.com",
            "run_id": 1,
            "niche_classification": {},
            "calibration_profile": "base",
            "profile_source": "fallback",
            "data_quality": "good",
            "data_sources": {},
            "context_readiness": {"context_score": 82},
            "confidence_summary": {"status": "good", "coverage": 0.8},
            "dimension_confidence": {"presencia": {"status": "good", "confidence": 0.8}},
            "composite_score": 70.0,
            "composite_reliable": True,
            "partial_score": False,
            "partial_dimensions": [],
            "dimensions": {},
            "llm_used": False,
            "social_scraped": False,
            "audit": {},
            "timestamp": "2026-04-24T00:00:00",
        }

        client = TestClient(app)
        with patch("src.api.app.validate_url", return_value=(True, "https://example.com")):
            with patch("src.api.app.brand_service.run", return_value=payload):
                response = client.post("/api/analyze", json={"url": "https://example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["context_readiness"]["context_score"], 82)
        self.assertEqual(response.json()["confidence_summary"]["status"], "good")
        self.assertEqual(response.json()["dimension_confidence"]["presencia"]["status"], "good")

    def test_run_evidence_endpoint_returns_persisted_evidence(self):
        from fastapi.testclient import TestClient
        from src.api.app import app
        from src.storage.sqlite_store import SQLiteStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)
            store.save_evidence_items(
                run_id,
                [{"source": "context", "quote": "robots.txt found", "confidence": 0.7}],
            )
            store.close()

            client = TestClient(app)
            with patch("src.api.app.BRAND3_DB_PATH", str(db_path)):
                response = client.get(f"/api/runs/{run_id}/evidence")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["quote"], "robots.txt found")


if __name__ == "__main__":
    unittest.main()
