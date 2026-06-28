"""Dismissal text matching and eligibility rules."""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import float_or_none as _float_or_none


COOKIE_DISMISS_PHRASES = (
    ("accept all", "accept_all"),
    ("allow all", "allow_all"),
    ("reject all", "reject_all"),
    ("decline all", "decline_all"),
    ("i agree", "agree"),
    ("agree", "agree"),
    ("accept", "accept"),
    ("reject", "reject"),
    ("decline", "decline"),
    ("continue", "continue"),
    ("close", "close"),
    ("dismiss", "dismiss"),
    ("got it", "got_it"),
    ("ok", "ok"),
    ("aceptar todas", "accept_all"),
    ("aceptar todo", "accept_all"),
    ("aceptar", "accept"),
    ("permitir todas", "allow_all"),
    ("rechazar todas", "reject_all"),
    ("rechazar todo", "reject_all"),
    ("rechazar", "reject"),
    ("denegar", "decline"),
    ("de acuerdo", "agree"),
    ("continuar", "continue"),
    ("cerrar", "close"),
    ("entendido", "got_it"),
    ("vale", "ok"),
    ("x", "close"),
    ("×", "close"),
    ("✕", "close"),
    ("✖", "close"),
)
NEWSLETTER_DISMISS_PHRASES = (
    ("close", "close"),
    ("dismiss", "dismiss"),
    ("x", "close"),
    ("×", "close"),
    ("✕", "close"),
    ("✖", "close"),
)
COMMON_DISMISS_IGNORED_TERMS = (
    "manage choices",
    "manage preference",
    "manage preferences",
    "preferences",
    "settings",
    "customize",
    "configurar",
    "configuración",
    "configuracion",
    "preferencias",
    "ajustes",
    "personalizar",
    "subscribe",
    "sign up",
    "signup",
    "join",
    "register",
    "learn more",
)
DISMISSAL_TARGET_SELECTOR = "button, [role='button'], input[type='button'], input[type='submit'], a, [aria-label], [title], [tabindex='0']"


def should_attempt_obstruction_dismissal(obstruction: dict[str, Any] | None) -> bool:
    if not isinstance(obstruction, dict):
        return False
    if obstruction.get("present") is not True:
        return False
    if obstruction.get("type") not in {"cookie_banner", "cookie_modal", "newsletter_modal", "promo_modal"}:
        return False
    if _float_or_none(obstruction.get("confidence")) is not None and _float_or_none(obstruction.get("confidence")) < 0.55:
        return False
    signals = " ".join(str(item) for item in obstruction.get("signals") or []).lower()
    if any(token in signals for token in ("login", "paywall", "geo")):
        return False
    return True


def dismissal_eligibility(obstruction: dict[str, Any] | None) -> str:
    obstruction_type = str((obstruction or {}).get("type") or "none")
    if not isinstance(obstruction, dict) or obstruction.get("present") is not True:
        return "not_eligible"
    if obstruction_type in {"login_wall", "unknown_overlay"}:
        return "not_eligible"
    if not should_attempt_obstruction_dismissal(obstruction):
        return "not_eligible"
    if obstruction_type in {"cookie_banner", "cookie_modal", "newsletter_modal", "promo_modal"}:
        return "eligible"
    return "not_eligible"


def dismissal_patterns_for_type(obstruction_type: str) -> tuple[tuple[str, str], ...]:
    if obstruction_type in {"newsletter_modal", "promo_modal"}:
        return NEWSLETTER_DISMISS_PHRASES
    if obstruction_type in {"cookie_banner", "cookie_modal"}:
        return COOKIE_DISMISS_PHRASES
    return ()


def dismissal_context_type_for(obstruction: dict[str, Any] | None) -> str:
    obstruction_type = str((obstruction or {}).get("type") or "none")
    if obstruction_type in {"cookie_banner", "cookie_modal"}:
        return obstruction_type
    if obstruction_type in {"newsletter_modal", "promo_modal"} and has_cookie_consent_signal(obstruction):
        return "cookie_modal"
    return obstruction_type


def has_cookie_consent_signal(obstruction: dict[str, Any] | None) -> bool:
    if not isinstance(obstruction, dict):
        return False
    overlay_values: list[str] = []
    overlay_values = obstruction.get("overlay_level_signals") or []
    if isinstance(overlay_values, list):
        overlay_values = [str(value) for value in overlay_values if value is not None]
    else:
        overlay_values = []
    signal_values = obstruction.get("signals") or []
    if isinstance(signal_values, list):
        overlay_values.extend(
            str(value)
            for value in signal_values
            if value is not None and any(token in str(value).lower() for token in ("dialog", "modal", "backdrop", "overlay"))
        )
    consent_values: list[str] = []
    for key in ("signals", "page_level_signals", "overlay_level_signals", "visual_signals"):
        raw_values = obstruction.get(key) or []
        if isinstance(raw_values, list):
            consent_values.extend(str(value) for value in raw_values if value is not None)
    overlay_joined = normalize_label(" ".join(overlay_values)).replace("_", " ")
    consent_joined = normalize_label(" ".join(consent_values)).replace("_", " ")
    has_overlay = any(token in overlay_joined for token in ("dialog", "modal", "backdrop", "overlay"))
    has_consent = any(token in consent_joined for token in ("cookie", "cookies", "consent", "privacy", "gdpr", "cmp"))
    return has_overlay and has_consent


def match_dismissal_pattern(normalized: str, patterns: tuple[tuple[str, str], ...]) -> dict[str, str] | None:
    if not is_concise_dismissal_label(normalized):
        return None
    for phrase, method in patterns:
        if contains_phrase(normalized, phrase):
            return {"phrase": phrase, "method": method}
    return None


def contains_phrase(text: str, phrase: str) -> bool:
    normalized_text = normalize_label(text)
    normalized_phrase = normalize_label(phrase)
    if not normalized_text or not normalized_phrase:
        return False
    if normalized_text == normalized_phrase:
        return True
    return (
        normalized_text.startswith(f"{normalized_phrase} ")
        or normalized_text.endswith(f" {normalized_phrase}")
        or f" {normalized_phrase} " in f" {normalized_text} "
    )


def is_concise_dismissal_label(normalized: str) -> bool:
    words = [item for item in normalized.split() if item]
    return 0 < len(words) <= 6 and len(normalized) <= 80


def rejection_reason(normalized: str, obstruction_type: str) -> str | None:
    if obstruction_type in {"login_wall", "unknown_overlay"}:
        return f"obstruction_type_not_eligible:{obstruction_type}"
    if obstruction_type in {"newsletter_modal", "promo_modal"}:
        if any(term in normalized for term in ("subscribe", "sign up", "signup", "join", "register")):
            return "newsletter_call_to_action_not_safe"
        if any(term in normalized for term in ("manage choices", "manage preferences", "preferences", "settings", "customize")):
            return "manage_choices_not_safe"
        return "not_close_or_dismiss"
    if obstruction_type in {"cookie_banner", "cookie_modal"}:
        if any(term in normalized for term in ("subscribe", "sign up", "signup", "join", "register")):
            return "unsafe_subscription_action"
        if any(term in normalized for term in COMMON_DISMISS_IGNORED_TERMS):
            return "manage_choices_not_safe"
        return "not_safe_cookie_action"
    return "not_relevant"


def dismissal_skip_note(obstruction: dict[str, Any] | None) -> str:
    if not isinstance(obstruction, dict):
        return "obstruction_unavailable"
    obstruction_type = str(obstruction.get("type") or "none")
    confidence = _float_or_none(obstruction.get("confidence"))
    signals = " ".join(str(item) for item in obstruction.get("signals") or []).lower()
    if obstruction_type in {"login_wall"}:
        return f"obstruction_type_not_eligible:{obstruction_type}"
    if any(token in signals for token in ("login", "paywall", "geo")):
        return "obstruction_signals_not_eligible"
    if obstruction_type == "unknown_overlay" and (confidence is None or confidence < 0.55):
        return "unknown_overlay_low_confidence"
    if confidence is not None and confidence < 0.55:
        return "obstruction_confidence_too_low"
    if obstruction.get("present") is not True:
        return "no_obstruction_detected"
    return "dismissal_not_safe"


def find_dismissal_patterns() -> list[tuple[str, str]]:
    return [
        ("accept all", "accept_all"),
        ("reject all", "reject_all"),
        ("continue", "continue"),
        ("close", "close"),
        ("manage choices", "manage_choices"),
    ]


def normalize_label(value: str) -> str:
    return " ".join(str(value or "").lower().replace("\n", " ").split())


def split_context_tokens(value: str) -> list[str]:
    normalized = normalize_label(value).replace("_", " ")
    tokens = [item for item in normalized.split() if item]
    if not tokens and value:
        tokens = [str(value)]
    return tokens
