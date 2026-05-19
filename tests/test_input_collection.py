from __future__ import annotations

from src.collectors.exa_collector import ExaData
from src.services.input_collection import _collect_exa_input, from_exa_payload


def test_from_exa_payload_preserves_diagnostics():
    payload = {
        "brand_name": "Brand",
        "mentions": [],
        "competitors": [],
        "ai_visibility_results": [],
        "news": [],
        "raw_responses": {"search_events": []},
        "diagnostics": {"status": "degraded", "failed_intents": ["mentions"]},
    }

    exa = from_exa_payload(payload)

    assert isinstance(exa, ExaData)
    assert exa is not None
    assert exa.diagnostics["status"] == "degraded"
    assert exa.diagnostics["failed_intents"] == ["mentions"]


class _FakeExaCollector:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def collect_brand_data(self, brand_name: str, brand_url: str):
        return ExaData(
            brand_name=brand_name,
            mentions=[],
            news=[],
            diagnostics={"status": "degraded", "failed_intents": ["mentions"], "no_result_intents": []},
        )


def test_collect_exa_input_marks_partial_when_failed_intents_exist():
    raw_input_cache: dict[str, str] = {}

    exa_data, _collector = _collect_exa_input(
        store=None,
        run_id=None,
        brand_name="Brand",
        effective_brand_url="https://brand.com",
        cache_read=lambda *_args, **_kwargs: None,
        raw_input_cache=raw_input_cache,
        exa_collector_cls=_FakeExaCollector,
    )

    assert raw_input_cache["exa"] == "partial"
    assert exa_data.diagnostics["status"] == "degraded"
