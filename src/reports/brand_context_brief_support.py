"""Helper heuristics for Brand Context Brief generation."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from src.reports.evidence_noise import looks_like_article_or_product_card_feed
from src.reports.brand_context_brief_types import BrandContextSignal


def _packet_signals(strategic_packet: dict[str, Any]) -> list[BrandContextSignal]:
    groups = strategic_packet.get("groups") if isinstance(strategic_packet, dict) else {}
    if not isinstance(groups, dict):
        return []
    signals: list[BrandContextSignal] = []
    for group, items in groups.items():
        for item in items or []:
            if not isinstance(item, dict):
                continue
            text = _clean(str(item.get("text") or ""))
            if not text:
                continue
            signals.append(
                BrandContextSignal(
                    text=text,
                    source="strategic_packet",
                    group=str(group),
                    url=str(item.get("url") or ""),
                    surface_role=str(item.get("surface_role") or ""),
                    entity_scope=str(item.get("entity_scope") or ""),
                )
            )
    return signals


def _layer_signals(layers: dict[str, Any]) -> list[BrandContextSignal]:
    signals: list[BrandContextSignal] = []
    group_by_layer = {
        "netspace": "product_offer",
        "tactispace": "mission_language",
        "aetherspace": "mission_language",
        "ambientspace": "values_language",
    }
    for layer, group in group_by_layer.items():
        data = layers.get(layer) or {}
        if not data.get("detected"):
            continue
        for value in _as_list(data.get("evidence")):
            text = _clean(str(value or ""))
            if not text:
                continue
            signals.append(
                BrandContextSignal(
                    text=text,
                    source=f"magenta_layer:{layer}",
                    group=group,
                    surface_role="layer_evidence",
                )
            )
    return signals


def _best_value_signal(signals: list[BrandContextSignal], *, roles: set[str]) -> BrandContextSignal | None:
    candidates = [
        signal
        for signal in signals
        if (not signal.surface_role or signal.surface_role in roles)
        and _has_value_context(signal.text)
        and not _is_context_noise(signal.text)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=_value_signal_priority)[0]


def _first_signal(signals: list[BrandContextSignal], *, groups: set[str], roles: set[str]) -> BrandContextSignal | None:
    candidates = [signal for signal in signals if signal.group in groups and (not signal.surface_role or signal.surface_role in roles)]
    if not candidates:
        return None
    return sorted(candidates, key=_signal_priority)[0]


def _best_operating_signal(signals: list[BrandContextSignal | None]) -> BrandContextSignal | None:
    candidates = [
        signal
        for signal in signals
        if signal and _has_operating_context(signal.text) and not _is_context_noise(signal.text)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=_operating_signal_priority)[0]


def _signals_by_group(signals: list[BrandContextSignal], groups: set[str]) -> list[BrandContextSignal]:
    return [signal for signal in signals if signal.group in groups]


def _signals_for_layer(signals: list[BrandContextSignal], layer: str) -> list[BrandContextSignal]:
    return [signal for signal in signals if signal.source == f"magenta_layer:{layer}"]


def _unique_signals(signals: list[BrandContextSignal]) -> list[BrandContextSignal]:
    seen: set[str] = set()
    unique: list[BrandContextSignal] = []
    for signal in signals:
        key = signal.text.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(signal)
    return unique


def _brief_targets_product_surface(brief: dict[str, Any]) -> bool:
    try:
        host = urlparse(str(brief.get("url") or "")).hostname or ""
    except ValueError:
        return False
    first_label = host.split(".")[0].lower()
    return first_label in {"lab", "app", "beta", "demo", "studio", "platform"}


def _value_signal_priority(signal: BrandContextSignal) -> tuple[int, int, int, int]:
    source_rank = 0 if signal.source == "strategic_packet" else 1
    role_rank = {
        "product_system": 0,
        "audited_surface": 1,
        "homepage": 2,
        "product": 2,
        "layer_evidence": 3,
    }.get(signal.surface_role or "", 4)
    richness_rank = -_value_signal_richness(signal.text)
    length_rank = abs(len(signal.text) - 160)
    return (source_rank, role_rank, richness_rank, length_rank)


def _operating_signal_priority(signal: BrandContextSignal) -> tuple[int, int, int, int]:
    source_rank = {
        "magenta_layer:tactispace": 0,
        "magenta_layer:netspace": 1,
        "strategic_packet": 2,
    }.get(signal.source, 3)
    group_rank = 0 if signal.group == "mission_language" else 1
    strength_rank = 0 if _has_strong_operating_signal(signal.text) else 1
    length_rank = abs(len(signal.text) - 140)
    return (source_rank, group_rank, strength_rank, length_rank)


def _signal_priority(signal: BrandContextSignal) -> tuple[int, int, int]:
    role_rank = {
        "mission_about": 0,
        "product_system": 1,
        "audited_surface": 2,
        "parent_home": 3,
        "about": 3,
        "product": 3,
        "homepage": 4,
        "layer_evidence": 5,
        "policy_security": 8,
    }.get(signal.surface_role or "", 6)
    source_rank = 0 if signal.source == "strategic_packet" else 1
    length_rank = abs(len(signal.text) - 160)
    return (role_rank, source_rank, length_rank)


def _source_role_from_surface(surface_role: str) -> str:
    return {
        "audited_surface": "homepage",
        "parent_home": "homepage",
        "mission_about": "about",
        "product_system": "product",
        "policy_security": "legal_navigation",
        "layer_evidence": "layer_evidence",
    }.get(surface_role, surface_role or "unknown")


def _has_value_context(text: str) -> bool:
    low = text.lower()
    return any(
        marker in low
        for marker in (
            "platform",
            "assistant",
            "product",
            "service",
            "services",
            "solution",
            "solutions",
            "offers",
            "provides",
            "personalized",
            "always-on",
            "through",
            "para ",
            "plataforma",
            "servicios",
            "soluciones",
            "ofrece",
            "convierte",
        )
    )


def _value_signal_richness(text: str) -> int:
    low = text.lower()
    return sum(
        1
        for marker in (
            "offers",
            "provides",
            "through",
            "personalized",
            "always-on",
            "for ",
            "para ",
            "convierte",
            "gestión",
            "gestion",
            "experience",
            "experiencia",
        )
        if marker in low
    )


def _has_strong_operating_signal(text: str) -> bool:
    low = text.lower()
    return any(
        marker in low
        for marker in (
            "platform that offers",
            "platform that provides",
            " is a revolutionary ai platform",
            " offers ",
            " provides ",
            "we build",
            "we are building",
            "we're building",
            "we create",
            "we offer",
            "ofrece",
            "provee",
            "creamos",
            "estamos creando",
        )
    )


def _has_operating_context(text: str) -> bool:
    low = text.lower()
    return any(
        marker in low
        for marker in (
            " is a ",
            " is an ",
            "platform",
            "offers",
            "provides",
            "we build",
            "we are building",
            "we're building",
            "we create",
            "we offer",
            "builds",
            "creates",
            "ofrece",
            "crea",
            "creamos",
            "estamos creando",
        )
    )


def _is_context_noise(text: str) -> bool:
    low = text.lower()
    if looks_like_article_or_product_card_feed(low):
        return True
    return any(
        marker in low
        for marker in (
            "online type a message",
            "capabilities platforms start chatting",
            "start chatting beta now available",
            "outlook sendgrid mailchimp",
            "type a message",
            "##",
        )
    )


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _clean(value: str) -> str:
    return " ".join(str(value or "").split()).strip(" -|•*\t")
