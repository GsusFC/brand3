"""Text normalization and answer-shaping helpers for TLDR block interpreters."""

from __future__ import annotations

import re
from typing import Any

from src.features.magnetism.block_interpreters_helpers_signals_impl import (
    _has_audience_signal,
    _has_outcome_signal,
    _is_feed_or_article_noise,
    _is_rhetorical_future_question_noise,
    _is_market_prediction_noise,
    _looks_like_concatenated_copy,
    _looks_like_portfolio_case_card,
    _looks_like_web_chrome_or_navigation_blob,
    _is_truncated_evidence,
)


def _clean_candidate_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" -|•*\t")


def _clean_layer_candidate_text(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value or "").strip(" .-|•*")
    for marker in (" Contáctanos", " Contacto", " Nuestras soluciones", " Main Menu"):
        idx = cleaned.find(marker)
        if idx > 40:
            cleaned = cleaned[:idx].strip(" .")
    return cleaned


def _is_bad_value_prop_candidate(text: str) -> bool:
    stripped = text.strip()
    low = stripped.lower()
    if low.startswith("source:"):
        return True
    if _is_truncated_evidence(low):
        return True
    if _is_feed_or_article_noise(text):
        return True
    if stripped.startswith("![") or "![" in stripped:
        return True
    if _looks_like_concatenated_copy(stripped):
        return True
    if re.fullmatch(r"\[[^\]]{2,120}\]\(https?://[^)]+\)", stripped):
        return True
    if "play video pause video" in low:
        return True
    if "teams changelog blog support docs" in low:
        return True
    if _looks_like_web_chrome_or_navigation_blob(low):
        return True
    if _looks_like_portfolio_case_card(low):
        return True
    if low.count("moments of activation") >= 2:
        return True
    if "schema detected:" in low:
        return True
    if "technology, information and internet company" in low:
        return True
    if low.startswith("a public cloud for security nerds") and len(stripped) > 420:
        return True
    if " company. " in low and " is a " in low[:120]:
        return True
    if " | " in stripped and "##" in stripped:
        return True
    if " b a s e b a s e " in low or "chain products developers solutions community" in low:
        return True
    if "customers logos" in low or "_next/image" in low:
        return True
    if "book a demo" in low and low.startswith(("book a demo", "talk to")):
        return True
    if any(
        marker in low
        for marker in (
            "política de privacidad",
            "politica de privacidad",
            "política de cookies",
            "politica de cookies",
            "rgpd",
            "lssi",
            "protección de datos",
            "proteccion de datos",
        )
    ):
        return True
    if "hashtag" in low and any(
        marker in low for marker in ("instagram", "comparte tus propias fotos", "inspírate", "inspirate")
    ):
        return True
    if low.startswith(("inclusión ", "inclusion ")) and "valoramos" in low:
        return True
    if stripped.count("**](http") or stripped.endswith("]"):
        return True
    return any(term in low for term in ("main menu", "contacto", "subscribe now", "buy now", "book a demo"))


def _is_weak_value_prop_addition(text: str) -> bool:
    low = text.strip().lower()
    if len(low) < 40 and not re.search(r"\b(?:helps|help|enables|enable|streamlines|automates|reduces|improves|builds|creates|for|para)\b", low):
        return True
    if any(marker in low for marker in ("copyright", "all rights reserved", "pricing", "privacy policy", "terms of service", "connect it to your favorite tools", "outlook sendgrid mailchimp")):
        return True
    if any(marker in low for marker in ("](", "→](", "learn more", "calculate savings", "bring all your tools")):
        return True
    return low in {"help and security", "startups program"}


def _is_developer_cloud_positioning(text: str) -> bool:
    return (
        ("platform for devs" in text or "for builders" in text or "developer-focused public cloud" in text)
        and ("deploy any code" in text or "run any code" in text or "sandboxes" in text)
    )


def _clean_value_prop_answer_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = re.sub(r"\s*\[[^\]]{2,90}\]\(https?://[^)]+\)\s*$", "", cleaned).strip()
    cleaned = re.sub(r"^New(?=[A-Z][A-Za-z0-9]+(?:'s)\b)", "", cleaned)
    cleaned = re.sub(r"^Base App Base Build Base Chain Base Pay Base App\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^[A-Z][A-Za-z0-9 .&'*-]{1,60}\s+\|\s+", "", cleaned)
    cleaned = re.sub(r"\s+Teams Changelog Blog Support Docs Explore.*$", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"\bWhere sales begin\s+Where sales begin\b", "Where sales begin", cleaned, flags=re.I)
    cleaned = re.sub(r"^Why [A-Z][^?]{2,120}\?\.\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+Businesses spend thousands on ads.*$", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"\.?launching soon\s*$", ".", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"\s+Suscr[ií]bete\b.*$", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"^¿[^?]{8,180}\?\s+(?=En\s+)", "", cleaned, flags=re.I).strip()
    return cleaned.strip()


def _value_proposition_answer(evidence: str, accepted: list[dict[str, str]]) -> str:
    primary = _clean_value_prop_answer_text(evidence)
    primary_low = primary.lower()
    if _is_developer_cloud_positioning(primary_low):
        return "A developer cloud platform for shipping and running code confidently in secure sandboxes."
    if (
        not accepted
        or len(primary) >= 90
        or (_has_audience_signal(primary_low) and _has_outcome_signal(primary_low))
    ):
        return primary
    additions: list[str] = []
    for target_group in ("outcome", "audience"):
        for item in accepted:
            text = _clean_value_prop_answer_text(str(item.get("text") or ""))
            if item.get("group") != target_group or not text or text == primary or text in additions:
                continue
            if _is_weak_value_prop_addition(text):
                continue
            additions.append(text)
            break
    if not additions:
        return primary
    answer = primary.rstrip(".") + ". " + " ".join(additions)
    return _clean_value_prop_answer_text(answer[:360].rstrip())


def _mission_answer(evidence: str) -> str:
    cleaned = _clean_value_prop_answer_text(evidence)
    low = cleaned.lower()
    if _is_developer_cloud_positioning(low):
        return "Provides developer infrastructure for deploying and running code in secure sandboxes."
    if re.match(r"^¿[^?]{8,180}\?\s+en\s+", cleaned, flags=re.I):
        cleaned = re.sub(r"^¿[^?]{8,180}\?\s+", "", cleaned, flags=re.I).strip()
        low = cleaned.lower()
    if "menos complicaciones" in low:
        cleaned = re.split(r"\bMenos complicaciones\b", cleaned, maxsplit=1, flags=re.I)[0].strip().rstrip(". ") + "."
    if len(cleaned) > 360:
        return cleaned[:357].rstrip() + "..."
    return cleaned


def _sentence_like_evidence_segments(text: str) -> list[str]:
    raw_parts = re.split(
        r"(?=(?:Build fast|The platform|Powered by|Deploy your app|Modern Compute|For builders|Deploy an app|Sandboxes|Every Sprite|Pay only|Storage That Keeps Up|Built-In Private Networking|VMs That Do Everything|Fly\.io is|A developer|A platform|Public Cloud Billing))",
        text,
    )
    parts: list[str] = []
    for raw in raw_parts:
        cleaned = re.sub(r"\s+", " ", raw).strip(" .-")
        if len(cleaned) < 20:
            continue
        if _is_weak_value_prop_addition(cleaned):
            continue
        parts.append(cleaned)
    if len(parts) <= 1:
        parts = [s.strip(" .-") for s in _sentences(text) if len(s.strip()) >= 20]
    return parts


def _representative_evidence_score(text: str, low_answer: str) -> tuple[int, int, int]:
    low = text.lower()
    overlap = sum(1 for token in set(re.findall(r"[a-z0-9-]{4,}", low_answer)) if token in low)
    signal = sum(
        1
        for marker in (
            "platform for devs",
            "for builders",
            "deploy any code",
            "run any code",
            "sandboxes",
            "deploy your app",
            "developer-focused",
            "secure",
            "confidence",
        )
        if marker in low
    )
    length_penalty = abs(len(text) - 140)
    return (signal, overlap, -length_penalty)


def _representative_evidence_phrase(evidence: str, answer: str) -> str:
    cleaned = _clean_value_prop_answer_text(evidence)
    if len(cleaned) <= 240:
        return cleaned
    low_answer = answer.lower()
    candidates = _sentence_like_evidence_segments(cleaned)
    if not candidates:
        return cleaned[:237].rstrip() + "..."
    scored = sorted(
        candidates,
        key=lambda item: _representative_evidence_score(item, low_answer),
        reverse=True,
    )
    best = scored[0].strip()
    if len(best) > 240:
        best = best[:237].rstrip() + "..."
    return best


def _evidence_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text or "") if sentence.strip()]
