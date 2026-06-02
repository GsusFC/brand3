from __future__ import annotations

import json
from unittest.mock import patch

from scripts.brand_intelligence_live_probe import _collect_tinyfish_fetch


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
