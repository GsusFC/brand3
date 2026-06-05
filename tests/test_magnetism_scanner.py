from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import importlib
import json
import tempfile
import threading
import time
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
    os.environ["BRAND3_SCANNER_API_TOKEN"] = "scanner-token-for-tests-123456"
    os.environ["BRAND3_MAX_CONCURRENT_ANALYSES"] = "1"
    os.environ["BRAND3_LLM_API_KEY"] = ""
    os.environ["GEMINI_API_KEY"] = ""
    os.environ["GOOGLE_API_KEY"] = ""


class FakeLLMAnalyzer:
    """Mock for LLMAnalyzer."""

    def __init__(self, api_key: str | None = "fake-key"):
        self.api_key = api_key
        self.captured_system = None
        self.captured_user = None
        self.mock_response: dict[str, Any] = {}

    def _call_json(self, system: str, user: str, max_tokens: int = 8000, **kwargs: Any) -> dict[str, Any]:
        self.captured_system = system
        self.captured_user = user
        self.captured_kwargs = kwargs
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

    def _scanner_api_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer scanner-token-for-tests-123456"}

    def tearDown(self):
        from web.workers.queue import set_run_magnetism_override

        set_run_magnetism_override(None)
        self.screenshot_mock.stop()
        self.client.__exit__(None, None, None)
        self._tmp.cleanup()
        for key in (
            "BRAND3_DB_PATH",
            "BRAND3_COOKIE_SECRET",
            "BRAND3_TEAM_TOKEN",
            "BRAND3_SCANNER_API_TOKEN",
            "BRAND3_MAX_CONCURRENT_ANALYSES",
            "BRAND3_LLM_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
        ):
            os.environ.pop(key, None)

    def test_web_routes_are_public_without_team_cookie(self):
        response = self.client.get("/magnetism-scanner")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Brand3 Scanner", response.text)

        response = self.client.get("/magnetism-scanner?lang=en")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Brand3 Scanner", response.text)
        self.assertIn('<html lang="en">', response.text)

        response = self.client.post(
            "/magnetism-scanner/analyze",
            data={"url": "", "manual_text": ""},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Input required", response.text)

        response = self.client.post("/magnetism-scanner/from-run", data={"run_id": 1})
        self.assertEqual(response.status_code, 404)

        response = self.client.get("/magnetism-scanner/scan/1")
        self.assertEqual(response.status_code, 404)

    def test_magnetism_scanner_preserves_language_on_detail_tabs(self):
        from web.storage import insert_magnetism_scan

        payload = MagnetismExtractor(llm=None).extract(
            url=None,
            manual_text="A memorable brand for teams that want clearer execution.",
            brand_name="Language Brand",
        )
        scan_id = insert_magnetism_scan(
            brand_name=payload["brand_name"],
            url=payload["url"] or "Manual Upload",
            magnetism_score=payload["magnetism_score"],
            coherence_score=payload["coherence_score"],
            quadrant=payload["quadrant"],
            raw_payload=json.dumps(payload),
        )

        detail_es = self.client.get(f"/magnetism-scanner/scan/{scan_id}?lang=es")
        detail_en = self.client.get(f"/magnetism-scanner/scan/{scan_id}?lang=en")
        research_es = self.client.get(f"/magnetism-scanner/scan/{scan_id}/research?lang=es")
        methodology_es = self.client.get(f"/magnetism-scanner/scan/{scan_id}/methodology?lang=es")

        self.assertEqual(detail_es.status_code, 200)
        self.assertEqual(detail_en.status_code, 200)
        self.assertEqual(research_es.status_code, 200)
        self.assertEqual(methodology_es.status_code, 200)
        self.assertIn("Auditoría", detail_es.text)
        self.assertIn("Evidencia", detail_es.text)
        self.assertIn("Audit", detail_en.text)
        self.assertIn("Evidence", detail_en.text)
        self.assertIn(f"/magnetism-scanner/scan/{scan_id}/audit?lang=es", detail_es.text)
        self.assertIn(f"/magnetism-scanner/scan/{scan_id}/research?lang=es", detail_es.text)
        self.assertIn("Grafo de evidencia", research_es.text)
        self.assertNotIn("Plan de adquisición", research_es.text)
        self.assertNotIn("Traza de adquisición", research_es.text)
        self.assertNotIn("Calidad de adquisición", research_es.text)
        self.assertIn("magnetism-hero-metric-value-compact", research_es.text)
        self.assertIn("Detalles de metodología", methodology_es.text)
        self.assertIn("Snapshot de Brand Audit", methodology_es.text)
        self.assertIn("Por qué parece existir la marca", methodology_es.text)
        self.assertIn("capa técnica", methodology_es.text)
        self.assertIn("magnetism-hero-metric-value-compact", methodology_es.text)
        self.assertNotIn("Why the brand appears to exist beyond the product.", methodology_es.text)
        self.assertIn('<html lang="es">', detail_es.text)

    def test_scan_detail_applies_cached_tldr_translation(self):
        from web.storage import insert_magnetism_scan

        payload = MagnetismExtractor(llm=None).extract(
            url=None,
            manual_text="We help finance teams close faster with reliable workflows.",
            brand_name="Translated Brand",
        )
        payload["tldr_brand3"]["value_proposition"]["detected"] = True
        payload["tldr_brand3"]["value_proposition"]["content"] = "Ayuda a equipos financieros a cerrar antes."
        payload["diagnosis"]["headline"] = "Diagnóstico original."
        payload["translations"] = {
            "magnetism_tldr": {
                "en": {
                    "translation_version": 1,
                    "translation_source": "magnetism_tldr_translation",
                    "target_lang": "en",
                    "tldr_brand3": {
                        "value_proposition": {
                            "content": "Helps finance teams close faster.",
                        }
                    },
                    "diagnosis": {
                        "headline": "Translated diagnosis.",
                        "key_observations": payload["diagnosis"].get("key_observations") or [],
                    },
                }
            }
        }
        scan_id = insert_magnetism_scan(
            brand_name=payload["brand_name"],
            url=payload["url"] or "Manual Upload",
            magnetism_score=payload["magnetism_score"],
            coherence_score=payload["coherence_score"],
            quadrant=payload["quadrant"],
            raw_payload=json.dumps(payload),
        )

        response = self.client.get(f"/magnetism-scanner/scan/{scan_id}?lang=en")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Helps finance teams close faster.", response.text)
        self.assertIn("Translated diagnosis.", response.text)
        self.assertNotIn("Ayuda a equipos financieros a cerrar antes.", response.text)

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
        self.assertNotIn("llm_strategist_pass", response.text)

    def test_scan_has_separate_research_and_methodology_pages(self):
        from web.storage import insert_magnetism_scan

        payload = MagnetismExtractor(llm=None).extract(
            url=None,
            manual_text="LangChain provides the agent engineering platform and open-source frameworks for reliable agents.",
            brand_name="LangChain",
        )
        payload["research_pack_source"] = "evidence_graph"
        payload["tldr_generation_mode"] = "analyst_pass_validated"
        payload["research_pack"] = {
            "resolved_entity": {
                "resolved_entity": "LangChain",
                "entity_type": "company",
                "entity_scope": "audited_surface",
                "parent_brand": "",
            },
            "category": "agent engineering platform",
            "offer": "LangChain provides the agent engineering platform and open-source frameworks for reliable agents.",
            "company_summary": "LangChain provides the agent engineering platform.",
            "product_summary": "LangGraph provides durable execution for long-running agents.",
            "source_map": {
                "https://www.langchain.com/about": {
                    "source_type": "owned_about",
                    "surface_role": "mission_about",
                    "entity_scope": "parent_brand",
                    "title": "About LangChain",
                },
                "https://docs.langchain.com/oss/javascript/langgraph/graph-api": {
                    "source_type": "owned_product",
                    "surface_role": "product:LangGraph",
                    "entity_scope": "product:LangGraph",
                    "title": "LangGraph",
                },
            },
            "noise_rejected": [],
            "evidence_gaps": [],
            "confidence_notes": [
                "entity_boundary_collision: external evidence includes near-name collisions; quarantined from TLDR input."
            ],
        }
        payload["research_pack"]["noise_rejected"] = [
            {
                "text": "Publicis Media is a separate near-name entity and must not inform the audited brand.",
                "kind": "noise",
                "topic": "entity_boundary_collision",
                "source_url": "https://www.publicisgroupe.com",
                "source_type": "noise",
                "source_label": "entity_boundary_collision",
            }
        ]
        payload["research_pack"]["competitive_context"] = [
            {
                "text": "Competitive context source: BrowserOS",
                "kind": "context",
                "source_url": "https://browseros.com/",
                "source_type": "competitive_context",
                "source_label": "competitive_context",
                "topic": "competitive_context",
                "confidence": "medium",
            }
        ]
        payload["research_pack"]["shadow_sources"] = [
            {
                "provider": "parallel",
                "mode": "advanced",
                "status": "ok",
                "result_total": 2,
                "unique_domain_count": 2,
                "unique_domains": ["g2.com", "reddit.com"],
                "intents": {
                    "mentions": {
                        "status": "ok",
                        "result_count": 2,
                        "unique_domains": ["g2.com", "reddit.com"],
                        "results": [
                            {
                                "url": "https://g2.com/products/langchain/reviews",
                                "title": "LangChain Reviews",
                                "excerpt": "Third-party review shadow signal.",
                            }
                        ],
                    }
                },
                "notes": [
                    "Shadow provider only; not used for scoring, TLDR claims, proof points, or recommendations."
                ],
            }
        ]
        payload["evidence_graph_summary"] = {
            "source_counts": {"owned_about": 1, "owned_product": 1},
            "claim_count": 2,
        }
        payload["research_pack_quality"] = {
            "version": "brand_research_pack_quality_v0_1",
            "total_score": 92.5,
            "status": "pass",
            "dimensions": {
                "offer": {"name": "offer", "score": 100.0, "status": "pass", "reasons": []},
                "audience": {"name": "audience", "score": 85.0, "status": "pass", "reasons": []},
                "differentiation": {
                    "name": "differentiation",
                    "score": 70.0,
                    "status": "warn",
                    "reasons": ["thin_differentiation_signal"],
                },
                "frictions": {"name": "frictions", "score": 100.0, "status": "pass", "reasons": []},
                "proof": {"name": "proof", "score": 100.0, "status": "pass", "reasons": []},
                "traceability": {"name": "traceability", "score": 100.0, "status": "pass", "reasons": []},
                "noise": {"name": "noise", "score": 92.5, "status": "pass", "reasons": []},
            },
            "warnings": ["thin_differentiation_signal"],
            "pack_summary": {
                "entity_type": "company",
                "official_url_count": 1,
                "analyzed_url_count": 2,
                "proof_point_count": 1,
                "evidence_gap_count": 0,
            },
            "gate": {"passed": True, "failures": []},
        }

        scan_id = insert_magnetism_scan(
            brand_name="LangChain",
            url="https://www.langchain.com",
            magnetism_score=int(payload["magnetism_score"]),
            coherence_score=int(payload["coherence_score"]),
            quadrant=payload["quadrant"],
            raw_payload=json.dumps(payload),
        )

        detail = self.client.get(f"/magnetism-scanner/scan/{scan_id}")
        research = self.client.get(f"/magnetism-scanner/scan/{scan_id}/research")
        reliability = self.client.get(f"/magnetism-scanner/scan/{scan_id}/evidence-reliability")
        methodology = self.client.get(f"/magnetism-scanner/scan/{scan_id}/methodology")

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(research.status_code, 200)
        self.assertEqual(reliability.status_code, 200)
        self.assertEqual(methodology.status_code, 200)
        self.assertIn("TLDR Brand3", detail.text)
        self.assertIn("Auditoría", detail.text)
        self.assertIn("Evidencia", detail.text)
        self.assertNotIn("Magenta Circle Signals", detail.text)
        self.assertIn("Superficies de producto", research.text)
        self.assertIn('href="#research-pack"', research.text)
        self.assertIn('href="#surface-map"', research.text)
        self.assertIn('href="#parallel-shadow"', research.text)
        self.assertIn('id="entity-boundary"', research.text)
        self.assertIn("product:LangGraph", research.text)
        self.assertIn("Warnings de límite de entidad", research.text)
        self.assertIn("entity_boundary_collision", research.text)
        self.assertIn("Publicis Media is a separate near-name entity", research.text)
        self.assertIn("Abrir fuente", research.text)
        self.assertIn("Contexto competitivo", research.text)
        self.assertIn("Competitive context source: BrowserOS", research.text)
        self.assertIn("Parallel Shadow", research.text)
        self.assertIn("señales externas para revisión manual", research.text)
        self.assertIn("Lectura de señales externas", research.text)
        self.assertIn("Candidatos externos", research.text)
        self.assertIn("g2.com", research.text)
        self.assertIn("Third-party review shadow signal.", research.text)
        self.assertNotIn("Third-party review shadow signal.", detail.text)
        self.assertIn("calidad del input, no de la marca", reliability.text)
        self.assertIn("thin_differentiation_signal", reliability.text)
        self.assertIn("gate_passed", reliability.text)
        self.assertIn("Metadata del resultado", methodology.text)
        self.assertIn("scanner_result_v1", methodology.text)
        self.assertIn("brand3_scanner_pipeline_2026_06_03", methodology.text)
        self.assertIn("research_pack=True", methodology.text)
        self.assertIn("parallel_shadow=True", methodology.text)
        self.assertIn("Detalles de metodología", methodology.text)
        self.assertIn("Señales Magenta Circle", methodology.text)

    def test_scan_audit_tab_uses_unified_scanner_layout_with_brand_audit_data(self):
        from src.models.brand import BrandScore, DimensionScore
        from web.storage import insert_magnetism_scan

        store = SQLiteStore(str(self.db))
        try:
            brand_id = store.upsert_brand("Audit Linked", "https://audit-linked.test")
            run_id = store.create_run(
                brand_id,
                "Audit Linked",
                "https://audit-linked.test",
                use_llm=True,
                use_social=True,
            )
            store.save_scores(
                run_id,
                BrandScore(
                    url="https://audit-linked.test",
                    brand_name="Audit Linked",
                    dimensions={
                        "coherencia": DimensionScore(
                            name="coherencia",
                            score=72.0,
                            insights=["Clear owned positioning."],
                        ),
                        "diferenciacion": DimensionScore(
                            name="diferenciacion",
                            score=51.0,
                            insights=["Differentiation needs sharper proof."],
                        ),
                    },
                    composite_score=63.0,
                ),
            )
            store.save_run_audit(
                run_id,
                {
                    "scoring_state_fingerprint": "auditlinked12345",
                    "executive_analysis_v2": {
                        "executive_summary": "Audit Linked has a clear offer with limited proof.",
                        "primary_risk": "The proof base does not yet support the clarity of the offer.",
                        "primary_opportunity": "Use the owned positioning as the anchor for stronger proof.",
                        "dimensions": {
                            "coherencia": {
                                "diagnosis": "The owned offer is coherent across the available evidence.",
                                "findings": ["The homepage and score evidence point to a stable message."],
                                "evidence": ["Clear owned positioning."],
                                "recommendation": "Keep the core offer language stable while adding proof.",
                                "confidence": "high",
                            }
                        },
                    },
                    "executive_analysis_v2_translations": {
                        "es": {
                            "executive_summary": "Audit Linked tiene una oferta clara con prueba limitada.",
                            "primary_risk": "La base de prueba todavía no sostiene la claridad de la oferta.",
                            "primary_opportunity": "Usar el posicionamiento propio como ancla para reforzar la prueba.",
                            "dimensions": {
                                "coherencia": {
                                    "diagnosis": "La oferta propia es coherente en la evidencia disponible.",
                                    "findings": ["La homepage y la puntuación apuntan a un mensaje estable."],
                                    "evidence": ["Posicionamiento propio claro."],
                                    "recommendation": "Mantener estable el lenguaje central mientras se añade prueba.",
                                    "confidence": "high",
                                }
                            },
                        }
                    },
                },
            )
            store.finalize_run(
                run_id=run_id,
                composite_score=63.0,
                llm_used=True,
                social_scraped=True,
                result_path="",
                summary="Audit Linked has a clear offer with limited proof.",
            )
        finally:
            store.close()

        payload = MagnetismExtractor(llm=None).extract_from_audit_snapshot(
            {
                "run": {
                    "id": run_id,
                    "brand_name": "Audit Linked",
                    "url": "https://audit-linked.test",
                },
                "features": [],
                "raw_inputs": [],
                "evidence_items": [],
            }
        )
        payload["source_run_id"] = run_id
        scan_id = insert_magnetism_scan(
            brand_name=payload["brand_name"],
            url=payload["url"],
            magnetism_score=payload["magnetism_score"],
            coherence_score=payload["coherence_score"],
            quadrant=payload["quadrant"],
            raw_payload=json.dumps(payload),
            source_run_id=run_id,
        )

        detail = self.client.get(f"/magnetism-scanner/scan/{scan_id}")
        audit = self.client.get(f"/magnetism-scanner/scan/{scan_id}/audit")
        audit_en = self.client.get(f"/magnetism-scanner/scan/{scan_id}/audit?lang=en")

        self.assertEqual(detail.status_code, 200)
        self.assertIn(f"/magnetism-scanner/scan/{scan_id}/audit?lang=es", detail.text)
        self.assertEqual(audit.status_code, 200)
        self.assertIn("brand3 scanner", audit.text)
        self.assertIn("Auditoría", audit.text)
        self.assertIn("TLDR Brand3", audit.text)
        self.assertIn("Audit Linked", audit.text)
        self.assertIn("Resumen ejecutivo", audit.text)
        self.assertIn("La base de prueba todavía no sostiene la claridad de la oferta.", audit.text)
        self.assertIn("La oferta propia es coherente en la evidencia disponible.", audit.text)
        self.assertIn("La homepage y la puntuación apuntan a un mensaje estable.", audit.text)
        self.assertIn("Mantener estable el lenguaje central mientras se añade prueba.", audit.text)
        self.assertIn("Auditoría por dimensión", audit.text)
        self.assertIn("Coherencia", audit.text)
        self.assertIn("Base de evidencia", audit.text)
        self.assertIn("Evidencia total", audit.text)
        self.assertNotIn("<title>brand-audit", audit.text)
        self.assertEqual(audit_en.status_code, 200)
        self.assertIn("The proof base does not yet support the clarity of the offer.", audit_en.text)
        self.assertIn("The owned offer is coherent across the available evidence.", audit_en.text)

        legacy_payload = dict(payload)
        legacy_payload.pop("research_pack_quality", None)
        legacy_scan_id = insert_magnetism_scan(
            brand_name="LangChain Legacy",
            url="https://www.langchain.com",
            magnetism_score=int(legacy_payload["magnetism_score"]),
            coherence_score=int(legacy_payload["coherence_score"]),
            quadrant=legacy_payload["quadrant"],
            raw_payload=json.dumps(legacy_payload),
        )
        legacy_reliability = self.client.get(f"/magnetism-scanner/scan/{legacy_scan_id}/evidence-reliability")

        self.assertEqual(legacy_reliability.status_code, 200)
        self.assertIn("No se persistió diagnóstico de calidad del Research Pack", legacy_reliability.text)

    def test_scanner_api_can_queue_from_audit_run_and_expose_sections(self):
        from src.models.brand import BrandScore, DimensionScore
        from web.storage import insert_magnetism_scan
        from web.workers.queue import set_run_magnetism_override

        store = SQLiteStore(str(self.db))
        try:
            brand_id = store.upsert_brand("API Linked", "https://api-linked.test")
            run_id = store.create_run(
                brand_id,
                "API Linked",
                "https://api-linked.test",
                use_llm=True,
                use_social=True,
            )
            store.save_scores(
                run_id,
                BrandScore(
                    url="https://api-linked.test",
                    brand_name="API Linked",
                    dimensions={
                        "coherencia": DimensionScore(
                            name="coherencia",
                            score=74.0,
                            insights=["API linked owned evidence."],
                        )
                    },
                    composite_score=74.0,
                ),
            )
            store.save_run_audit(
                run_id,
                {
                    "scoring_state_fingerprint": "apilinked12345",
                    "executive_analysis_v2": {
                        "executive_summary": "API Linked has an attached audit snapshot.",
                        "primary_risk": "Proof remains thin.",
                        "primary_opportunity": "Use API access for team workflows.",
                        "dimensions": {},
                    }
                },
            )
            store.finalize_run(
                run_id=run_id,
                composite_score=74.0,
                llm_used=True,
                social_scraped=True,
                result_path="",
                summary="API Linked has an attached audit snapshot.",
            )
        finally:
            store.close()

        payload = MagnetismExtractor(llm=None).extract_from_audit_snapshot(
            {
                "run": {
                    "id": run_id,
                    "brand_name": "API Linked",
                    "url": "https://api-linked.test",
                },
                "features": [],
                "raw_inputs": [],
                "evidence_items": [],
            }
        )
        payload["source_run_id"] = run_id
        payload["scanner_readiness"] = {
            "status": "publishable",
            "publishable": True,
            "reason_codes": [],
        }
        set_run_magnetism_override(
            lambda job, progress_cb=None: json.loads(json.dumps(payload))
        )

        queued = self.client.post(
            "/api/v1/scanner",
            json={"audit_run_id": run_id},
            headers=self._scanner_api_headers(),
        )

        self.assertEqual(queued.status_code, 202)
        queued_payload = queued.json()
        self.assertEqual(queued_payload["status"], "queued")
        self.assertEqual(queued_payload["source_run_id"], run_id)
        self.assertIn("/api/v1/scanner/", queued_payload["result_url"])

        scan_id = insert_magnetism_scan(
            brand_name=payload["brand_name"],
            url=payload["url"],
            magnetism_score=payload["magnetism_score"],
            coherence_score=payload["coherence_score"],
            quadrant=payload["quadrant"],
            raw_payload=json.dumps(payload),
            source_run_id=run_id,
        )

        status = self.client.get(f"/api/v1/scanner/{scan_id}", headers=self._scanner_api_headers())
        result = self.client.get(f"/api/v1/scanner/{scan_id}/result", headers=self._scanner_api_headers())
        evidence = self.client.get(f"/api/v1/scanner/{scan_id}/evidence", headers=self._scanner_api_headers())
        methodology = self.client.get(f"/api/v1/scanner/{scan_id}/methodology", headers=self._scanner_api_headers())
        audit = self.client.get(f"/api/v1/scanner/{scan_id}/audit", headers=self._scanner_api_headers())

        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.json()["result_available"])
        self.assertEqual(status.json()["scanner_readiness"]["status"], "publishable")
        self.assertEqual(status.json()["scan_mode"]["mode"], "from_audit_run")
        self.assertTrue(status.json()["scan_mode"]["comparable"])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["audit"]["source_run_id"], run_id)
        self.assertEqual(result.json()["scan_mode"]["mode"], "from_audit_run")
        self.assertTrue(result.json()["scan_mode"]["comparable"])
        self.assertEqual(
            result.json()["result_metadata"]["scanner_readiness"]["status"],
            "publishable",
        )
        self.assertEqual(
            result.json()["result_metadata"]["scan_mode"]["mode"],
            "from_audit_run",
        )
        self.assertEqual(
            result.json()["result_metadata"]["publication_decision"]["status"],
            "publishable",
        )
        self.assertTrue(
            result.json()["result_metadata"]["publication_decision"]["publishable"]
        )
        self.assertIn("tldr_brand3", result.json())
        self.assertIn("scanner_result_v1", result.text)
        self.assertEqual(evidence.status_code, 200)
        self.assertIn("research_pack_source", evidence.text)
        self.assertEqual(methodology.status_code, 200)
        self.assertIn("result_metadata", methodology.json()["methodology"])
        self.assertEqual(
            methodology.json()["methodology"]["result_metadata"]["scanner_readiness"]["status"],
            "publishable",
        )
        self.assertEqual(
            methodology.json()["methodology"]["result_metadata"]["publication_decision"]["status"],
            "publishable",
        )
        self.assertEqual(audit.status_code, 200)
        self.assertTrue(audit.json()["available"])
        self.assertIn("API Linked has an attached audit snapshot.", audit.text)

    def test_scanner_api_requires_token(self):
        response = self.client.post("/api/v1/scanner", json={"url": "https://example.com"})
        invalid_body = self.client.post(
            "/api/v1/scanner",
            json={"url": "https://example.com", "mode": "advanced"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "scanner_api_unauthorized")
        self.assertEqual(invalid_body.status_code, 401)
        self.assertEqual(invalid_body.json()["error"]["code"], "scanner_api_unauthorized")

    def test_scanner_api_can_queue_from_url(self):
        with unittest.mock.patch(
            "web.workers.url_validator.socket.getaddrinfo",
            side_effect=lambda _h, _p: [(2, 1, 6, "", ("1.1.1.1", 0))],
        ):
            response = self.client.post(
                "/api/v1/scanner",
                json={"url": "https://example.com", "lang": "en"},
                headers=self._scanner_api_headers(),
            )

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["status"], "queued")
        self.assertEqual(payload["url"], "https://example.com")
        self.assertIsNone(payload["source_run_id"])
        self.assertEqual(payload["scan_mode"]["mode"], "canonical_url")
        self.assertTrue(payload["scan_mode"]["comparable"])
        self.assertIn("/api/v1/scanner/", payload["status_url"])

    def test_scanner_api_rejects_invalid_create_requests(self):
        headers = self._scanner_api_headers()

        missing = self.client.post("/api/v1/scanner", json={}, headers=headers)
        both = self.client.post(
            "/api/v1/scanner",
            json={"url": "https://example.com", "audit_run_id": 123},
            headers=headers,
        )
        bad_url = self.client.post(
            "/api/v1/scanner",
            json={"url": "not-a-url"},
            headers=headers,
        )
        missing_audit = self.client.post(
            "/api/v1/scanner",
            json={"audit_run_id": 999999},
            headers=headers,
        )
        unknown_field = self.client.post(
            "/api/v1/scanner",
            json={"url": "https://example.com", "mode": "advanced"},
            headers=headers,
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.json()["error"]["code"], "invalid_scanner_create_request")
        self.assertEqual(both.status_code, 400)
        self.assertEqual(both.json()["error"]["code"], "invalid_scanner_create_request")
        self.assertEqual(bad_url.status_code, 400)
        self.assertEqual(bad_url.json()["error"]["code"], "url_rejected")
        self.assertEqual(missing_audit.status_code, 404)
        self.assertEqual(missing_audit.json()["error"]["code"], "audit_run_not_found")
        self.assertEqual(unknown_field.status_code, 422)

    def test_scanner_api_not_ready_sections_return_stable_409(self):
        from web.storage import insert_magnetism_job

        scan_id = insert_magnetism_job(
            token="queued-scan-token",
            brand_name="Queued API",
            url="https://queued.test",
            input_type="url",
            input_value="https://queued.test",
        )
        headers = self._scanner_api_headers()

        for suffix in ("result", "evidence", "methodology", "audit"):
            response = self.client.get(f"/api/v1/scanner/{scan_id}/{suffix}", headers=headers)
            payload = response.json()
            self.assertEqual(response.status_code, 409)
            self.assertEqual(payload["error"]["code"], "scan_not_ready")
            self.assertEqual(payload["error"]["status"]["id"], scan_id)
            self.assertFalse(payload["error"]["status"]["result_available"])

    def test_scanner_api_missing_scan_returns_stable_404(self):
        response = self.client.get("/api/v1/scanner/999999/result", headers=self._scanner_api_headers())

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "scan_not_found")

    def test_scan_detail_shows_tldr_strategy_metadata(self):
        from web.storage import insert_magnetism_scan

        payload = MagnetismExtractor(llm=None).extract_from_audit_snapshot(
            {
                "run": {
                    "id": 404,
                    "brand_name": "Strategy Brand",
                    "url": "https://strategy.test",
                },
                "features": [],
                "raw_inputs": [
                    {
                        "source": "web",
                        "payload": {
                            "markdown_content": (
                                "A memorable line. Strategy Brand is the workflow platform "
                                "for teams that reduces manual reporting and keeps operators aligned."
                            )
                        },
                    }
                ],
                "evidence_items": [],
            }
        )
        payload["tldr_strategy"] = {
            "mode": "llm_analyst_pass",
            "verdict_vs_current": "better",
            "main_gain": "Sharper block interpretation.",
            "main_risk": "Evidence is still sparse.",
            "validation_notes": ["mission: downgraded from declared."],
        }
        scan_id = insert_magnetism_scan(
            brand_name="Strategy Brand",
            url="https://strategy.test",
            magnetism_score=payload["metrics"]["magnetism_score"],
            coherence_score=payload["metrics"]["coherence_score"],
            quadrant=payload["metrics"]["quadrant"],
            raw_payload=json.dumps(payload),
        )

        self._unlock_team_cookie()
        response = self.client.get(f"/magnetism-scanner/scan/{scan_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("llm_analyst_pass", response.text)
        self.assertIn("Guardrail corrections", response.text)
        self.assertIn("Sharper block interpretation.", response.text)

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
        self.assertNotIn("research_pack", result)
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

    def test_extractor_prompt_rejects_page_chrome_as_brand_evidence(self):
        fake_llm = FakeLLMAnalyzer(api_key="valid-key")
        extractor = MagnetismExtractor(llm=fake_llm)  # type: ignore[arg-type]

        fake_llm.mock_response = {
            "brand_name": "Chrome Noise",
            "url": "https://chrome-noise.test",
            "magenta_circle": {
                "mindspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "aetherspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "gamespace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "envispace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "netspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "tactispace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "ambientspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
            },
        }

        result = extractor.extract(
            url="https://chrome-noise.test",
            manual_text=(
                "Pricing Log in Sign up Cookie settings Privacy Policy "
                "Latest news: AI prediction roundup."
            ),
            brand_name="Chrome Noise",
        )

        self.assertEqual(result["fallback_used"], False)
        self.assertIn("Do not use page chrome as brand evidence", fake_llm.captured_user)
        self.assertIn("navigation labels", fake_llm.captured_user)
        self.assertIn("cookie banners", fake_llm.captured_user)
        self.assertIn("login/sign-up buttons", fake_llm.captured_user)
        self.assertIn("generic CTAs", fake_llm.captured_user)
        self.assertIn("blog/feed/news card titles", fake_llm.captured_user)
        self.assertIn("mark the layer as not_detected", fake_llm.captured_user)

    def test_extractor_prompt_includes_relevant_evidence_after_legacy_8k_cutoff(self):
        fake_llm = FakeLLMAnalyzer(api_key="valid-key")
        extractor = MagnetismExtractor(llm=fake_llm)  # type: ignore[arg-type]
        late_evidence = "Late evidence: We build resilient AI workflows for regulated finance teams."

        fake_llm.mock_response = {
            "brand_name": "Long Page",
            "url": "https://long-page.test",
            "magenta_circle": {
                "mindspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "aetherspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "gamespace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "envispace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "netspace": {"detected": True, "finding": "AI workflows for finance teams", "evidence": late_evidence, "confidence": "high"},
                "tactispace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "ambientspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
            },
        }

        result = extractor.extract(
            url="https://long-page.test",
            manual_text=("x" * 8500) + late_evidence,
            brand_name="Long Page",
        )

        self.assertEqual(result["fallback_used"], False)
        self.assertIn(late_evidence, fake_llm.captured_user)
        self.assertEqual(result["magenta_circle"]["netspace"]["evidence"], late_evidence)

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

        with unittest.mock.patch("src.features.magnetism.extractor.BRAND3_MAGNETISM_RESEARCH_PACK_TLDR", False), \
             unittest.mock.patch("src.features.magnetism.extractor.BRAND3_BRAND_RESEARCH_GRAPH_PACK", False):
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

    def test_extractor_from_brand_audit_snapshot_rederives_tldr_after_llm_with_packet(self):
        fake_llm = FakeLLMAnalyzer(api_key="valid-key")
        fake_llm.mock_response = {
            "brand_name": "Fly Test",
            "url": "https://fly.test",
            "magenta_circle": {
                "mindspace": {"detected": True, "finding": "Build fast", "evidence": "Build fast", "confidence": "high"},
                "aetherspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "gamespace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "envispace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "netspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "tactispace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
                "ambientspace": {"detected": False, "finding": None, "evidence": None, "confidence": "insufficient"},
            },
        }
        extractor = MagnetismExtractor(llm=fake_llm)  # type: ignore[arg-type]
        snapshot = {
            "run": {"id": 140, "brand_name": "Fly Test", "url": "https://fly.test"},
            "features": [],
            "raw_inputs": [],
            "evidence_items": [
                {
                    "source": "web",
                    "url": "https://fly.test",
                    "quote": "Fly Test is a platform for devs who want to ship, powered by sandboxes that let you deploy any code with confidence.",
                    "feature_name": "positioning",
                    "dimension_name": "coherencia",
                    "confidence": 0.9,
                }
            ],
        }

        with unittest.mock.patch("src.features.magnetism.extractor.BRAND3_MAGNETISM_RESEARCH_PACK_TLDR", False), \
             unittest.mock.patch("src.features.magnetism.extractor.BRAND3_BRAND_RESEARCH_GRAPH_PACK", False):
            result = extractor.extract_from_audit_snapshot(snapshot)

        value_prop = result["tldr_brand3"]["value_proposition"]
        self.assertEqual(value_prop["mode"], "compressed")
        self.assertIn("developer cloud platform", value_prop["answer"])
        self.assertEqual(result["magenta_circle"]["netspace"]["status"], "detected")
        self.assertGreater(result["metrics"]["coherence_score"], 40)

    def test_extractor_from_brand_audit_snapshot_surfaces_proof_as_credibility_support(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {
                "id": 126,
                "brand_name": "Proof Brand",
                "url": "https://proofbrand.test",
            },
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "canonical_url": "https://proofbrand.test/",
                        "markdown_content": (
                            "Proof Brand is a treasury platform for finance teams "
                            "that helps reduce reconciliation time."
                        ),
                    },
                },
                {
                    "source": "web",
                    "payload": {
                        "canonical_url": "https://proofbrand.test/case-study/dena",
                        "markdown_content": (
                            "DeNA scaled treasury operations with Proof Brand across multiple entities."
                        ),
                    },
                },
            ],
            "evidence_items": [],
        }

        result = extractor.extract_from_audit_snapshot(snapshot)

        proof_support = result["evidence_packet_summary"]["proof_support"]
        credibility_support = result["system_reading"]["credibility_support"]

        self.assertEqual(proof_support["status"], "observed")
        self.assertEqual(credibility_support["status"], "observed")
        self.assertEqual(credibility_support["count"], 1)
        self.assertTrue(
            any(
                "case-study/dena" in str(item.get("url") or "")
                for item in credibility_support["evidence"]
            )
        )
        self.assertIn("do not define mission", credibility_support["reading"])
        self.assertEqual(result["tldr_brand3"]["mission"]["mode"], "not_detected")
        self.assertEqual(result["tldr_brand3"]["personality"]["mode"], "not_detected")

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

    @unittest.mock.patch("web.routes.magnetism_scanner.validate_url")
    def test_web_route_url_analysis_queues_canonical_service(
        self,
        mock_validate_url,
    ):
        from web.workers.queue import set_run_magnetism_override

        captured_jobs = []

        def fake_magnetism(job: dict) -> dict:
            captured_jobs.append(job)
            return {
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

        set_run_magnetism_override(fake_magnetism)
        mock_validate_url.return_value = (True, "https://example.com")

        self._unlock_team_cookie()
        response = self.client.post(
            "/magnetism-scanner/analyze",
            data={"url": "https://example.com", "manual_text": ""},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertRegex(response.headers["location"], r"^/magnetism-scanner/.+/status\?lang=es$")
        mock_validate_url.assert_called_once_with("https://example.com")
        token = response.headers["location"].split("/")[2]

        from web.storage import get_magnetism_scan_by_token

        scan = get_magnetism_scan_by_token(token)
        self.assertIsNotNone(scan)
        self.assertIn(scan["status"], {"queued", "running", "ready"})
        self.assertEqual(scan["input_type"], "url")
        self.assertEqual(scan["input_value"], "https://example.com")

        for _ in range(30):
            scan = get_magnetism_scan_by_token(token)
            if scan and scan["status"] == "ready":
                break
            time.sleep(0.2)

        self.assertEqual(scan["status"], "ready")
        payload = json.loads(scan["raw_payload"])
        self.assertEqual(payload["source"], "brand_audit_snapshot")
        self.assertEqual(payload["extraction_mode"], "canonical_snapshot")
        self.assertEqual(payload["source_run_id"], 77)
        self.assertEqual(captured_jobs[0]["input_type"], "url")
        self.assertNotIn("deprecation", payload)

    @unittest.mock.patch("web.routes.magnetism_scanner.validate_url")
    def test_web_route_url_analysis_blocks_degraded_canonical_tldr(
        self,
        mock_validate_url,
    ):
        from web.workers.queue import set_run_magnetism_override

        def fake_degraded_magnetism(job: dict) -> dict:
            return {
                "brand_name": "Degraded Canonical",
                "url": "https://example.com",
                "magnetism_score": 0,
                "coherence_score": 36,
                "quadrant": "pending",
                "source": "brand_audit_snapshot",
                "extraction_mode": "canonical_snapshot",
                "source_run_id": 77,
                "tldr_generation_mode": "legacy_fallback_no_llm",
                "warnings": ["Analyst Pass disabled because no LLM API key is available."],
                "tldr_brand3": {},
            }

        set_run_magnetism_override(fake_degraded_magnetism)
        mock_validate_url.return_value = (True, "https://example.com")

        self._unlock_team_cookie()
        response = self.client.post(
            "/magnetism-scanner/analyze",
            data={"url": "https://example.com", "manual_text": ""},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        token = response.headers["location"].split("/")[2]

        from web.storage import get_magnetism_scan_by_token

        scan = None
        for _ in range(30):
            scan = get_magnetism_scan_by_token(token)
            if scan and scan["status"] == "failed":
                break
            time.sleep(0.2)

        self.assertEqual(scan["status"], "failed")
        self.assertEqual(
            scan["error_message"],
            "failed:canonical_tldr_degraded:no_llm",
        )
        payload = json.loads(scan["raw_payload"])
        self.assertEqual(payload["tldr_generation_mode"], "legacy_fallback_no_llm")
        self.assertEqual(payload["scanner_readiness"]["status"], "failed")
        self.assertEqual(payload["publication_decision"]["status"], "failed")
        self.assertEqual(payload["publication_decision"]["source_status"], "failed")
        self.assertEqual(
            payload["scanner_readiness"]["reason_codes"],
            ["canonical_tldr_degraded:no_llm"],
        )

    def test_direct_scan_insert_marks_degraded_canonical_payload_failed(self):
        from web.storage import get_magnetism_scan, insert_magnetism_scan

        payload = {
            "brand_name": "Direct Degraded",
            "url": "https://example.com",
            "magnetism_score": 0,
            "coherence_score": 36,
            "quadrant": "pending",
            "source": "brand_audit_snapshot",
            "source_run_id": 123,
            "tldr_generation_mode": "legacy_fallback_llm_error",
            "tldr_brand3": {},
        }
        scan_id = insert_magnetism_scan(
            brand_name=payload["brand_name"],
            url=payload["url"],
            magnetism_score=payload["magnetism_score"],
            coherence_score=payload["coherence_score"],
            quadrant=payload["quadrant"],
            raw_payload=json.dumps(payload),
            source_run_id=123,
        )

        row = get_magnetism_scan(scan_id)
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["error_message"], "failed:canonical_tldr_degraded:llm_error")
        stored = json.loads(row["raw_payload"])
        self.assertEqual(stored["scanner_readiness"]["status"], "failed")
        self.assertEqual(stored["publication_decision"]["status"], "failed")
        self.assertEqual(stored["publication_decision"]["source_status"], "failed")

    def test_direct_manual_scan_insert_marks_payload_debug_only(self):
        from web.storage import get_magnetism_scan, insert_magnetism_scan

        payload = MagnetismExtractor(llm=None).extract(
            url=None,
            manual_text="Manual evidence for a debug-only scanner result.",
            brand_name="Manual Debug",
        )
        scan_id = insert_magnetism_scan(
            brand_name=payload["brand_name"],
            url=payload["url"] or "Manual Upload",
            magnetism_score=payload["magnetism_score"],
            coherence_score=payload["coherence_score"],
            quadrant=payload["quadrant"],
            raw_payload=json.dumps(payload),
        )

        row = get_magnetism_scan(scan_id)
        self.assertEqual(row["status"], "ready")
        stored = json.loads(row["raw_payload"])
        self.assertEqual(stored["scanner_readiness"]["status"], "debug_only")
        self.assertFalse(stored["scanner_readiness"]["publishable"])
        self.assertEqual(stored["publication_decision"]["status"], "debug_only")
        self.assertFalse(stored["publication_decision"]["publishable"])
        self.assertTrue(stored["publication_decision"]["ui_readable"])
        self.assertEqual(stored["scan_mode"]["mode"], "legacy_manual")
        self.assertFalse(stored["scan_mode"]["comparable"])
        self.assertIn("manual_input_debug_path", stored["scan_mode"]["reason_codes"])

    def test_research_pack_tldr_flag_on_uses_analyst_pass_and_persists_payload(self):
        from web.storage import insert_magnetism_scan, get_magnetism_scan

        fake_llm = FakeLLMAnalyzer()
        fake_llm.mock_response = {
            "entity_reading": "Base44 is a company-level AI app builder.",
            "verdict_vs_current": "better",
            "main_gain": "The offer is grounded in the Research Pack.",
            "main_risk": "Founder context still needs human review.",
            "tldr_brand3": {
                "value_proposition": {
                    "answer": "An AI app builder for non-technical founders.",
                    "claim_type": "declared",
                    "mode": "compressed",
                    "confidence": "high",
                    "reasoning": "The owned homepage states the offer directly.",
                    "evidence_used": ["Base44 is an AI app builder for non-technical founders."],
                    "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                    "counter_evidence": [],
                    "human_review_recommended": False,
                }
            },
        }
        extractor = MagnetismExtractor(llm=fake_llm)  # type: ignore[arg-type]
        snapshot = {
            "run": {"id": 505, "brand_name": "Base44", "url": "https://base44.com"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "canonical_url": "https://base44.com",
                        "markdown_content": (
                            "Base44 is an AI app builder for non-technical founders. "
                            "Build and ship apps fast."
                        ),
                    },
                },
                {
                    "source": "entity_research_packet",
                    "payload": {
                        "input_url": "https://base44.com",
                        "audited_surface_type": "parent_home",
                        "entity_name": "Base44",
                        "parent_brand": None,
                        "product_name": None,
                        "brand_architecture": "single_brand_surface",
                        "owned_surfaces": [
                            {
                                "url": "https://base44.com",
                                "role": "audited_surface",
                                "entity_scope": "audited_surface",
                                "reason": "input",
                            }
                        ],
                        "limitations": [],
                    },
                },
            ],
            "evidence_items": [],
        }

        with unittest.mock.patch("src.features.magnetism.extractor.BRAND3_MAGNETISM_RESEARCH_PACK_TLDR", True), \
             unittest.mock.patch("src.features.magnetism.extractor.BRAND3_BRAND_RESEARCH_GRAPH_PACK", False), \
             unittest.mock.patch.object(extractor, "_extract_via_llm", return_value=None):
            result = extractor.extract_from_audit_snapshot(snapshot)

        scan_id = insert_magnetism_scan(
            brand_name=result["brand_name"],
            url=result["url"],
            magnetism_score=result["magnetism_score"],
            coherence_score=result["coherence_score"],
            quadrant=result["quadrant"],
            raw_payload=json.dumps(result),
        )
        stored = get_magnetism_scan(scan_id)
        payload = json.loads(stored["raw_payload"])

        self.assertEqual(result["tldr_generation_mode"], "analyst_pass_validated")
        self.assertIn("research_pack", result)
        self.assertIn("research_pack_quality", result)
        self.assertIn(result["research_pack_quality"]["status"], {"pass", "warn", "fail"})
        self.assertIn("gate", result["research_pack_quality"])
        self.assertEqual(result["research_pack_source"], "snapshot_builder")
        self.assertNotIn("evidence_graph_summary", result)
        self.assertIn("analyst_tldr_raw", result)
        self.assertIn("analyst_tldr_validated", result)
        self.assertIn("legacy_tldr_brand3", result)
        self.assertEqual(result["tldr_strategy"]["mode"], "llm_analyst_pass")
        self.assertEqual(result["tldr_brand3"]["value_proposition"]["claim_type"], "declared")
        self.assertEqual(payload["tldr_generation_mode"], "analyst_pass_validated")
        self.assertIn("research_pack", payload)
        self.assertIn("research_pack_quality", payload)
        self.assertIn("analyst_tldr_validated", payload)

    def test_graph_pack_flag_uses_evidence_graph_research_pack(self):
        fake_llm = FakeLLMAnalyzer()
        fake_llm.mock_response = {
            "entity_reading": "SigmaOS is a browser product.",
            "verdict_vs_current": "better",
            "main_gain": "The graph recovers product offer claims.",
            "main_risk": "Values remain under-evidenced.",
            "tldr_brand3": {
                "value_proposition": {
                    "answer": "A browser that organizes tabs into workspaces and task-like lists.",
                    "claim_type": "declared",
                    "mode": "compressed",
                    "confidence": "high",
                    "reasoning": "The EvidenceGraph contains recovered owned product claims.",
                    "evidence_used": ["The new home for your internet. One window. Many workspaces. All your tabs."],
                    "evidence_sources": [{"source_key": "https://sigmaos.com", "source_type": "owned_official"}],
                    "counter_evidence": [],
                    "human_review_recommended": False,
                }
            },
        }
        extractor = MagnetismExtractor(llm=fake_llm)  # type: ignore[arg-type]
        snapshot = {
            "run": {"id": 507, "brand_name": "SigmaOS", "url": "https://sigmaos.com"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "canonical_url": "https://sigmaos.com",
                        "markdown_content": (
                            "A smarter way to browse the internet.\n"
                            "The new home for your internet. One window. Many workspaces. All your tabs.\n"
                            "Your tabs are like tasks in a to-do list. Mark them as done once they're complete.\n"
                            "Download Free\n"
                        ),
                    },
                }
            ],
            "evidence_items": [],
        }

        with unittest.mock.patch("src.features.magnetism.extractor.BRAND3_MAGNETISM_RESEARCH_PACK_TLDR", True), \
             unittest.mock.patch("src.features.magnetism.extractor.BRAND3_BRAND_RESEARCH_GRAPH_PACK", True), \
             unittest.mock.patch.object(extractor, "_extract_via_llm", return_value=None):
            result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(result["tldr_generation_mode"], "analyst_pass_validated")
        self.assertEqual(result["research_pack_source"], "evidence_graph")
        self.assertEqual(result["research_pack_recommendation"]["builder"], "graph")
        self.assertIn("research_pack_quality", result)
        self.assertEqual(result["research_pack_quality"]["version"], "brand_research_pack_quality_v0_1")
        self.assertIn("audience", result["research_pack_quality"]["dimensions"])
        self.assertIn("evidence_graph_summary", result)
        self.assertGreater(result["evidence_graph_summary"]["claim_count"], 0)
        self.assertIn("The new home for your internet", result["research_pack"]["offer"])
        self.assertEqual(result["tldr_brand3"]["value_proposition"]["claim_type"], "declared")

    def test_graph_pack_flag_uses_legacy_when_recommendation_blocks_graph(self):
        class _Recommended:
            pack = "legacy-pack"
            graph_summary = None
            recommendation = {
                "builder": "legacy",
                "promotion_status": "blocked",
                "reason_codes": ["legacy_fields_lost"],
            }

        snapshot = {"run": {"id": 508, "brand_name": "Example", "url": "https://example.com"}}

        with unittest.mock.patch("src.features.magnetism.extractor.BRAND3_BRAND_RESEARCH_GRAPH_PACK", True), \
             unittest.mock.patch("src.features.magnetism.extractor.build_recommended_research_pack", return_value=_Recommended()) as build_mock:
            pack, graph_summary, recommendation = MagnetismExtractor._build_research_pack(snapshot)

        self.assertEqual(pack, "legacy-pack")
        self.assertIsNone(graph_summary)
        self.assertEqual(recommendation["builder"], "legacy")
        build_mock.assert_called_once_with(snapshot, allow_graph=True)

    def test_contextdev_visual_enrichment_shadow_records_dry_run_without_mutating_research_pack(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 509, "brand_name": "Audit Brand", "url": "https://audit.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "canonical_url": "https://audit.test",
                        "markdown_content": "Audit Brand is workflow infrastructure for finance operators.",
                    },
                }
            ],
            "evidence_items": [],
            "contextdev_candidate_summary": {
                "candidate_count": 1,
                "candidates": [
                    {
                        "candidate_id": "ctxdev_visual_fonts_1",
                        "candidate_type": "visual_fonts",
                        "supports_channel": "visual_identity",
                        "text": "Aeonik, Twklausanne",
                        "source_url": "https://audit.test",
                        "provider": "contextdev",
                        "raw_ref": "test",
                    }
                ],
            },
        }

        with unittest.mock.patch("src.features.magnetism.extractor.BRAND3_MAGNETISM_RESEARCH_PACK_TLDR", False), \
             unittest.mock.patch("src.features.magnetism.extractor.BRAND3_BRAND_RESEARCH_GRAPH_PACK", False), \
             unittest.mock.patch("src.features.magnetism.extractor.BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT", True):
            result = extractor.extract_from_audit_snapshot(snapshot)

        shadow = result["contextdev_visual_enrichment_shadow"]
        self.assertEqual(shadow["status"], "evaluated")
        self.assertEqual(shadow["promotion_report"]["status_counts"]["promotable"], 1)
        self.assertEqual(shadow["field_updates"][0]["field"], "visual_or_conceptual_signals")
        self.assertIn(
            "Font signal: Aeonik, Twklausanne",
            shadow["enriched_pack_delta"]["visual_or_conceptual_signals"][0],
        )
        self.assertNotIn(
            "Font signal: Aeonik, Twklausanne",
            " ".join(result["research_pack"]["visual_or_conceptual_signals"]),
        )

    def test_contextdev_visual_enrichment_shadow_reads_persisted_raw_input_summary(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 511, "brand_name": "Audit Brand", "url": "https://audit.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "canonical_url": "https://audit.test",
                        "markdown_content": "Audit Brand is workflow infrastructure for finance operators.",
                    },
                },
                {
                    "source": "contextdev_candidate_summary",
                    "payload": {
                        "candidate_count": 1,
                        "candidates": [
                            {
                                "candidate_id": "ctxdev_visual_colors_1",
                                "candidate_type": "visual_colors",
                                "supports_channel": "visual_identity",
                                "text": "near-black background, electric blue accent",
                                "source_url": "https://audit.test",
                                "provider": "contextdev",
                                "raw_ref": "test",
                            }
                        ],
                    },
                },
            ],
            "evidence_items": [],
        }

        with unittest.mock.patch("src.features.magnetism.extractor.BRAND3_MAGNETISM_RESEARCH_PACK_TLDR", False), \
             unittest.mock.patch("src.features.magnetism.extractor.BRAND3_BRAND_RESEARCH_GRAPH_PACK", False), \
             unittest.mock.patch("src.features.magnetism.extractor.BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT", True):
            result = extractor.extract_from_audit_snapshot(snapshot)

        shadow = result["contextdev_visual_enrichment_shadow"]
        self.assertEqual(shadow["status"], "evaluated")
        self.assertEqual(shadow["field_updates"][0]["candidate_type"], "visual_colors")

    def test_contextdev_visual_enrichment_shadow_is_absent_when_flag_is_disabled(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 510, "brand_name": "Audit Brand", "url": "https://audit.test"},
            "features": [],
            "raw_inputs": [],
            "evidence_items": [],
            "contextdev_candidate_summary": {
                "candidate_count": 1,
                "candidates": [
                    {
                        "candidate_id": "ctxdev_visual_fonts_1",
                        "candidate_type": "visual_fonts",
                        "supports_channel": "visual_identity",
                        "text": "Aeonik, Twklausanne",
                        "source_url": "https://audit.test",
                        "provider": "contextdev",
                        "raw_ref": "test",
                    }
                ],
            },
        }

        with unittest.mock.patch("src.features.magnetism.extractor.BRAND3_MAGNETISM_RESEARCH_PACK_TLDR", False), \
             unittest.mock.patch("src.features.magnetism.extractor.BRAND3_BRAND_RESEARCH_GRAPH_PACK", False), \
             unittest.mock.patch("src.features.magnetism.extractor.BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT", False):
            result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertNotIn("contextdev_visual_enrichment_shadow", result)

    def test_extract_from_audit_snapshot_does_not_surface_acquisition_lab_payload(self):
        extractor = MagnetismExtractor(llm=None)
        snapshot = {
            "run": {"id": 508, "brand_name": "SigmaOS", "url": "https://sigmaos.com"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "brand_research_acquisition_plan",
                    "payload": {"resolved_entity": "SigmaOS"},
                },
                {
                    "source": "brand_research_acquisition_trace",
                    "payload": {"coverage": {"planned_sources": 1}},
                },
                {
                    "source": "brand_research_acquisition_quality",
                    "payload": {"score": 72, "label": "degraded"},
                },
                {
                    "source": "web",
                    "payload": {
                        "canonical_url": "https://sigmaos.com",
                        "markdown_content": "SigmaOS is a browser that organizes tabs into workspaces.",
                    },
                },
            ],
            "evidence_items": [],
        }

        with unittest.mock.patch("src.features.magnetism.extractor.BRAND3_MAGNETISM_RESEARCH_PACK_TLDR", False), \
             unittest.mock.patch("src.features.magnetism.extractor.BRAND3_BRAND_RESEARCH_GRAPH_PACK", False):
            result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(result["source"], "brand_audit_snapshot")
        self.assertNotIn("brand_research_acquisition_plan", result)
        self.assertNotIn("brand_research_acquisition_trace", result)
        self.assertNotIn("brand_research_acquisition_quality", result)

    def test_research_pack_tldr_flag_falls_back_when_llm_fails(self):
        fake_llm = FakeLLMAnalyzer()
        fake_llm.mock_response = {}
        extractor = MagnetismExtractor(llm=fake_llm)  # type: ignore[arg-type]
        snapshot = {
            "run": {"id": 506, "brand_name": "Base44", "url": "https://base44.com"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "canonical_url": "https://base44.com",
                        "markdown_content": "Base44 is an AI app builder for non-technical founders.",
                    },
                },
                {
                    "source": "entity_research_packet",
                    "payload": {
                        "input_url": "https://base44.com",
                        "audited_surface_type": "parent_home",
                        "entity_name": "Base44",
                        "parent_brand": None,
                        "product_name": None,
                        "brand_architecture": "single_brand_surface",
                        "owned_surfaces": [
                            {
                                "url": "https://base44.com",
                                "role": "audited_surface",
                                "entity_scope": "audited_surface",
                                "reason": "input",
                            }
                        ],
                        "limitations": [],
                    },
                },
            ],
            "evidence_items": [],
        }

        with unittest.mock.patch("src.features.magnetism.extractor.BRAND3_MAGNETISM_RESEARCH_PACK_TLDR", True), \
             unittest.mock.patch.object(extractor, "_extract_via_llm", return_value=None):
            result = extractor.extract_from_audit_snapshot(snapshot)

        self.assertEqual(result["tldr_generation_mode"], "legacy_fallback_llm_error")
        self.assertIn("legacy_tldr_brand3", result)
        self.assertIn("warnings", result)
        self.assertTrue(result["warnings"])
        self.assertIn("analyst_tldr_validated", result)
        self.assertIn("analyst_tldr_analysis_error", result)
        self.assertEqual(result["tldr_brand3"], result["legacy_tldr_brand3"])

    def test_magnetism_status_page_shows_scanner_phase_steps(self):
        from web.workers.queue import set_run_magnetism_override

        release = threading.Event()

        def slow_magnetism(job: dict, progress_cb=None) -> dict:
            if progress_cb is not None:
                progress_cb("interpreting")
            release.wait(timeout=5)
            return {
                "brand_name": "Waiting Brand",
                "url": "Manual Upload",
                "magnetism_score": 51,
                "coherence_score": 57,
                "quadrant": "Low Magnetism - Low Coherence",
                "source": "legacy_extraction",
                "extraction_mode": "legacy_extraction",
                "metrics": {},
                "tldr_brand3": {},
                "magenta_circle": {},
            }

        set_run_magnetism_override(slow_magnetism)
        self._unlock_team_cookie()
        response = self.client.post(
            "/magnetism-scanner/analyze",
            data={"url": "", "manual_text": "We build useful tools."},
            follow_redirects=False,
        )
        status_url = response.headers["location"]
        token = status_url.split("/")[2]

        from web.storage import get_magnetism_scan_by_token

        row = None
        for _ in range(30):
            row = get_magnetism_scan_by_token(token)
            if row and row["status"] == "running" and row["phase"] == "interpreting":
                break
            time.sleep(0.2)

        try:
            self.assertEqual(row["status"], "running")
            self.assertEqual(row["phase"], "interpreting")
            status_resp = self.client.get(status_url, follow_redirects=False)
            self.assertEqual(status_resp.status_code, 200)
            self.assertIn("brand_scanner_status", status_resp.text)
            self.assertIn("Recopilando web pública", status_resp.text)
            self.assertIn("Leyendo señales externas", status_resp.text)
            self.assertIn("Construyendo evidencia", status_resp.text)
            self.assertIn("Calculando salud de marca", status_resp.text)
            self.assertIn("Generando TLDR estratégico", status_resp.text)
            self.assertIn("Esta lista muestra la fase del Brand3 Scanner", status_resp.text)

            status_resp_en = self.client.get(status_url.replace("?lang=es", "?lang=en"), follow_redirects=False)
            self.assertEqual(status_resp_en.status_code, 200)
            self.assertIn("Collecting public web evidence", status_resp_en.text)
            self.assertIn("Reading external signals", status_resp_en.text)
            self.assertIn("Building evidence", status_resp_en.text)
            self.assertIn("Calculating brand health", status_resp_en.text)
            self.assertIn("Generating strategic TLDR", status_resp_en.text)
            self.assertIn("This list shows the Brand3 Scanner phase", status_resp_en.text)
            self.assertNotIn("Recopilando web pública", status_resp_en.text)
        finally:
            release.set()


    def test_web_routes_flow(self):
        from web.workers.queue import set_run_magnetism_override

        def fake_manual_magnetism(job: dict) -> dict:
            return MagnetismExtractor(llm=None).extract(
                url=None,
                manual_text=job.get("input_value") or "",
            )

        set_run_magnetism_override(fake_manual_magnetism)
        self._unlock_team_cookie()
        # GET index page when empty
        r = self.client.get("/magnetism-scanner")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Brand3 Scanner", r.text)
        self.assertIn("Analizar marca", r.text)
        self.assertIn("Auditoría, evidencia y TLDR estratégico de una marca pública.", r.text)
        self.assertIn("Resultado incluido", r.text)
        self.assertIn("TLDR Brand3", r.text)
        self.assertIn("Auditoría de Marca", r.text)
        self.assertIn("legacy/debug, no comparable", r.text)
        self.assertIn("evita la adquisición de Brand Audit", r.text)
        self.assertIn("todavía no hay escaneos Magnetism", r.text)

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
        # Should redirect to status page while the queued scan runs.
        self.assertEqual(r_ok.status_code, 303)
        status_url = r_ok.headers["location"]
        self.assertRegex(status_url, r"^/magnetism-scanner/.+/status\?lang=es$")
        r_status = self.client.get(status_url, follow_redirects=False)
        self.assertIn(r_status.status_code, {200, 303})

        token = status_url.split("/")[2]
        from web.storage import get_magnetism_scan_by_token

        scan = None
        for _ in range(30):
            scan = get_magnetism_scan_by_token(token)
            if scan and scan["status"] == "ready":
                break
            time.sleep(0.2)
        self.assertEqual(scan["status"], "ready")
        redirect_url = f"/magnetism-scanner/scan/{scan['id']}"

        # Follow redirect or GET detail page
        r_detail = self.client.get(redirect_url)
        self.assertEqual(r_detail.status_code, 200)
        self.assertIn("Legacy Direct Extraction", r_detail.text)
        self.assertIn("legacy_extraction", r_detail.text)
        self.assertIn("Manual Upload Brand", r_detail.text)
        self.assertIn("TLDR Brand3", r_detail.text)
        self.assertIn("9 bloques estratégicos derivados de 7 señales Magenta", r_detail.text)
        self.assertIn("source signal: Emotions → Magnetism", r_detail.text)
        self.assertIn("Method notes", r_detail.text)
        self.assertIn("Evidence", r_detail.text)
        self.assertIn("evidence_basis:", r_detail.text)
        self.assertIn("Detalles de metodología", r_detail.text)

        # GET non-existent detail
        r_not_found = self.client.get("/magnetism-scanner/scan/99999")
        self.assertEqual(r_not_found.status_code, 404)

        # GET index showing past scan
        r_index_populated = self.client.get("/magnetism-scanner")
        self.assertEqual(r_index_populated.status_code, 200)
        self.assertIn("Manual Upload Brand", r_index_populated.text)
        self.assertNotIn("todavía no hay escaneos Magnetism", r_index_populated.text)

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


def test_entity_research_parent_surfaces_improve_lab_product_tldr():
    extractor = MagnetismExtractor(llm=None)
    snapshot = {
        "run": {"id": 144, "brand_name": "tinyNature", "url": "https://lab.naturaumana.ai"},
        "features": [],
        "raw_inputs": [
            {
                "source": "entity_research_packet",
                "payload": {
                    "version": "entity_research_packet_v0_1",
                    "input_url": "https://lab.naturaumana.ai",
                    "audited_surface_type": "product_lab",
                    "entity_name": "tinyNature",
                    "parent_brand": "Natura Umana",
                    "product_name": "tinyNature",
                    "brand_architecture": "parent_brand_with_product_surface",
                    "owned_surfaces": [
                        {"url": "https://lab.naturaumana.ai", "role": "audited_surface", "entity_scope": "audited_surface", "reason": "input"},
                        {"url": "https://www.naturaumana.ai/mission", "role": "mission_about", "entity_scope": "parent_brand", "reason": "mission"},
                        {"url": "https://www.naturaumana.ai/natureos", "role": "product_system", "entity_scope": "parent_brand", "reason": "system"},
                        {"url": "https://www.naturaumana.ai/privacy-policy", "role": "policy_security", "entity_scope": "parent_brand", "reason": "privacy"},
                    ],
                },
            },
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://lab.naturaumana.ai",
                    "markdown_content": (
                        "Life orchestration, perfected by nature.\n"
                        "tinyNature is a personal AI assistant platform for life orchestration.\n"
                        "tinyNature is not just a chatbot; it is a command center.\n"
                        "---\n"
                        "## Subpage: https://www.naturaumana.ai/mission\n"
                        "Our mission is to build technology that enhances life without distraction.\n"
                        "We are building the future of human-machine interaction through voice-first personal agents.\n"
                        "---\n"
                        "## Subpage: https://www.naturaumana.ai/privacy-policy\n"
                        "Privacy first. Your data stays yours. Security is at the core."
                    ),
                },
            },
        ],
        "evidence_items": [],
    }

    result = extractor.extract_from_audit_snapshot(snapshot)
    tldr = result["tldr_brand3"]

    assert tldr["value_proposition"]["detected"] is True
    assert "personal AI assistant" in tldr["value_proposition"]["answer"]
    assert tldr["mission"]["detected"] is True
    assert "enhances life without distraction" in tldr["mission"]["answer"]
    assert tldr["vision"]["detected"] is True
    assert "future of human-machine interaction" in tldr["vision"]["answer"]
    assert tldr["values"]["detected"] is True
    assert set(item.lower() for item in tldr["values"]["answer"]) & {"privacy", "security"}

if __name__ == "__main__":
    unittest.main()
