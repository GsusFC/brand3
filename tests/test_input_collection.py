from __future__ import annotations

from src.collectors.exa_collector import ExaData
from src.collectors.parallel_shadow_collector import ParallelShadowData, ParallelShadowIntent, ParallelShadowResult
from src.collectors.web_collector import WebData
from src.services.input_collection import (
    _cache_reader,
    _collect_exa_input,
    _collect_parallel_shadow_input,
    _collect_web_input,
    _set_acquisition_state,
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


def test_set_acquisition_state_updates_cache_and_preserves_existing_details():
    raw_input_cache: dict[str, str] = {}
    acquisition_steps: dict[str, object] = {}

    _set_acquisition_state(
        raw_input_cache,
        acquisition_steps,
        source="web",
        raw_cache_status="error",
        status="cache_error",
        cache_status="error",
        eligible=True,
        details={"cache_error": "sqlite unavailable"},
    )
    _set_acquisition_state(
        raw_input_cache,
        acquisition_steps,
        source="web",
        raw_cache_status="miss",
        status="fetched",
        cache_status="miss",
        eligible=True,
        details={"chars": 128},
    )

    assert raw_input_cache["web"] == "miss"
    assert acquisition_steps["web"].status == "fetched"
    assert acquisition_steps["web"].cache_status == "miss"
    assert acquisition_steps["web"].details == {
        "cache_error": "sqlite unavailable",
        "chars": 128,
    }


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


class _FailingCacheStore:
    def get_latest_raw_input(self, **_kwargs):
        raise RuntimeError("sqlite unavailable")


class _InvalidCacheStore:
    def get_latest_raw_input(self, **_kwargs):
        return {"unexpected": "payload"}


class _FakeWebCollector:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def scrape(self, url: str):
        return WebData(url=url, markdown_content="Fresh owned homepage copy")


class _FailingStorageStore:
    def save_raw_input(self, *_args, **_kwargs):
        raise RuntimeError("disk is read-only")


class _RecordingStorageStore:
    def __init__(self):
        self.saved = []

    def save_raw_input(self, run_id, source, payload):
        self.saved.append((run_id, source, payload))


def test_collect_web_input_records_raw_payload_ref_after_successful_storage():
    acquisition_steps: dict[str, object] = {}
    raw_input_cache: dict[str, str] = {}
    store = _RecordingStorageStore()

    web_data, _collector = _collect_web_input(
        store=store,
        run_id=123,
        url="https://brand.com",
        cache_read=lambda *_args, **_kwargs: None,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        web_collector_cls=_FakeWebCollector,
    )

    assert store.saved == [(123, "web", web_data)]
    assert acquisition_steps["web"].details["raw_payload_ref"] == {
        "store": "raw_inputs",
        "run_id": 123,
        "source": "web",
    }


def test_collect_web_input_preserves_cache_read_error_in_acquisition_details():
    acquisition_steps: dict[str, object] = {}
    raw_input_cache: dict[str, str] = {}
    cache_read = _cache_reader(
        store=_FailingCacheStore(),
        brand_name="Brand",
        url="https://brand.com",
        refresh=False,
        acquisition_steps=acquisition_steps,
    )

    web_data, _collector = _collect_web_input(
        store=None,
        run_id=None,
        url="https://brand.com",
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        web_collector_cls=_FakeWebCollector,
    )

    assert web_data.markdown_content == "Fresh owned homepage copy"
    assert raw_input_cache["web"] == "miss"
    assert acquisition_steps["web"].status == "fetched"
    assert acquisition_steps["web"].cache_status == "miss"
    assert acquisition_steps["web"].details["cache_error"] == "sqlite unavailable"


def test_collect_web_input_preserves_storage_error_in_acquisition_details():
    acquisition_steps: dict[str, object] = {}
    raw_input_cache: dict[str, str] = {}

    web_data, _collector = _collect_web_input(
        store=_FailingStorageStore(),
        run_id=123,
        url="https://brand.com",
        cache_read=lambda *_args, **_kwargs: None,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        web_collector_cls=_FakeWebCollector,
    )

    assert web_data.markdown_content == "Fresh owned homepage copy"
    assert raw_input_cache["web"] == "miss"
    assert acquisition_steps["web"].status == "fetched"
    assert acquisition_steps["web"].cache_status == "miss"
    assert acquisition_steps["web"].details["storage_errors"] == [
        {"action": "web save", "error": "disk is read-only"}
    ]


def test_collect_web_input_preserves_invalid_cache_payload_in_acquisition_details():
    acquisition_steps: dict[str, object] = {}
    raw_input_cache: dict[str, str] = {}
    cache_read = _cache_reader(
        store=_InvalidCacheStore(),
        brand_name="Brand",
        url="https://brand.com",
        refresh=False,
        acquisition_steps=acquisition_steps,
    )

    web_data, _collector = _collect_web_input(
        store=None,
        run_id=None,
        url="https://brand.com",
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        web_collector_cls=_FakeWebCollector,
    )

    assert web_data.markdown_content == "Fresh owned homepage copy"
    assert raw_input_cache["web"] == "miss"
    assert acquisition_steps["web"].status == "fetched"
    assert acquisition_steps["web"].cache_status == "miss"
    assert "unexpected" in acquisition_steps["web"].details["cache_error"]


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
