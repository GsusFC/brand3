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
            "evidence_summary": {"total": 3},
            "trust_summary": {"overall_status": "good", "overall_status_label": "bueno"},
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
        self.assertEqual(response.json()["evidence_summary"]["total"], 3)
        self.assertEqual(response.json()["trust_summary"]["overall_status"], "good")

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
                [
                    {
                        "source": "context",
                        "quote": "robots.txt found",
                        "dimension_name": "presencia",
                        "confidence": 0.7,
                    },
                    {
                        "source": "exa",
                        "quote": "positive mention found",
                        "dimension_name": "percepcion",
                        "confidence": 0.6,
                    },
                ],
            )
            store.close()

            client = TestClient(app)
            with patch("src.api.app.BRAND3_DB_PATH", str(db_path)):
                response = client.get(f"/api/runs/{run_id}/evidence")
                filtered = client.get(f"/api/runs/{run_id}/evidence?dimension=presencia&source=context")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["quote"], "robots.txt found")
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(len(filtered.json()), 1)
        self.assertEqual(filtered.json()[0]["dimension_name"], "presencia")
        self.assertEqual(filtered.json()[0]["source"], "context")

    def test_run_evidence_summary_endpoint_returns_snapshot_summary(self):
        from fastapi.testclient import TestClient
        from src.api.app import app
        from src.storage.sqlite_store import SQLiteStore
        from src.models.brand import FeatureValue

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)
            store.save_features(
                run_id,
                {
                    "presencia": {
                        "web_presence": FeatureValue(
                            "web_presence",
                            80.0,
                            raw_value={"evidence_snippet": "homepage reachable"},
                            confidence=0.9,
                            source="web_scrape",
                        )
                    }
                },
            )
            store.save_evidence_items(
                run_id,
                [{"source": "context", "quote": "robots.txt found", "dimension_name": "presencia", "confidence": 0.7}],
            )
            store.close()

            client = TestClient(app)
            with patch("src.services.brand_service.BRAND3_DB_PATH", str(db_path)):
                response = client.get(f"/api/runs/{run_id}/evidence-summary")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 2)
        self.assertEqual(response.json()["by_dimension"]["presencia"], 2)
        self.assertEqual(response.json()["by_source"]["context"], 1)

    def test_run_evidence_summary_endpoint_404s_for_missing_run(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        with patch("src.api.app.brand_service.run_evidence_summary", side_effect=ValueError("Run 999 not found")):
            response = client.get("/api/runs/999/evidence-summary")

        self.assertEqual(response.status_code, 404)

    def test_run_dimension_confidence_endpoint_returns_snapshot_summary(self):
        from fastapi.testclient import TestClient
        from src.api.app import app
        from src.storage.sqlite_store import SQLiteStore
        from src.models.brand import FeatureValue

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)
            store.save_features(
                run_id,
                {
                    "presencia": {
                        "web_presence": FeatureValue(
                            "web_presence",
                            80.0,
                            raw_value={"evidence_snippet": "homepage reachable"},
                            confidence=0.9,
                            source="web_scrape",
                        )
                    }
                },
            )
            store.save_evidence_items(
                run_id,
                [{"source": "context", "quote": "robots.txt found", "dimension_name": "presencia", "confidence": 0.7}],
            )
            store.close()

            client = TestClient(app)
            with patch("src.services.brand_service.BRAND3_DB_PATH", str(db_path)):
                response = client.get(f"/api/runs/{run_id}/dimension-confidence")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["presencia"]["status"], "insufficient_data")
        self.assertIn("social_footprint", response.json()["presencia"]["missing_signals"])

    def test_run_dimension_confidence_endpoint_404s_for_missing_run(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        with patch("src.api.app.brand_service.run_dimension_confidence", side_effect=ValueError("Run 999 not found")):
            response = client.get("/api/runs/999/dimension-confidence")

        self.assertEqual(response.status_code, 404)

    def test_run_trust_summary_endpoint_combines_trust_signals(self):
        from fastapi.testclient import TestClient
        from src.api.app import app
        from src.storage.sqlite_store import SQLiteStore
        from src.models.brand import FeatureValue
        from src.collectors.context_collector import ContextData

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            brand_id = store.upsert_brand("Example", "https://example.com")
            run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)
            store.save_raw_input(
                run_id,
                "context",
                ContextData(url="https://example.com", coverage=0.8, confidence=0.85, context_score=80),
            )
            store.save_features(
                run_id,
                {
                    "presencia": {
                        "web_presence": FeatureValue(
                            "web_presence",
                            80.0,
                            raw_value={"evidence_snippet": "homepage reachable"},
                            confidence=0.9,
                            source="web_scrape",
                        )
                    }
                },
            )
            store.save_evidence_items(
                run_id,
                [{"source": "context", "quote": "robots.txt found", "dimension_name": "presencia", "confidence": 0.7}],
            )
            store.close()

            client = TestClient(app)
            with patch("src.services.brand_service.BRAND3_DB_PATH", str(db_path)):
                response = client.get(f"/api/runs/{run_id}/trust-summary")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["run_id"], run_id)
        self.assertEqual(payload["overall_status"], "insufficient_data")
        self.assertEqual(payload["overall_status_label"], "datos insuficientes")
        self.assertEqual(payload["overall_reason"], "multiple_dimensions_insufficient")
        self.assertEqual(payload["overall_reason_label"], "multiples dimensiones con datos insuficientes")
        self.assertEqual(payload["trust_summary"]["overall_status"], "insufficient_data")
        self.assertEqual(payload["trust_summary"]["context"]["status"], "good")
        self.assertEqual(payload["trust_summary"]["evidence"]["total"], 2)
        self.assertEqual(payload["context_readiness"]["status"], "good")
        self.assertEqual(payload["context_readiness"]["coverage_label"], "alta")
        self.assertEqual(payload["context_readiness"]["confidence_label"], "alta")
        self.assertEqual(payload["evidence_summary"]["total"], 2)
        self.assertEqual(payload["dimension_confidence"]["presencia"]["status"], "insufficient_data")
        self.assertEqual(payload["dimension_status_counts"]["insufficient_data"], 5)

    def test_run_trust_summary_endpoint_404s_for_missing_run(self):
        from fastapi.testclient import TestClient
        from src.api.app import app

        client = TestClient(app)
        with patch("src.api.app.brand_service.run_trust_summary", side_effect=ValueError("Run 999 not found")):
            response = client.get("/api/runs/999/trust-summary")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
