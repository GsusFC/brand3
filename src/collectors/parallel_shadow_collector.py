"""Parallel Search shadow collector.

This collector is intentionally observational. Its output is stored as a raw
input and surfaced in BrandResearchPack shadow metadata, but it must not feed
scoring, TLDR claims, or production decisions until explicitly promoted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


PARALLEL_SEARCH_URL = "https://api.parallel.ai/v1/search"
USER_AGENT = "Brand3/0.1"

DEFAULT_INTENTS = ("mentions", "competitors", "news", "ai_visibility")

_INTENT_OBJECTIVES = {
    "mentions": "Find external mentions, reviews, community discussion, and perception signals for the audited brand.",
    "competitors": "Find competitors, alternatives, and category context for the audited brand.",
    "news": "Find recent news, announcements, launches, funding, or public updates for the audited brand.",
    "ai_visibility": "Find sources that indicate AI visibility, documentation, knowledge graph, and machine-readable presence.",
}


@dataclass(slots=True)
class ParallelShadowResult:
    url: str
    title: str = ""
    excerpt: str = ""
    published_date: str = ""
    text_chars: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "excerpt": self.excerpt,
            "published_date": self.published_date,
            "text_chars": self.text_chars,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParallelShadowResult":
        return cls(
            url=str(data.get("url") or ""),
            title=str(data.get("title") or ""),
            excerpt=str(data.get("excerpt") or ""),
            published_date=str(data.get("published_date") or ""),
            text_chars=int(data.get("text_chars") or 0),
        )


@dataclass(slots=True)
class ParallelShadowIntent:
    intent: str
    status: str
    elapsed_ms: int = 0
    error: str = ""
    result_count: int = 0
    unique_domains: list[str] = field(default_factory=list)
    results: list[ParallelShadowResult] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    search_id: str = ""
    warnings: Any = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "intent": self.intent,
            "status": self.status,
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
            "result_count": self.result_count,
            "unique_domains": list(self.unique_domains),
            "results": [item.to_dict() for item in self.results],
            "usage": self.usage,
            "search_id": self.search_id,
            "warnings": self.warnings,
        }
        return {key: value for key, value in payload.items() if value not in ("", None)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParallelShadowIntent":
        results = data.get("results") if isinstance(data.get("results"), list) else []
        return cls(
            intent=str(data.get("intent") or ""),
            status=str(data.get("status") or "unknown"),
            elapsed_ms=int(data.get("elapsed_ms") or 0),
            error=str(data.get("error") or ""),
            result_count=int(data.get("result_count") or 0),
            unique_domains=[str(item) for item in (data.get("unique_domains") or []) if str(item).strip()],
            results=[ParallelShadowResult.from_dict(item) for item in results if isinstance(item, dict)],
            usage=data.get("usage") if isinstance(data.get("usage"), dict) else None,
            search_id=str(data.get("search_id") or ""),
            warnings=data.get("warnings"),
        )


@dataclass(slots=True)
class ParallelShadowData:
    brand_name: str
    brand_url: str
    provider: str = "parallel"
    mode: str = "advanced"
    status: str = "ok"
    intents: dict[str, ParallelShadowIntent] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "parallel_shadow_v0_1",
            "provider": self.provider,
            "mode": self.mode,
            "status": self.status,
            "brand_name": self.brand_name,
            "brand_url": self.brand_url,
            "intents": {key: value.to_dict() for key, value in self.intents.items()},
            "summary": self.summary(),
            "diagnostics": dict(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParallelShadowData":
        intents = data.get("intents") if isinstance(data.get("intents"), dict) else {}
        return cls(
            brand_name=str(data.get("brand_name") or ""),
            brand_url=str(data.get("brand_url") or ""),
            provider=str(data.get("provider") or "parallel"),
            mode=str(data.get("mode") or "advanced"),
            status=str(data.get("status") or "ok"),
            intents={
                str(name): ParallelShadowIntent.from_dict(item)
                for name, item in intents.items()
                if isinstance(item, dict)
            },
            diagnostics=data.get("diagnostics") if isinstance(data.get("diagnostics"), dict) else {},
        )

    def summary(self) -> dict[str, Any]:
        ok = sum(1 for item in self.intents.values() if item.status == "ok")
        skipped = sum(1 for item in self.intents.values() if item.status == "skipped")
        errors = sum(1 for item in self.intents.values() if item.status == "error")
        domains: set[str] = set()
        result_total = 0
        elapsed_total = 0
        for item in self.intents.values():
            result_total += item.result_count
            elapsed_total += item.elapsed_ms
            domains.update(item.unique_domains)
        return {
            "ok": ok,
            "skipped": skipped,
            "error": errors,
            "result_total": result_total,
            "unique_domain_count": len(domains),
            "unique_domains": sorted(domains),
            "avg_latency_ms": int(elapsed_total / max(1, len(self.intents))),
        }


class ParallelShadowCollector:
    """Collect Parallel Search results for shadow coverage measurement."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        mode: str = "advanced",
        limit: int = 5,
        timeout_seconds: int = 12,
    ) -> None:
        self.api_key = (api_key or os.environ.get("PARALLEL_API_KEY") or "").strip()
        self.mode = mode if mode in {"basic", "advanced"} else "advanced"
        self.limit = max(1, min(int(limit or 5), 10))
        self.timeout_seconds = max(1, int(timeout_seconds or 12))

    def collect(
        self,
        brand_name: str,
        brand_url: str,
        *,
        intents: tuple[str, ...] = DEFAULT_INTENTS,
    ) -> ParallelShadowData:
        if not self.api_key:
            return ParallelShadowData(
                brand_name=brand_name,
                brand_url=brand_url,
                mode=self.mode,
                status="skipped",
                diagnostics={"reason": "PARALLEL_API_KEY not set"},
            )
        data = ParallelShadowData(brand_name=brand_name, brand_url=brand_url, mode=self.mode)
        for intent in intents:
            data.intents[intent] = self._search_intent(brand_name, brand_url, intent)
        if any(item.status == "error" for item in data.intents.values()):
            data.status = "partial" if any(item.status == "ok" for item in data.intents.values()) else "error"
        return data

    def _search_intent(self, brand_name: str, brand_url: str, intent: str) -> ParallelShadowIntent:
        objective = _INTENT_OBJECTIVES.get(intent, _INTENT_OBJECTIVES["mentions"])
        payload = {
            "objective": objective,
            "search_queries": _search_queries(brand_name, brand_url, intent),
            "mode": self.mode,
            "max_chars_total": max(1000, self.limit * 1500),
            "client_model": "brand3-shadow",
        }
        start = time.perf_counter()
        request = Request(
            PARALLEL_SEARCH_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
        except HTTPError as exc:
            return ParallelShadowIntent(
                intent=intent,
                status="error",
                elapsed_ms=_elapsed_ms(start),
                error=_http_error_message(exc),
            )
        except Exception as exc:
            return ParallelShadowIntent(
                intent=intent,
                status="error",
                elapsed_ms=_elapsed_ms(start),
                error=str(exc),
            )

        results: list[ParallelShadowResult] = []
        for item in _list(parsed.get("results"))[: self.limit]:
            excerpts = [str(excerpt) for excerpt in _list(item.get("excerpts")) if excerpt]
            excerpt = _clip(" ".join(excerpts), 800)
            results.append(
                ParallelShadowResult(
                    url=str(item.get("url") or ""),
                    title=str(item.get("title") or ""),
                    published_date=str(item.get("publish_date") or item.get("published_date") or ""),
                    excerpt=excerpt,
                    text_chars=sum(len(part) for part in excerpts),
                )
            )
        domains = sorted({_domain(item.url) for item in results if item.url})
        return ParallelShadowIntent(
            intent=intent,
            status="ok",
            elapsed_ms=_elapsed_ms(start),
            result_count=len(results),
            unique_domains=domains,
            results=results,
            usage=parsed.get("usage") if isinstance(parsed.get("usage"), dict) else None,
            search_id=str(parsed.get("search_id") or ""),
            warnings=parsed.get("warnings"),
        )


def _search_queries(brand_name: str, brand_url: str, intent: str) -> list[str]:
    domain = _domain(brand_url)
    base = " ".join(part for part in (brand_name, domain) if part).strip()
    suffixes = {
        "mentions": ("reviews community discussion perception", "G2 ProductHunt Reddit customer sentiment"),
        "competitors": ("competitors alternatives category market", "similar products comparison"),
        "news": ("recent news announcements launches funding", "latest public updates"),
        "ai_visibility": ("AI visibility llms.txt schema docs knowledge graph", "AI search recommendations documentation"),
    }.get(intent, ("mentions reviews perception",))
    return [f"{base} {suffix}".strip() for suffix in suffixes if f"{base} {suffix}".strip()]


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or parsed.path).lower().removeprefix("www.").strip("/")


def _clip(text: str, limit: int) -> str:
    cleaned = " ".join(str(text or "").split())
    return cleaned[:limit]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _http_error_message(exc: HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")[:500]
    except Exception:
        body = ""
    return f"HTTP {exc.code}: {body}".strip()
