"""Pure helper predicates and text utilities for TLDR block interpreters."""

from __future__ import annotations

import re
from typing import Any

from src.reports.evidence_noise import looks_like_article_or_product_card_feed
from src.reports.vertical_signals import product_offer_family_allows_multiple_lines, product_offer_family_for_text


def _clean_candidate_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" -|•*\t")


def _contains_keyword(text: str, keyword: str) -> bool:
    escaped = re.escape(keyword.lower())
    if " " in keyword:
        return re.search(escaped, text, flags=re.IGNORECASE) is not None
    return (
        re.search(
            rf"(?<![A-Za-zÀ-ÿ0-9]){escaped}(?![A-Za-zÀ-ÿ0-9])",
            text,
            flags=re.IGNORECASE,
        )
        is not None
    )


def _has_operating_activity_signal(text: str) -> bool:
    return any(
        term in text
        for term in (
            "we build",
            "we create",
            "we provide",
            "we offer",
            "we operate",
            "we deliver",
            "we help",
            "we make",
            "we enable",
            "we empower",
            "deploy",
            "deploys",
            "run any code",
            "lets you run",
            "lets you deploy",
            "launch instantly",
            "runs on",
            "builds",
            "creates",
            "provides",
            "offers",
            "operates",
            "delivers",
            "offers",
            "accepts",
            "implements",
            "creamos",
            "construimos",
            "ofrecemos",
            "ofrece",
            "acepta",
            "implementa",
            "proporcionamos",
            "desarrollamos",
            "estamos creando",
            "estamos creado",
            "convierte",
        )
    )


def _has_formal_mission_signal(text: str) -> bool:
    low = text.strip().lower()
    return any(marker in low for marker in ("mission", "purpose", "we exist", "we do", "what we do", "our mission", "nuestra misión", "nuestra mision"))


def _has_future_signal(text: str) -> bool:
    return any(
        term in text
        for term in (
            "future",
            "future of",
            "vision",
            "visión",
            "futuro",
            "futura",
            "new model",
            "new paradigm",
            "next generation",
            "next",
            "toward",
            "towards",
            "transform",
            "redefine",
            "paradigm",
            "nuevo modelo",
            "nuevo paradigma",
            "nueva generación",
            "creative entity",
            "creative work",
            "wield power",
            "world stage",
        )
    )


def _has_offer_signal(text: str) -> bool:
    return any(
        term in text
        for term in (
            "offer",
            "offers",
            "solution",
            "solutions",
            "platform",
            "product",
            "service",
            "services",
            "api",
            "system",
            "assistant",
            "companion",
            "management",
            "streamline",
            "centralise",
            "centralize",
            "reconcile",
            "execute",
            "forecast",
            "payments",
            "pagos",
            "billing",
            "facturación",
            "financial services",
            "servicios financieros",
            "revenue",
            "ingresos",
            "product development",
            "planning and building",
            "teams and agents",
            "human intelligence",
            "business analyst",
            "research people",
            "research people and companies",
            "soluciones",
            "open stack",
            "materias primas",
            "ingredientes",
            "biorremediación",
            "cosmética",
            "nutrición",
        )
    )


def _has_audience_signal(text: str) -> bool:
    return any(
        term in text
        for term in (
            "for ",
            "para ",
            "founders",
            "teams",
            "developers",
            "enterprises",
            "creators",
            "customers",
            "clients",
            "operators",
            "startups",
            "makers",
            "subscribers",
            "athletes",
            "atletas",
            "banks",
            "erp",
            "cosmética",
            "nutrición",
            "health animal",
            "salud animal",
        )
    )


def _has_outcome_signal(text: str) -> bool:
    return any(
        term in text
        for term in (
            "save time",
            "simplify",
            "streamline",
            "secure",
            "transparent",
            "instant",
            "help teams",
            "ship software",
            "build and ship",
            "control",
            "grow",
            "grow your business",
            "grow your revenue",
            "hacer crecer",
            "gestionar",
            "gestionar el movimiento de dinero",
            "modelos personalizados",
            "potenciar",
            "transform",
            "reduce",
            "save",
            "last over time",
            "built to last",
            "duren en el tiempo",
            "dure en el tiempo",
            "duraderos",
            "duraderas",
            "build relationships",
            "get things done",
            "improve",
            "valuable channel",
            "turn subscribers into customers",
            "biorremediación",
        )
    )


def _is_vague_mission_slogan(text: str) -> bool:
    low = text.strip().lower()
    return low in {"we make good shit"} or "shit" in low


def _is_values_statement_as_mission(text: str) -> bool:
    low = text.strip().lower()
    return low.startswith(("valoramos ", "we value ", "we believe ")) and not _has_formal_mission_signal(low)


def _is_feed_or_article_noise(text: str) -> bool:
    low = text.strip().lower()
    url_count = len(re.findall(r"https?://", low))
    if any(marker in low for marker in ("]]>", "#respond", "/feed/", "?p=")):
        return True
    if url_count >= 2:
        return True
    if re.search(r"\b(?:mon|tue|wed|thu|fri|sat|sun),\s+\d{1,2}\s+[a-z]{3}\s+\d{4}", low):
        return True
    if looks_like_article_or_product_card_feed(low):
        return True
    editorial_markers = (
        "imagínate",
        "imaginate",
        "cómo puedes beneficiarte",
        "como puedes beneficiarte",
        "lo que no quieren que sepas",
        "descubre por qué",
        "descubre por que",
        "activo subyacente",
        "caídas de precios",
        "caidas de precios",
        "este tipo de seguridad",
        "muchos, ya que",
        "no te quedes fuera",
        "tú tienes una decisión",
        "tu tienes una decision",
        "quedarte en la sombra",
        "ser parte del cambio",
    )
    return any(marker in low for marker in editorial_markers)


def _is_rhetorical_future_question_noise(text: str) -> bool:
    low = text.strip().lower()
    if not _has_future_signal(low):
        return False
    if not low.endswith("?") and "?" not in low:
        return False
    rhetorical_markers = (
        "cómo ves el futuro",
        "como ves el futuro",
        "qué opinas del futuro",
        "que opinas del futuro",
        "imaginas el futuro",
        "ves el futuro",
    )
    return any(marker in low for marker in rhetorical_markers)


def _is_market_prediction_noise(text: str) -> bool:
    low = text.strip().lower()
    if not _has_future_signal(low):
        return False
    market_prediction_markers = (
        "japón está liderando",
        "japon está liderando",
        "japon esta liderando",
        "japón ha comprendido",
        "japon ha comprendido",
        "el futuro de las finanzas pasa por",
        "el futuro de las criptomonedas",
        "otros aún no ven",
        "otros aun no ven",
        "referente global",
        "incertidumbre regulatoria",
        "mercado japonés",
        "mercado japones",
    )
    if any(marker in low for marker in market_prediction_markers):
        return True
    talks_about_external_market = any(term in low for term in ("japón", "japon", "países", "paises", "mercado"))
    talks_about_brand_action = any(
        term in low
        for term in (
            "we are building",
            "we're building",
            "our vision",
            "nuestra visión",
            "nuestra vision",
            "estamos creando",
            "estamos creado",
            "bokeroon",
        )
    )
    return talks_about_external_market and not talks_about_brand_action


def _is_testimonial_evidence(text: str) -> bool:
    low = text.strip().lower()
    return low.startswith((">", "“", "\"")) or " nos ofrece " in low or " customer " in low


def _is_truncated_evidence(text: str) -> bool:
    return bool(re.search(r"\b(?:com|streamli|throu|softwar|platfor|developmen|infrastructur|users?|c|w|cr)\s*$", text.strip(), re.I))


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
    if any(marker in low for marker in ("política de privacidad", "politica de privacidad", "política de cookies", "politica de cookies", "rgpd", "lssi", "protección de datos", "proteccion de datos")):
        return True
    if "hashtag" in low and any(marker in low for marker in ("instagram", "comparte tus propias fotos", "inspírate", "inspirate")):
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


def _looks_like_web_chrome_or_navigation_blob(low: str) -> bool:
    chrome_hits = sum(
        1
        for marker in (
            "sign in",
            "subscribe",
            "book a call",
            "work about",
            "services collections",
            "home newsletter",
            "columnists",
            "podcast products events",
            "guides consulting",
            "search about us careers",
            "get a demo",
            "launch now",
        )
        if marker in low
    )
    if chrome_hits >= 2:
        return True
    if "[&>*]" in low or "*]:block" in low:
        return True
    return False


def _looks_like_portfolio_case_card(low: str) -> bool:
    if len(low) > 180 and any(marker in low for marker in ("book a call", "work about", "services collections")):
        return True
    if (
        any(marker in low for marker in ("case study", "portfolio", "crafting a brand", "brand and platform redesign"))
        and not any(marker in low for marker in ("we are", "we build", "we provide", "platform for", "service for"))
    ):
        return True
    if "go sprint" in low and "go to market" in low and "what's included" in low:
        return True
    return False


def _looks_like_concatenated_copy(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 80:
        return False
    space_ratio = stripped.count(" ") / max(len(stripped), 1)
    return space_ratio < 0.04


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
    cleaned = re.sub(r"^Why [A-Z][^?]{2,120}\?\.\s*", "", cleaned)
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


def _clean_layer_candidate_text(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value or "").strip(" .-|•*")
    for marker in (" Contáctanos", " Contacto", " Nuestras soluciones", " Main Menu"):
        idx = cleaned.find(marker)
        if idx > 40:
            cleaned = cleaned[:idx].strip(" .")
    return cleaned


def _is_navigation_noise(value: str) -> bool:
    low = value.lower().strip()
    if low.startswith("main menu"):
        return True
    nav_tokens = ("contacto", "contáctanos", "menu", "menú", "alternar menú")
    return len(value) < 120 and sum(1 for token in nav_tokens if token in low) >= 2
