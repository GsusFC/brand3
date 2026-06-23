"""Shared text/URL helpers for Brand Research Pack source modeling."""

from __future__ import annotations

import re
from typing import Any


def _clean_text(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    text = text.strip(" -|•*")
    return text


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


def _looks_like_page_chrome(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in ("navigation", "menu", "footer", "header", "feed", "article prediction", "page chrome", "breadcrumbs", "sign in", "log in", "top of page"))


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


def _primary_web_text(payload: dict[str, Any]) -> str:
    markdown = str(payload.get("markdown_content") or payload.get("content") or "").strip()
    if not markdown:
        return ""
    primary = markdown.split("\n---\n", 1)[0]
    lines = [_clean_text(line) for line in primary.splitlines()]
    for index, line in enumerate(lines):
        if not line or _looks_like_page_chrome(line):
            continue
        if len(line) >= 24 or any(mark in line for mark in (".", ",", ":", "?", "!", " is ", " are ")):
            return _clean_text(" ".join(lines[index:]))
    return _clean_text(primary)


def _confidence_notes(
    *,
    resolved,
    source_map,
    proof_points,
    founder_or_press_context,
    web_payload,
    entity_packet,
) -> list[str]:
    notes = list(resolved.notes)
    if resolved.parent_brand:
        notes.append(f"Parent brand detected: {resolved.parent_brand}.")
    if resolved.entity_type in {"product", "sub_brand"} and resolved.surface_role == "product_surface":
        notes.append("Treat the input as a product surface, not as the whole company brand.")
    if not proof_points:
        notes.append("No direct proof-point evidence surfaced in the snapshot.")
    if not founder_or_press_context:
        notes.append("No founder or press context surfaced in the snapshot.")
    if web_payload and not _primary_web_text(web_payload):
        notes.append("Web payload did not provide a clean primary page text block.")
    owned_count = sum(1 for source in source_map.values() if source.source_type.startswith("owned"))
    if owned_count:
        notes.append(f"{owned_count} owned source(s) were retained in the pack.")
    if entity_packet and entity_packet.get("limitations"):
        notes.extend(str(item) for item in entity_packet.get("limitations") if str(item).strip())
    return _unique_texts(notes)


def _evidence_gaps(
    *,
    company_summary: str,
    product_summary: str,
    offer: str,
    audience: str,
    outcome: str,
    proof_points: list[Any],
    mission: str,
    official_urls: list[str],
) -> list[str]:
    gaps = []
    if not offer:
        gaps.append("No clear offer sentence was extracted.")
    if not audience:
        gaps.append("Audience remains thin or absent.")
    if not outcome:
        gaps.append("Outcome language remains thin or absent.")
    if not mission:
        gaps.append("Mission/purpose language remains thin or absent.")
    if not proof_points:
        gaps.append("No proof-point evidence was retained.")
    if not company_summary and not product_summary:
        gaps.append("No usable homepage or summary sentence was extracted.")
    if len(official_urls) <= 1:
        gaps.append("Only one official URL was retained; parent context may still be incomplete.")
    return gaps


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]

