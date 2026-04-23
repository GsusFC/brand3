"""Cheap context-readiness collector.

This module performs a low-cost pre-scan using only stdlib HTTP calls. It is
intended to run before paid/deeper collectors and produce transparent signals
about whether a site is legible to search engines and AI systems.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


KEY_PAGE_PATHS = (
    "/about",
    "/blog",
    "/faq",
    "/pricing",
    "/docs",
    "/changelog",
    "/reviews",
    "/case-studies",
)


@dataclass
class ContextData:
    url: str
    homepage_status: int = 0
    robots_found: bool = False
    sitemap_found: bool = False
    sitemap_url_count: int = 0
    llms_txt_found: bool = False
    llms_full_found: bool = False
    ai_plugin_found: bool = False
    schema_types: list[str] = field(default_factory=list)
    key_pages: dict[str, bool] = field(default_factory=dict)
    avg_words: int = 0
    avg_internal_links: int = 0
    pages_crawled: int = 0
    context_score: float = 0.0
    coverage: float = 0.0
    confidence: float = 0.0
    confidence_reason: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    error: str = ""


class ContextCollector:
    """Collects machine-readability signals without paid APIs."""

    def __init__(self, timeout_seconds: float = 4.0):
        self.timeout_seconds = timeout_seconds

    def scan(self, url: str) -> ContextData:
        base = self._normalize_base(url)
        data = ContextData(url=base)
        homepage, status = self._fetch_text(base, "/")
        data.homepage_status = status
        if not homepage:
            data.error = "homepage_unavailable"
            data.coverage = 0.0
            data.confidence = 0.0
            data.confidence_reason = ["homepage_unavailable", "low_coverage"]
            data.opportunities = ["Homepage could not be fetched for context pre-scan"]
            return data

        robots, _ = self._fetch_text(base, "/robots.txt")
        sitemap, _ = self._fetch_text(base, "/sitemap.xml")
        llms_txt, _ = self._fetch_text(base, "/llms.txt")
        llms_full, _ = self._fetch_text(base, "/llms-full.txt")
        ai_plugin, _ = self._fetch_text(base, "/.well-known/ai-plugin.json")

        data.pages_crawled = 1
        data.robots_found = bool(robots)
        data.sitemap_found = bool(sitemap)
        data.sitemap_url_count = self._count_sitemap_urls(sitemap or "")
        data.llms_txt_found = bool(llms_txt and len(llms_txt.strip()) > 40)
        data.llms_full_found = bool(llms_full and len(llms_full.strip()) > 100)
        data.ai_plugin_found = self._valid_json(ai_plugin)
        data.schema_types = sorted(self._extract_schema_types(homepage))
        data.key_pages = {
            path.strip("/").replace("-", "_"): self._head_ok(base, path)
            for path in KEY_PAGE_PATHS
        }
        data.avg_words = self._count_words(homepage)
        data.avg_internal_links = len(self._extract_internal_links(base, homepage))

        data.context_score = self._score(data, homepage, robots or "")
        data.coverage = self._coverage(data)
        data.confidence, data.confidence_reason = self._confidence(data)
        data.opportunities = self._opportunities(data, robots or "")
        return data

    def _normalize_base(self, url: str) -> str:
        candidate = url.strip()
        if "://" not in candidate:
            candidate = f"https://{candidate}"
        parsed = urlparse(candidate)
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc or parsed.path
        return f"{scheme}://{netloc}".rstrip("/")

    def _fetch_text(self, base: str, path: str) -> tuple[str, int]:
        req = Request(
            urljoin(base + "/", path.lstrip("/")),
            headers={"User-Agent": "Brand3-ContextCollector/1.0"},
        )
        try:
            with urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read(1_000_000)
                charset = resp.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace"), int(getattr(resp, "status", 200) or 200)
        except HTTPError as exc:
            return "", int(exc.code)
        except (URLError, TimeoutError, ValueError, OSError):
            return "", 0

    def _head_ok(self, base: str, path: str) -> bool:
        req = Request(
            urljoin(base + "/", path.lstrip("/")),
            method="HEAD",
            headers={"User-Agent": "Brand3-ContextCollector/1.0"},
        )
        try:
            with urlopen(req, timeout=self.timeout_seconds) as resp:
                return 200 <= int(getattr(resp, "status", 200) or 200) < 400
        except HTTPError as exc:
            return 200 <= int(exc.code) < 400
        except (URLError, TimeoutError, ValueError, OSError):
            return False

    def _count_sitemap_urls(self, xml: str) -> int:
        return len(re.findall(r"<loc>\s*[^<]+\s*</loc>", xml or "", flags=re.IGNORECASE))

    def _valid_json(self, text: str | None) -> bool:
        if not text:
            return False
        try:
            json.loads(text)
            return True
        except json.JSONDecodeError:
            return False

    def _extract_schema_types(self, html: str) -> set[str]:
        types: set[str] = set()
        blocks = re.findall(
            r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
            html or "",
            flags=re.IGNORECASE | re.DOTALL,
        )
        for block in blocks:
            try:
                payload = json.loads(unescape(block).strip())
            except json.JSONDecodeError:
                continue
            self._walk_schema_types(payload, types)
        return types

    def _walk_schema_types(self, value, types: set[str]) -> None:
        if isinstance(value, dict):
            raw_type = value.get("@type")
            if isinstance(raw_type, str):
                types.add(raw_type)
            elif isinstance(raw_type, list):
                types.update(str(item) for item in raw_type if item)
            for key in ("@graph", "mainEntity", "itemListElement"):
                self._walk_schema_types(value.get(key), types)
        elif isinstance(value, list):
            for item in value:
                self._walk_schema_types(item, types)

    def _count_words(self, html: str) -> int:
        text = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html or "", flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&[a-z]+;", " ", text, flags=re.IGNORECASE)
        words = [word for word in re.split(r"\s+", text.strip()) if len(word) > 1]
        return len(words)

    def _extract_internal_links(self, base: str, html: str) -> set[str]:
        origin = urlparse(base).netloc.lower()
        links: set[str] = set()
        for href in re.findall(r"href=[\"']([^\"'#]+)", html or "", flags=re.IGNORECASE):
            parsed = urlparse(urljoin(base + "/", href))
            if parsed.netloc.lower() != origin:
                continue
            path = (parsed.path or "/").rstrip("/") or "/"
            if path == "/" or re.search(r"\.(css|js|png|jpg|jpeg|gif|svg|ico|xml|json|txt)$", path, re.I):
                continue
            links.add(path)
        return links

    def _score(self, data: ContextData, homepage: str, robots: str) -> float:
        score = 0.0
        if data.homepage_status and data.homepage_status < 400:
            score += 10
        if data.robots_found:
            score += 8
            if re.search(r"gptbot|claudebot|perplexitybot", robots, re.I):
                score += 4
        if data.sitemap_found:
            score += 8 if data.sitemap_url_count >= 20 else 5
        if data.llms_txt_found:
            score += 5
        if "Organization" in data.schema_types:
            score += 8
        if "WebSite" in data.schema_types:
            score += 5
        if "SearchAction" in data.schema_types or "SearchAction" in homepage:
            score += 4
        if "BreadcrumbList" in data.schema_types:
            score += 4
        if "FAQPage" in data.schema_types:
            score += 4
        if "SpeakableSpecification" in data.schema_types or "speakable" in homepage.lower():
            score += 4
        if "sameAs" in homepage:
            score += 5
        key_count = sum(1 for exists in data.key_pages.values() if exists)
        score += min(key_count * 3, 18)
        if data.avg_words >= 500:
            score += 8
        elif data.avg_words >= 250:
            score += 5
        elif data.avg_words >= 100:
            score += 2
        if data.avg_internal_links >= 10:
            score += 5
        elif data.avg_internal_links >= 5:
            score += 3
        elif data.avg_internal_links >= 2:
            score += 1
        return round(min(score, 100.0), 1)

    def _coverage(self, data: ContextData) -> float:
        checks = [
            data.homepage_status and data.homepage_status < 400,
            data.robots_found,
            data.sitemap_found,
            data.llms_txt_found,
            bool(data.schema_types),
            any(data.key_pages.values()),
            data.avg_words >= 100,
            data.avg_internal_links >= 2,
        ]
        return round(sum(1 for item in checks if item) / len(checks), 2)

    def _confidence(self, data: ContextData) -> tuple[float, list[str]]:
        coverage = data.coverage
        source_quality = 1.0 if data.homepage_status and data.homepage_status < 400 else 0.0
        freshness = 1.0
        diversity = min(
            1.0,
            (
                int(data.robots_found)
                + int(data.sitemap_found)
                + int(bool(data.schema_types))
                + int(any(data.key_pages.values()))
            ) / 4,
        )
        confidence = round(
            (0.4 * coverage) + (0.3 * source_quality) + (0.2 * freshness) + (0.1 * diversity),
            2,
        )
        reasons: list[str] = []
        if coverage < 0.3:
            reasons.append("low_coverage")
        if not data.sitemap_found:
            reasons.append("missing_sitemap")
        if not data.robots_found:
            reasons.append("missing_robots")
        if not data.schema_types:
            reasons.append("missing_schema")
        if not any(data.key_pages.values()):
            reasons.append("missing_key_pages")
        if not reasons:
            reasons.append("sufficient_context_signals")
        return confidence, reasons

    def _opportunities(self, data: ContextData, robots: str) -> list[str]:
        opportunities: list[str] = []
        if not data.llms_txt_found:
            opportunities.append("Add /llms.txt to summarize the site for AI systems")
        if not data.sitemap_found:
            opportunities.append("Add sitemap.xml so crawlers can discover key pages")
        if data.robots_found and not re.search(r"gptbot|claudebot|perplexitybot", robots, re.I):
            opportunities.append("Mention AI crawlers in robots.txt")
        if not data.schema_types:
            opportunities.append("Add JSON-LD schema such as Organization and WebSite")
        if not data.key_pages.get("about"):
            opportunities.append("Add /about to make brand identity explicit")
        if not (data.key_pages.get("reviews") or "Review" in data.schema_types or "AggregateRating" in data.schema_types):
            opportunities.append("Add reviews/case studies as proof signals")
        if data.avg_words < 250:
            opportunities.append("Increase content depth on the homepage")
        return opportunities[:6]
