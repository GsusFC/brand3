from __future__ import annotations

from scripts.brand_intelligence_benchmark import (
    _filter_cases_by_providers,
    _parse_args,
    _parse_input_sources,
    main,
)
from src.research.brand_intelligence_benchmark import BrandIntelligenceBenchmarkCase


def test_filter_cases_by_providers_keeps_requested_owned_web_providers() -> None:
    cases = [
        BrandIntelligenceBenchmarkCase("A", "https://a.example", owned_web_provider="firecrawl"),
        BrandIntelligenceBenchmarkCase("B", "https://b.example", owned_web_provider="playwright"),
        BrandIntelligenceBenchmarkCase("C", "https://c.example", owned_web_provider="tinyfish"),
    ]

    filtered = _filter_cases_by_providers(cases, "firecrawl, tinyfish")

    assert [case.owned_web_provider for case in filtered] == ["firecrawl", "tinyfish"]


def test_filter_cases_by_providers_returns_all_cases_without_filter() -> None:
    cases = [
        BrandIntelligenceBenchmarkCase("A", "https://a.example", owned_web_provider="firecrawl"),
        BrandIntelligenceBenchmarkCase("B", "https://b.example", owned_web_provider="playwright"),
    ]

    assert _filter_cases_by_providers(cases, "") == cases


def test_parse_input_sources_is_case_insensitive_and_trims() -> None:
    parsed = _parse_input_sources(" hyperbrowser , tinyfish ,")

    assert parsed == {"hyperbrowser", "tinyfish"}


def test_parse_input_sources_returns_none_when_empty() -> None:
    assert _parse_input_sources(None) is None
    assert _parse_input_sources("") is None


def test_parse_args_includes_run_input_sources(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["brand_intelligence_benchmark.py", "--run-input-sources", "hyperbrowser,tinyfish"])

    args = _parse_args()

    assert args.run_input_sources == "hyperbrowser,tinyfish"


def test_main_forwards_run_input_sources_to_run_probe(monkeypatch, tmp_path) -> None:
    calls: list[dict] = []

    def fake_load_cases(_: object) -> list[BrandIntelligenceBenchmarkCase]:
        return [BrandIntelligenceBenchmarkCase("ChatGPT", "https://chatgpt.com")]

    def fake_filter_cases(cases: list[BrandIntelligenceBenchmarkCase], _providers: str):
        return cases

    def fake_run_probe(**kwargs):
        calls.append(kwargs)
        return {
            "input": {"brand": kwargs["brand"], "url": kwargs["url"], "owned_web_provider": kwargs["owned_web_provider"]},
            "entity": {"resolution_status": "resolved"},
            "plan": {},
            "inventory": {"eligible_channels": []},
            "evidence_graph": {"summary": {"evidence_count": 0}},
            "observations": [],
        }

    def fake_summarize(payloads: list[dict], *, cases):
        return {
            "case_count": len(payloads),
            "inventory_ready_count": 0,
            "provider_metrics": {},
        }

    def fake_render(summary: dict) -> str:
        return "# Brand Intelligence Acquisition Benchmark\n"

    monkeypatch.setattr("sys.argv", [
        "brand_intelligence_benchmark.py",
        "--run-input-sources",
        "hyperbrowser",
        "--cases-file",
        "out/none.json",
        "--output-dir",
        str(tmp_path),
    ])

    monkeypatch.setattr("scripts.brand_intelligence_benchmark._load_cases", fake_load_cases)
    monkeypatch.setattr("scripts.brand_intelligence_benchmark._filter_cases_by_providers", fake_filter_cases)
    monkeypatch.setattr("scripts.brand_intelligence_benchmark.run_probe", fake_run_probe)
    monkeypatch.setattr("scripts.brand_intelligence_benchmark.summarize_brand_intelligence_benchmark", fake_summarize)
    monkeypatch.setattr("scripts.brand_intelligence_benchmark.render_brand_intelligence_benchmark_markdown", fake_render)

    result_code = main()

    assert result_code == 0
    assert calls
    assert calls[0]["run_input_sources"] == {"hyperbrowser"}
