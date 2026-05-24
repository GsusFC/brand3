"""Optional persistence helpers for Visual Signature evidence.

This layer stores evidence as raw inputs only. It does not influence Brand3
scoring, rubric dimensions, or production UI behavior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


PersistenceSchemaVersion = Literal["visual-signature-persistence-1"]


@dataclass
class VisualSignaturePersistenceBundle:
    schema_version: PersistenceSchemaVersion = "visual-signature-persistence-1"
    run_id: int | None = None
    brand_name: str | None = None
    website_url: str | None = None
    run_metadata: dict[str, Any] = field(default_factory=dict)
    artifact_refs: dict[str, Any] = field(default_factory=dict)
    raw_visual_signature_payload: dict[str, Any] | None = None
    vision_payload: dict[str, Any] | None = None
    agreement_payload: dict[str, Any] | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


def build_visual_signature_persistence_bundle(
    *,
    raw_visual_signature_payload: dict[str, Any] | None,
    vision_payload: dict[str, Any] | None = None,
    agreement_payload: dict[str, Any] | None = None,
    run_id: int | None = None,
    brand_name: str | None = None,
    website_url: str | None = None,
    screenshot_path: str | Path | None = None,
    secondary_screenshot_path: str | Path | None = None,
    manifest_path: str | Path | None = None,
    capture_type: str | None = None,
    secondary_capture_type: str | None = None,
) -> VisualSignaturePersistenceBundle:
    raw = raw_visual_signature_payload or {}
    vision = vision_payload or (raw.get("vision") if isinstance(raw, dict) else None) or {}
    agreement = agreement_payload or (vision.get("agreement") if isinstance(vision, dict) else None) or {}

    acquisition = raw.get("acquisition") if isinstance(raw, dict) else {}
    screenshot = vision.get("screenshot") if isinstance(vision, dict) else {}

    primary_capture_type = _normalize_capture_type(capture_type or (screenshot or {}).get("capture_type"))
    secondary_capture_type = _normalize_capture_type(secondary_capture_type)
    if secondary_capture_type == "unknown":
        secondary_capture_type = None

    run_metadata = {
        "acquisition_status": _acquisition_status(acquisition),
        "screenshot_available": bool((screenshot or {}).get("available")),
        "viewport_available": primary_capture_type == "viewport" or bool(vision.get("viewport_composition")),
        "full_page_available": primary_capture_type == "full_page" or secondary_capture_type == "full_page",
        "interpretation_status": str(
            (raw.get("interpretation_status") if isinstance(raw, dict) else None) or "unknown"
        ),
        "agreement_level": str((agreement or {}).get("agreement_level") or "unknown"),
    }
    artifact_refs = {
        "screenshot_path": str(screenshot_path) if screenshot_path else None,
        "secondary_screenshot_path": str(secondary_screenshot_path) if secondary_screenshot_path else None,
        "manifest_path": str(manifest_path) if manifest_path else None,
        "capture_type": primary_capture_type,
        "secondary_capture_type": secondary_capture_type,
    }
    artifact_refs = {key: value for key, value in artifact_refs.items() if value not in (None, "")}
    return VisualSignaturePersistenceBundle(
        run_id=run_id,
        brand_name=brand_name or (raw.get("brand_name") if isinstance(raw, dict) else None),
        website_url=website_url or (raw.get("website_url") if isinstance(raw, dict) else None),
        run_metadata=run_metadata,
        artifact_refs=artifact_refs,
        raw_visual_signature_payload=raw if isinstance(raw, dict) else None,
        vision_payload=vision if isinstance(vision, dict) else None,
        agreement_payload=agreement if isinstance(agreement, dict) else None,
    )


def persist_visual_signature_bundle(store, run_id: int | None, bundle: VisualSignaturePersistenceBundle) -> None:
    if not store or run_id is None:
        return
    store.save_visual_signature_evidence(run_id, bundle.to_dict())


def persist_visual_signature_result(
    store,
    run_id: int | None,
    result: dict[str, Any] | None,
) -> None:
    """Persist a Visual Signature payload from a broader Brand3 run result.

    This is intentionally inert unless the run result already contains a
    Visual Signature payload. It keeps the persistence path optional and
    evidence-only.
    """
    if not store or run_id is None or not isinstance(result, dict):
        return
    payload = result.get("visual_signature") or result.get("visual_signature_evidence")
    if not isinstance(payload, dict):
        return
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else None
    screenshot = (vision or {}).get("screenshot") if isinstance(vision, dict) else None
    bundle = build_visual_signature_persistence_bundle(
        raw_visual_signature_payload=payload,
        vision_payload=vision,
        agreement_payload=(vision or {}).get("agreement") if isinstance(vision, dict) else None,
        run_id=run_id,
        brand_name=result.get("brand_name") or result.get("brand"),
        website_url=result.get("website_url") or result.get("url"),
        screenshot_path=(screenshot or {}).get("path") if isinstance(screenshot, dict) else None,
        secondary_screenshot_path=(screenshot or {}).get("secondary_path") if isinstance(screenshot, dict) else None,
        manifest_path=result.get("visual_signature_manifest_path"),
        capture_type=(screenshot or {}).get("capture_type") if isinstance(screenshot, dict) else None,
        secondary_capture_type=(screenshot or {}).get("secondary_capture_type") if isinstance(screenshot, dict) else None,
    )
    persist_visual_signature_bundle(store, run_id, bundle)


def _acquisition_status(acquisition: Any) -> str:
    if not isinstance(acquisition, dict):
        return "unknown"
    errors = acquisition.get("errors") or []
    status_code = acquisition.get("status_code")
    if errors:
        return "error"
    if isinstance(status_code, int) and 200 <= status_code < 400:
        return "ok"
    if status_code is not None:
        return "unknown" if status_code == 0 else "ok"
    return "ok" if acquisition else "unknown"


def _normalize_capture_type(value: Any) -> str:
    capture_type = str(value or "").strip().lower()
    if capture_type in {"viewport", "full_page"}:
        return capture_type
    return "unknown"


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value
