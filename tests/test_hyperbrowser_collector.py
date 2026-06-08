from __future__ import annotations

from src.collectors.hyperbrowser_collector import (
    HyperbrowserCollector,
    branding_summary,
)


def test_hyperbrowser_fetch_response_normalizes_core_outputs() -> None:
    collector = HyperbrowserCollector(api_key="test")

    data = collector._normalize_response(
        "https://example.com",
        {
            "jobId": "job_123",
            "status": "completed",
            "data": {
                "metadata": {"title": "Example", "sourceURL": "https://example.com"},
                "markdown": "# Example\n\nBody",
                "html": "<h1>Example</h1>",
                "links": ["https://www.iana.org/domains/example", ""],
                "screenshot": "https://cdn.example/screenshot.png",
                "branding": {
                    "colorScheme": "light",
                    "colors": {"primary": "#111111", "background": "#ffffff"},
                    "fonts": [{"family": "Inter", "role": "body"}],
                    "images": {"logo": "https://example.com/logo.svg"},
                    "confidence": {"overall": 0.8},
                },
            },
        },
        elapsed_ms=42,
    )

    assert data.job_id == "job_123"
    assert data.status == "completed"
    assert data.title == "Example"
    assert data.text_chars == len("# Example\n\nBody")
    assert data.html_chars == len("<h1>Example</h1>")
    assert data.links == ["https://www.iana.org/domains/example"]
    assert data.screenshot
    assert data.error == ""


def test_hyperbrowser_fetch_response_extracts_json_payload_from_data() -> None:
    collector = HyperbrowserCollector(api_key="test")

    data = collector._normalize_response(
        "https://example.com",
        {
            "jobId": "job_456",
            "status": "completed",
            "data": {
                "metadata": {"title": "JSON Brand", "sourceURL": "https://example.com"},
                "markdown": "payload body",
                "json": {"offer": "Example offer", "audience": "Everyone", "proofPoints": ["A", "B"]},
            },
        },
        elapsed_ms=99,
    )

    assert data.json_payload == {"offer": "Example offer", "audience": "Everyone", "proofPoints": ["A", "B"]}


def test_branding_summary_is_conservative_with_missing_fields() -> None:
    summary = branding_summary(
        {
            "colorScheme": "dark",
            "colors": {"primary": "#000", "secondary": ""},
            "fonts": [{"family": "Geist"}],
            "images": {"favicon": "https://example.com/favicon.ico"},
            "confidence": {"overall": 0.7},
        }
    )

    assert summary == {
        "color_scheme": "dark",
        "color_count": 1,
        "font_count": 1,
        "logo_detected": True,
        "overall_confidence": 0.7,
    }


def test_search_payload() -> None:
    collector = HyperbrowserCollector(api_key="test")
    captured: dict[str, object] = {}

    def _post(payload, *, endpoint):
        captured["payload"] = payload
        captured["endpoint"] = endpoint
        return {"status": "completed", "results": [{"title": "Test", "url": "https://example.com"}]}

    collector._post = _post  # type: ignore[method-assign]

    response = collector.search("acme", limit=7)

    assert response["status"] == "completed"
    assert str(captured["endpoint"]).endswith("/search")
    assert captured["payload"] == {"query": "acme", "limit": 7}


def test_extract_waits_for_completion_when_job_is_pending() -> None:
    collector = HyperbrowserCollector(api_key="test")
    states = [
        {"status": "running", "jobId": "job_1"},
        {"status": "completed", "data": {"results": ["done"]}},
    ]

    def _post(payload, *, endpoint):
        captured["post_called"] = True
        return states[0]

    captured = {"post_called": False, "get_calls": 0}

    def _get(*, endpoint):  # noqa: ARG001
        captured["get_calls"] += 1
        state = states.pop(0)
        return state

    collector._post = _post  # type: ignore[method-assign]
    collector._get = _get  # type: ignore[method-assign]
    collector._wait_for_job = collector._wait_for_job  # keep real wait loop
    result = collector.extract(
        ["https://example.com"],
        wait_for_completion=True,
        max_wait_seconds=1,
        poll_interval_seconds=0,
    )

    assert captured["post_called"] is True
    assert captured["get_calls"] >= 1
    assert result["status"] == "completed"


def test_extract_falls_back_to_api_extract_on_not_found() -> None:
    collector = HyperbrowserCollector(api_key="test")
    calls: list[str] = []

    def _post(payload, *, endpoint):  # noqa: ARG001
        calls.append(endpoint)
        if endpoint.endswith("/api/web/extract"):
            return {"status": "error", "error": "Not Found: Cannot POST /api/web/extract"}
        return {"status": "completed", "json": {"offer": "test offer"}}

    collector._post = _post  # type: ignore[method-assign]

    response = collector.extract("https://example.com", wait_for_completion=False)

    assert calls == [
        "https://api.hyperbrowser.ai/api/web/extract",
        "https://api.hyperbrowser.ai/api/extract",
    ]
    assert response["status"] == "completed"
    assert response["_hyperbrowser_extract_endpoint"] == "https://api.hyperbrowser.ai/api/extract"
