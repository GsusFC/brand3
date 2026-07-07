"""SearchAPI.io collector for budgeted vertical external-proof fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"
SEARCHAPI_STRATEGY_VERSION = "vertical_fallback_v1"
USER_AGENT = "Brand3/0.1"


@dataclass(slots=True)
class SearchApiResult:
    url: str
    title: str = ""
    snippet: str = ""
    source: str = ""
    domain: str = ""
    date: str = ""
    position: int = 0
    intent: str = ""
    query: str = ""
    engine: str = "google_light"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "source": self.source,
            "domain": self.domain,
            "date": self.date,
            "position": self.position,
            "intent": self.intent,
            "query": self.query,
            "engine": self.engine,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchApiResult":
        return cls(
            url=str(data.get("url") or data.get("link") or ""),
            title=str(data.get("title") or ""),
            snippet=str(data.get("snippet") or ""),
            source=str(data.get("source") or ""),
            domain=str(data.get("domain") or ""),
            date=str(data.get("date") or ""),
            position=int(data.get("position") or 0),
            intent=str(data.get("intent") or ""),
            query=str(data.get("query") or ""),
            engine=str(data.get("engine") or "google_light"),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
        )


@dataclass(slots=True)
class SearchApiIntent:
    intent: str
    status: str
    query: str = ""
    engine: str = "google_light"
    elapsed_ms: int = 0
    error: str = ""
    result_count: int = 0
    results: list[SearchApiResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "status": self.status,
            "query": self.query,
            "engine": self.engine,
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
            "result_count": self.result_count,
            "results": [item.to_dict() for item in self.results],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchApiIntent":
        results = data.get("results") if isinstance(data.get("results"), list) else []
        return cls(
            intent=str(data.get("intent") or ""),
            status=str(data.get("status") or "unknown"),
            query=str(data.get("query") or ""),
            engine=str(data.get("engine") or "google_light"),
            elapsed_ms=int(data.get("elapsed_ms") or 0),
            error=str(data.get("error") or ""),
            result_count=int(data.get("result_count") or 0),
            results=[SearchApiResult.from_dict(item) for item in results if isinstance(item, dict)],
        )


@dataclass(slots=True)
class SearchApiData:
    brand_name: str
    brand_url: str
    provider: str = "searchapi"
    mode: str = "vertical_fallback"
    status: str = "ok"
    intents: dict[str, SearchApiIntent] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SEARCHAPI_STRATEGY_VERSION,
            "provider": self.provider,
            "mode": self.mode,
            "status": self.status,
            "brand_name": self.brand_name,
            "brand_url": self.brand_url,
            "intents": {key: value.to_dict() for key, value in self.intents.items()},
            "diagnostics": dict(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchApiData":
        intents = data.get("intents") if isinstance(data.get("intents"), dict) else {}
        return cls(
            brand_name=str(data.get("brand_name") or ""),
            brand_url=str(data.get("brand_url") or ""),
            provider=str(data.get("provider") or "searchapi"),
            mode=str(data.get("mode") or "vertical_fallback"),
            status=str(data.get("status") or "ok"),
            intents={
                str(name): SearchApiIntent.from_dict(item)
                for name, item in intents.items()
                if isinstance(item, dict)
            },
            diagnostics=data.get("diagnostics") if isinstance(data.get("diagnostics"), dict) else {},
        )


class SearchApiCollector:
    """Budgeted SearchAPI.io fallback.

    This collector is intentionally query/result only. It discovers citable
    sources; it does not summarize, classify, or score brand strategy.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        limit: int = 5,
        timeout_seconds: int = 10,
    ) -> None:
        self.api_key = (api_key or os.environ.get("SEARCHAPI_API_KEY") or "").strip()
        self.limit = max(1, min(int(limit or 5), 10))
        self.timeout_seconds = max(1, int(timeout_seconds or 10))

    def collect(
        self,
        brand_name: str,
        brand_url: str,
        *,
        intents: tuple[str, ...],
        queries_by_intent: dict[str, str] | None = None,
    ) -> SearchApiData:
        if not self.api_key:
            return SearchApiData(
                brand_name=brand_name,
                brand_url=brand_url,
                status="skipped",
                diagnostics={"reason": "SEARCHAPI_API_KEY not set"},
            )
        data = SearchApiData(brand_name=brand_name, brand_url=brand_url)
        for intent in intents:
            query = (queries_by_intent or {}).get(intent) or _fallback_query(brand_name, brand_url, intent)
            data.intents[intent] = self._search_intent(intent=intent, query=query)
        if any(item.status == "error" for item in data.intents.values()):
            data.status = "partial" if any(item.status == "ok" for item in data.intents.values()) else "error"
        data.diagnostics = {
            "strategy": SEARCHAPI_STRATEGY_VERSION,
            "planned_intents": list(intents),
            "result_total": sum(item.result_count for item in data.intents.values()),
            "failed_intents": [name for name, item in data.intents.items() if item.status == "error"],
            "no_result_intents": [name for name, item in data.intents.items() if item.status == "no_results"],
        }
        return data

    def _search_intent(self, *, intent: str, query: str) -> SearchApiIntent:
        start = time.perf_counter()
        engine = "google_light"
        params = {
            "engine": engine,
            "q": query,
            "api_key": self.api_key,
            "gl": "us",
            "hl": "en",
        }
        request = Request(
            f"{SEARCHAPI_URL}?{urlencode(params)}",
            headers={"User-Agent": USER_AGENT},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return SearchApiIntent(
                intent=intent,
                status="error",
                query=query,
                engine=engine,
                elapsed_ms=_elapsed_ms(start),
                error=_http_error_message(exc),
            )
        except Exception as exc:
            return SearchApiIntent(
                intent=intent,
                status="error",
                query=query,
                engine=engine,
                elapsed_ms=_elapsed_ms(start),
                error=str(exc),
            )

        results = [
            _result_from_organic(item, intent=intent, query=query, engine=engine)
            for item in _list(parsed.get("organic_results"))[: self.limit]
            if isinstance(item, dict)
        ]
        status = "ok" if results else "no_results"
        return SearchApiIntent(
            intent=intent,
            status=status,
            query=query,
            engine=engine,
            elapsed_ms=_elapsed_ms(start),
            result_count=len(results),
            results=results,
        )


def _result_from_organic(item: dict[str, Any], *, intent: str, query: str, engine: str) -> SearchApiResult:
    url = str(item.get("link") or item.get("url") or "")
    domain = str(item.get("domain") or _domain(url))
    return SearchApiResult(
        url=url,
        title=str(item.get("title") or ""),
        snippet=str(item.get("snippet") or ""),
        source=str(item.get("source") or ""),
        domain=domain,
        date=str(item.get("date") or ""),
        position=int(item.get("position") or 0),
        intent=intent,
        query=query,
        engine=engine,
        metadata={
            "displayed_link": item.get("displayed_link") or "",
            "snippet_highlighted_words": item.get("snippet_highlighted_words") or [],
        },
    )


def _fallback_query(brand_name: str, brand_url: str, intent: str) -> str:
    domain = _domain(brand_url)
    base = " ".join(part for part in (brand_name, domain) if part).strip()
    suffixes = {
        "news": "news funding launch announcement",
        "external_mentions": "reviews community discussion customers",
        "ai_visibility": "llms.txt documentation AI visibility",
    }
    suffix = suffixes.get(intent, "reviews mentions")
    return f"{base} {suffix}".strip()


def _domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or parsed.path).lower().removeprefix("www.").strip("/")


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _http_error_message(exc: HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")[:500]
    except Exception:
        body = ""
    return f"HTTP {exc.code}: {body}".strip()
