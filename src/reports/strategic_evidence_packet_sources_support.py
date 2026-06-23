"""Owned raw web/page candidate helpers for strategic evidence packets."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from src.reports.strategic_evidence_packet_helpers_noise_support import _clean_quote

_EMBEDDED_SUBPAGE_RE = re.compile(r"(?:^|\n)## Subpage:\s*(?P<url>\S+)\s*\n", re.IGNORECASE)


def _is_proof_page_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        path = urlparse(url).path.lower()
    except ValueError:
        return False
    return any(
        marker in path
        for marker in (
            "/customers",
            "/customer",
            "/clients",
            "/client",
            "/clientes",
            "/cliente",
            "/case-study",
            "/case-studies",
            "/success-stories",
            "/stories",
            "/casos",
            "/caso-de-exito",
            "/casos-de-exito",
            "/reviews",
            "/review",
            "/ratings",
            "/resenas",
            "/reseñas",
            "/opiniones",
            "/testimonials",
            "/testimonial",
            "/testimonios",
            "/testimonio",
        )
    )


def _primary_web_page_text(markdown: str) -> str:
    match = _EMBEDDED_SUBPAGE_RE.search(markdown or "")
    if not match:
        return markdown
    return markdown[: match.start()].strip(" -\n")


def _embedded_web_subpage_texts(markdown: str) -> list[tuple[str, str]]:
    matches = list(_EMBEDDED_SUBPAGE_RE.finditer(markdown or ""))
    pages: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        page_url = match.group("url").strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        text = (markdown[start:end] or "").strip(" -\n")
        if page_url or text:
            pages.append((page_url, text))
    return pages


def _raw_candidate_lines(text: str) -> list[str]:
    candidates: list[str] = []
    cta_pattern = re.compile(
        r"\b(?:start free trial|book demo|contact sales|contacta con ventas|try for free|get started|inicia sesión|log in)\b",
        re.I,
    )
    for raw in (text or "").splitlines():
        line = _clean_quote(raw)
        if not line:
            continue
        cta_chunks = [_clean_quote(chunk) for chunk in cta_pattern.split(line)]
        cta_chunks = [chunk for chunk in cta_chunks if len(chunk) >= 8]
        if len(cta_chunks) > 1:
            candidates.extend(cta_chunks)
            continue
        if len(line) <= 320:
            candidates.append(line)
            continue
        chunks = re.split(r"(?<=[.!?])\s+|\s{2,}", line)
        candidates.extend(_clean_quote(chunk) for chunk in chunks if len(_clean_quote(chunk)) >= 8)
    return candidates[:160]


def _candidate_dedupe_key(text: str, *, url: str | None, group: str) -> tuple[str, str, str]:
    normalized_url = (str(url or "").rstrip("/")).lower()
    fingerprint = re.sub(r"\s+", " ", str(text or "").strip().lower())
    return (normalized_url, group, fingerprint)


def _looks_like_about_mission_or_values_line(low: str) -> bool:
    return low.startswith(
        (
            "historia de la marca",
            "nuestra misión",
            "nuestra mision",
            "nuestro propósito",
            "nuestro proposito",
            "valores y filosofía",
            "valores y filosofia",
            "inclusión ",
            "inclusion ",
            "valoramos ",
        )
    ) or "inclusión valoramos" in low or "inclusion valoramos" in low


def _groups_for(text: str, source_type: str, url: str | None = None) -> list[str]:
    from src.reports.strategic_evidence_packet_helpers import (
        GROUP_KEYWORDS,
        OWNED_SOURCE_TYPES,
        _looks_like_bare_page_label,
        _looks_like_testimonial_quote,
    )

    low = text.lower()
    if _looks_like_testimonial_quote(low):
        return ["proof_points"]

    if source_type in OWNED_SOURCE_TYPES and _is_proof_page_url(url):
        return [] if _looks_like_bare_page_label(low) else ["proof_points"]

    groups = [
        group
        for group, keywords in GROUP_KEYWORDS.items()
        if any(keyword in low for keyword in keywords)
    ]
    if "product_offer" in groups and _looks_like_about_mission_or_values_line(low):
        groups = [group for group in groups if group != "product_offer"]
    if source_type not in OWNED_SOURCE_TYPES and groups:
        groups = [group for group in groups if group in {"proof_points", "third_party_context"}]
        if "third_party_context" not in groups:
            groups.append("third_party_context")
    return list(dict.fromkeys(groups))


def _add_owned_raw_page_candidates(
    packet: Any,
    seen: set[tuple[str, str, str]],
    text: str,
    source_url: str,
    entity_research_packet: dict[str, Any] | None = None,
) -> None:
    from src.reports.strategic_evidence_packet_helpers import _add_candidate_line as _add_candidate_line_impl

    added = 0
    max_lines = 32 if _is_proof_page_url(source_url) else 24
    for line in _raw_candidate_lines(text):
        before = sum(len(values) for values in packet.groups.values())
        _add_candidate_line_impl(
            packet,
            seen,
            text=line,
            source_type="owned_raw",
            source_domain=None,
            url=source_url,
            feature_name="raw_web",
            dimension=None,
            entity_research_packet=entity_research_packet,
        )
        after = sum(len(values) for values in packet.groups.values())
        if after > before:
            added += 1
            packet.source_counts["owned_raw"] = packet.source_counts.get("owned_raw", 0) + 1
        if added >= max_lines:
            break


def _add_owned_raw_web_candidates(
    packet: Any,
    snapshot: dict[str, Any],
    seen: set[tuple[str, str, str]],
    entity_research_packet: dict[str, Any] | None = None,
) -> None:
    if entity_research_packet is None:
        from src.reports.strategic_evidence_packet_helpers_support import _entity_research_packet

        entity_research_packet = _entity_research_packet(snapshot)
    run_url = ((snapshot.get("run") or {}).get("url") or packet.url or "")
    for raw_input in snapshot.get("raw_inputs") or []:
        if raw_input.get("source") not in {"web", "hyperbrowser"}:
            continue
        payload = raw_input.get("payload") or {}
        markdown = str(
            payload.get("markdown_content")
            or payload.get("content")
            or payload.get("markdown")
            or ""
        )
        if not markdown:
            continue
        source_url = str(
            payload.get("canonical_url")
            or payload.get("source_url")
            or payload.get("url")
            or payload.get("page_url")
            or run_url
        )
        pages = [(source_url, _primary_web_page_text(markdown))]
        pages.extend(_embedded_web_subpage_texts(markdown))
        for page_url, page_text in pages:
            if page_text:
                _add_owned_raw_page_candidates(
                    packet,
                    seen,
                    page_text,
                    page_url,
                    entity_research_packet=entity_research_packet,
                )
