"""Discovery payload helpers for Brand3 runs."""

from __future__ import annotations

from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData
from src.collectors.web_collector import WebData
from src.discovery.entity_discovery import discover_entity
from src.discovery.search_plan import build_discovery_search_plan
from src.services.serialization import _to_jsonable


def _entity_discovery_payload(
    *,
    brand_name: str,
    url: str,
    web_data: WebData | None,
    exa_data: ExaData | None,
    context_data: ContextData | None,
) -> dict[str, object]:
    try:
        return _to_jsonable(
            discover_entity(
                brand_name=brand_name,
                url=url,
                web_data=web_data,
                exa_data=exa_data,
                context_data=context_data,
            )
        )
    except Exception:
        return {
            "entity_type": "unknown",
            "analysis_scope": "url_only",
            "confidence": 0.0,
            "warnings": ["entity_discovery_failed"],
        }


def _discovery_search_plan_payload(
    *, entity_discovery: dict[str, object], brand_name: str, url: str
) -> dict[str, object]:
    try:
        return _to_jsonable(
            build_discovery_search_plan(
                entity_discovery=entity_discovery, brand_name=brand_name, url=url
            )
        )
    except Exception:
        primary_entity = brand_name or url or "Unknown"
        return {
            "primary_entity": primary_entity,
            "requested_entity": brand_name or primary_entity,
            "analysis_mode": "url_only",
            "queries": [
                f"{primary_entity} brand positioning",
                f"{primary_entity} latest updates",
                f"{primary_entity} reviews reputation",
                f"{primary_entity} competitors",
            ],
            "owned_urls": [url] if url else [],
        }


def _annotate_content_source(features_by_dim: dict[str, dict], content_source: str) -> None:
    feature_names = {
        "coherencia": {
            "visual_consistency",
            "messaging_consistency",
            "tone_consistency",
            "cross_channel_coherence",
        },
        "diferenciacion": {
            "positioning_clarity",
            "uniqueness",
            "content_authenticity",
            "brand_personality",
        },
    }
    for dim_name, names in feature_names.items():
        for feature_name, feature in features_by_dim.get(dim_name, {}).items():
            if feature_name not in names:
                continue
            if not isinstance(feature.raw_value, dict):
                continue
            feature.raw_value["content_source"] = content_source
