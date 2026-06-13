"""SV9 signal library: legacy V5 feature extractors reassigned to components.

The V5 rubric dies; its extractors survive as evidence providers for specific
tiles (baldosas v3.1). High tiles in most components describe things that are
not on the brand's own site (who imitates it, who boasts about using it,
cross-surface consistency) — exactly the external evidence the legacy
collectors already gather.

`collect_signals` is read-only over the persisted audit snapshot. The vision
helpers may call the vision model over the persisted screenshot when the
audit-time visual analysis fell back to local pixel heuristics; they never
mutate V5 data (results are cached in sv9_visual_evidence).
"""

from __future__ import annotations

import json
from typing import Any

_VISION_EVIDENCE_PROMPT = """Analyze this website screenshot as brand identity evidence. The brand is "{brand_name}".

Return ONLY valid JSON:
{{
  "logo_detected": <true/false>,
  "logo_position": "top-left|top-center|top-right|none",
  "palette_defined": <true/false>,
  "dominant_colors": ["..."],
  "typography_intentional": <true/false>,
  "visual_system_consistent": <true/false>,
  "art_direction_intentional": <true/false>,
  "design_verdict": "custom|professional-generic|template|ai-generated",
  "aesthetic_universe": "<one short phrase, or empty>",
  "concept_signals": ["observations that hint at a creative concept connecting the visuals"],
  "observations": "<brief description>"
}}"""

# (V5 dimension, V5 feature) -> SV9 component that consumes it as evidence.
SIGNAL_MAP: dict[str, list[tuple[str, str]]] = {
    # Visual-system tiles of Idea de marca.
    "brand_idea": [
        ("coherencia", "visual_consistency"),
    ],
    # High Magnetism tiles (active preference, belonging pride) are
    # unobservable without third parties.
    "magnetism": [
        ("percepcion", "brand_sentiment"),
        ("percepcion", "mention_volume"),
    ],
    # Personality consistency tiles.
    "personality": [
        ("coherencia", "tone_consistency"),
    ],
    # Differential-versus-alternatives tiles of Propuesta de valor.
    "value_proposition": [
        ("diferenciacion", "positioning_clarity"),
        ("diferenciacion", "competitor_distance"),
    ],
    # Public business decisions / proof tiles of Propósito.
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
            raw_value = feature.get("raw_value")
            rows.append(
                {
                    "feature": feature_name,
                    "legacy_dimension": dimension_name,
                    "value": feature.get("value"),
                    "confidence": feature.get("confidence"),
                    "source": feature.get("source"),
                    # The raw extractor payload carries the actual observations
                    # (detected palette, logo, style, quotes). A bare number is
                    # unjudgeable evidence for tiles.
                    "detail": str(raw_value)[:600] if raw_value else None,
                }
            )
        if rows:
            signals[component] = rows
    return signals


def merge_signals(
    base: dict[str, list[dict[str, Any]]],
    extra: dict[str, list[dict[str, Any]]] | None,
) -> dict[str, list[dict[str, Any]]]:
    if not extra:
        return base
    merged = {key: list(rows) for key, rows in base.items()}
    for key, rows in extra.items():
        merged.setdefault(key, []).extend(rows)
    return merged


def screenshot_url_from_snapshot(snapshot: dict[str, Any]) -> str | None:
    """Pull the persisted screenshot URL out of the audit snapshot, if any.

    Accepts both raw-input shapes: `payload` already parsed (get_run_snapshot)
    and `payload_json` as a string (raw table rows).
    """
    for row in snapshot.get("raw_inputs") or []:
        entry = dict(row) if not isinstance(row, dict) else row
        if str(entry.get("source") or "") != "screenshot_capture":
            continue
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            try:
                payload = json.loads(entry.get("payload_json") or "{}")
            except json.JSONDecodeError:
                continue
        capture = payload.get("capture") or {}
        url = capture.get("screenshot_url")
        if url:
            return str(url)
    return None


def snapshot_brand_name(snapshot: dict[str, Any]) -> str:
    run = snapshot.get("run")
    if isinstance(run, dict) and run.get("brand_name"):
        return str(run["brand_name"])
    return str(snapshot.get("brand_name") or "")


def audit_visual_method(snapshot: dict[str, Any]) -> str:
    """How the audit-time visual analysis was produced (vision vs local fallback)."""
    for row in snapshot.get("features") or []:
        feature = dict(row) if not isinstance(row, dict) else row
        if feature.get("feature_name") != "visual_consistency":
            continue
        raw = str(feature.get("raw_value") or "")
        if "vision_llm" in raw or "'method': 'mixed'" in raw:
            return "vision"
        if "local_image_analysis" in raw or "heuristic_fallback" in raw:
            return "local"
    return "absent"


def compute_vision_observations(
    snapshot: dict[str, Any],
    *,
    analyzer: Any = None,
) -> dict[str, Any] | None:
    """Run the vision model over the persisted screenshot. Returns None when
    there is no screenshot, no vision key, or the call fails (signals enrich,
    never block)."""
    url = screenshot_url_from_snapshot(snapshot)
    if not url:
        return None
    if analyzer is None:
        from src.features.visual_analyzer import VisualAnalyzer

        analyzer = VisualAnalyzer()
    if not getattr(analyzer, "vision_api_key", None):
        return None
    try:
        image_path = analyzer._download_image(url)
        if not image_path:
            return None
        image_b64 = analyzer._encode_image_base64(image_path)
        prompt = _VISION_EVIDENCE_PROMPT.format(brand_name=snapshot_brand_name(snapshot))
        payload = analyzer._call_vision_api(image_b64, prompt)
    except Exception:
        return None
    if not isinstance(payload, dict) or "logo_detected" not in payload:
        return None
    return payload


def vision_signals(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Expose vision observations as evaluator signals.

    Idea de marca owns the visual-system rungs; Coherencia's 'el diseño cuenta
    la misma historia que el copy' rung also benefits from the design verdict.
    """
    detail = json.dumps(payload, ensure_ascii=False)[:600]
    base = {
        "feature": "vision_observations",
        "legacy_dimension": "sv9_vision_pass",
        "value": payload.get("design_verdict"),
        "confidence": "high",
        "source": "vision_llm",
        "detail": detail,
    }
    return {"brand_idea": [dict(base)], "coherencia": [dict(base)]}
