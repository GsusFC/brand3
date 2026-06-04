from __future__ import annotations

from src.collectors.exa_collector import ExaData
from src.collectors.parallel_shadow_collector import ParallelShadowData, ParallelShadowIntent, ParallelShadowResult
from src.services.input_collection import (
    _collect_exa_input,
    _collect_parallel_shadow_input,
    from_exa_payload,
)


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
    acquisition_steps: dict[str, object] = {}

    exa_data, _collector = _collect_exa_input(
        store=None,
        run_id=None,
        brand_name="Brand",
        effective_brand_url="https://brand.com",
        cache_read=lambda *_args, **_kwargs: None,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        exa_collector_cls=_FakeExaCollector,
    )

    assert raw_input_cache["exa"] == "partial"
    assert exa_data.diagnostics["status"] == "degraded"
    assert acquisition_steps["exa"].status == "partial"
    assert acquisition_steps["exa"].eligible is True


class _FakeParallelShadowCollector:
    def collect(self, brand_name: str, brand_url: str):
        return ParallelShadowData(
            brand_name=brand_name,
            brand_url=brand_url,
            status="ok",
            intents={
                "mentions": ParallelShadowIntent(
                    intent="mentions",
                    status="ok",
                    result_count=1,
                    unique_domains=["g2.com"],
                    results=[
                        ParallelShadowResult(
                            url="https://g2.com/products/brand/reviews",
                            title="Brand Reviews",
                            excerpt="Shadow review signal.",
                        )
                    ],
                )
            },
        )


def test_collect_parallel_shadow_input_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("BRAND3_PARALLEL_SHADOW_ENABLED", raising=False)
    raw_input_cache: dict[str, str] = {}
    acquisition_steps: dict[str, object] = {}

    result = _collect_parallel_shadow_input(
        store=None,
        run_id=None,
        brand_name="Brand",
        effective_brand_url="https://brand.com",
        cache_read=lambda *_args, **_kwargs: None,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        parallel_shadow_collector_cls=_FakeParallelShadowCollector,
    )

    assert result is None
    assert raw_input_cache["parallel_shadow"] == "disabled"
    assert acquisition_steps["parallel_shadow"].status == "disabled"
    assert acquisition_steps["parallel_shadow"].eligible is False


def test_collect_parallel_shadow_input_runs_when_enabled(monkeypatch):
    monkeypatch.setenv("BRAND3_PARALLEL_SHADOW_ENABLED", "1")
    raw_input_cache: dict[str, str] = {}
    acquisition_steps: dict[str, object] = {}

    result = _collect_parallel_shadow_input(
        store=None,
        run_id=None,
        brand_name="Brand",
        effective_brand_url="https://brand.com",
        cache_read=lambda *_args, **_kwargs: None,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        parallel_shadow_collector_cls=_FakeParallelShadowCollector,
    )

    assert result is not None
    assert result.summary()["result_total"] == 1
    assert raw_input_cache["parallel_shadow"] == "ok"
    assert acquisition_steps["parallel_shadow"].status == "ok"
    assert acquisition_steps["parallel_shadow"].eligible is True


def test_collect_parallel_shadow_input_reuses_cached_payload(monkeypatch):
    monkeypatch.setenv("BRAND3_PARALLEL_SHADOW_ENABLED", "1")
    raw_input_cache: dict[str, str] = {}
    acquisition_steps: dict[str, object] = {}
    cached = _FakeParallelShadowCollector().collect("Brand", "https://brand.com").to_dict()

    result = _collect_parallel_shadow_input(
        store=None,
        run_id=None,
        brand_name="Brand",
        effective_brand_url="https://brand.com",
        cache_read=lambda *_args, **_kwargs: cached,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        parallel_shadow_collector_cls=_FakeParallelShadowCollector,
    )

    assert result is not None
    assert result.summary()["result_total"] == 1
    assert raw_input_cache["parallel_shadow"] == "hit"
    assert acquisition_steps["parallel_shadow"].status == "hit"
    assert acquisition_steps["parallel_shadow"].eligible is True
