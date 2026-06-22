"""Internal helpers for report derivation and source grouping."""

from __future__ import annotations

import json
from typing import Any, Literal
from urllib.parse import urlparse

from src.reports.derivation_readiness import _as_str, parse_raw_value

SourceType = Literal[
    "owned",
    "encyclopedic",
    "social",
    "news",
    "changelog",
    "review",
    "other",
]

_EVIDENCE_KEYS = ("evidence", "quotes", "examples", "messaging_gaps", "tone_examples")

_DIMENSION_ORDER: tuple[str, ...] = (
    "coherencia",
    "presencia",
    "percepcion",
    "diferenciacion",
    "vitalidad",
)

_DIMENSION_LABELS: dict[str, str] = {
    "coherencia": "Coherence",
    "presencia": "Presence",
    "percepcion": "Perception",
    "diferenciacion": "Differentiation",
    "vitalidad": "Vitality",
}

_ENCYCLOPEDIC_HOSTS = {"wikipedia.org", "crunchbase.com", "pitchbook.com"}
_SOCIAL_HOSTS = {
    "linkedin.com",
    "x.com",
    "twitter.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "facebook.com",
    "github.com",
}
_REVIEW_HOSTS = {"g2.com", "capterra.com", "trustpilot.com", "producthunt.com"}
_NEWS_HOSTS = {
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "forbes.com",
    "bloomberg.com",
    "reuters.com",
    "nytimes.com",
    "washingtonpost.com",
    "ft.com",
    "economist.com",
    "bbc.com",
    "bbc.co.uk",
    "cnn.com",
    "wsj.com",
    "theguardian.com",
    "axios.com",
    "businessinsider.com",
    "venturebeat.com",
    "arstechnica.com",
    "fastcompany.com",
    "elpais.com",
    "elmundo.es",
    "expansion.com",
    "cincodias.elpais.com",
    "eleconomista.es",
    "lavanguardia.com",
}
_CHANGELOG_PATH_MARKERS = ("/changelog", "/releases", "/blog/release", "/release-notes")
_OWNED_CONTENT_SOURCES = {
    "firecrawl",
    "browser_fallback",
    "owned_fallback",
    "official_related",
}

_SOURCE_GROUP_ORDER: tuple[tuple[str, str], ...] = (
    ("owned", "Owned"),
    ("encyclopedic", "Encyclopedic"),
    ("news", "News"),
    ("social", "Social"),
    ("review", "Reviews"),
    ("changelog", "Changelog"),
    ("other", "Other"),
)

_BANDS = (
    (20, "F", "critico"),
    (40, "D", "debil"),
    (55, "C", "mixed"),
    (70, "C+", "mixed"),
    (85, "B", "solido"),
    (100, "A", "fuerte"),
)


def _report_evidence_items_by_dimension(snapshot: dict) -> dict[str, list[dict]]:
    by_dim: dict[str, list[dict]] = {}
    for item in snapshot.get("evidence_items") or []:
        dimension = item.get("dimension_name") or ""
        quote = _as_str(item.get("quote")).strip()
        source_url = _as_str(item.get("url")).strip()
        if not dimension or not (quote or source_url):
            continue
        by_dim.setdefault(dimension, []).append(
            {
                "quote": quote,
                "source_url": source_url,
                "signal": item.get("source") or None,
            }
        )
    return by_dim


def _dedupe_report_evidence(items: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for item in items:
        key = (
            _as_str(item.get("quote")).strip(),
            _as_str(item.get("source_url")).strip(),
        )
        if not key[0] and not key[1]:
            continue
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _verdict_from(feature_raw: Any, band_label: str) -> str:
    if isinstance(feature_raw, dict):
        for key in ("verdict", "summary", "reasoning"):
            value = feature_raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return band_label


def _badge_type_from_band(letter: str) -> str:
    if letter in ("A", "B"):
        return "ok"
    if letter in ("D", "F"):
        return "warn"
    return "neutral"


def _first_nonempty(*values: Any) -> str:
    for v in values:
        s = _as_str(v).strip()
        if s:
            return s
    return ""


def _parse_json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return value if isinstance(value, list) else []


def _load_dimension_labels() -> dict[str, str]:
    return _DIMENSION_LABELS


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _cost_policy_from_snapshot(snapshot: dict) -> dict:
    run = snapshot.get("run") or {}
    raw_inputs = snapshot.get("raw_inputs") or []
    raw_sources = sorted({
        item.get("source")
        for item in raw_inputs
        if isinstance(item, dict) and item.get("source")
    })
    skipped: dict[str, str] = {}
    if run.get("use_llm") in (0, False):
        skipped["llm"] = "disabled_by_request"
    elif run.get("llm_used") in (0, False):
        skipped["llm"] = "not_used"
    if run.get("use_social") in (0, False):
        skipped["social"] = "disabled_by_request"
    elif run.get("social_scraped") in (0, False):
        skipped["social"] = "not_scraped"
    return {
        "available": bool(raw_sources or skipped),
        "raw_input_sources": raw_sources,
        "persisted_raw_inputs": len(raw_inputs),
        "skipped": skipped,
    }


def _group_sources(snapshot: dict, collect_evidences) -> tuple[dict[str, list[str]], list[str]]:
    evidences = collect_evidences(snapshot)
    buckets: dict[str, list[str]] = {key: [] for key, _ in _SOURCE_GROUP_ORDER}
    seen: set[str] = set()
    all_urls: list[str] = []
    for ev in evidences:
        if not ev.url or ev.url in seen:
            continue
        seen.add(ev.url)
        all_urls.append(ev.url)
        buckets.setdefault(ev.source_type, []).append(ev.url)

    grouped: dict[str, list[str]] = {}
    for key, label in _SOURCE_GROUP_ORDER:
        urls = buckets.get(key) or []
        if urls:
            grouped[label] = urls
    return grouped, all_urls


def _extract_domain(url: str | None) -> str | None:
    if not url or not isinstance(url, str):
        return None
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return None
    host = host.lower().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _host_suffix_match(host: str, needle: str) -> bool:
    return host == needle or host.endswith("." + needle)


def _infer_source_type(url: str | None, brand_domain: str | None) -> SourceType:
    host = _extract_domain(url)
    if not host:
        return "other"
    if brand_domain and (host == brand_domain or host.endswith("." + brand_domain)):
        path = (urlparse(url).path or "").lower() if url else ""
        if any(marker in path for marker in _CHANGELOG_PATH_MARKERS):
            return "changelog"
        return "owned"
    for candidate in _ENCYCLOPEDIC_HOSTS:
        if _host_suffix_match(host, candidate):
            return "encyclopedic"
    for candidate in _SOCIAL_HOSTS:
        if _host_suffix_match(host, candidate):
            return "social"
    for candidate in _REVIEW_HOSTS:
        if _host_suffix_match(host, candidate):
            return "review"
    path = (urlparse(url).path or "").lower() if url else ""
    if any(marker in path for marker in _CHANGELOG_PATH_MARKERS):
        return "changelog"
    for candidate in _NEWS_HOSTS:
        if _host_suffix_match(host, candidate):
            return "news"
    return "other"


def _build_evidence(
    dimension: str,
    feature_name: str | None,
    quote: str | None,
    url: str | None,
    sentiment: str | None,
    brand_domain: str | None,
    extra: dict | None = None,
):
    q = (quote or "").strip() or None
    u = (url or "").strip() or None
    if u and not (u.startswith("http://") or u.startswith("https://")):
        u = None
    if not q and not u:
        return None
    source_type = _infer_source_type(u, brand_domain)
    from src.reports.derivation import Evidence

    return Evidence(
        dimension=dimension,
        quote=q,
        url=u,
        source_type=source_type,
        source_domain=_extract_domain(u),
        sentiment=(sentiment or None),
        feature_name=feature_name,
        extra=extra or {},
    )


def _iter_feature_evidences(
    dimension: str,
    feature_name: str | None,
    raw: Any,
    brand_domain: str | None,
):
    if not isinstance(raw, dict):
        return []

    out = []

    def add(
        quote: str | None = None,
        url: str | None = None,
        sentiment: str | None = None,
        extra: dict | None = None,
    ) -> None:
        ev = _build_evidence(
            dimension=dimension,
            feature_name=feature_name,
            quote=quote,
            url=url,
            sentiment=sentiment,
            brand_domain=brand_domain,
            extra=extra,
        )
        if ev is not None:
            out.append(ev)

    for key in _EVIDENCE_KEYS:
        items = raw.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                quote = item.get("quote") or item.get("snippet") or item.get("text") or item.get("example")
                url = item.get("source_url") or item.get("url")
                sentiment = item.get("signal") or item.get("sentiment") or item.get("tone")
                extra = {k: v for k, v in item.items() if k in ("title", "date", "source")}
                add(quote=quote, url=url, sentiment=sentiment, extra=extra)
            elif isinstance(item, str) and item.strip():
                add(quote=item)

    single_url = raw.get("evidence_url")
    if isinstance(single_url, str):
        add(url=single_url)

    single_quote = raw.get("evidence_snippet")
    if isinstance(single_quote, str):
        add(quote=single_quote)

    snippets = raw.get("evidence_snippets")
    if isinstance(snippets, list):
        for s in snippets:
            if isinstance(s, str) and s.strip():
                add(quote=s)

    insights = raw.get("evidence_insights")
    if isinstance(insights, list):
        for s in insights:
            if isinstance(s, str) and s.strip():
                add(quote=s)

    return out
