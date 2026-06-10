"""SV9 signal library: legacy V5 feature extractors reassigned to components.

The V5 rubric dies; its extractors survive as evidence providers for specific
ladder rungs (design doc section 9). High rungs in most ladders describe things
that are not on the brand's own site (who imitates it, who boasts about using
it, cross-surface consistency) — exactly the external evidence the legacy
collectors already gather.

This module is read-only over the persisted audit snapshot. It never recomputes
features and never calls providers.
"""

from __future__ import annotations

from typing import Any

# (V5 dimension, V5 feature) -> SV9 component that consumes it as evidence.
SIGNAL_MAP: dict[str, list[tuple[str, str]]] = {
    # Visual system rungs of Idea de marca.
    "brand_idea": [
        ("coherencia", "visual_consistency"),
    ],
    # High Magnetism rungs (active preference, belonging pride) are
    # unobservable without third parties.
    "magnetism": [
        ("percepcion", "brand_sentiment"),
        ("percepcion", "mention_volume"),
    ],
    # Personality consistency rungs.
    "personality": [
        ("coherencia", "tone_consistency"),
    ],
    # Differential-versus-alternatives rungs of Propuesta de valor.
    "value_proposition": [
        ("diferenciacion", "positioning_clarity"),
        ("diferenciacion", "competitor_distance"),
    ],
    # Public business decisions / proof rungs of Propósito.
    "core_purpose": [
        ("vitalidad", "content_recency"),
        ("vitalidad", "momentum"),
    ],
    # External axis of Coherencia: web versus the rest of digital spaces.
    "coherencia": [
        ("coherencia", "messaging_consistency"),
        ("coherencia", "tone_consistency"),
        ("coherencia", "cross_channel_coherence"),
    ],
}


def collect_signals(snapshot: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Pull mapped V5 feature values out of an audit snapshot, per component.

    Returns {component_key: [{feature, dimension, value, confidence, source}]}.
    Missing features are silently skipped: signals enrich evaluation, they are
    never a precondition.
    """
    features = snapshot.get("features") or []
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in features:
        feature = dict(row) if not isinstance(row, dict) else row
        dimension_name = str(feature.get("dimension_name") or "")
        feature_name = str(feature.get("feature_name") or "")
        if dimension_name and feature_name:
            by_key[(dimension_name, feature_name)] = feature

    signals: dict[str, list[dict[str, Any]]] = {}
    for component, wanted in SIGNAL_MAP.items():
        rows = []
        for dimension_name, feature_name in wanted:
            feature = by_key.get((dimension_name, feature_name))
            if feature is None:
                continue
            rows.append(
                {
                    "feature": feature_name,
                    "legacy_dimension": dimension_name,
                    "value": feature.get("value"),
                    "confidence": feature.get("confidence"),
                    "source": feature.get("source"),
                }
            )
        if rows:
            signals[component] = rows
    return signals
