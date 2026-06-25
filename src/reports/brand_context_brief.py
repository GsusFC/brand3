"""Brand Context Brief for TLDR interpreters.

This is a deterministic synthesis layer between raw evidence grouping and TLDR
block interpretation. It does not invent strategy; it selects compact entity
signals that help block interpreters reason from brand/product context instead
of isolated scraper lines.
"""

from __future__ import annotations

from typing import Any

from src.reports.brand_context_brief_support import (
    _best_operating_signal,
    _best_value_signal,
    _brief_targets_product_surface,
    _clean,
    _first_signal,
    _layer_signals,
    _packet_signals,
    _signals_by_group,
    _signals_for_layer,
    _signal_priority,
    _source_role_from_surface,
    _unique_signals,
    _value_signal_priority,
    _is_context_noise,
)
from src.reports.brand_context_brief_types import BrandContextBrief, BrandContextSignal


def build_brand_context_brief(
    *,
    brand_name: str,
    url: str,
    layers: dict[str, Any] | None = None,
    strategic_packet: dict[str, Any] | None = None,
) -> BrandContextBrief:
    layers = layers or {}
    packet_signals = _packet_signals(strategic_packet or {})
    layer_signals = _layer_signals(layers)
    all_signals = packet_signals + layer_signals

    what_it_is = _first_signal(all_signals, groups={"product_offer", "mission_language"}, roles={"product_system", "audited_surface", "parent_home", "about", "product", "homepage", "layer_evidence"})
    value_signal = _best_value_signal(
        _signals_by_group(all_signals, {"product_offer", "outcome", "audience"}),
        roles={"product_system", "audited_surface", "product", "homepage", "layer_evidence"},
    )
    mission_signal = _first_signal(all_signals, groups={"mission_language"}, roles={"mission_about", "parent_home", "product_system", "about", "homepage", "product", "layer_evidence"})
    if mission_signal and _is_context_noise(mission_signal.text):
        mission_signal = None
    if not mission_signal:
        mission_signal = _best_operating_signal(
            [
                *_signals_for_layer(layer_signals, "tactispace"),
                *_signals_for_layer(layer_signals, "netspace"),
                what_it_is,
                value_signal,
            ]
        )
    future_signal = _first_signal(all_signals, groups={"vision_language"}, roles={"mission_about", "product_system", "about", "product", "layer_evidence"})
    belief_signals = _unique_signals(_signals_by_group(all_signals, {"values_language"}))[:4]

    limitations: list[str] = []
    if not what_it_is:
        limitations.append("No compact entity description was found.")
    if not mission_signal:
        limitations.append("No operating mission signal was found.")
    if not future_signal:
        limitations.append("No future-direction signal was found.")

    return BrandContextBrief(
        version="brand_context_brief_v0_1",
        brand_name=brand_name,
        url=url,
        what_it_is=what_it_is,
        value_proposition_signal=value_signal,
        operating_mission_signal=mission_signal,
        future_direction_signal=future_signal,
        belief_signals=belief_signals,
        limitations=limitations,
    )


def brand_context_candidates(block: str, brief: dict[str, Any] | None, layer: str) -> list[dict[str, str]]:
    if not isinstance(brief, dict):
        return []
    key_by_block = {
        "value_proposition": "value_proposition_signal",
        "mission": "operating_mission_signal",
        "vision": "future_direction_signal",
    }
    signal_key = key_by_block.get(block)
    if not signal_key:
        return []
    signal = brief.get(signal_key)
    if not isinstance(signal, dict) or not signal.get("text"):
        return []
    if block == "value_proposition" and not _brief_targets_product_surface(brief):
        return []
    group_by_block = {
        "value_proposition": "product_offer",
        "mission": "mission_language",
        "vision": "vision_language",
    }
    return [
        {
            "text": str(signal.get("text") or ""),
            "layer": layer,
            "source": "brand_context_brief",
            "group": group_by_block[block],
            "source_type": "context_brief",
            "feature_name": "brand_context_brief",
            "url": str(signal.get("url") or ""),
            "surface_role": str(signal.get("surface_role") or ""),
            "entity_scope": str(signal.get("entity_scope") or ""),
            "source_role": _source_role_from_surface(str(signal.get("surface_role") or "")),
            "block": block,
        }
    ]

