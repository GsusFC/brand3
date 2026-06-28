"""Owned-surface legal identity extraction helpers."""

from __future__ import annotations

import re

from src.collectors.web_collector import WebData

_LEGAL_LABEL_PATTERNS = (
    re.compile(
        r"(?:raz[oó]n\s+social|denominaci[oó]n\s+social|legal\s+name|company\s+name)\s*[:\-]?\s*([^\n|]{3,120})",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?:titular(?:idad)?|owner|owned\s+by|operated\s+by)\s*[:\-]?\s*([^\n|]{3,120})",
        flags=re.IGNORECASE,
    ),
)

_CORPORATE_SUFFIXES = (
    "s.l.u.",
    "s.l.",
    "slu",
    "sl",
    "s.a.",
    "sa",
    "llc",
    "l.l.c.",
    "ltd",
    "ltd.",
    "limited",
    "inc",
    "inc.",
    "corp",
    "corp.",
    "corporation",
    "gmbh",
    "bv",
    "b.v.",
    "sas",
    "s.a.s.",
)

_CORPORATE_NAME_PATTERN = re.compile(
    r"\b([A-Z0-9][A-Z0-9&.,'() /-]{2,100}?(?:,\s*|\s+)(?:S\.?\s*L\.?\s*U?\.?|S\.?\s*A\.?|LLC|L\.L\.C\.|Ltd\.?|Limited|Inc\.?|Corp\.?|Corporation|GmbH|B\.?V\.?|SAS|S\.A\.S\.))\b",
    flags=re.IGNORECASE,
)


def derive_legal_name(*, brand_name: str, web_data: WebData | None) -> str | None:
    if web_data is None:
        return None
    haystacks = [
        str(web_data.title or ""),
        str(web_data.meta_description or ""),
        str(web_data.markdown_content or ""),
        str(web_data.html or ""),
    ]
    candidates: list[str] = []
    for haystack in haystacks:
        if not haystack:
            continue
        for pattern in _LEGAL_LABEL_PATTERNS:
            for match in pattern.finditer(haystack):
                candidate = _normalize_legal_name(match.group(1))
                if _looks_like_legal_name(candidate, brand_name=brand_name):
                    candidates.append(candidate)
        for match in _CORPORATE_NAME_PATTERN.finditer(haystack):
            candidate = _normalize_legal_name(match.group(1))
            if _looks_like_legal_name(candidate, brand_name=brand_name):
                candidates.append(candidate)
    return _best_legal_name(candidates, brand_name=brand_name)


def legal_name_aliases(legal_name: str | None) -> set[str]:
    cleaned = _normalize_legal_name(legal_name or "")
    if not cleaned:
        return set()
    aliases = {_normalize_token(cleaned)}
    stripped = cleaned
    for suffix in _CORPORATE_SUFFIXES:
        stripped = re.sub(rf"(?:,\s*|\s+){re.escape(suffix)}$", "", stripped, flags=re.IGNORECASE).strip(" ,.-")
    stripped_token = _normalize_token(stripped)
    if len(stripped_token) >= 4:
        aliases.add(stripped_token)
    return {alias for alias in aliases if len(alias) >= 4}


def _best_legal_name(candidates: list[str], *, brand_name: str) -> str | None:
    if not candidates:
        return None
    unique = list(dict.fromkeys(candidate for candidate in candidates if candidate))
    brand_token = _normalize_token(brand_name)
    unique.sort(
        key=lambda candidate: (
            0 if brand_token and brand_token in _normalize_token(candidate) else 1,
            -len(candidate),
        )
    )
    return unique[0] if unique else None


def _looks_like_legal_name(candidate: str, *, brand_name: str) -> bool:
    if not candidate or len(candidate) < 6:
        return False
    low = candidate.lower()
    if any(marker in low for marker in ("privacy policy", "cookie policy", "terms of service", "aviso legal")):
        return False
    has_suffix = any(re.search(rf"(?:,\s*|\s+){re.escape(suffix)}$", low) for suffix in _CORPORATE_SUFFIXES)
    if not has_suffix:
        return False
    token = _normalize_token(candidate)
    return len(token) >= 6 and any(anchor in token for anchor in _brand_anchor_tokens(brand_name))


def _normalize_legal_name(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = re.sub(r"\s+", " ", text).strip(" \t\r\n|:;,-")
    return text[:120].strip()


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def _brand_anchor_tokens(value: str) -> set[str]:
    parts = {
        _normalize_token(part)
        for part in re.split(r"[^a-z0-9]+", (value or "").lower())
        if part and part not in {"www", "com", "net", "org", "io", "ai", "co", "es", "company"}
    }
    whole = _normalize_token(value)
    if len(whole) >= 6:
        parts.add(whole)
    return {part for part in parts if len(part) >= 4}
