"""Noise and label heuristics for strategic evidence packet helpers."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from src.reports.evidence_noise import looks_like_article_or_product_card_feed


NOISE_MARKERS = (
    "; evidence=",
    "source_type=",
    "dimension=",
    "feature=",
    "__next_data__",
    "graphql api",
    "product roadmap",
    "rg --files",
    "/bin/bash",
)


def _clean_quote(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip(" -|•*\t")
    text = re.sub(r"^#+\s*", "", text).strip()
    text = re.sub(r"^sign in to [^,]{2,80},\s*", "", text, flags=re.I).strip()
    text = re.sub(
        r"^(?P<brand>[A-Z][^.!?]{1,80})(?:\s+\([^)]{2,120}\))?\s+(?P=brand)\s+is\s+(?:a|an)\s+[^.!?]{2,120}\s+company\.\s*",
        "",
        text,
        flags=re.I,
    )
    for marker in (" [![", "🚀 See the teams behind", " See the teams behind this year"):
        idx = text.find(marker)
        if idx > 40:
            text = text[:idx].strip()
    if " # " in text:
        before, after = text.split(" # ", 1)
        repeated = before.lower().split(" - ")[-1].strip()
        if repeated and repeated in after.lower():
            text = after.strip()
    text = re.sub(
        r"^[^.!?]{8,110}\s+[|–]\s+[^.!?]{2,80}\s+(?=(?:the|el|la|los|las|kit is|[A-Z][a-z0-9]+ is)\b)",
        "",
        text,
        count=1,
        flags=re.I,
    ).strip()
    text = re.sub(r"\s+(for|para|with|by|to)$", "", text, flags=re.I).strip()
    return text.strip()


def _reject_reason(text: str) -> str | None:
    low = text.lower().strip()
    if not low or len(low) < 6:
        return "empty_or_too_short"
    if low.startswith(("http://", "https://")):
        return "url_only"
    if low.startswith("source:"):
        return "source_metadata"
    if text.strip().startswith("![") or _looks_like_image_or_logo_noise(text, low):
        return "image_alt_text_noise"
    if _looks_like_legal_or_footer_noise(low):
        return "legal_or_footer_noise"
    if _looks_like_directory_profile_noise(low):
        return "company_profile_metadata"
    if _looks_like_customer_story_fragment(low):
        return "customer_story_fragment_noise"
    if _looks_truncated(low):
        return "truncated_fragment_noise"
    if low in {"we make good shit"}:
        return "generic_slogan_noise"
    if _looks_like_short_label(low):
        return "navigation_or_section_heading_noise"
    if "company details" in low or ("industry:" in low and "type:" in low):
        return "company_profile_metadata"
    if "employees:" in low and "monthly growth" in low:
        return "company_profile_metadata"
    if any(marker in low for marker in NOISE_MARKERS):
        return "internal_or_technical_noise"
    if re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", low) or "finding email" in low or "credits left" in low:
        return "demo_contact_or_app_state_noise"
    if re.match(r"^([a-z][a-z0-9& .-]{2,50}) \1 is (?:a|an) ", low):
        return "embedded_directory_or_competitor_noise"
    if re.fullmatch(r"\[[^\]]{2,90}\]\(https?://[^)]+\)", text.strip()):
        return "markdown_link_only_noise"
    if low in {"platform capabilities", "explore services", "help and security", "startups program", "shots shots designers services explore popular"}:
        return "navigation_or_section_heading_noise"
    if "differentiates from" in low and any(marker in low for marker in ("logo", "mark", "blue", "green", "visual", "sterility", "wellness")):
        return "visual_comparison_noise"
    if (
        "api dashboard try" in low
        or "try api for free" in low
        or "one platform, two great hosting paths" in low
        or low in {"api dashboard", "dashboard"}
        or ("products pricing" in low and len(low) < 90)
    ):
        return "navigation_or_cta_noise"
    profile_hits = sum(1 for marker in ("employs", "founded in", "headquartered", "total funding", "yoy") if marker in low)
    if profile_hits >= 2:
        return "company_profile_metadata"
    if "manufacturing company" in low and "wide range of products" in low:
        return "company_profile_metadata"
    if re.match(r"^[a-z0-9 .,&()-]{2,90} is a [a-z &-]+ company\. .{0,90}\bis a ", low):
        return "company_profile_metadata"
    nav_hits = sum(
        1
        for marker in (
            "pricing", "customers", "partners", "log in", "book demo", "open positions",
            "solutions", "resources", "backed by", "join us", "about us", "contact", "sign up",
        )
        if marker in low
    )
    if nav_hits >= 3:
        return "navigation_or_hiring_noise"
    if any(marker in low for marker in ("/news/", "/blog/", "read more", "press release")):
        return "article_or_navigation_noise"
    if looks_like_article_or_product_card_feed(low):
        return "article_or_navigation_noise"
    if "hashtag" in low and any(marker in low for marker in ("instagram", "comparte tus propias fotos", "inspírate", "inspirate")):
        return "article_or_navigation_noise"
    if "operando en más de" in low or "operando en mas de" in low:
        return "company_profile_metadata"
    if "cookies" in low or "cookie" in low:
        return "legal_or_footer_noise"
    if "carrito de compra" in low:
        return "navigation_or_cta_noise"
    if "special price" in low and len(low) < 80:
        return "navigation_or_section_heading_noise"
    if "to showcase" in low and (" at " in low or "conference" in low):
        return "promotion_or_event_noise"
    if _looks_like_promotion_or_event(low) and not any(marker in low for marker in ("platform", "software", "api")):
        return "promotion_or_event_noise"
    if _looks_like_ecommerce_grid_noise(low):
        return "navigation_or_cta_noise"
    if "magic quadrant" in low or "named a leader" in low:
        return "analyst_report_or_award_noise"
    return None


def _looks_like_image_or_logo_noise(text: str, low: str) -> bool:
    return (
        "![" in text
        or "_next/image" in low
        or "copy svg" in low
        or "download svg" in low
        or "get the sentry logo" in low
        or "customer logos" in low
        or re.search(r"\b(?:logo|logos)\b", low) and "http" in low
    )


def _looks_like_ecommerce_grid_noise(low: str) -> bool:
    ecommerce_nav_hits = sum(
        1
        for marker in (
            "view more",
            "view collection",
            "shop now",
            "special price",
            "buscar producto",
            "back in stock",
            "new trending",
            "código:",
            "codigo:",
            "finalizan en",
            "obtén un",
            "obten un",
        )
        if marker in low
    )
    category_hits = sum(
        1
        for marker in (
            "sillas",
            "sofás",
            "sofas",
            "mesas",
            "taburetes",
            "almacenaje",
            "decoración",
            "decoracion",
            "iluminación",
            "iluminacion",
            "textil",
            "electrodomésticos",
            "electrodomesticos",
            "jardín",
            "jardin",
        )
        if marker in low
    )
    return ecommerce_nav_hits >= 2 or (ecommerce_nav_hits >= 1 and category_hits >= 4)


def _looks_like_legal_or_footer_noise(low: str) -> bool:
    legal_hits = sum(
        1
        for marker in (
            "privacy policy",
            "política de privacidad",
            "politica de privacidad",
            "política de cookies",
            "politica de cookies",
            "terms of service",
            "copyright",
            "all rights reserved",
            "legal entity",
            "aviso legal",
            "protección de datos",
            "proteccion de datos",
            "información personal",
            "informacion personal",
            "datos personales",
            "legislación vigente",
            "legislacion vigente",
            "medidas técnicas y organizativas",
            "medidas tecnicas y organizativas",
            "rgpd",
            "lssi",
            "effective date",
            "last updated",
            "opt-out",
        )
        if marker in low
    )
    if legal_hits >= 1 and any(
        marker in low
        for marker in (
            "policy",
            "política",
            "politica",
            "terms",
            "copyright",
            "legal",
            "all rights",
            "protección de datos",
            "proteccion de datos",
            "información personal",
            "informacion personal",
            "datos personales",
            "legislación vigente",
            "legislacion vigente",
            "medidas técnicas y organizativas",
            "medidas tecnicas y organizativas",
            "rgpd",
            "lssi",
        )
    ):
        return True
    nav_hits = sum(
        1
        for marker in ("company", "blog", "careers", "pricing", "docs", "support", "resources", "status")
        if marker in low
    )
    return nav_hits >= 5 and ("copyright" in low or "privacy" in low or "terms" in low)


def _looks_like_directory_profile_noise(low: str) -> bool:
    return any(
        marker in low
        for marker in (
            "company profile & funding",
            "company profile, team, funding",
            "pitchbook",
            "crunchbase",
            "tracxn",
            "your browser was unable to load",
            "leadership hire last 30 days",
            "boeing is among the largest global aerospace manufacturers",
        )
    )


def _looks_like_customer_story_fragment(low: str) -> bool:
    return (
        low.startswith("read story]")
        or "read story](" in low
        or "customers/" in low and ("![" in low or "**" in low or "_next/image" in low)
    )


def _looks_truncated(low: str) -> bool:
    return bool(re.search(r"\b(?:throu|softwar|platfor|developmen|infrastructur|users?|c|w|cr)\s*$", low.strip(), re.I))


def _looks_like_testimonial_quote(low: str) -> bool:
    stripped = low.strip()
    if not stripped.startswith(("“", '"', "> “", ">")):
        return False
    return any(
        marker in stripped
        for marker in (
            " for us",
            " customer",
            " using ",
            " nos ofrece",
            " nos ayuda",
            " servicio al cliente",
            " procesos de trabajo",
        )
    )


def _looks_like_promotion_or_event(low: str) -> bool:
    return any(
        marker in low
        for marker in (
            "off your first payment",
            "use code",
            "welcome20",
            "conference",
            "webinar",
            "register now",
            "save your spot",
            "named a leader",
            "magic quadrant",
        )
    )


def _looks_like_short_label(low: str) -> bool:
    if len(low) > 64:
        return False
    if any(mark in low for mark in (".", "?", "!")):
        return False
    if low.startswith(("we ", "our ", "built ", "build ", "make ", "meet ", "earn ")):
        return False
    if re.search(r"\b(?:is|are|helps|help|enables|enable|offers|provides|builds|creates|automates|streamlines|improves|reduces)\b", low):
        return False
    if low in {
        "case studies",
        "customer stories",
        "testimonials",
        "reviews",
        "estudios de caso",
        "casos de éxito",
        "testimonios",
        "reseñas",
        "opiniones",
    }:
        return True
    return any(marker in low for marker in (" + ", "products", "services", "platform", "infrastructure", "software delivery", "financial services"))


def _looks_like_bare_page_label(low: str) -> bool:
    if len(low) > 40:
        return False
    if any(mark in low for mark in (".", "?", "!", ":", "|")):
        return False
    if any(char.isdigit() for char in low):
        return False
    return not re.search(
        r"\b(?:is|are|helps|help|enables|enable|offers|provides|builds|creates|automates|streamlines|improves|reduces|usó|logró|alcanzo|alcanzó|genera|mejora|reduce|optimiza|escala|scaled)\b",
        low,
    )


def _looks_like_title_or_directory(low: str) -> bool:
    return (
        " | " in low
        or " - " in low[:120]
        or "company details" in low
        or "industry:" in low
        or "employees:" in low
    )
