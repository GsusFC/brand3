"""Deterministic block evidence shortlists for Analyst TLDR."""

from __future__ import annotations

from typing import Any


TLDR_BLOCK_SHORTLIST_FIELDS: dict[str, tuple[str, ...]] = {
    "core_purpose": ("declared_purpose", "company_summary", "product_summary"),
    "magnetism": ("offer", "company_summary", "visual_or_conceptual_signals"),
    "value_proposition": ("offer", "product_summary", "outcome", "audience"),
    "personality": ("tone_of_voice", "personality_signals"),
    "brand_idea": ("visual_or_conceptual_signals", "offer", "future_direction"),
    "attributes": ("attributes_signals", "personality_signals"),
    "values": ("values_signals", "declared_purpose"),
    "mission": ("declared_mission", "declared_purpose", "company_summary"),
    "vision": ("future_direction", "visual_or_conceptual_signals"),
}

TLDR_BLOCK_SIGNAL_FIELDS: dict[str, tuple[str, ...]] = {
    "personality": ("tone_of_voice", "personality_signals"),
    "attributes": ("attributes_signals", "personality_signals"),
    "values": ("values_signals",),
}



def block_evidence_shortlists(pack: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    if not isinstance(pack, dict):
        return {}
    source_map = pack.get("source_map") if isinstance(pack.get("source_map"), dict) else {}
    default_source_key = _default_source_key(source_map, pack)
    result: dict[str, list[dict[str, str]]] = {}
    for block, fields in TLDR_BLOCK_SHORTLIST_FIELDS.items():
        rows: list[dict[str, str]] = []
        fallback_rows: list[dict[str, str]] = []
        seen: set[str] = set()
        for field in fields:
            value = pack.get(field)
            items = value if isinstance(value, list) else [value]
            for item in items:
                text = _extract_text(item)
                if not text:
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                row = {
                    "text": text,
                    "field": field,
                    "source_key": _extract_source_key(item, default_source_key),
                }
                if _looks_structural_blob(text):
                    fallback_rows.append(row)
                else:
                    rows.append(row)
                if len(rows) >= 4:
                    break
            if len(rows) >= 4:
                break
        if not rows:
            rows = fallback_rows[:4]
        result[block] = rows
    return result


def shortlist_rows_for_block(pack: dict[str, Any], block: str) -> list[dict[str, str]]:
    return list(block_evidence_shortlists(pack).get(block, []))


def shortlist_texts_for_block(pack: dict[str, Any], block: str) -> list[str]:
    return [row["text"] for row in shortlist_rows_for_block(pack, block) if row.get("text")]


def block_signal_candidates(pack: dict[str, Any]) -> dict[str, list[str]]:
    if not isinstance(pack, dict):
        return {}
    result: dict[str, list[str]] = {}
    for block, fields in TLDR_BLOCK_SIGNAL_FIELDS.items():
        terms: list[str] = []
        seen: set[str] = set()
        for field in fields:
            value = pack.get(field)
            items = value if isinstance(value, list) else [value]
            for item in items:
                for term in _extract_signal_terms(item):
                    key = term.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    terms.append(term)
                    if len(terms) >= 4:
                        break
                if len(terms) >= 4:
                    break
            if len(terms) >= 4:
                break
        result[block] = terms
    return result


def signal_candidates_for_block(pack: dict[str, Any], block: str) -> list[str]:
    return list(block_signal_candidates(pack).get(block, []))


def _extract_text(item: Any) -> str:
    if isinstance(item, dict):
        for key in ("text", "label", "title"):
            value = _clean_text(item.get(key))
            if value:
                return value
        return ""
    return _clean_text(item)


def _extract_signal_terms(item: Any) -> list[str]:
    text = _extract_text(item)
    if not text:
        return []
    if _looks_sentence_like(text):
        return []
    raw_terms = text.split(",") if "," in text else [text]
    terms: list[str] = []
    for raw in raw_terms:
        term = _clean_text(str(raw).strip(" [](){}'\""))
        if not term or _looks_sentence_like(term):
            continue
        if _looks_synthetic_metric(term):
            continue
        if len(term.split()) > 4 or len(term) > 40:
            continue
        terms.append(term)
    return terms


def _extract_source_key(item: Any, fallback: str) -> str:
    if isinstance(item, dict):
        for key in ("source_url", "url", "source_key"):
            value = _clean_text(item.get(key))
            if value:
                return value.rstrip("/") if value.startswith(("http://", "https://")) else value
    return fallback


def _default_source_key(source_map: dict[str, Any], pack: dict[str, Any]) -> str:
    official_urls = pack.get("official_urls")
    if isinstance(official_urls, list):
        for item in official_urls:
            value = _clean_text(item)
            if value:
                return value.rstrip("/") if value.startswith(("http://", "https://")) else value
    for key, value in source_map.items():
        if isinstance(value, dict) and str(value.get("source_type") or "").startswith("owned"):
            normalized = _clean_text(value.get("url") or key)
            if normalized:
                return normalized.rstrip("/") if normalized.startswith(("http://", "https://")) else normalized
    return _clean_text(pack.get("input_url")).rstrip("/")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _looks_sentence_like(value: str) -> bool:
    low = value.lower()
    if any(marker in low for marker in (".", "!", "?", ";", ":")):
        return True
    return len(low.split()) > 8


def _looks_structural_blob(value: str) -> bool:
    text = _clean_text(value)
    if not text:
        return False
    if text.startswith("#") and len(text.split()) > 30:
        return True
    return len(text) > 320 and any(marker in text for marker in ("How ", "SDK, API", "Platform UI", "Run the same test suite"))


def _looks_synthetic_metric(value: str) -> bool:
    low = _clean_text(value).lower()
    if "_" in low:
        return True
    return low in {
        "web_presence",
        "search_visibility",
        "content_recency",
        "publication_cadence",
        "momentum",
        "visual_consistency",
        "tone_consistency",
        "positioning_clarity",
        "brand_sentiment",
        "site_structure",
        "content_depth",
    }
