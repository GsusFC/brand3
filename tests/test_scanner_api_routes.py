from fastapi.responses import JSONResponse

from web.routes import scanner_api


def test_ready_scan_row_or_error_returns_404_for_missing_scan(monkeypatch):
    monkeypatch.setattr(scanner_api, "get_magnetism_scan", lambda scan_id: None)

    response = scanner_api._ready_scan_row_or_error(123)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404


def test_ready_scan_row_or_error_returns_409_for_unready_scan(monkeypatch):
    monkeypatch.setattr(
        scanner_api,
        "get_magnetism_scan",
        lambda scan_id: {"id": scan_id, "status": "queued", "phase": "queued"},
    )
    monkeypatch.setattr(
        scanner_api,
        "_api_scan_status",
        lambda row, lang="es": {"id": row["id"], "status": row["status"]},
    )

    response = scanner_api._ready_scan_row_or_error(123)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 409


def test_ready_scan_row_or_error_returns_ready_row(monkeypatch):
    row = {"id": 123, "status": "ready"}
    monkeypatch.setattr(scanner_api, "get_magnetism_scan", lambda scan_id: row)

    assert scanner_api._ready_scan_row_or_error(123) == row
