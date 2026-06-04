from web.scanner_api.presenters import scanner_status_payload


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
