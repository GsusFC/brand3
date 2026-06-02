from __future__ import annotations

import json
from unittest.mock import patch

from scripts.contextdev_capability_benchmark import (
    ContextDevBenchmarkCase,
    ContextDevClient,
    run_case,
    summarize_capability_payload,
    summarize_contextdev_capability_benchmark,
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


def test_contextdev_client_sends_auth_user_agent_and_json_body() -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["method"] = request.method
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["auth"] = request.headers["Authorization"]
        captured["user_agent"] = request.headers["User-agent"]
        captured["timeout"] = timeout
        return _Response({"products": [{"name": "Product A"}]})

    client = ContextDevClient(api_key="test-key", timeout_seconds=12)

    with patch("scripts.contextdev_capability_benchmark.urlopen", fake_urlopen):
        payload = client.post("/brand/ai/products", {"domain": "example.com", "maxProducts": 2})

    assert captured["url"] == "https://api.context.dev/v1/brand/ai/products"
    assert captured["method"] == "POST"
    assert captured["body"] == {"domain": "example.com", "maxProducts": 2}
    assert captured["auth"] == "Bearer test-key"
    assert captured["user_agent"] == "Brand3-Lab/0.1"
    assert captured["timeout"] == 12
    assert payload["products"][0]["name"] == "Product A"


def test_run_case_calls_expected_contextdev_capability_endpoints() -> None:
    urls = []

    def fake_urlopen(request, timeout):
        urls.append(request.full_url)
        if "/brand/retrieve" in request.full_url:
            return _Response({"brand": {"title": "Example", "description": "Example company", "colors": [{"hex": "#000"}], "logos": [{"url": "logo"}], "industries": {"naics": []}}})
        if "/web/styleguide" in request.full_url:
            return _Response({"styleguide": {"colors": {"text": "#111"}, "typography": {"p": {}}, "components": {"button": {}}}})
        if "/web/fonts" in request.full_url:
            return _Response({"fonts": [{"font": "Example Sans"}]})
        if "/web/scrape/images" in request.full_url:
            return _Response({"images": [{"url": "https://example.com/image.png"}]})
        if "/web/screenshot" in request.full_url:
            return _Response({"screenshot": "https://cdn.example.com/screen.png", "screenshotType": "viewport"})
        if "/brand/ai/products" in request.full_url:
            return _Response({"products": [{"name": "Example Product"}]})
        return _Response({"status": "error", "error": "unexpected"})

    client = ContextDevClient(api_key="test-key")
    case = ContextDevBenchmarkCase("Example", "https://www.example.com", label="example")

    with patch("scripts.contextdev_capability_benchmark.urlopen", fake_urlopen):
        payload = run_case(client, case, ["retrieve_brand", "styleguide", "fonts", "images", "screenshot", "products"])

    assert any("/brand/retrieve" in url for url in urls)
    assert any("/web/styleguide" in url for url in urls)
    assert any("/web/fonts" in url for url in urls)
    assert any("/web/scrape/images" in url for url in urls)
    assert any("/web/screenshot" in url for url in urls)
    assert any("/brand/ai/products" in url for url in urls)
    assert payload["summary"]["failed_capabilities"] == []
    assert "entity_resolution" in payload["summary"]["brand3_channel_candidates"]
    assert "visual_identity" in payload["summary"]["brand3_channel_candidates"]
    assert "visual_evidence" in payload["summary"]["brand3_channel_candidates"]
    assert "product_extraction" in payload["summary"]["brand3_channel_candidates"]


def test_summarize_capability_payload_extracts_signal_counts() -> None:
    assert summarize_capability_payload("retrieve_brand", {"brand": {"title": "A", "description": "B", "logos": [{"url": "x"}], "colors": [{"hex": "#fff"}]}})["signal_count"] == 2
    assert summarize_capability_payload("styleguide", {"styleguide": {"colors": {"text": "#111"}, "components": {"button": {}}, "typography": {"p": {}}}})["signal_count"] == 3
    assert summarize_capability_payload("fonts", {"fonts": [{"font": "A"}, {"font": "B"}]})["font_count"] == 2
    assert summarize_capability_payload("images", {"images": [{"url": "https://example.com/a.png"}]})["image_count"] == 1
    assert summarize_capability_payload("screenshot", {"screenshot": "https://example.com/screen.png"})["has_screenshot"] is True
    assert summarize_capability_payload("products", {"products": [{"name": "A"}]})["product_count"] == 1


def test_summarize_contextdev_capability_benchmark_aggregates_cases() -> None:
    payload = {
        "case": {"brand": "Example", "domain": "example.com"},
        "summary": {
            "successful_capabilities": ["retrieve_brand"],
            "failed_capabilities": ["products"],
            "brand3_channel_candidates": ["entity_resolution"],
            "capabilities": {
                "retrieve_brand": {"status": "ok", "signal_count": 4},
                "products": {"status": "error", "signal_count": 0},
            },
        },
    }

    summary = summarize_contextdev_capability_benchmark([payload])

    assert summary["case_count"] == 1
    assert summary["successful_capability_count"] == 1
    assert summary["failed_capability_count"] == 1
    assert summary["capability_metrics"]["retrieve_brand"]["signal_total"] == 4
    assert summary["brand3_channel_candidate_counts"]["entity_resolution"] == 1
