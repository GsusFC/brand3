from web.scanner_api.presenters import (
    scanner_methodology_payload,
    scanner_result_metadata,
    scanner_status_payload,
)


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
        lang="en",
    )

    assert payload["result_available"] is True
    assert payload["status_url"] == "/api/v1/scanner/42"
    assert payload["result_url"] == "/api/v1/scanner/42/result"
    assert payload["evidence_url"] == "/api/v1/scanner/42/evidence"
    assert payload["methodology_url"] == "/api/v1/scanner/42/methodology"
    assert payload["audit_url"] == "/api/v1/scanner/42/audit"
    assert payload["ui_url"] == "/magnetism-scanner/scan/42?lang=en"
    assert payload["scanner_readiness"]["status"] == "publishable"


def test_scanner_status_payload_hides_ui_url_until_ready():
    payload = scanner_status_payload(
        {"id": 42, "status": "running"},
        phase="extracting",
        readiness={"status": "degraded", "publishable": False, "reason_codes": ["pending"]},
    )

    assert payload["phase"] == "extracting"
    assert payload["result_available"] is False
    assert payload["ui_url"] is None


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
        publication_decision={"status": "publishable", "publishable": True},
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
