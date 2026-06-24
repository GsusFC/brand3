"""Signal and noise heuristics for TLDR block interpreters."""

from __future__ import annotations

import re

from src.reports.evidence_noise import looks_like_article_or_product_card_feed


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
    return any(
        marker in low
        for marker in (
            "mission",
            "purpose",
            "we exist",
            "we do",
            "what we do",
            "our mission",
            "nuestra misión",
            "nuestra mision",
        )
    )


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


def _is_navigation_noise(value: str) -> bool:
    low = value.lower().strip()
    if low.startswith("main menu"):
        return True
    nav_tokens = ("contacto", "contáctanos", "menu", "menú", "alternar menú")
    return len(value) < 120 and sum(1 for token in nav_tokens if token in low) >= 2


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
