"""Capture adapter for Phase One.

Reads existing Visual Signature capture outputs and normalizes them into a
small Phase One source object. The raw capture remains primary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.visual_signature.phase_one.types import PhaseOneSourceCapture


def load_phase_one_sources(
    capture_manifest_path: str | Path,
    dismissal_audit_path: str | Path | None = None,
) -> list[PhaseOneSourceCapture]:
    capture_manifest_path = Path(capture_manifest_path)
    dismissal_audit_path = Path(dismissal_audit_path) if dismissal_audit_path else None
    capture_manifest = _load_json(capture_manifest_path)
    dismissal_audit = _load_json(dismissal_audit_path) if dismissal_audit_path else {}
    dismissal_rows = _dismissal_rows_by_brand(dismissal_audit)

    sources: list[PhaseOneSourceCapture] = []
    for row in capture_manifest.get("results", []):
        if not isinstance(row, dict):
            continue
        brand_name = str(row.get("brand_name") or "")
        supplemental = dismissal_rows.get(brand_name, {})
        source = PhaseOneSourceCapture(
            brand_name=brand_name,
            website_url=str(row.get("website_url") or row.get("page_url") or ""),
            capture_id=_capture_id(row),
            captured_at=str(row.get("captured_at") or capture_manifest.get("captured_at") or ""),
            viewport_width=_int_or_none(row.get("viewport_width") or row.get("width")),
            viewport_height=_int_or_none(row.get("viewport_height") or row.get("height")),
            raw_screenshot_path=_primary_screenshot_path(row),
            page_url=str(row.get("page_url") or row.get("website_url") or ""),
            source_manifest_path=str(capture_manifest_path),
            source_dismissal_audit_path=str(dismissal_audit_path) if dismissal_audit_path else None,
            perceptual_state=str(row.get("perceptual_state") or ""),
            perceptual_transitions=_list_of_dicts(row.get("perceptual_transitions")),
            mutation_audit=_dict_or_none(row.get("mutation_audit")) or _dict_or_none(supplemental.get("mutation_audit")),
            raw_viewport_metrics=_dict_or_none(row.get("raw_viewport_metrics")),
            before_obstruction=_dict_or_none(row.get("before_obstruction")),
            after_obstruction=_dict_or_none(row.get("after_obstruction")),
            dismissal_eligibility=str(row.get("dismissal_eligibility") or supplemental.get("dismissal_eligibility") or ""),
            dismissal_block_reason=str(row.get("dismissal_block_reason") or supplemental.get("dismissal_block_reason") or ""),
            dismissal_attempted=bool(row.get("dismissal_attempted")),
            dismissal_successful=bool(row.get("dismissal_successful")),
            clean_attempt_screenshot_path=_clean_attempt_screenshot_path(row),
            capture_variant=str(row.get("capture_variant") or ""),
            clean_attempt_capture_variant=str(row.get("clean_attempt_capture_variant") or ""),
            capture_type=str(row.get("capture_type") or ""),
        )
        sources.append(source)
    return sources


def _dismissal_rows_by_brand(dismissal_audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in dismissal_audit.get("results", []):
        if isinstance(row, dict):
            rows[str(row.get("brand_name") or "")] = row
    return rows


def _primary_screenshot_path(row: dict[str, Any]) -> str | None:
    for key in ("raw_screenshot_path", "screenshot_path"):
        value = row.get(key)
        if value:
            return str(value)
    return None


def _clean_attempt_screenshot_path(row: dict[str, Any]) -> str | None:
    for key in ("clean_attempt_screenshot_path", "secondary_screenshot_path"):
        value = row.get(key)
        if value:
            return str(value)
    return None


def _capture_id(row: dict[str, Any]) -> str:
    screenshot = _primary_screenshot_path(row)
    if screenshot:
        return Path(screenshot).stem
    return str(row.get("brand_name") or "capture")


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}
