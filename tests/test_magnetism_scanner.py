from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import importlib
import json
import tempfile
import unittest
import unittest.mock
from typing import Any

from src.features.magnetism.extractor import MagnetismExtractor
from src.features.llm_analyzer import LLMAnalyzer
from src.storage.sqlite_store import SQLiteStore


def _install_env(db_path: Path) -> None:
    os.environ["BRAND3_DB_PATH"] = str(db_path)
    os.environ["BRAND3_COOKIE_SECRET"] = "t" * 40
    os.environ["BRAND3_TEAM_TOKEN"] = "team"
    os.environ["BRAND3_MAX_CONCURRENT_ANALYSES"] = "1"


class FakeLLMAnalyzer:
    """Mock for LLMAnalyzer."""

    def __init__(self, api_key: str | None = "fake-key"):
        self.api_key = api_key
        self.captured_system = None
        self.captured_user = None
        self.mock_response: dict[str, Any] = {}

    def _call_json(self, system: str, user: str, max_tokens: int = 8000) -> dict[str, Any]:
        self.captured_system = system
        self.captured_user = user
        return self.mock_response


class MagnetismScannerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "brand3.sqlite3"
        _install_env(self.db)

        # Run ensure_schema to apply migrations
        store = SQLiteStore(str(self.db))
        store.close()

        for mod_name in list(sys.modules):
            if mod_name.startswith("web") or mod_name == "src.config":
                importlib.reload(sys.modules[mod_name])

        from fastapi.testclient import TestClient
        from web.app import app

        self.client = TestClient(app)
        self.client.__enter__()

        # Mock _take_playwright_screenshot to avoid slow real browser runs
        self.screenshot_mock = unittest.mock.patch(
            "src.services.brand_service._take_playwright_screenshot",
            return_value={
                "screenshot_url": "file:///tmp/mock-brand3-shot.png",
                "screenshot_path": "/tmp/mock-brand3-shot.png",
                "screenshot_provider": "playwright",
            }
        )
        self.mock_screenshot_fn = self.screenshot_mock.start()

    def _unlock_team_cookie(self) -> None:
        from web.middleware.team_cookie import COOKIE_NAME, create_serializer

        token = create_serializer("t" * 40).dumps({"unlocked_at": 1})
        self.client.cookies.set(COOKIE_NAME, token)

    def tearDown(self):
        self.screenshot_mock.stop()
        self.client.__exit__(None, None, None)
        self._tmp.cleanup()
        for key in (
            "BRAND3_DB_PATH",
            "BRAND3_COOKIE_SECRET",
            "BRAND3_TEAM_TOKEN",
            "BRAND3_MAX_CONCURRENT_ANALYSES",
        ):
            os.environ.pop(key, None)

    def test_web_routes_require_team_cookie(self):
        response = self.client.get("/magnetism-scanner")
        self.assertEqual(response.status_code, 403)
        self.assertIn("restricted to FLOC team access", response.text)

        response = self.client.post(
            "/magnetism-scanner/analyze",
            data={"manual_text": "We build developer tools."},
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post("/magnetism-scanner/from-run", data={"run_id": 1})
        self.assertEqual(response.status_code, 403)

        response = self.client.get("/magnetism-scanner/scan/1")
        self.assertEqual(response.status_code, 403)

    def test_database_helpers(self):
        from web.storage import insert_magnetism_scan, get_magnetism_scan, list_magnetism_scans

        payload = {
            "brand_name": "Test Brand",
            "url": "https://testbrand.com",
            "magnetism_score": 88,
            "coherence_score": 92,
            "quadrant": "High Magnetism - High Coherence",
            "executive_headline": "Test headline",
            "observations": ["Obs 1", "Obs 2", "Obs 3"],
            "tldr_grid": {
                "niche": "niche",
                "value_proposition": "vp",
                "target_audience": "audience",
                "friction": "friction",
                "uniqueness": "uniq",
                "primary_cta": "cta",
                "core_promise": "promise",
                "behavioral_hook": "hook",
                "tone": "tone"
            },
            "score_breakdown": {
                "magnetism": {"emotional_appeal": 88, "functional_differentiation": 88, "narrative_gravitas": 88, "assessment": "test"},
                "coherence": {"visual_identity": 92, "tactical_alignment": 92, "message_consistency": 92, "assessment": "test"}
            },
            "magenta_circle": {
                "mindspace": {"status": "detected", "findings": "find", "evidence": []},
                "aetherspace": {"status": "not_detected", "findings": "find", "evidence": []},
                "gamespace": {"status": "not_detected", "findings": "find", "evidence": []},
                "envispace": {"status": "not_detected", "findings": "find", "evidence": []},
                "netspace": {"status": "not_detected", "findings": "find", "evidence": []},
                "tactispace": {"status": "not_detected", "findings": "find", "evidence": []},
                "ambientspace": {"status": "not_detected", "findings": "find", "evidence": []}
            }
        }

        scan_id = insert_magnetism_scan(
            brand_name=payload["brand_name"],
            url=payload["url"],
            magnetism_score=payload["magnetism_score"],
            coherence_score=payload["coherence_score"],
            quadrant=payload["quadrant"],
            raw_payload=json.dumps(payload)
        )

        self.assertGreater(scan_id, 0)

        # get scan
        scan = get_magnetism_scan(scan_id)
        self.assertIsNotNone(scan)
        self.assertEqual(scan["brand_name"], "Test Brand")
        self.assertEqual(scan["magnetism_score"], 88)
        self.assertEqual(scan["coherence_score"], 92)

        # list scans
        scans = list_magnetism_scans(limit=10)
        self.assertEqual(len(scans), 1)
        self.assertEqual(scans[0]["id"], scan_id)

    def test_legacy_scan_detail_is_normalized_for_new_template(self):
        from web.storage import insert_magnetism_scan

        legacy_payload = {
            "brand_name": "Legacy Brand",
            "url": "https://legacy.test",
            "magnetism_score": 48,
            "coherence_score": 56,
            "quadrant": "Low Magnetism - Low Coherence",
            "executive_headline": "Legacy headline",
            "observations": ["Legacy obs 1", "Legacy obs 2", "Legacy obs 3"],
            "tldr_grid": {"niche": "old"},
            "score_breakdown": {"magnetism": {}, "coherence": {}},
            "magenta_circle": {
                "mindspace": {"status": "detected", "findings": "Earn every second", "evidence": ["Earn every second"]},
                "aetherspace": {"status": "not_detected", "findings": "No clear signal detected in the provided sources.", "evidence": []},
                "gamespace": {"status": "not_detected", "findings": "No clear signal detected in the provided sources.", "evidence": []},
                "envispace": {"status": "not_detected", "findings": "No clear signal detected in the provided sources.", "evidence": []},
                "netspace": {"status": "not_detected", "findings": "No clear signal detected in the provided sources.", "evidence": []},
                "tactispace": {"status": "not_detected", "findings": "No clear signal detected in the provided sources.", "evidence": []},
                "ambientspace": {"status": "not_detected", "findings": "No clear signal detected in the provided sources.", "evidence": []},
            },
        }
        scan_id = insert_magnetism_scan(
            brand_name="Legacy Brand",
            url="https://legacy.test",
            magnetism_score=48,
            coherence_score=56,
            quadrant="Low Magnetism - Low Coherence",
            raw_payload=json.dumps(legacy_payload),
        )

        self._unlock_team_cookie()
        response = self.client.get(f"/magnetism-scanner/scan/{scan_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("TLDR Brand3", response.text)
        self.assertIn("Earn every second", response.text)
        self.assertIn("evidence_basis:", response.text)
        self.assertIn("extraction_mode", response.text)
        self.assertIn("unknown", response.text)

    def test_scan_detail_shows_canonical_extraction_mode(self):
        from web.storage import insert_magnetism_scan

        payload = MagnetismExtractor(llm=None).extract_from_audit_snapshot(
            {
                "run": {
                    "id": 303,
                    "brand_name": "Canonical Detail",
                    "url": "https://canonical-detail.test",
                },
                "features": [],
                "raw_inputs": [],
                "evidence_items": [
                    {
                        "source": "context",
                        "url": "https://canonical-detail.test",
                        "quote": (
                            "Canonical Detail is a workflow platform for finance teams "
                            "that helps reduce reconciliation time."
                        ),
                        "feature_name": "positioning",
                        "dimension_name": "coherencia",
                        "confidence": 0.9,
                    }
                ],
            }
        )
        scan_id = insert_magnetism_scan(
            brand_name=payload["brand_name"],
            url=payload["url"],
            magnetism_score=payload["magnetism_score"],
            coherence_score=payload["coherence_score"],
            quadrant=payload["quadrant"],
            raw_payload=json.dumps(payload),
        )

        self._unlock_team_cookie()
        response = self.client.get(f"/magnetism-scanner/scan/{scan_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("extraction_mode", response.text)
        self.assertIn("canonical_snapshot", response.text)
        self.assertIn("canonical_source", response.text)
        self.assertIn("brand_audit_snapshot", response.text)
        self.assertIn("Canonical Brand Audit Snapshot", response.text)
        self.assertNotIn("legacy_extraction", response.text)

    def test_scan_detail_shows_legacy_direct_warning(self):
        from web.storage import insert_magnetism_scan

        payload = MagnetismExtractor(llm=None).extract(
            url=None,
            manual_text="We have a proprietary framework and pricing. API is ready.",
            brand_name="Legacy Detail",
        )
        scan_id = insert_magnetism_scan(
            brand_name=payload["brand_name"],
            url=payload["url"] or "Manual Upload",
            magnetism_score=payload["magnetism_score"],
            coherence_score=payload["coherence_score"],
            quadrant=payload["quadrant"],
            raw_payload=json.dumps(payload),
        )

        self._unlock_team_cookie()
        response = self.client.get(f"/magnetism-scanner/scan/{scan_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("extraction_mode", response.text)
        self.assertIn("legacy_direct", response.text)
        self.assertIn("direct_source", response.text)
        self.assertIn("manual_evidence", response.text)
        self.assertIn("Legacy Direct Extraction", response.text)
        self.assertIn("legacy_extraction", response.text)
        self.assertIn("replacement=extract_from_audit_snapshot", response.text)

    def test_extractor_heuristic_fallback(self):
        extractor = MagnetismExtractor(llm=None)
        
        result = extractor.extract(
            url=None,
            manual_text="We have a proprietary framework and pricing. API is ready. Buy now!",
            brand_name="Heuristic Manual"
        )
        
        self.assertEqual(result["brand_name"], "Heuristic Manual")
        self.assertEqual(result["fallback_used"], True)
        self.assertEqual(result["source"], "direct_magnetism_legacy")
        self.assertEqual(result["extraction_mode"], "legacy_direct")
        self.assertEqual(result["direct_source_provider"], "manual_evidence")
        self.assertIsNone(result["canonical_evidence_source"])
        self.assertEqual(result["deprecation"]["replacement"], "extract_from_audit_snapshot")
        self.assertEqual(result["magenta_circle"]["mindspace"]["status"], "detected")
        self.assertEqual(result["magenta_circle"]["netspace"]["status"], "detected")
        self.assertEqual(result["magenta_circle"]["tactispace"]["status"], "not_detected")
        self.assertEqual(result["magenta_circle"]["gamespace"]["status"], "not_detected")
        self.assertEqual(result["url"], "manual")
        
        # Test default brand name inference from url
        result_url = extractor.extract(
            url="https://acme-tools.co.uk",
            manual_text="We build developer platforms.",
            brand_name=None
        )
        self.assertEqual(result_url["brand_name"], "Acme-tools")

    def test_extractor_llm_success(self):
        fake_llm = FakeLLMAnalyzer(api_key="valid-key")
        extractor = MagnetismExtractor(llm=fake_llm)  # type: ignore

        fake_llm.mock_response = {
            "brand_name": "Llm Brand",
            "url": "https://llmbrand.com",
            "magenta_circle": {
                "mindspace": {"detected": True, "finding": "Earn every second", "evidence": "Earn every second", "confidence": "high"},
                "aetherspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "gamespace": {"detected": True, "finding": "Precise operator brand", "evidence": "Built for precise operators", "confidence": "medium"},
                "envispace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "netspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "tactispace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "ambientspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"}
            }
        }

        result = extractor.extract(
            url="https://llmbrand.com",
            manual_text="landing page content here",
            brand_name="Llm Brand"
        )

        self.assertEqual(result["brand_name"], "Llm Brand")
        self.assertEqual(result["fallback_used"], False)
        self.assertEqual(result["source"], "direct_magnetism_legacy")
        self.assertEqual(result["extraction_mode"], "legacy_direct")
        self.assertIn("metrics", result)
        self.assertIn("tldr_brand3", result)
        self.assertGreater(result["magnetism_score"], 0)
        self.assertNotEqual(result["magnetism_score"], 90)
        self.assertEqual(result["magenta_circle"]["mindspace"]["status"], "detected")
        self.assertEqual(result["magenta_circle"]["mindspace"]["evidence"], "Earn every second")
        self.assertEqual(result["tldr_brand3"]["magnetism"]["content"], "Earn every second")
        self.assertIn("Do not produce scores", fake_llm.captured_user)
        self.assertNotIn("comprehensive audit", fake_llm.captured_user.lower())

    def test_extractor_from_brand_audit_snapshot_reuses_evidence(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 123, "brand_name": "Audit Brand", "url": "https://audit.test"},
            "features": [],
            "raw_inputs": [],
            "evidence_items": [
                {
                    "source": "context",
                    "url": "https://audit.test",
                    "quote": "Earn every second with AI workflow infrastructure.",
                    "feature_name": "positioning",
                    "dimension_name": "coherencia",
                    "confidence": 0.9,
                },
                {
                    "source": "context",
                    "url": "https://audit.test/pricing",
                    "quote": "API integrations and transparent pricing for operators.",
                    "feature_name": "site_structure",
                    "dimension_name": "presencia",
                    "confidence": 0.8,
                },
            ],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(result["source"], "brand_audit_snapshot")
        self.assertEqual(result["extraction_mode"], "canonical_snapshot")
        self.assertEqual(result["canonical_evidence_source"], "brand_audit_snapshot")
        self.assertNotIn("deprecation", result)
        self.assertEqual(result["source_run_id"], 123)
        self.assertEqual(result["brand_name"], "Audit Brand")
        self.assertEqual(result["evidence_packet_summary"]["source"], "brand_audit_snapshot")
        self.assertEqual(result["evidence_packet_summary"]["evidence_item_count"], 2)
        self.assertIn("system_reading", result)
        self.assertEqual(result["magenta_circle"]["mindspace"]["status"], "detected")
        self.assertEqual(result["tldr_brand3"]["magnetism"]["detected"], True)

    def test_extractor_from_brand_audit_snapshot_uses_strategic_packet_groups(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 124, "brand_name": "Packet Brand", "url": "https://packet.test"},
            "features": [],
            "raw_inputs": [],
            "evidence_items": [
                {
                    "source": "context",
                    "url": "https://packet.test",
                    "quote": "Packet Brand is the workflow platform for finance teams that helps reduce reconciliation time.",
                    "feature_name": "positioning",
                    "dimension_name": "coherencia",
                    "confidence": 0.9,
                }
            ],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertIn("strategic_evidence_packet", result)
        self.assertEqual(
            result["tldr_brand3"]["value_proposition"]["answer"],
            "Packet Brand is the workflow platform for finance teams that helps reduce reconciliation time.",
        )
        self.assertEqual(result["tldr_brand3"]["value_proposition"]["confidence"], "high")
        self.assertEqual(result["magenta_circle"]["netspace"]["status"], "detected")
        self.assertIn(
            "workflow platform",
            result["magenta_circle"]["netspace"]["evidence"],
        )
        self.assertGreater(result["metrics"]["coherence_score"], 40)
        self.assertIn("Strategic packet groups used", " ".join(result["tldr_brand3"]["value_proposition"]["observations"]))
        self.assertEqual(result["tldr_brand3"]["mission"]["mode"], "not_detected")
        self.assertEqual(
            result["evidence_packet_summary"]["strategic_group_counts"]["product_offer"],
            1,
        )

    def test_extractor_from_brand_audit_snapshot_prefers_raw_owned_page_over_search_snippet(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 125, "brand_name": "Raw Preferred", "url": "https://rawpreferred.test"},
            "features": [
                {
                    "dimension_name": "presencia",
                    "feature_name": "search_visibility",
                    "value": 80,
                    "confidence": 0.8,
                    "source": "exa",
                    "raw_value": str({
                        "evidence": [
                            {
                                "url": "https://rawpreferred.test/",
                                "title": "Raw Preferred - LinkedIn",
                                "snippet": "Raw Preferred is a Software Development company. Raw Preferred is a purpose-built platform for product teams that streamli",
                            }
                        ]
                    }),
                }
            ],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "canonical_url": "https://rawpreferred.test/",
                        "markdown_content": "Raw Preferred is a purpose-built product development platform for product teams that streamlines planning and roadmap execution.",
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        answer = result["tldr_brand3"]["value_proposition"]["answer"]
        self.assertEqual(
            answer,
            "Raw Preferred is a purpose-built product development platform for product teams that streamlines planning and roadmap execution.",
        )
        self.assertNotIn("Software Development company", answer)
        self.assertNotIn("LinkedIn", answer)

    def test_extractor_from_brand_audit_snapshot_prefers_substantive_offer_over_title(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 126, "brand_name": "Title Brand", "url": "https://titlebrand.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "markdown_content": "Title Brand | Web Search API\nReal-time AI search engine with a powerful web search API, web crawling API, and deep research tools for developers and enterprises.",
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(
            result["tldr_brand3"]["value_proposition"]["answer"],
            "Real-time AI search engine with a powerful web search API, web crawling API, and deep research tools for developers and enterprises.",
        )

    def test_value_proposition_flags_multiple_offer_candidates_from_snapshot(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 137, "brand_name": "Multi Offer", "url": "https://multi.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "markdown_content": (
                            "Multi Offer is a treasury platform for finance teams that streamlines cash visibility.\n"
                            "Multi Offer also provides payment automation services for operators that reduce manual work."
                        ),
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        value_prop = result["tldr_brand3"]["value_proposition"]
        self.assertTrue(value_prop["detected"])
        self.assertTrue(value_prop["human_review_recommended"])
        self.assertTrue(
            any("multiple offer signals" in item for item in value_prop["counter_evidence"])
        )
        self.assertIn("Multiple product_offer candidates", " ".join(value_prop["observations"]))

    def test_extractor_from_brand_audit_snapshot_combines_short_offer_with_outcome(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 127, "brand_name": "Transport Brand", "url": "https://transport.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "markdown_content": "Software de planificación de transporte\nAutomatiza tus procesos de contratación de transporte. Reduce costes.",
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        answer = result["tldr_brand3"]["value_proposition"]["answer"]
        self.assertEqual(
            answer,
            "Software de planificación de transporte. Automatiza tus procesos de contratación de transporte. Reduce costes.",
        )
        self.assertEqual(result["tldr_brand3"]["value_proposition"]["confidence"], "medium")

    def test_extractor_from_brand_audit_snapshot_does_not_extend_complete_short_offer(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 128, "brand_name": "Creator Brand", "url": "https://creator.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "markdown_content": "The email platform made for creators: Make email your most valuable channel\nReach your audience and turn subscribers into customers Unlimited landing pages",
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(
            result["tldr_brand3"]["value_proposition"]["answer"],
            "The email platform made for creators: Make email your most valuable channel",
        )

    def test_mission_rejects_customer_testimonial_as_operating_activity(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 129, "brand_name": "Ship Brand", "url": "https://ship.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "markdown_content": "> “Ship Brand nos ofrece múltiples soluciones para optimizar la gestión y el coste de transporte.”",
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(result["tldr_brand3"]["mission"]["mode"], "not_detected")

    def test_mission_rejects_truncated_formal_mission_snippet(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 130, "brand_name": "Video Brand", "url": "https://video.test"},
            "features": [],
            "raw_inputs": [],
            "evidence_items": [
                {
                    "source": "context",
                    "url": "https://video.test/about",
                    "quote": "At Video Brand, our mission revolves around empowering individuals throu",
                    "feature_name": "search_visibility",
                    "dimension_name": "coherencia",
                    "confidence": 0.8,
                }
            ],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(result["tldr_brand3"]["mission"]["mode"], "not_detected")

    def test_vision_rejects_current_product_transform_language(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 131, "brand_name": "Avatar Brand", "url": "https://avatar.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "markdown_content": "Transform photos into videos with realistic lip-syncing and natural facial expressions.",
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(result["tldr_brand3"]["vision"]["mode"], "not_detected")

    def test_vision_accepts_future_or_generation_language(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 132, "brand_name": "Wealth Brand", "url": "https://wealth.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "markdown_content": "Impulsando una gestión patrimonial independiente para la nueva generación de asesores mediante infraestructura tecnológica nativa en inteligencia artificial.",
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(result["tldr_brand3"]["vision"]["confidence"], "medium")
        self.assertIn("nueva generación", result["tldr_brand3"]["vision"]["answer"])

    def test_strategic_packet_groups_enrich_magenta_layers_conservatively(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 133, "brand_name": "Layer Brand", "url": "https://layer.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "markdown_content": "Make operations measurable. Layer Brand is the workflow platform for operations teams that reduces manual reporting. A precise and trusted operating system for modern teams.",
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(result["magenta_circle"]["mindspace"]["status"], "detected")
        self.assertEqual(result["magenta_circle"]["netspace"]["status"], "detected")
        self.assertIn(
            result["magenta_circle"]["gamespace"]["status"],
            {"detected", "not_detected"},
        )
        self.assertGreater(result["metrics"]["magnetism_score"], 0)

    def test_strategic_packet_rejected_mission_does_not_enrich_tactispace(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 134, "brand_name": "Rejected Mission", "url": "https://reject.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "markdown_content": "> “Rejected Mission nos ofrece múltiples soluciones para optimizar la gestión y el coste de transporte.”",
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(result["tldr_brand3"]["mission"]["mode"], "not_detected")
        self.assertEqual(result["magenta_circle"]["tactispace"]["status"], "not_detected")

    def test_extractor_llm_exception_falls_back(self):
        class ExceptionLLM(FakeLLMAnalyzer):
            def _call_json(self, system: str, user: str, max_tokens: int = 8000) -> dict[str, Any]:
                raise RuntimeError("API failure")

        extractor = MagnetismExtractor(llm=ExceptionLLM())  # type: ignore
        
        result = extractor.extract(
            url=None,
            manual_text="We have a pricing and developer framework.",
            brand_name="Fallback Brand"
        )
        
        self.assertEqual(result["fallback_used"], True)
        self.assertEqual(result["magenta_circle"]["mindspace"]["status"], "detected")
        self.assertEqual(result["magenta_circle"]["tactispace"]["status"], "not_detected")

    @unittest.mock.patch("web.routes.magnetism_scanner.run_magnetism_from_url")
    @unittest.mock.patch("web.routes.magnetism_scanner.validate_url")
    @unittest.mock.patch("web.routes.magnetism_scanner.LLMAnalyzer")
    def test_web_route_url_analysis_delegates_to_canonical_service(
        self,
        mock_llm_class,
        mock_validate_url,
        mock_run_magnetism_from_url,
    ):
        mock_llm_class.return_value.api_key = None
        mock_validate_url.return_value = (True, "https://example.com")
        mock_run_magnetism_from_url.return_value = {
            "brand_name": "Canonical Route",
            "url": "https://example.com",
            "magnetism_score": 62,
            "coherence_score": 70,
            "quadrant": "Low Magnetism - High Coherence",
            "source": "brand_audit_snapshot",
            "extraction_mode": "canonical_snapshot",
            "source_run_id": 77,
            "metrics": {},
            "tldr_brand3": {},
            "magenta_circle": {},
        }

        self._unlock_team_cookie()
        response = self.client.post(
            "/magnetism-scanner/analyze",
            data={"url": "https://example.com", "manual_text": ""},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        mock_validate_url.assert_called_once_with("https://example.com")
        mock_run_magnetism_from_url.assert_called_once_with(
            "https://example.com",
            llm=mock_llm_class.return_value,
        )
        scan_id = int(response.headers["location"].rsplit("/", 1)[-1])

        from web.storage import get_magnetism_scan

        scan = get_magnetism_scan(scan_id)
        self.assertIsNotNone(scan)
        payload = json.loads(scan["raw_payload"])
        self.assertEqual(payload["source"], "brand_audit_snapshot")
        self.assertEqual(payload["extraction_mode"], "canonical_snapshot")
        self.assertEqual(payload["source_run_id"], 77)
        self.assertNotIn("deprecation", payload)

    @unittest.mock.patch("web.routes.magnetism_scanner.LLMAnalyzer")
    def test_web_routes_flow(self, mock_llm_class):
        mock_llm_class.return_value.api_key = None
        self._unlock_team_cookie()
        # GET index page when empty
        r = self.client.get("/magnetism-scanner")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Brand Magnetism Scanner", r.text)
        self.assertIn("no magnetism scans recorded yet", r.text)

        # POST analyze error
        r_err = self.client.post("/magnetism-scanner/analyze", data={"url": "", "manual_text": ""})
        self.assertEqual(r_err.status_code, 400)
        self.assertIn("Input required", r_err.text)

        # POST analyze error invalid URL
        r_url_err = self.client.post("/magnetism-scanner/analyze", data={"url": "not-a-valid-url"})
        self.assertEqual(r_url_err.status_code, 400)
        self.assertIn("URL rejected", r_url_err.text)

        # POST analyze success with manual input (runs heuristic fallback automatically since LLM default is None or disabled)
        r_ok = self.client.post(
            "/magnetism-scanner/analyze",
            data={
                "url": "",
                "manual_text": "We are building a paradigm shifting framework with simple subscribe checkout."
            },
            follow_redirects=False
        )
        # Should redirect to detail page
        self.assertEqual(r_ok.status_code, 303)
        redirect_url = r_ok.headers["location"]
        self.assertTrue(redirect_url.startswith("/magnetism-scanner/scan/"))

        # Follow redirect or GET detail page
        r_detail = self.client.get(redirect_url)
        self.assertEqual(r_detail.status_code, 200)
        self.assertIn("Legacy Direct Extraction", r_detail.text)
        self.assertIn("legacy_extraction", r_detail.text)
        self.assertIn("Manual Upload Brand", r_detail.text)
        self.assertIn("TLDR Brand3", r_detail.text)
        self.assertIn("9 strategic blocks derived from 7 Magenta signals", r_detail.text)
        self.assertIn("source signal: Emotions → Magnetism", r_detail.text)
        self.assertIn("evidence_basis:", r_detail.text)
        self.assertIn("Methodology Details", r_detail.text)

        # GET non-existent detail
        r_not_found = self.client.get("/magnetism-scanner/scan/99999")
        self.assertEqual(r_not_found.status_code, 404)

        # GET index showing past scan
        r_index_populated = self.client.get("/magnetism-scanner")
        self.assertEqual(r_index_populated.status_code, 200)
        self.assertIn("Manual Upload Brand", r_index_populated.text)
        self.assertNotIn("no magnetism scans recorded yet", r_index_populated.text)

    def test_human_research_language_produces_value_proposition(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 135, "brand_name": "Ethos", "url": "https://agent.askethos.com"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "markdown_content": "Ethos - Human intelligence, on-demand. Research people and companies to build relationships that get things done.",
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        block = result["tldr_brand3"]["value_proposition"]
        self.assertNotEqual(block["mode"], "not_detected")
        self.assertIn("Research people and companies", block["answer"])
        self.assertEqual(result["magenta_circle"]["netspace"]["status"], "detected")

    def test_cultural_ambition_enriches_vision_without_faking_value_proposition(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 136, "brand_name": "MSCHF", "url": "https://mschf.com"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "markdown_content": "Home | MSCHF MSCHF, as a practice and as an entity, manifests the ambition for creative work / a creative entity to wield power in culture and on the world stage.",
                    },
                }
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(result["tldr_brand3"]["value_proposition"]["mode"], "not_detected")
        self.assertEqual(result["tldr_brand3"]["vision"]["confidence"], "medium")
        self.assertEqual(result["magenta_circle"]["gamespace"]["status"], "detected")
        self.assertEqual(result["magenta_circle"]["tactispace"]["status"], "detected")


if __name__ == "__main__":
    unittest.main()
