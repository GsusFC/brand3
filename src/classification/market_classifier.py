"""Heuristic market classification proposals.

This is the cheap first pass. It emits traceable tags with evidence, but only
auto-accepts obvious deterministic signals. LLM and human review can build on
the same schemas without changing the score pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from src.classification.schemas import ClassificationTag, MarketClassification


@dataclass(frozen=True)
class EvidenceSnippet:
    text: str
    source_url: str = ""
    source_type: str = ""


@dataclass(frozen=True)
class HeuristicRule:
    group: str
    tag: str
    confidence: str
    status: str
    needles: tuple[str, ...]
    reason_code: str


_RULES = (
    HeuristicRule(
        "business_model",
        "B2B",
        "high",
        "accepted",
        ("for teams", "for businesses", "for companies", "enterprise", "book a demo"),
        "explicit_b2b_language",
    ),
    HeuristicRule(
        "business_model",
        "SaaS",
        "high",
        "accepted",
        ("software as a service", "saas", "cloud platform", "hosted platform"),
        "explicit_saas_language",
    ),
    HeuristicRule(
        "business_model",
        "subscription",
        "high",
        "accepted",
        ("per month", "monthly", "annual plan", "subscription", "per seat"),
        "explicit_subscription_language",
    ),
    HeuristicRule(
        "technology_capability",
        "API",
        "high",
        "accepted",
        ("api", "sdk", "developer docs", "documentation"),
        "explicit_developer_interface",
    ),
    HeuristicRule(
        "technology_capability",
        "image generation",
        "medium",
        "proposed",
        ("generate image", "image generation", "upscale", "enhance images"),
        "inferred_image_generation",
    ),
    HeuristicRule(
        "technology_capability",
        "generative AI",
        "medium",
        "proposed",
        ("generative ai", "generate text", "generate video", "generate content", "ai-generated"),
        "inferred_generative_ai",
    ),
    HeuristicRule(
        "sector_industry",
        "project management",
        "medium",
        "proposed",
        ("issue tracking", "project planning", "roadmap", "sprints"),
        "inferred_project_management",
    ),
    HeuristicRule(
        "sector_industry",
        "content production",
        "medium",
        "proposed",
        ("content production", "create content", "creative workflow", "video production"),
        "inferred_content_production",
    ),
    HeuristicRule(
        "sector_industry",
        "fintech",
        "medium",
        "proposed",
        ("payments", "corporate card", "spend management", "banking"),
        "inferred_fintech",
    ),
    HeuristicRule(
        "market_signals",
        "public customer logos",
        "medium",
        "proposed",
        ("customer logos", "trusted by", "customers include"),
        "public_customer_signal",
    ),
)


def classify_market_heuristic(
    *,
    brand_key: str,
    domain: str | None = None,
    evidence: list[dict] | list[EvidenceSnippet] | None = None,
) -> MarketClassification:
    snippets = [_snippet(item) for item in evidence or []]
    text = "\n".join(item.text for item in snippets).lower()
    tags: list[ClassificationTag] = []

    active_url = _active_url(domain, snippets)
    if active_url:
        tags.append(
            _tag(
                "corporate_status",
                "active",
                "medium",
                "accepted",
                "Public website or owned evidence is available.",
                active_url,
                "active_domain_present",
            )
        )

    for rule in _RULES:
        if _has_any(text, rule.needles):
            tags.append(
                _tag(
                    rule.group,
                    rule.tag,
                    rule.confidence,
                    rule.status,
                    _match_line(snippets, rule.needles),
                    _match_url(snippets, rule.needles),
                    rule.reason_code,
                )
            )

    return MarketClassification(brand_key=brand_key, tags=tags)


def _tag(
    group: str,
    tag: str,
    confidence: str,
    status: str,
    evidence_text: str,
    source_url: str,
    reason_code: str,
) -> ClassificationTag:
    return ClassificationTag(
        group=group,
        tag=tag,
        confidence=confidence,
        status=status,
        evidence_text=evidence_text,
        source_url=source_url,
        classifier="heuristic",
        reason_codes=(reason_code,),
    )


def _snippet(value: dict | EvidenceSnippet) -> EvidenceSnippet:
    if isinstance(value, EvidenceSnippet):
        return value
    return EvidenceSnippet(
        text=str(value.get("text") or value.get("excerpt") or value.get("title") or ""),
        source_url=str(value.get("source_url") or value.get("url") or ""),
        source_type=str(value.get("source_type") or value.get("source") or ""),
    )


def _active_url(domain: str | None, snippets: list[EvidenceSnippet]) -> str:
    if domain:
        raw = domain.strip()
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        host = parsed.netloc or parsed.path
        if host:
            return f"https://{host}"
    for snippet in snippets:
        if snippet.source_url and snippet.source_type in {"owned", "owned_web", "website"}:
            return snippet.source_url
    return ""


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _match_line(snippets: list[EvidenceSnippet], needles: tuple[str, ...]) -> str:
    for snippet in snippets:
        lower = snippet.text.lower()
        if any(needle in lower for needle in needles):
            return snippet.text[:260]
    return ""


def _match_url(snippets: list[EvidenceSnippet], needles: tuple[str, ...]) -> str:
    for snippet in snippets:
        lower = snippet.text.lower()
        if any(needle in lower for needle in needles):
            return snippet.source_url
    return ""
