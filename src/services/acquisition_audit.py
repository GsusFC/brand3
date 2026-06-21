"""Acquisition provenance and audit helpers for Brand3 runs."""

from __future__ import annotations

from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData
from src.collectors.web_collector import WebData
from src.research.acquisition_plan import build_brand_research_acquisition_plan
from src.research.acquisition_trace import (
    build_brand_research_acquisition_quality_summary,
    build_brand_research_acquisition_trace,
)
from src.services.serialization import _to_jsonable


_ACQUISITION_AUDIT_MAX_FIELD_CHARS = 2000


def _truncate_for_audit(value):
    if isinstance(value, str) and len(value) > _ACQUISITION_AUDIT_MAX_FIELD_CHARS:
        return value[:_ACQUISITION_AUDIT_MAX_FIELD_CHARS] + "...[truncated]"
    if isinstance(value, dict):
        return {str(k): _truncate_for_audit(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_truncate_for_audit(v) for v in value]
    return value


def _visual_evidence_signal(screenshot_capture: dict | None) -> dict:
    """Structured visual-evidence quality flag for the snapshot.

    The capture layer describes the condition (captured / skipped / failed /
    missing) and makes it visible; it does not decide whether a visual
    dimension is evaluable — that stays with the readiness/scoring layer.
    """
    capture = screenshot_capture if isinstance(screenshot_capture, dict) else {}
    status = str(capture.get("status") or "")
    if status == "captured" and capture.get("screenshot_url"):
        return {"status": "captured", "available": True}
    if status == "skipped":
        return {
            "status": "skipped",
            "available": False,
            "reason": str(capture.get("reason") or "not_attempted"),
        }
    if status in {"error", "timeout"}:
        return {
            "status": "failed",
            "available": False,
            "error_type": str(capture.get("error_type") or status),
            "error_message": str(capture.get("error_message") or ""),
        }
    return {"status": "missing", "available": False}


def _acquisition_audit_payload(
    *,
    acquisition_provenance: dict,
    acquisition_steps: dict,
    raw_input_cache: dict,
    screenshot_capture: dict | None,
    data_quality: str,
    content_source: str,
) -> dict:
    """Capture conditions for the persisted snapshot.

    Downstream consumers read the DB snapshot, not the in-memory result, so
    without this they cannot tell fresh fetches from cache hits or partial /
    failed sources. Long strings are truncated — raw_inputs keeps the full
    payloads.
    """
    steps = {
        name: step.to_payload() for name, step in (acquisition_steps or {}).items()
    }
    return _truncate_for_audit(
        _to_jsonable(
            {
                "version": "acquisition_audit_v1",
                "data_quality": data_quality,
                "content_source": content_source,
                "raw_input_cache": dict(raw_input_cache or {}),
                "steps": steps,
                "provenance": acquisition_provenance,
                "screenshot": screenshot_capture,
                "visual_evidence": _visual_evidence_signal(screenshot_capture),
            }
        )
    )


def _acquisition_provenance_summary(
    *,
    brand_name: str,
    url: str,
    web_data: WebData | None,
    exa_data: ExaData | None,
    context_data: ContextData | None,
    discovery_enrichment_payload: dict[str, object] | None,
    raw_input_cache: dict[str, str],
    content_source: str,
    data_quality: str,
) -> dict[str, object]:
    plan = build_brand_research_acquisition_plan(
        seed_url=url,
        brand_name=brand_name,
        web_data=web_data,
        exa_data=exa_data,
        context_data=context_data,
    ).to_dict()
    trace = build_brand_research_acquisition_trace(
        acquisition_plan=plan,
        discovery_enrichment=discovery_enrichment_payload,
        raw_input_cache=raw_input_cache,
        content_source=content_source,
        data_quality=data_quality,
        web_data=web_data,
        exa_data=exa_data,
    )
    quality = build_brand_research_acquisition_quality_summary(trace)
    return {
        "plan": plan,
        "trace": trace,
        "quality": quality,
    }


def _context_evidence_items(context_data: ContextData | None) -> list[dict[str, object]]:
    if not context_data:
        return []
    base = context_data.url.rstrip("/")
    items: list[dict[str, object]] = []
    if context_data.sitemap_found:
        items.append({
            "source": "context",
            "url": f"{base}/sitemap.xml",
            "quote": f"sitemap.xml found with {context_data.sitemap_url_count} URLs",
            "feature_name": "site_structure",
            "dimension_name": "presencia",
            "confidence": 0.8,
            "freshness_days": 0,
        })
    if context_data.robots_found:
        items.append({
            "source": "context",
            "url": f"{base}/robots.txt",
            "quote": "robots.txt found",
            "feature_name": "site_structure",
            "dimension_name": "presencia",
            "confidence": 0.75,
            "freshness_days": 0,
        })
    if context_data.llms_txt_found:
        items.append({
            "source": "context",
            "url": f"{base}/llms.txt",
            "quote": "llms.txt found",
            "feature_name": "ai_discoverability",
            "dimension_name": "presencia",
            "confidence": 0.7,
            "freshness_days": 0,
        })
    if context_data.schema_types:
        items.append({
            "source": "context",
            "url": base,
            "quote": "Schema detected: " + ", ".join(context_data.schema_types[:8]),
            "feature_name": "structured_identity",
            "dimension_name": "coherencia",
            "confidence": 0.75,
            "freshness_days": 0,
        })
    found_pages = [name for name, exists in context_data.key_pages.items() if exists]
    if found_pages:
        items.append({
            "source": "context",
            "url": base,
            "quote": "Key pages found: " + ", ".join(found_pages),
            "feature_name": "content_depth",
            "dimension_name": "diferenciacion",
            "confidence": 0.65,
            "freshness_days": 0,
        })
    return items
