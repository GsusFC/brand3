from __future__ import annotations

import re
from urllib.parse import urlparse


_OWNED_SOURCE_CLASSES = {"owned"}
_OWNED_RELATIONS = {"audited_surface", "same_root_surface", "owned_surface", "parent_home"}
_GENERIC_HOST_TOKENS = {"www", "com", "io", "ai", "app", "co", "net", "org", "es"}


def _normalize_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def brand_aliases(brand_name: str | None) -> set[str]:
    raw = (brand_name or "").strip().lower()
    aliases: set[str] = set()
    normalized = _normalize_text(raw)
    if normalized:
        aliases.add(normalized)

    candidate = raw
    if "://" not in candidate and "." in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    if host:
        aliases.add(_normalize_text(host))
        root = host.split(".", 1)[0]
        if root and root not in _GENERIC_HOST_TOKENS:
            aliases.add(_normalize_text(root))

    return {alias for alias in aliases if alias and alias not in _GENERIC_HOST_TOKENS}


def is_owned_result(result) -> bool:
    source_class = str(getattr(result, "source_class", "") or "").strip().lower()
    relation = str(getattr(result, "relation", "") or "").strip().lower()
    return source_class in _OWNED_SOURCE_CLASSES or relation in _OWNED_RELATIONS


def subject_relevance(result, brand_name: str | None) -> float:
    aliases = brand_aliases(brand_name)
    if not aliases:
        return 0.5

    title = _normalize_text(getattr(result, "title", "") or "")
    url = _normalize_text(getattr(result, "url", "") or "")
    text = _normalize_text(
        ((getattr(result, "text", "") or "") + " " + (getattr(result, "summary", "") or ""))
    )

    if any(alias and (alias in title or alias in url) for alias in aliases):
        return 1.0
    if any(alias and alias in text for alias in aliases):
        return 0.7
    return 0.0


def filter_relevant_results(results, brand_name: str | None, *, min_relevance: float = 0.6):
    return [result for result in results if subject_relevance(result, brand_name) >= min_relevance]


def filter_independent_relevant_results(results, brand_name: str | None, *, min_relevance: float = 0.6):
    return [
        result
        for result in results
        if not is_owned_result(result) and subject_relevance(result, brand_name) >= min_relevance
    ]
