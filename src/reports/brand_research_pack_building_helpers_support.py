"""Shared text and signal helpers for brand research pack building."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.reports.derivation import collect_evidences
from src.reports.strategic_evidence_packet import StrategicEvidenceLine


def _first_meaningful_text(*candidates: str) -> str:
    for candidate in candidates:
        text = _clean_text(candidate)
        if text:
            return text
    return ""


def _lines_text(lines: Iterable[StrategicEvidenceLine]) -> str:
    return _first_meaningful_text(*(_line.text for _line in lines if _line.text))


def _line_texts(lines: Iterable[StrategicEvidenceLine]) -> list[str]:
    return [_clean_text(line.text) for line in lines if _clean_text(line.text)]


def _tone_summary(lines: list[StrategicEvidenceLine], fallback: str) -> str:
    text = _lines_text(lines)
    if text:
        return text
    return fallback


def _infer_audience(lines: list[StrategicEvidenceLine], offer: str, summary: str) -> str:
    text = _lines_text(lines)
    if text:
        return text
    if offer:
        lowered = offer.lower()
        if "for " in lowered:
            return offer
    return summary


def _infer_outcome(lines: list[StrategicEvidenceLine], offer: str, summary: str) -> str:
    text = _lines_text(lines)
    if text:
        return text
    if offer:
        return offer
    return summary


def _concept_signals(*texts: str) -> list[str]:
    signals: list[str] = []
    for text in texts:
        cleaned = _clean_text(text)
        if not cleaned:
            continue
        if cleaned not in signals:
            signals.append(cleaned)
    return signals[:8]


def _attribute_signals(texts: list[str], snapshot: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    for text in texts:
        cleaned = _clean_text(text)
        if cleaned and cleaned not in signals:
            signals.append(cleaned)
    for item in collect_evidences(snapshot):
        if item.feature_name and item.feature_name not in signals:
            signals.append(item.feature_name)
    return signals[:12]


def _infer_category(
    offer: str,
    product_summary: str,
    company_summary: str,
    exa_payload: dict[str, Any],
    context_payload: dict[str, Any],
    resolved: Any,
) -> str:
    for text in (offer, product_summary, company_summary, getattr(resolved, "resolved_entity", "")):
        low = str(text or "").lower()
        if "platform" in low:
            return "platform"
        if "crypto" in low or "token" in low:
            return "crypto"
        if "ai" in low or "llm" in low:
            return "ai"
        if "payments" in low or "billing" in low:
            return "fintech"
    if exa_payload.get("news"):
        return "market_context"
    if context_payload.get("homepage_status"):
        return str(context_payload.get("homepage_status") or "unknown")
    return "unknown"


def _looks_like_crypto_product(text: str) -> bool:
    low = str(text or "").lower()
    return any(marker in low for marker in ("crypto", "token", "wallet", "defi", "web3"))


def _looks_like_page_chrome(text: str) -> bool:
    low = text.lower()
    return any(
        marker in low
        for marker in ("navigation", "menu", "footer", "header", "feed", "article prediction", "page chrome", "breadcrumbs", "sign in", "log in", "top of page")
    )


def _looks_like_press_or_founder_text(text: str) -> bool:
    low = text.lower()
    return any(
        marker in low
        for marker in (
            "founder",
            "founders",
            "press",
            "interview",
            "announc",
            "launch",
            "raised",
            "raises",
            "exit",
            "acquisition",
            "acquired",
        )
    )


def _filter_values_signals(lines: list[StrategicEvidenceLine]) -> list[str]:
    values: list[str] = []
    for line in lines:
        text = _clean_text(line.text)
        if not text:
            continue
        if text not in values:
            values.append(text)
    return values


def _clean_text(value: str) -> str:
    text = str(value or "").strip()
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    text = " ".join(text.split())
    return text.strip(" -|•*")


def _unique_texts(values: list[str] | tuple[str, ...] | Any) -> list[str]:
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = _clean_text(str(value or ""))
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out

