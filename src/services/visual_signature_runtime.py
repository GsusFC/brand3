"""Visual Signature shadow-run helpers."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import unquote, urlparse

from src.storage.sqlite_store import SQLiteStore
from src.visual_signature import build_visual_signature_scan, extract_visual_signature
from src.visual_signature.persistence import (
    build_visual_signature_persistence_bundle,
    persist_visual_signature_bundle,
)
from src.visual_signature.vision import enrich_visual_signature_with_vision

logger = logging.getLogger(__name__)


def _visual_signature_shadow_screenshot_payload(
    screenshot_capture: dict[str, object] | None,
    *,
    page_url: str,
) -> dict[str, object] | None:
    if not isinstance(screenshot_capture, dict):
        return None
    screenshot_url = str(screenshot_capture.get("screenshot_url") or "").strip()
    if not screenshot_url:
        return None
    parsed = urlparse(screenshot_url)
    payload: dict[str, object] = {
        "screenshot_url": screenshot_url,
        "page_url": page_url,
        "source": screenshot_capture.get("source") or "existing_brand3_screenshot",
    }
    if parsed.scheme == "file":
        payload["path"] = unquote(parsed.path)
        payload["capture_type"] = "viewport"
        payload["viewport_width"] = 1440
        payload["viewport_height"] = 1200
    return payload


def _visual_signature_shadow_failure_payload(
    *,
    brand_name: str,
    url: str,
    error: str,
) -> dict[str, object]:
    return {
        "brand_name": brand_name,
        "website_url": url,
        "analyzed_url": url,
        "interpretation_status": "not_interpretable",
        "acquisition": {
            "adapter": "visual_signature_shadow_run",
            "status_code": None,
            "warnings": [],
            "errors": [error],
        },
        "extraction_confidence": {
            "score": 0.0,
            "level": "low",
            "factors": {},
            "limitations": ["shadow_run_extraction_failed"],
        },
        "version": "visual-signature-mvp-1",
    }


def _run_visual_signature_shadow(
    *,
    enabled: bool,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    url: str,
    web_data: Any | None,
    content_web: Any | None,
    screenshot_capture: dict[str, object] | None,
    extractor=extract_visual_signature,
    vision_enricher=enrich_visual_signature_with_vision,
    persistence_fn=persist_visual_signature_bundle,
) -> dict[str, object]:
    events: list[str] = []
    if not enabled:
        logger.info("visual_signature shadow skipped (disabled)")
        return {"status": "skipped", "events": ["skipped"], "persisted": False}

    logger.info("visual_signature shadow started (run_id=%s brand=%s)", run_id, brand_name)
    events.append("started")
    screenshot_payload = _visual_signature_shadow_screenshot_payload(
        screenshot_capture,
        page_url=url,
    )
    payload: dict[str, object]
    status = "completed"

    try:
        payload = extractor(
            brand_name=brand_name,
            website_url=url,
            web_data=web_data,
            content_web=content_web,
            screenshot_payload=screenshot_payload,
        )
    except Exception as exc:
        status = "acquisition_failed"
        events.append("acquisition_failed")
        payload = _visual_signature_shadow_failure_payload(
            brand_name=brand_name,
            url=url,
            error=str(exc),
        )
        logger.warning("visual_signature shadow acquisition_failed (run_id=%s): %s", run_id, exc, exc_info=True)

    if payload.get("interpretation_status") == "not_interpretable" and "acquisition_failed" not in events:
        status = "acquisition_failed"
        events.append("acquisition_failed")
        logger.warning("visual_signature shadow acquisition_failed (run_id=%s): interpretation not_interpretable", run_id)

    if screenshot_payload:
        try:
            payload = vision_enricher(
                visual_signature_payload=payload,
                screenshot_path=str(screenshot_payload.get("path") or "") or None,
                screenshot_payload=screenshot_payload,
            )
        except Exception as exc:
            events.append("vision_skipped")
            logger.warning("visual_signature shadow vision skipped (run_id=%s): %s", run_id, exc, exc_info=True)
    else:
        events.append("vision_skipped")

    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else None
    screenshot = (vision or {}).get("screenshot") if isinstance(vision, dict) else {}
    visual_signature_scan = build_visual_signature_scan(payload)
    bundle = build_visual_signature_persistence_bundle(
        raw_visual_signature_payload=payload,
        vision_payload=vision,
        agreement_payload=(vision or {}).get("agreement") if isinstance(vision, dict) else None,
        visual_signature_scan=visual_signature_scan,
        run_id=run_id,
        brand_name=brand_name,
        website_url=url,
        screenshot_path=(screenshot or {}).get("path") if isinstance(screenshot, dict) else (screenshot_payload or {}).get("path"),
        capture_type=(screenshot or {}).get("capture_type") if isinstance(screenshot, dict) else (screenshot_payload or {}).get("capture_type"),
    )

    persisted = False
    try:
        persistence_fn(store, run_id, bundle)
        persisted = bool(store and run_id is not None)
        if persisted:
            events.append("persisted")
            logger.info("visual_signature shadow persisted (run_id=%s)", run_id)
    except Exception as exc:
        events.append("persistence_skipped")
        logger.warning("visual_signature shadow persistence skipped (run_id=%s): %s", run_id, exc, exc_info=True)

    events.append("completed")
    logger.info("visual_signature shadow completed (run_id=%s status=%s)", run_id, status)
    return {
        "status": status,
        "events": events,
        "persisted": persisted,
        "interpretation_status": payload.get("interpretation_status"),
        "agreement_level": ((vision or {}).get("agreement") or {}).get("agreement_level") if isinstance(vision, dict) else None,
        "visual_signature_score": visual_signature_scan.get("score"),
        "visual_signature_scan_status": visual_signature_scan.get("status"),
    }


def _snapshot_has_visual_signature_scan(snapshot: dict[str, Any]) -> bool:
    for item in snapshot.get("raw_inputs") or []:
        if item.get("source") != "visual_signature" or not isinstance(item.get("payload"), dict):
            continue
        scan = item["payload"].get("visual_signature_scan")
        if isinstance(scan, dict) and scan.get("schema_version") == "visual-signature-scan-v1":
            return True
    return False


def _web_data_from_snapshot(snapshot: dict[str, Any], *, fallback_url: str):
    from src.collectors.web_collector import WebData

    selected: WebData | None = None
    for item in snapshot.get("raw_inputs") or []:
        if item.get("source") != "web" or not isinstance(item.get("payload"), dict):
            continue
        try:
            selected = WebData(**item["payload"])
        except TypeError:
            continue
    return selected or WebData(url=fallback_url)


def _content_web_from_snapshot(snapshot: dict[str, Any], *, fallback):
    from src.collectors.web_collector import WebData

    selected: WebData | None = None
    for item in snapshot.get("raw_inputs") or []:
        payload = item.get("payload")
        if item.get("source") != "web" or not isinstance(payload, dict):
            continue
        if payload.get("derived") != "discovery_enrichment":
            continue
        try:
            selected = WebData(**{key: value for key, value in payload.items() if key != "derived"})
        except TypeError:
            continue
    return selected or fallback


def _screenshot_capture_from_snapshot(snapshot: dict[str, Any]) -> dict[str, object] | None:
    selected: dict[str, object] | None = None
    for item in snapshot.get("raw_inputs") or []:
        if item.get("source") != "screenshot_capture" or not isinstance(item.get("payload"), dict):
            continue
        capture = item["payload"].get("capture")
        if isinstance(capture, dict):
            selected = capture
    return selected


def run_visual_signature_for_existing_run(
    *,
    store: SQLiteStore,
    run_id: int,
    extractor=extract_visual_signature,
    vision_enricher=enrich_visual_signature_with_vision,
    persistence_fn=persist_visual_signature_bundle,
) -> dict[str, object]:
    snapshot = store.get_run_snapshot(run_id)
    if not snapshot:
        raise ValueError(f"run {run_id} not found")
    run_payload = snapshot.get("run") or {}
    brand_name = str(run_payload.get("brand_name") or "")
    url = str(run_payload.get("url") or "")
    if not url:
        raise ValueError(f"run {run_id} has no url")
    web_data = _web_data_from_snapshot(snapshot, fallback_url=url)
    content_web = _content_web_from_snapshot(snapshot, fallback=web_data)
    screenshot_capture = _screenshot_capture_from_snapshot(snapshot)
    return _run_visual_signature_shadow(
        enabled=True,
        store=store,
        run_id=run_id,
        brand_name=brand_name or url,
        url=url,
        web_data=web_data,
        content_web=content_web,
        screenshot_capture=screenshot_capture,
        extractor=extractor,
        vision_enricher=vision_enricher,
        persistence_fn=persistence_fn,
    )


def ensure_visual_signature_for_existing_run(
    *,
    store: SQLiteStore,
    run_id: int,
    extractor=extract_visual_signature,
    vision_enricher=enrich_visual_signature_with_vision,
    persistence_fn=persist_visual_signature_bundle,
) -> dict[str, object]:
    snapshot = store.get_run_snapshot(run_id)
    if not snapshot:
        raise ValueError(f"run {run_id} not found")
    if _snapshot_has_visual_signature_scan(snapshot):
        return {"status": "already_available", "persisted": False, "run_id": run_id}
    return run_visual_signature_for_existing_run(
        store=store,
        run_id=run_id,
        extractor=extractor,
        vision_enricher=vision_enricher,
        persistence_fn=persistence_fn,
    )
