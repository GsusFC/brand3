"""Visual Signature shadow-run helpers."""

from __future__ import annotations

import logging
from typing import Any

from src.storage.sqlite_store import SQLiteStore
from src.visual_signature import extract_visual_signature
from src.visual_signature.persistence import persist_visual_signature_bundle
from src.visual_signature.vision import enrich_visual_signature_with_vision
from src.services.visual_signature_snapshot import (
    _content_web_from_snapshot as _content_web_from_snapshot_impl,
    _screenshot_capture_from_snapshot as _screenshot_capture_from_snapshot_impl,
    _snapshot_has_visual_signature_evidence as _snapshot_has_visual_signature_evidence_impl,
    _snapshot_has_visual_signature_scan as _snapshot_has_visual_signature_scan_impl,
    _visual_signature_shadow_screenshot_payload as _visual_signature_shadow_screenshot_payload_impl,
    _web_data_from_snapshot as _web_data_from_snapshot_impl,
)
from src.services.visual_signature_runtime_snapshot_support import require_snapshot
from src.services.visual_signature_runtime_snapshot_support import snapshot_identity
from src.services.visual_signature_runtime_support import build_failure_payload
from src.services.visual_signature_runtime_support import build_shadow_bundle
from src.services.visual_signature_runtime_support import enrich_payload_with_vision
from src.services.visual_signature_runtime_support import persist_shadow_bundle
from src.services.visual_signature_runtime_support import shadow_result

logger = logging.getLogger(__name__)


def _visual_signature_shadow_screenshot_payload(
    screenshot_capture: dict[str, object] | None,
    *,
    page_url: str,
) -> dict[str, object] | None:
    return _visual_signature_shadow_screenshot_payload_impl(
        screenshot_capture,
        page_url=page_url,
    )


def _visual_signature_shadow_failure_payload(
    *,
    brand_name: str,
    url: str,
    error: str,
) -> dict[str, object]:
    return build_failure_payload(
        brand_name=brand_name,
        url=url,
        error=error,
    )


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

    payload = enrich_payload_with_vision(
        payload=payload,
        screenshot_payload=screenshot_payload,
        run_id=run_id,
        vision_enricher=vision_enricher,
        logger=logger,
        events=events,
    )
    vision, _screenshot, shadow_bundle = build_shadow_bundle(
        payload=payload,
        run_id=run_id,
        brand_name=brand_name,
        url=url,
        screenshot_payload=screenshot_payload,
    )

    persisted = persist_shadow_bundle(
        store=store,
        run_id=run_id,
        bundle=shadow_bundle["bundle"],
        persistence_fn=persistence_fn,
        logger=logger,
        events=events,
    )

    events.append("completed")
    logger.info("visual_signature shadow completed (run_id=%s status=%s)", run_id, status)
    return shadow_result(
        status=status,
        events=events,
        persisted=persisted,
        payload=payload,
        vision=vision,
        visual_signature_scan=shadow_bundle["visual_signature_scan"],
        visual_signature_evidence=shadow_bundle["visual_signature_evidence"],
    )


def _snapshot_has_visual_signature_scan(snapshot: dict[str, Any]) -> bool:
    return _snapshot_has_visual_signature_scan_impl(snapshot)


def _snapshot_has_visual_signature_evidence(snapshot: dict[str, Any]) -> bool:
    return _snapshot_has_visual_signature_evidence_impl(snapshot)


def _web_data_from_snapshot(snapshot: dict[str, Any], *, fallback_url: str):
    return _web_data_from_snapshot_impl(snapshot, fallback_url=fallback_url)


def _content_web_from_snapshot(snapshot: dict[str, Any], *, fallback):
    return _content_web_from_snapshot_impl(snapshot, fallback=fallback)


def _screenshot_capture_from_snapshot(snapshot: dict[str, Any]) -> dict[str, object] | None:
    return _screenshot_capture_from_snapshot_impl(snapshot)


def run_visual_signature_for_existing_run(
    *,
    store: SQLiteStore,
    run_id: int,
    extractor=extract_visual_signature,
    vision_enricher=enrich_visual_signature_with_vision,
    persistence_fn=persist_visual_signature_bundle,
) -> dict[str, object]:
    snapshot = require_snapshot(store, run_id)
    brand_name, url = snapshot_identity(snapshot, run_id=run_id)
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
    snapshot = require_snapshot(store, run_id)
    if _snapshot_has_visual_signature_scan(snapshot) and _snapshot_has_visual_signature_evidence(snapshot):
        return {"status": "already_available", "persisted": False, "run_id": run_id}
    return run_visual_signature_for_existing_run(
        store=store,
        run_id=run_id,
        extractor=extractor,
        vision_enricher=vision_enricher,
        persistence_fn=persistence_fn,
    )
