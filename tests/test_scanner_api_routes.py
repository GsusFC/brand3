import json

import pytest
from fastapi.responses import JSONResponse

from web.routes import scanner_api
from web.scanner_api.schemas import ScannerErrorResponse
from web.middleware.scanner_api_auth import scanner_api_error_response

pytestmark = pytest.mark.anyio


def _json_response_payload(response: JSONResponse) -> dict:
    return json.loads(response.body.decode("utf-8"))


def test_scanner_api_error_response_matches_public_contract():
    response = scanner_api_error_response(
        401,
        code="scanner_api_unauthorized",
        message="Missing or invalid Scanner API token.",
    )

    assert response.status_code == 401
    assert ScannerErrorResponse.model_validate(_json_response_payload(response))


async def test_ready_scan_row_or_error_returns_404_for_missing_scan(monkeypatch):
    monkeypatch.setattr(scanner_api, "get_magnetism_scan", lambda scan_id: None)

    response = await scanner_api._ready_scan_row_or_error(123)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert ScannerErrorResponse.model_validate(_json_response_payload(response))


async def test_ready_scan_row_or_error_returns_409_for_unready_scan(monkeypatch):
    monkeypatch.setattr(
        scanner_api,
        "get_magnetism_scan",
        lambda scan_id: {"id": scan_id, "status": "queued", "phase": "queued"},
    )
    monkeypatch.setattr(
        scanner_api,
        "_api_scan_status",
        lambda row, lang="es": {
            "id": row["id"],
            "status": row["status"],
            "phase": "queued",
            "brand_name": None,
            "url": None,
            "source_run_id": None,
            "created_at": None,
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "failure_diagnostics": None,
            "scanner_readiness": {
                "status": "degraded",
                "publishable": False,
                "reason_codes": ["pending"],
            },
            "scan_mode": {"mode": "unknown", "comparable": False, "reason_codes": ["pending"]},
            "result_available": False,
            "status_url": f"/api/v1/scanner/{row['id']}",
            "result_url": f"/api/v1/scanner/{row['id']}/result",
            "evidence_url": f"/api/v1/scanner/{row['id']}/evidence",
            "methodology_url": f"/api/v1/scanner/{row['id']}/methodology",
            "audit_url": f"/api/v1/scanner/{row['id']}/audit",
            "strategic_reading_url": f"/api/v1/scanner/{row['id']}/strategic-reading",
            "ui_url": None,
        },
    )

    response = await scanner_api._ready_scan_row_or_error(123)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 409
    parsed = ScannerErrorResponse.model_validate(_json_response_payload(response))
    assert parsed.error.status is not None
    assert parsed.error.status.id == 123


async def test_ready_scan_row_or_error_returns_ready_row(monkeypatch):
    row = {"id": 123, "status": "ready"}
    monkeypatch.setattr(scanner_api, "get_magnetism_scan", lambda scan_id: row)

    assert await scanner_api._ready_scan_row_or_error(123) == row
