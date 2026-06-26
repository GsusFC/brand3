"""Shared DOM obstruction patterns and context helpers."""

from __future__ import annotations

import re


COOKIE_TERMS = (
    "cookie",
    "cookies",
    "consent",
    "privacy",
    "gdpr",
    "ccpa",
    "onetrust",
    "trustarc",
    "usercentrics",
    "cookiebot",
    "didomi",
    "quantcast",
    "cmp",
)
NEWSLETTER_TERMS = ("newsletter", "subscribe", "subscription", "email signup")
LOGIN_TERMS = ("login", "log in", "sign in", "signin", "create account", "members only", "paywall")
PROMO_TERMS = ("promo", "promotion", "discount", "offer", "sale", "coupon")
OVERLAY_TERMS = (
    "modal",
    "dialog",
    "overlay",
    "backdrop",
    "popup",
    "pop-up",
    "popover",
    "aria-modal",
    "role=\"dialog",
    "role='dialog",
)

FIXED_LIKE_RE = re.compile(r"position\s*:\s*fixed|\bfixed\b|inset-0|fixed-bottom|bottom-0|sticky")
BOTTOM_LIKE_RE = re.compile(r"bottom\s*:\s*0|bottom-0|fixed-bottom|cookie[-_\s]?bar|consent[-_\s]?bar")
FULL_LIKE_RE = re.compile(r"inset\s*:\s*0|inset-0|height\s*:\s*100(?:vh|%)|min-height\s*:\s*100vh|w-screen|h-screen")
HIGH_Z_RE = re.compile(r"z-index\s*:\s*(?:[9]\d{2,}|\d{4,})|z-\[?\d{3,}\]?|z-50")
OVERLAY_CUES_RE = re.compile(
    r"modal|dialog|overlay|backdrop|popup|pop-up|popover|aria-modal|role=['\"]?dialog|"
    r"position\s*:\s*fixed|fixed-bottom|bottom-0|inset-0|z-\[?\d{3,}\]?|z-50|sticky"
)
PAGE_CUES_RE = re.compile(
    r"<(header|nav|footer)\b|site-header|site-nav|navbar|topbar|masthead|breadcrumb|menu|"
    r"utility-nav|primary-nav|secondary-nav|header__|nav__"
)
HEIGHT_VH_RE = re.compile(r"height\s*:\s*(\d+(?:\.\d+)?)(vh|%)")
HEIGHT_PX_RE = re.compile(r"height\s*:\s*(\d+(?:\.\d+)?)px")


def split_term_signals(text: str, terms: tuple[str, ...], *, signal_prefix: str) -> tuple[list[str], list[str]]:
    page_level_signals: list[str] = []
    overlay_level_signals: list[str] = []
    for term in terms:
        for context in term_contexts(text, term):
            signal = f"{signal_prefix}:{term}"
            if context_has_page_level_cues(context):
                page_level_signals.append(signal)
            elif context_has_overlay_cues(context):
                overlay_level_signals.append(signal)
            else:
                page_level_signals.append(signal)
    return page_level_signals, overlay_level_signals


def term_contexts(text: str, term: str, *, window: int = 220, limit: int = 3) -> list[str]:
    contexts: list[str] = []
    for match in re.finditer(re.escape(term), text):
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        contexts.append(text[start:end])
        if len(contexts) >= limit:
            break
    return contexts


def context_has_overlay_cues(context: str) -> bool:
    return bool(OVERLAY_CUES_RE.search(context))


def context_has_page_level_cues(context: str) -> bool:
    return bool(PAGE_CUES_RE.search(context))
