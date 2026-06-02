"""Owned content extraction bake-off utilities.

This module is intentionally evaluation-only. It compares extraction methods on
the same captured HTML so Brand3 can reason about extraction quality without
changing the production acquisition path.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from html import unescape
from typing import Callable

from src.collectors.web_collector import WebCollector


DEFAULT_NOISE_TERMS = (
    "accept cookies",
    "reject all",
    "cookie preferences",
    "privacy policy",
    "terms of service",
    "login",
    "sign in",
    "careers",
    "contact us",
)

DEFAULT_STRATEGIC_TERMS = (
    "customer",
    "customers",
    "case study",
    "pricing",
    "platform",
    "product",
    "security",
    "soc 2",
    "enterprise",
    "workflow",
    "workflows",
    "automation",
    "integrations",
)


@dataclass(frozen=True)
class ExtractionMethodResult:
    method: str
    score: float
    text_chars: int
    line_count: int
    expected_hits: list[str]
    rejected_hits: list[str]
    noise_hits: list[str]
    strategic_hits: list[str]
    text_preview: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExtractionBakeoffResult:
    case_id: str
    winner: str
    results: list[ExtractionMethodResult]

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "winner": self.winner,
            "results": [item.as_dict() for item in self.results],
        }


ExtractionMethod = Callable[[str], str]


def evaluate_owned_content_extraction(
    *,
    case_id: str,
    html: str,
    expected_terms: list[str],
    rejected_terms: list[str] | None = None,
    noise_terms: list[str] | None = None,
    strategic_terms: list[str] | None = None,
    methods: dict[str, ExtractionMethod] | None = None,
) -> ExtractionBakeoffResult:
    """Evaluate extraction methods against a small, explicit quality contract."""
    selected_methods = methods or default_extraction_methods()
    rejected = rejected_terms or []
    noise = noise_terms or list(DEFAULT_NOISE_TERMS)
    strategic = strategic_terms or list(DEFAULT_STRATEGIC_TERMS)

    results = [
        _evaluate_method(
            method=name,
            text=extractor(html),
            expected_terms=expected_terms,
            rejected_terms=rejected,
            noise_terms=noise,
            strategic_terms=strategic,
        )
        for name, extractor in selected_methods.items()
    ]
    results.sort(key=lambda item: item.score, reverse=True)
    winner = results[0].method if results else ""
    return ExtractionBakeoffResult(case_id=case_id, winner=winner, results=results)


def default_extraction_methods() -> dict[str, ExtractionMethod]:
    return {
        "brand3_current_html_fallback": extract_brand3_current_html_fallback,
        "section_aware_html": extract_section_aware_html,
        "visible_body_text": extract_visible_body_text,
    }


def extract_brand3_current_html_fallback(html: str) -> str:
    return WebCollector()._html_to_markdown_fallback(html)


def extract_section_aware_html(html: str) -> str:
    """Extract text after dropping common page chrome before block parsing."""
    collector = WebCollector()
    reduced = _remove_page_chrome(html)
    return collector._html_to_markdown_fallback(reduced)


def extract_visible_body_text(html: str) -> str:
    """Naive visible-text baseline that intentionally keeps more page chrome."""
    if not html:
        return ""
    body = _body_fragment(html)
    body = re.sub(
        r"<(script|style|noscript|svg|iframe)[^>]*>.*?</\1>",
        " ",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"<[^>]+>", "\n", body)
    lines = [_normalize_text(line) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _evaluate_method(
    *,
    method: str,
    text: str,
    expected_terms: list[str],
    rejected_terms: list[str],
    noise_terms: list[str],
    strategic_terms: list[str],
) -> ExtractionMethodResult:
    clean_text = (text or "").strip()
    normalized = clean_text.lower()
    expected_hits = _term_hits(normalized, expected_terms)
    rejected_hits = _term_hits(normalized, rejected_terms)
    noise_hits = _term_hits(normalized, noise_terms)
    strategic_hits = _term_hits(normalized, strategic_terms)
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]

    expected_score = len(expected_hits) / max(1, len(expected_terms))
    strategic_score = min(1.0, len(strategic_hits) / 4)
    length_score = _length_score(len(clean_text))
    diversity_score = _line_diversity_score(lines)
    rejection_penalty = min(1.0, len(rejected_hits) / max(1, len(rejected_terms) or 1))
    noise_penalty = min(1.0, len(noise_hits) / 5)

    score = (
        expected_score * 0.55
        + strategic_score * 0.15
        + length_score * 0.20
        + diversity_score * 0.10
        - rejection_penalty * 0.35
        - noise_penalty * 0.15
    )

    return ExtractionMethodResult(
        method=method,
        score=round(max(0.0, min(1.0, score)), 4),
        text_chars=len(clean_text),
        line_count=len(lines),
        expected_hits=expected_hits,
        rejected_hits=rejected_hits,
        noise_hits=noise_hits,
        strategic_hits=strategic_hits,
        text_preview=clean_text[:360],
    )


def _length_score(text_chars: int) -> float:
    if text_chars <= 0:
        return 0.0
    if text_chars < 200:
        return text_chars / 200
    if text_chars <= 8000:
        return 1.0
    return max(0.4, 1.0 - ((text_chars - 8000) / 20000))


def _line_diversity_score(lines: list[str]) -> float:
    if not lines:
        return 0.0
    unique = {line.lower() for line in lines}
    return min(1.0, len(unique) / len(lines))


def _term_hits(normalized_text: str, terms: list[str] | tuple[str, ...]) -> list[str]:
    hits = []
    for term in terms or []:
        normalized = str(term or "").strip().lower()
        if normalized and normalized in normalized_text:
            hits.append(normalized)
    return hits


def _remove_page_chrome(html: str) -> str:
    if not html:
        return ""
    reduced = re.sub(
        r"<(nav|header|footer|aside|form)[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    reduced = re.sub(
        r"<(?P<tag>[a-z0-9]+)[^>]*(?:cookie|consent|banner|modal|drawer|menu)[^>]*>.*?</(?P=tag)>",
        " ",
        reduced,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return reduced


def _body_fragment(html: str) -> str:
    match = re.search(r"<body[^>]*>(.*?)</body>", html or "", flags=re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else (html or "")


def _normalize_text(text: str) -> str:
    return unescape(re.sub(r"\s+", " ", text or "")).strip()
