from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from scripts.brand_intelligence_live_probe import (
    _collect_contextdev_markdown,
    _collect_tinyfish_fetch,
    _web_data_payload,
)


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_tinyfish_fetch_maps_result_to_web_data(monkeypatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "test-key")

    def fake_urlopen(request, timeout):
        assert request.full_url == "https://api.fetch.tinyfish.ai"
        assert request.headers["X-api-key"] == "test-key"
        assert timeout == 150
        return _Response(
            {
                "results": [
                    {
                        "url": "https://example.com",
                        "final_url": "https://www.example.com",
                        "title": "Example",
                        "description": "Example description",
                        "text": "# Example\nUseful page copy.",
                        "links": ["https://www.example.com/about"],
                        "image_links": ["https://www.example.com/logo.png"],
                        "latency_ms": 123,
                    }
                ],
                "errors": [],
            }
        )

    with patch("scripts.brand_intelligence_live_probe.urlopen", fake_urlopen):
        data = _collect_tinyfish_fetch("https://example.com")

    assert data.content_source == "tinyfish_fetch"
    assert data.canonical_url == "https://www.example.com"
    assert data.title == "Example"
    assert data.meta_description == "Example description"
    assert "Useful page copy" in data.markdown_content
    assert data.links == ["https://www.example.com/about"]
    assert data.images == ["https://www.example.com/logo.png"]
    assert data.load_time_ms == 123
    assert data.error == ""


def test_tinyfish_fetch_preserves_original_input_url_and_canonical_final_url(monkeypatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "test-key")

    def fake_urlopen(request, timeout):
        return _Response(
            {
                "results": [
                    {
                        "url": "https://example.com",
                        "final_url": "https://www.example.com",
                        "title": "Example",
                        "description": "Example description",
                        "text": "# Example\nUseful page copy.",
                        "links": ["https://www.example.com/about"],
                        "image_links": ["https://www.example.com/logo.png"],
                        "latency_ms": 123,
                    }
                ],
                "errors": [],
            }
        )

    with patch("scripts.brand_intelligence_live_probe.urlopen", fake_urlopen):
        data = _collect_tinyfish_fetch("https://example.com")

    downstream_payload = _web_data_payload(data)

    assert data.url == "https://example.com"
    assert data.canonical_url == "https://www.example.com"
    assert downstream_payload["url"] == "https://www.example.com"
    assert data.canonical_url != data.url


def test_tinyfish_fetch_returns_structured_error(monkeypatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "test-key")

    def fake_urlopen(request, timeout):
        return _Response(
            {
                "results": [],
                "errors": [{"url": "https://example.com", "error": "bot_blocked"}],
            }
        )

    with patch("scripts.brand_intelligence_live_probe.urlopen", fake_urlopen):
        data = _collect_tinyfish_fetch("https://example.com")

    assert data.content_source == "tinyfish_fetch"
    assert data.error == "bot_blocked"


def test_contextdev_markdown_maps_response_to_web_data(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXT_DEV_API_KEY", "test-key")

    def fake_urlopen(request, timeout):
        parsed = urlparse(request.full_url)
        query = parse_qs(parsed.query)
        assert parsed.scheme == "https"
        assert parsed.netloc == "api.context.dev"
        assert parsed.path == "/v1/web/scrape/markdown"
        assert query["url"] == ["https://example.com"]
        assert query["includeLinks"] == ["true"]
        assert query["includeImages"] == ["true"]
        assert query["maxAgeMs"] == ["0"]
        assert request.headers["Authorization"] == "Bearer test-key"
        assert request.headers["User-agent"] == "Brand3-Lab/0.1"
        assert timeout == 150
        return _Response(
            {
                "success": True,
                "markdown": "# Example\nUseful page copy.",
                "url": "https://www.example.com",
            }
        )

    with patch("scripts.brand_intelligence_live_probe.urlopen", fake_urlopen):
        data = _collect_contextdev_markdown("https://example.com")

    assert data.content_source == "contextdev_markdown"
    assert data.canonical_url == "https://www.example.com"
    assert "Useful page copy" in data.markdown_content
    assert data.error == ""


def test_contextdev_markdown_returns_structured_error(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXT_DEV_API_KEY", "test-key")

    def fake_urlopen(request, timeout):
        return _Response(
            {
                "status": "error",
                "message": "Brand not found for domain",
                "code": 404,
            }
        )

    with patch("scripts.brand_intelligence_live_probe.urlopen", fake_urlopen):
        data = _collect_contextdev_markdown("https://example.com")

    assert data.content_source == "contextdev_markdown"
    assert data.error == "Brand not found for domain"


def test_contextdev_markdown_reads_http_error_body(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXT_DEV_API_KEY", "test-key")

    def fake_urlopen(request, timeout):
        body = BytesIO(json.dumps({"message": "Insufficient credits"}).encode("utf-8"))
        raise HTTPError(request.full_url, 403, "Forbidden", {}, body)

    with patch("scripts.brand_intelligence_live_probe.urlopen", fake_urlopen):
        data = _collect_contextdev_markdown("https://example.com")

    assert data.content_source == "contextdev_markdown"
    assert data.error == "Insufficient credits"
