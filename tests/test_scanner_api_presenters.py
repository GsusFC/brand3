import json

from web.scanner_api.models import scanner_failure_diagnostics_from_row, scanner_readiness_from_row
from web.scanner_api.presenters import (
    scanner_methodology_payload,
    scanner_research_evidence_payload,
    scanner_result_payload,
    scanner_result_metadata,
    scanner_status_payload,
)
from web.scanner_api.schemas import (
    FailureDiagnostics,
    ScannerAuditResponse,
    ScannerAuditSnapshotResponse,
    ScannerEvidenceResponse,
    ScannerMethodologyResponse,
    ScannerResultMetadata,
    ScannerResultResponse,
    ScannerStrategicReadingResponse,
    ScannerStatus,
    scanner_openapi_spec,
)


def _scanner_result_metadata_fixture() -> dict:
    return {
        "result_version": "scanner_result_v1",
        "pipeline_version": "brand3_scanner_pipeline_2026_06_03",
        "generated_with": {
            "audit_snapshot": True,
            "research_pack": True,
            "evidence_graph": True,
            "analyst_pass": True,
            "research_pack_quality": True,
            "parallel_shadow": False,
        },
        "scanner_readiness": {
            "status": "publishable",
            "publishable": True,
            "reason_codes": [],
        },
        "publication_decision": {
            "version": "publication_decision_v1",
            "surface": "magnetism_scan",
            "status": "publishable",
            "publishable": True,
            "listable": True,
            "ui_readable": True,
            "api_readable": True,
            "reason_codes": [],
            "source_status": "publishable",
            "source_version": "",
        },
        "stale_against_current_pipeline": False,
        "scan_mode": {"mode": "from_audit_run", "comparable": True, "reason_codes": []},
    }


def test_scanner_readiness_from_row_uses_payload_manual_detection_without_input_type():
    readiness = scanner_readiness_from_row(
        {
            "source_run_id": None,
            "input_type": None,
            "raw_payload": json.dumps(
                {
                    "source": "direct_magnetism_legacy",
                    "direct_source_provider": "manual_evidence",
                    "url": "manual",
                }
            ),
        }
    )

    assert readiness["status"] == "debug_only"
    assert "manual_input_debug_path" in readiness["reason_codes"]


def test_scanner_status_payload_exposes_stable_urls_for_ready_scan():
    payload = scanner_status_payload(
        {
            "id": 42,
            "status": "ready",
            "phase": "ready",
            "brand_name": "Example",
            "url": "https://example.com",
            "source_run_id": 7,
            "created_at": "2026-06-04T10:00:00",
            "started_at": "2026-06-04T10:00:01",
            "completed_at": "2026-06-04T10:00:02",
            "error_message": None,
        },
        phase="ready",
        readiness={"status": "publishable", "publishable": True, "reason_codes": []},
        scan_mode={"mode": "from_audit_run", "comparable": True, "reason_codes": []},
        lang="en",
    )

    assert payload["result_available"] is True
    assert payload["status_url"] == "/api/v1/scanner/42"
    assert payload["result_url"] == "/api/v1/scanner/42/result"
    assert payload["evidence_url"] == "/api/v1/scanner/42/evidence"
    assert payload["methodology_url"] == "/api/v1/scanner/42/methodology"
    assert payload["audit_url"] == "/api/v1/scanner/42/audit"
    assert payload["strategic_reading_url"] == "/api/v1/scanner/42/strategic-reading"
    assert payload["ui_url"] == "/magnetism-scanner/scan/42?lang=en"
    assert payload["scanner_readiness"]["status"] == "publishable"
    assert payload["scan_mode"]["mode"] == "from_audit_run"
    assert payload["scan_mode"]["comparable"] is True
    assert payload["failure_diagnostics"] is None
    assert ScannerStatus.model_validate(payload).id == 42


def test_scanner_status_payload_uses_sv9_as_primary_ui_when_available():
    payload = scanner_status_payload(
        {
            "id": 42,
            "status": "ready",
            "phase": "ready",
            "brand_name": "Example",
            "url": "https://example.com",
            "source_run_id": 7,
        },
        phase="ready",
        readiness={"status": "publishable", "publishable": True, "reason_codes": []},
        scan_mode={"mode": "from_audit_run", "comparable": True, "reason_codes": []},
        sv9_scan_id=99,
        lang="en",
    )

    assert payload["sv9_scan_id"] == 99
    assert payload["sv9_url"] == "/sv9/scan/99"
    assert payload["ui_url"] == "/sv9/scan/99"
    assert ScannerStatus.model_validate(payload).sv9_scan_id == 99


def test_scanner_status_payload_hides_ui_url_until_ready():
    payload = scanner_status_payload(
        {"id": 42, "status": "running"},
        phase="extracting",
        readiness={"status": "degraded", "publishable": False, "reason_codes": ["pending"]},
        scan_mode={"mode": "canonical_url", "comparable": True, "reason_codes": []},
    )

    assert payload["phase"] == "extracting"
    assert payload["result_available"] is False
    assert payload["ui_url"] is None
    assert payload["scan_mode"]["mode"] == "canonical_url"
    assert ScannerStatus.model_validate(payload).status == "running"


def test_failure_diagnostics_from_failed_tldr_timeout_is_safe():
    diagnostics = scanner_failure_diagnostics_from_row(
        {
            "id": 42,
            "status": "failed",
            "phase": "failed",
            "error_message": "failed:canonical_tldr_degraded:llm_timeout",
            "raw_payload": json.dumps(
                {
                    "scanner_readiness": {
                        "status": "failed",
                        "publishable": False,
                        "reason_codes": ["canonical_tldr_degraded:llm_timeout"],
                    },
                    "analyst_tldr_analysis_error": {
                        "reason": "llm_timeout",
                        "detail": "secret-ish raw provider detail should not leak",
                        "error_type": "timeout",
                        "model": "gemini-test",
                    },
                }
            ),
        }
    )

    assert diagnostics == {
        "available": True,
        "component": "analyst_tldr",
        "phase": "failed",
        "reason_code": "canonical_tldr_degraded:llm_timeout",
        "failure_type": "timeout",
        "retryable": True,
        "safe_message": "The Analyst Pass LLM call timed out before producing a publishable TLDR.",
        "model": "gemini-test",
        "error_type": "timeout",
    }
    assert "secret-ish" not in json.dumps(diagnostics)
    assert FailureDiagnostics.model_validate(diagnostics).failure_type == "timeout"


def test_scanner_result_payload_exposes_stable_section_urls_and_audit_link():
    result_metadata = _scanner_result_metadata_fixture()
    payload = scanner_result_payload(
        {"status": "ready"},
        {
            "id": 42,
            "brand_name": "Example",
            "url": "https://example.com",
            "created_at": "June 04, 2026 at 10:00 AM UTC",
            "magnetism_score": 74,
            "coherence_score": 81,
            "quadrant": "Clear",
            "scan_mode": {"mode": "from_audit_run", "comparable": True, "reason_codes": []},
            "source_run_id": 7,
            "payload": {
                "tldr_brand3": {"value_proposition": {"answer": "Example value."}},
                "tldr_strategy": {"mode": "llm_analyst_pass"},
            },
        },
        result_metadata=result_metadata,
        lang="en",
    )

    assert payload["scores"] == {
        "magnetism": 74,
        "coherence": 81,
        "quadrant": "Clear",
    }
    assert payload["audit"] == {
        "available": True,
        "source_run_id": 7,
        "api_url": "/api/v1/scanner/42/audit",
    }
    assert payload["evidence_api_url"] == "/api/v1/scanner/42/evidence"
    assert payload["methodology_api_url"] == "/api/v1/scanner/42/methodology"
    assert payload["strategic_reading_api_url"] == "/api/v1/scanner/42/strategic-reading"
    assert payload["ui_url"] == "/magnetism-scanner/scan/42?lang=en"
    assert payload["result_metadata"]["result_version"] == "scanner_result_v1"
    assert ScannerResultResponse.model_validate(payload).id == 42


def test_scanner_result_payload_uses_sv9_as_primary_ui_when_available():
    result_metadata = _scanner_result_metadata_fixture()
    payload = scanner_result_payload(
        {"status": "ready"},
        {
            "id": 42,
            "brand_name": "Example",
            "url": "https://example.com",
            "created_at": "June 04, 2026 at 10:00 AM UTC",
            "magnetism_score": 74,
            "coherence_score": 81,
            "quadrant": "Clear",
            "scan_mode": {"mode": "from_audit_run", "comparable": True, "reason_codes": []},
            "source_run_id": 7,
            "payload": {"tldr_brand3": {}, "tldr_strategy": {}},
        },
        result_metadata=result_metadata,
        sv9_scan_id=99,
        lang="en",
    )

    assert payload["sv9_scan_id"] == 99
    assert payload["sv9_url"] == "/sv9/scan/99"
    assert payload["ui_url"] == "/sv9/scan/99"
    assert ScannerResultResponse.model_validate(payload).sv9_scan_id == 99


def test_scanner_result_metadata_reports_current_pipeline_inputs():
    metadata = scanner_result_metadata(
        {
            "source_run_id": 7,
            "research_pack": {"shadow_sources": [{"provider": "parallel"}]},
            "research_pack_quality": {"status": "pass"},
            "evidence_graph_summary": {"nodes": 3},
            "research_pack_source": "evidence_graph",
            "tldr_generation_mode": "analyst_pass_validated",
        },
        scanner_readiness={"status": "publishable", "publishable": True, "reason_codes": []},
        publication_decision={
            "version": "publication_decision_v1",
            "surface": "magnetism_scan",
            "status": "publishable",
            "publishable": True,
            "listable": True,
            "ui_readable": True,
            "api_readable": True,
            "reason_codes": [],
            "source_status": "publishable",
            "source_version": "",
        },
    )

    assert metadata["result_version"] == "scanner_result_v1"
    assert metadata["generated_with"] == {
        "audit_snapshot": True,
        "research_pack": True,
        "evidence_graph": True,
        "analyst_pass": True,
        "research_pack_quality": True,
        "parallel_shadow": True,
    }
    assert metadata["stale_against_current_pipeline"] is False
    assert metadata["scanner_readiness"]["status"] == "publishable"
    assert metadata["publication_decision"]["status"] == "publishable"
    assert ScannerResultMetadata.model_validate(metadata).result_version == "scanner_result_v1"


def test_scanner_methodology_payload_uses_defaults_for_legacy_payloads():
    payload = scanner_methodology_payload(
        {
            "metrics": {"clarity": 70},
            "score_breakdown": {"offer": 0.7},
            "limitations": ["limited evidence"],
        },
        result_metadata={"result_version": "scanner_result_v1"},
    )

    assert payload["result_metadata"]["result_version"] == "scanner_result_v1"
    assert payload["tldr_generation_mode"] == "unknown"
    assert payload["research_pack_source"] == "legacy_snapshot"
    assert payload["metrics"] == {"clarity": 70}
    assert payload["score_breakdown"] == {"offer": 0.7}
    assert payload["limitations"] == ["limited evidence"]
    assert payload["research_pack"] == {}


def test_scanner_methodology_response_contract_accepts_stable_envelope():
    methodology = scanner_methodology_payload(
        {
            "metrics": {"clarity": 70},
            "score_breakdown": {"offer": 0.7},
            "limitations": ["limited evidence"],
        },
        result_metadata=_scanner_result_metadata_fixture(),
    )

    envelope = {"id": 42, "brand_name": "Example", "methodology": methodology}

    assert ScannerMethodologyResponse.model_validate(envelope).id == 42


def test_scanner_evidence_response_contract_accepts_flexible_body():
    envelope = {
        "id": 42,
        "brand_name": "Example",
        "evidence": {
            "research_pack_source": "evidence_graph",
            "block_evidence": [{"key": "value_proposition"}],
        },
    }

    assert ScannerEvidenceResponse.model_validate(envelope).brand_name == "Example"


def test_scanner_audit_response_contract_accepts_available_and_missing_shapes():
    available = {
        "id": 42,
        "available": True,
        "source_run_id": 7,
        "run": {
            "id": 7,
            "brand_name": "Example",
            "url": "https://example.com",
            "composite_score": 74.0,
            "completed_at": "2026-06-04T10:00:00",
        },
        "audit": {"summary": "Example audit."},
    }
    missing = {"id": 43, "available": False, "reason": "missing_source_run"}

    assert ScannerAuditResponse.model_validate(available).source_run_id == 7
    assert ScannerAuditResponse.model_validate(missing).reason == "missing_source_run"


def test_scanner_audit_snapshot_response_contract_accepts_available_and_missing_shapes():
    available = {
        "id": 42,
        "available": True,
        "source_run_id": 7,
        "run": {
            "id": 7,
            "brand_name": "Example",
            "url": "https://example.com",
            "composite_score": 74.0,
            "completed_at": "2026-06-04T10:00:00",
        },
        "debug": {
            "raw_inputs": [{"source": "web", "payload": {"url": "https://example.com"}}],
            "counts": {"raw_inputs": 1, "features": 0, "evidence_items": 0},
        },
    }
    missing = {"id": 43, "available": False, "reason": "missing_source_run"}

    assert ScannerAuditSnapshotResponse.model_validate(available).source_run_id == 7
    assert ScannerAuditSnapshotResponse.model_validate(missing).reason == "missing_source_run"


def test_scanner_strategic_reading_response_contract_accepts_available_and_missing_shapes():
    available = {
        "id": 42,
        "brand_name": "Example",
        "url": "https://example.com",
        "available": True,
        "source_run_id": 7,
        "layer": "client_strategic_reading",
        "internal_name": "client_tldr_v2",
        "client_strategic_reading": {
            "generation_mode": "fallback_client_v2",
            "score_reading": {"status": "computed"},
            "legacy_tldr_brand3_v2": {},
        },
        "ui_url": "/magnetism-scanner/scan/42/client-tldr-v2?lang=en",
    }
    missing = {
        "id": 43,
        "brand_name": "Example",
        "url": "https://example.com",
        "available": False,
        "source_run_id": None,
        "reason": "missing_source_run",
        "layer": "client_strategic_reading",
        "internal_name": "client_tldr_v2",
        "client_strategic_reading": None,
        "ui_url": "/magnetism-scanner/scan/43/client-tldr-v2?lang=es",
    }

    assert ScannerStrategicReadingResponse.model_validate(available).available is True
    assert ScannerStrategicReadingResponse.model_validate(missing).reason == "missing_source_run"


def test_scanner_openapi_spec_exposes_strategic_reading_endpoint():
    spec = scanner_openapi_spec()

    assert "/api/v1/scanner/{scan_id}/strategic-reading" in spec["paths"]
    assert "ScannerStrategicReadingResponse" in spec["components"]["schemas"]
    assert "/api/v1/scanner/{scan_id}/audit-snapshot" in spec["paths"]
    assert "ScannerAuditSnapshotResponse" in spec["components"]["schemas"]


def test_scanner_research_evidence_payload_falls_back_to_source_map_surfaces():
    payload = scanner_research_evidence_payload(
        {
            "research_pack_source": "evidence_graph",
            "tldr_generation_mode": "analyst_pass_validated",
            "research_pack": {
                "resolved_entity": {"name": "LangChain"},
                "source_map": {
                    "https://langchain.com": {
                        "source_type": "owned_official",
                        "surface_role": "homepage",
                        "entity_scope": "audited_surface",
                    },
                    "https://langchain.com/langgraph": {
                        "source_type": "owned_product",
                        "surface_role": "product_page",
                        "entity_scope": "product:LangGraph",
                    },
                },
                "offer": "Build reliable AI agents.",
            },
            "evidence_graph_summary": {"source_counts": {"owned_official": 1, "owned_product": 1}},
            "analyst_tldr_validated": {
                "tldr_brand3": {
                    "value_proposition": {
                        "answer": "Build reliable AI agents.",
                        "claim_type": "offer",
                        "confidence": "high",
                        "evidence_used": ["Build reliable AI agents."],
                    }
                }
            },
        },
        entity_packet={},
    )

    assert payload["entity"]["name"] == "LangChain"
    assert payload["research_pack_source"] == "evidence_graph"
    assert payload["owned_surfaces"][0]["url"] == "https://langchain.com"
    assert payload["product_surfaces"][0]["entity_scope"] == "product:LangGraph"
    assert payload["source_counts"] == {"owned_official": 1, "owned_product": 1}
    assert payload["block_evidence"][0]["key"] == "value_proposition"
    assert payload["block_evidence"][0]["confidence"] == "high"


def test_scanner_research_evidence_payload_exposes_shadow_and_entity_boundary_review():
    payload = scanner_research_evidence_payload(
        {
            "research_pack": {
                "confidence_notes": [
                    "entity_boundary_collision: near-name result quarantined.",
                    "entity_boundary_collision: near-name result quarantined.",
                    "other note",
                ],
                "noise_rejected": [
                    {
                        "text": "Publicis Media is a separate near-name entity",
                        "topic": "entity_boundary_collision",
                        "source_url": "https://example.com/publicis",
                        "source_type": "external_review",
                    },
                    {
                        "text": "Generic unrelated result",
                        "topic": "noise",
                    },
                ],
                "shadow_sources": [
                    {
                        "provider": "parallel",
                        "mode": "audit",
                        "status": "complete",
                        "result_total": 2,
                        "unique_domain_count": 1,
                        "unique_domains": ["g2.com"],
                        "intents": {
                            "mentions": {
                                "status": "complete",
                                "result_count": 2,
                                "unique_domains": ["g2.com"],
                                "results": [
                                    {
                                        "url": "https://g2.com/example",
                                        "title": "Example reviews",
                                        "excerpt": "Third-party review shadow signal.",
                                    }
                                ],
                            }
                        },
                    }
                ],
            }
        },
        entity_packet={"owned_surfaces": [], "product_surfaces": []},
    )

    assert payload["entity_boundary_warnings"] == [
        "entity_boundary_collision: near-name result quarantined."
    ]
    assert payload["entity_boundary_rejections"] == [
        {
            "text": "Publicis Media is a separate near-name entity",
            "topic": "entity_boundary_collision",
            "source_url": "https://example.com/publicis",
            "source_type": "external_review",
        }
    ]
    shadow = payload["shadow_sources"][0]
    assert shadow["provider"] == "parallel"
    assert shadow["readout"]["domain_summary"] == "g2.com"
    assert shadow["readout"]["signal_types"][0]["label"] == "mentions / reviews / community"
    assert shadow["readout"]["review_candidates"][0]["excerpt"] == "Third-party review shadow signal."
