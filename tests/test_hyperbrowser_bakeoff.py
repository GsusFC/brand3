from __future__ import annotations

from src.collectors.hyperbrowser_collector import HyperbrowserFetchData, DEFAULT_TIMEOUT_SECONDS
from scripts.hyperbrowser_bakeoff import (
    AcquisitionRow,
    compare_rows,
    run_hyperbrowser,
    render_markdown,
    summarize_bakeoff,
)


def test_compare_rows_reports_hyperbrowser_delta_vs_current() -> None:
    comparison = compare_rows(
        [
            AcquisitionRow(
                brand="Example",
                url="https://example.com",
                provider="current_web_collector",
                text_chars=300,
                html_chars=1000,
                link_count=2,
            ),
            AcquisitionRow(
                brand="Example",
                url="https://example.com",
                provider="hyperbrowser",
                text_chars=500,
                html_chars=1800,
                link_count=5,
                has_branding=True,
            ),
        ]
    )

    assert comparison["hyperbrowser_usable_text"] is True
    assert comparison["hyperbrowser_branding_present"] is True
    assert comparison["text_char_delta_vs_current"] == 200
    assert comparison["html_char_delta_vs_current"] == 800
    assert comparison["link_delta_vs_current"] == 3


def test_hyperbrowser_bakeoff_markdown_contains_branding_columns() -> None:
    summary = summarize_bakeoff(
        [
            {
                "case": {"brand": "Example", "domain": "example.com"},
                "rows": [
                    {
                        "brand": "Example",
                        "url": "https://example.com",
                        "provider": "hyperbrowser",
                        "status": "ok",
                        "elapsed_ms": 10,
                        "text_chars": 400,
                        "html_chars": 1200,
                        "link_count": 3,
                        "has_branding": True,
                        "has_screenshot": False,
                        "color_count": 2,
                        "font_count": 1,
                        "logo_detected": True,
                        "title": "Example",
                        "final_url": "https://example.com",
                        "error": "",
                        "usable_text": True,
                    }
                ],
                "comparison": {"hyperbrowser_branding_present": True},
            }
        ]
    )

    markdown = render_markdown(summary)

    assert "Hyperbrowser Bakeoff" in markdown
    assert "Branding" in markdown
    assert "Screenshot" in markdown
    assert "| Example | hyperbrowser | ok | 400 | 3 | yes | no | yes |  |" in markdown


def test_fetch_json_variant_uses_default_schema() -> None:
    case = ("LangChain", "https://www.langchain.com")

    captured = {}

    class _Collector:  # pragma: no cover - behavior tested through call contract
        def __init__(self, *args, **kwargs):
            captured["init"] = kwargs

        def fetch(self, _url: str, **kwargs):
            captured["kwargs"] = kwargs
            return HyperbrowserFetchData(
                url=_url,
                markdown="# LangChain",
                html="<h1>LangChain</h1>",
                links=["https://example.com/a", "https://example.com/b"],
                branding={"colorScheme": "dark", "colors": {}, "fonts": [], "images": {}, "confidence": {}},
                json_payload={"offer": "test offer"},
            )

    import scripts.hyperbrowser_bakeoff as target

    original = target.HyperbrowserCollector
    target.HyperbrowserCollector = _Collector
    try:
        row, raw = run_hyperbrowser(
            case=target.BakeoffCase(*case),
            timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
            include_branding=True,
            include_screenshot=False,
            cache_max_age_seconds=86400,
            variant="fetch-json",
            json_schema_path=None,
            json_prompt="extract summary",
            exclude_selectors=["nav"],
            include_selectors=None,
        )
    finally:
        target.HyperbrowserCollector = original

    assert row.status == "ok"
    assert row.text_chars == len("# LangChain")
    assert raw.get("json_payload") == {"offer": "test offer"}
    assert captured.get("kwargs", {}).get("json_schema") == {
        "type": "object",
        "properties": {
            "offer": {"type": "string"},
            "audience": {"type": "string"},
            "proofPoints": {"type": "array", "items": {"type": "string"}},
        },
    }


def test_search_variant_calls_search_and_reports_results() -> None:
    case = ("LangChain", "https://www.langchain.com")
    captured = {}

    class _Collector:  # pragma: no cover - behavior tested through call contract
        def __init__(self, *args, **kwargs):
            captured["init"] = kwargs

        def fetch(self, _url: str, **kwargs):
            return HyperbrowserFetchData(url=_url)

        def search(self, query: str, *, limit: int = 10, payload_overrides=None):
            captured["search"] = {"query": query, "limit": limit}
            return {
                "status": "completed",
                "data": {
                    "query": "LangChain",
                    "results": [
                        {
                            "title": "LangChain",
                            "url": "https://www.langchain.com",
                            "description": "LLM tooling",
                        }
                    ],
                },
            }

        def extract(self, *args, **kwargs):
            return {"status": "error", "error": "not expected"}

    import scripts.hyperbrowser_bakeoff as target

    original = target.HyperbrowserCollector
    target.HyperbrowserCollector = _Collector
    try:
        row, raw = run_hyperbrowser(
            case=target.BakeoffCase(*case),
            timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
            include_branding=True,
            include_screenshot=False,
            cache_max_age_seconds=86400,
            variant="search",
            search_query=None,
            search_limit=4,
            extract_wait_seconds=5,
            extract_poll_interval=0.1,
            json_schema_path=None,
            json_prompt="search prompt",
            exclude_selectors=None,
            include_selectors=None,
        )
    finally:
        target.HyperbrowserCollector = original

    assert row.provider_variant == "search"
    assert row.text_chars > 0
    assert raw["query"] == "LangChain"
    assert raw["results_count"] == 1
    assert captured.get("search") == {"query": "LangChain", "limit": 4}


def test_extract_json_variant_uses_default_schema() -> None:
    case = ("LangChain", "https://www.langchain.com")
    captured = {}

    class _Collector:  # pragma: no cover - behavior tested through call contract
        def __init__(self, *args, **kwargs):
            captured["init"] = kwargs

        def fetch(self, *args, **kwargs):
            return HyperbrowserFetchData(url=case[1])

        def search(self, query: str, *, limit: int = 10, payload_overrides=None):
            return {"status": "error", "error": "not expected"}

        def extract(
            self,
            _urls: str | list[str],
            *,
            prompt: str | None = None,
            schema: dict[str, object] | None = None,
            wait_for_completion: bool = True,
            max_wait_seconds: int = 90,
            poll_interval_seconds: float = 1.0,
            payload_overrides: dict[str, object] | None = None,
        ):
            captured["extract"] = {
                "prompt": prompt,
                "schema": schema,
                "wait_for_completion": wait_for_completion,
                "max_wait_seconds": max_wait_seconds,
            }
            return {
                "status": "completed",
                "json": {"offer": "test offer"},
                "elapsedMs": 77,
            }

    import scripts.hyperbrowser_bakeoff as target

    original = target.HyperbrowserCollector
    target.HyperbrowserCollector = _Collector
    try:
        row, raw = run_hyperbrowser(
            case=target.BakeoffCase(*case),
            timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
            include_branding=True,
            include_screenshot=False,
            cache_max_age_seconds=86400,
            variant="extract-json",
            search_query=None,
            search_limit=4,
            extract_wait_seconds=5,
            extract_poll_interval=0.1,
            json_schema_path=None,
            json_prompt="extract prompt",
            exclude_selectors=None,
            include_selectors=None,
        )
    finally:
        target.HyperbrowserCollector = original

    assert row.provider_variant == "extract-json"
    assert row.text_chars > 0
    assert captured["extract"]["prompt"] == "extract prompt"
    assert captured["extract"]["schema"] == {
        "type": "object",
        "properties": {
            "offer": {"type": "string"},
            "audience": {"type": "string"},
            "proofPoints": {"type": "array", "items": {"type": "string"}},
        },
    }
    assert raw.get("json_payload") == {"offer": "test offer"}
