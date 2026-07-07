"""Text preprocessing and compaction helpers for BrandResearchPack building."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from src.reports.brand_research_pack import ResearchEvidence
from src.research.evidence_graph import EvidenceClaim, EvidenceGraph

from src.reports.brand_research_pack_building_helpers import _looks_like_crypto_product


_LANGUAGE_SELECTOR_TOKENS = (
    "english",
    "français",
    "deutsch",
    "italiano",
    "nederlands",
    "português",
    "español",
    "العربية",
    "polski",
    "中文",
    "română",
    "latviešu",
    "svenska",
    "eesti",
    "hrvatski",
    "lietuviškas",
    "dansk",
    "suomi",
    "slovenščina",
    "עברית",
    "tiếng việt",
    "ไทย",
    "filipino",
)


def _looks_like_language_selector_fragment(text: str) -> bool:
    low = text.lower()
    hits = sum(1 for token in _LANGUAGE_SELECTOR_TOKENS if token in low)
    return hits >= 4


def _strip_navigation_noise_tail(text: str) -> str:
    lowered = text.lower()
    nav_cut_markers = (
        "popular cities",
        "see more cities",
        "select your city",
        "join the millions of people worldwide",
        "top worldwide experiences",
        "we are with you",
    )
    for marker in nav_cut_markers:
        idx = lowered.find(marker)
        if idx > 90:
            return text[:idx].strip(" .,:;|")
    return text


def _strip_language_selector(text: str) -> str:
    lowered = text.lower()
    marker = " | en "
    idx = lowered.find(marker)
    if idx < 0:
        return text
    if _looks_like_language_selector_fragment(lowered[idx + len(marker) - 1 :]):
        return text[:idx].strip(" .,:;|")
    return text


def _normalize_research_pack_text(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    if not cleaned:
        return ""
    cleaned = _strip_language_selector(cleaned)
    cleaned = _strip_navigation_noise_tail(cleaned)
    if cleaned.startswith("# "):
        cleaned = cleaned[2:].strip()
    if " see experiences " in cleaned.lower() and cleaned.lower().count(" see experiences ") >= 4:
        return _compact_offer_text(cleaned)
    if len(cleaned) <= 420:
        return _compact_offer_text(cleaned)
    return _compact_offer_text(cleaned)


def _looks_like_url_only(text: str) -> bool:
    cleaned = " ".join(str(text or "").split()).strip()
    return cleaned.startswith(("http://", "https://")) and " " not in cleaned


def _audience_text(claims: Iterable[EvidenceClaim], fallback_texts: Iterable[str]) -> str:
    for claim in claims:
        if (
            claim.claim_type == "audience"
            and claim.text
            and not _looks_like_audience_noise(claim.text)
            and not _looks_like_extraction_artifact(claim.text)
            and not _looks_like_integration_title_audience(claim)
        ):
            return claim.text
    return _infer_audience_from_texts(fallback_texts)


def _looks_like_product_summary_noise(text: str) -> bool:
    low = " ".join(str(text or "").lower().split())
    if not low:
        return True
    pricing_markers = {"free", "basic", "pro", "max", "enterprise", "plan", "plans", "pricing"}
    tokens = set(low.replace("/", " ").split())
    if _looks_like_language_selector_fragment(low):
        return True
    if len(tokens) <= 5 and tokens & pricing_markers:
        return True
    if _looks_like_language_selector_fragment(low) or " | en " in low:
        return True
    return any(
        marker in low
        for marker in (
            "free pro enterprise",
            "basic pro max",
            "pricing plans",
            "compare plans",
            "pick the plan",
            "plan that fits",
            "fits your stage",
            "billing cycle",
            "credit package",
            "changing your plan",
            "top up",
            "skip to main content",
            "ask assistant",
            "api playground",
            "schema detected",
            "copy logo as svg",
            "copy wordmark as svg",
            "select your city",
            "popular cities",
            "see experiences",
        )
    )


def _looks_like_audience_noise(text: str) -> bool:
    cleaned = " ".join(str(text or "").split()).strip()
    low = cleaned.lower()
    if not cleaned:
        return True
    if low in {"free", "basic", "pro", "max", "enterprise", "startup", "starter"}:
        return True
    if low.startswith("meet the "):
        return True
    if low.startswith(("<loc>", "</loc>", "<lastmod>", "</url>")):
        return True
    if low.startswith("http://") or low.startswith("https://"):
        return True
    if "|" in cleaned or cleaned.count(" - ") >= 1:
        return True
    if any(
        marker in low
        for marker in (
            "evaluate your",
            "free pro enterprise",
            "pricing",
            "copyright",
            "privacy policy",
            "unit of evaluation",
            "model calls",
            "nodes are running",
            "pick the plan",
            "plan that fits",
            "fits your stage",
            "billing cycle",
            "credit package",
            "changing your plan",
            "top up",
            "google gemini enterprise",
            "sitemap",
            "lastmod",
            "skip to main content",
            "ask assistant",
            "api playground",
        )
    ):
        return True
    return False


def _looks_like_extraction_artifact(text: str) -> bool:
    cleaned = " ".join(str(text or "").split()).strip()
    low = cleaned.lower()
    if not cleaned:
        return True
    if low.startswith(("<loc>", "</loc>", "<lastmod>", "</url>", "urlset ")):
        return True
    return any(
        marker in low
        for marker in (
            "skip to main content",
            "search... ",
            "search...\u2318",
            "api playground",
            "ask assistant",
            "\u2318 k",
            "ctrl k",
            "main content parallel home page",
            "privacy policy terms",
        )
    )


def _looks_like_integration_title_audience(claim: EvidenceClaim) -> bool:
    text = " ".join(str(claim.text or "").split())
    low = text.lower()
    path = urlparse(str(claim.source_url or "")).path.lower()
    has_audience_marker = any(marker in low for marker in (" teams", " users", " developers", " companies", " for "))
    return "/integrations/" in path and len(text.split()) <= 5 and not has_audience_marker


def _infer_audience_from_texts(texts: Iterable[str]) -> str:
    low = " ".join(str(text or "") for text in texts).lower()
    if not low:
        return ""
    if "legal and development teams" in low:
        return "legal and development teams"
    if "development teams" in low:
        return "development teams"
    if "ai agents" in low and "developers" in low:
        return "AI builders and developers"
    if "ai teams" in low or "agent" in low and "teams" in low:
        return "AI teams"
    if "companies" in low and ("generative ai" in low or "ai" in low):
        return "companies deploying generative AI"
    if "enterprise" in low or "enterprises" in low:
        return "enterprise teams"
    if "operations teams" in low:
        return "operations teams"
    if "teams" in low:
        return "teams"
    if "founders" in low:
        return "founders"
    if "traders" in low:
        return "traders"
    if "browser" in low or "tabs" in low or "workspaces" in low or "internet" in low:
        return "browser users"
    return ""


def _strip_offer_cta_tail(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    searchable = cleaned.lower()
    for marker in (
        " unete a ",
        " quieres unirte",
        " get started",
        " start free",
        " try for free",
        " download free",
        " book a demo",
        " contact us",
    ):
        idx = searchable.find(marker)
        if idx > 40:
            cleaned = cleaned[:idx].strip(" .,:;")
            break
    return cleaned


def _compact_offer_text(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    cleaned = _strip_offer_cta_tail(cleaned)
    if len(cleaned) <= 420:
        return cleaned
    sentences = [part.strip() for part in cleaned.replace("?", ".").replace("!", ".").split(".") if part.strip()]
    priority = [
        sentence
        for sentence in sentences
        if any(
            marker in sentence.lower()
            for marker in (
                "agent engineering platform",
                "observe",
                "evaluate",
                "deploy",
                "traces",
                "platform",
                "framework",
                "assistant",
                "browser",
                "recommendation",
                "recommendations",
                "plan",
                "integration",
                "integrates",
                "shopping list",
                "evidence-backed",
                "peer-reviewed",
                "built on",
                "nutrition",
                "goals",
                "microbiome",
            )
        )
    ]
    selected = sorted(priority, key=_offer_sentence_score, reverse=True) or sentences
    compact = _join_offer_sentences(selected, max_chars=420)
    compact = compact.replace("Get a demo ", "").strip()
    compact = _strip_offer_cta_tail(compact)
    if " Observability Evaluation " in compact:
        compact = compact.split(" Observability Evaluation ", 1)[0].strip()
    if compact and not compact.endswith("."):
        compact += "."
    return compact


def _join_offer_sentences(sentences: list[str], *, max_chars: int) -> str:
    selected: list[str] = []
    for sentence in sentences:
        sentence = _clean_offer_sentence(sentence)
        if not sentence:
            continue
        candidate = ". ".join(selected + [sentence]).strip()
        if candidate and not candidate.endswith("."):
            candidate += "."
        if len(candidate) <= max_chars:
            selected.append(sentence)
        if len(selected) >= 3:
            break
    if selected:
        return ". ".join(selected).strip()
    first = sentences[0].strip() if sentences else ""
    return first[:max_chars].rsplit(" ", 1)[0].strip(" .,:;")


def _clean_offer_sentence(sentence: str) -> str:
    cleaned = " ".join(str(sentence or "").split()).strip(" .,:;")
    if " # " in cleaned:
        cleaned = cleaned.rsplit(" # ", 1)[-1].strip(" .,:;")
    return cleaned


def _offer_sentence_score(sentence: str) -> int:
    low = str(sentence or "").lower()
    score = 0
    for marker, weight in (
        ("your nutrition", 45),
        ("weekly nutrition plan", 35),
        ("help you reach your goals", 34),
        ("shopping list", 28),
        ("recommendation", 24),
        ("recommendations", 24),
        ("integration", 20),
        ("integrates", 20),
        ("nutrition", 18),
        ("plan", 18),
        ("dashboard", 14),
        ("evidence-backed", 14),
        ("peer-reviewed", 14),
        ("goals", 12),
        ("built on", 12),
        ("microbiome", 10),
        ("platform", 10),
        ("assistant", 10),
    ):
        if marker in low:
            score += weight
    if len(sentence) < 80:
        score -= 8
    if len(sentence) > 260:
        score -= 6
    return score
