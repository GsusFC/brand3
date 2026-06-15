from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from src.services.feature_pipeline import extract_features


class _ConcurrencyTracker:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def run(self) -> dict:
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(0.03)
            return {"feature": SimpleNamespace(source="heuristic")}
        finally:
            with self.lock:
                self.active -= 1


def _make_extractor(tracker: _ConcurrencyTracker):
    class Extractor:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def extract(self, *args, **kwargs) -> dict:
            return tracker.run()

    return Extractor


def _extract_with_tracker(tracker: _ConcurrencyTracker) -> dict[str, dict]:
    extractor = _make_extractor(tracker)
    return extract_features(
        web_data=None,
        content_web=None,
        exa_data=None,
        social_data=None,
        context_data=None,
        competitor_data=None,
        llm=None,
        use_llm=False,
        data_quality="good",
        content_source="test",
        research_pack=None,
        screenshot_url=None,
        screenshot_limitation=None,
        skip_visual_analysis=True,
        presencia_cls=extractor,
        vitalidad_cls=extractor,
        coherencia_cls=extractor,
        diferenciacion_cls=extractor,
        percepcion_cls=extractor,
        annotate_content_source=lambda features, source: None,
    )


def test_feature_pipeline_is_sequential_by_default(monkeypatch) -> None:
    monkeypatch.delenv("BRAND3_FEATURE_PARALLELISM", raising=False)
    tracker = _ConcurrencyTracker()

    features = _extract_with_tracker(tracker)

    assert set(features) == {
        "presencia",
        "vitalidad",
        "coherencia",
        "diferenciacion",
        "percepcion",
    }
    assert tracker.max_active == 1


def test_feature_pipeline_parallelism_is_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("BRAND3_FEATURE_PARALLELISM", "2")
    tracker = _ConcurrencyTracker()

    features = _extract_with_tracker(tracker)

    assert set(features) == {
        "presencia",
        "vitalidad",
        "coherencia",
        "diferenciacion",
        "percepcion",
    }
    assert tracker.max_active == 2


def test_parallel_feature_pipeline_merges_cloned_llm_metrics(monkeypatch) -> None:
    monkeypatch.setenv("BRAND3_FEATURE_PARALLELISM", "2")

    class FakeLLM:
        def __init__(self, api_key=None, base_url=None, model=None) -> None:
            self.api_key = api_key or "test-key"
            self.base_url = base_url or "https://llm.example"
            self.model = model or "test-model"
            self.timeout_seconds = 10
            self.cache_hits = 0
            self.cache_misses = 0
            self.cache_writes = 0
            self.call_failures = []

    class LLMExtractor:
        def __init__(self, llm=None, *args, **kwargs) -> None:
            self.llm = llm

        def extract(self, *args, **kwargs) -> dict:
            if self.llm is not None:
                self.llm.cache_hits += 1
            return {"feature": SimpleNamespace(source="llm" if self.llm else "heuristic")}

    class HeuristicExtractor:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def extract(self, *args, **kwargs) -> dict:
            return {"feature": SimpleNamespace(source="heuristic")}

    llm = FakeLLM()
    features = extract_features(
        web_data=None,
        content_web=None,
        exa_data=None,
        social_data=None,
        context_data=None,
        competitor_data=None,
        llm=llm,
        use_llm=True,
        data_quality="insufficient",
        content_source="test",
        research_pack=None,
        screenshot_url=None,
        screenshot_limitation=None,
        skip_visual_analysis=True,
        presencia_cls=HeuristicExtractor,
        vitalidad_cls=LLMExtractor,
        coherencia_cls=LLMExtractor,
        diferenciacion_cls=LLMExtractor,
        percepcion_cls=LLMExtractor,
        annotate_content_source=lambda features, source: None,
    )

    assert features["coherencia"] == {}
    assert features["diferenciacion"] == {}
    assert llm.cache_hits == 2
