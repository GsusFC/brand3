"""Script-facing helpers for Visual Signature screenshot capture."""

from __future__ import annotations

from pathlib import Path

from src.visual_signature._internal.playwright_capture_helpers_capture_runtime import _derived_capture_path
from src.visual_signature.capture.playwright_capture_runtime import _normalize_capture_type
from src.visual_signature.capture.screenshot_capture_manifest import invoke_capture_fn
from src.visual_signature.capture.screenshot_capture_models import CaptureBrand


def normalize_brands(brands: list[CaptureBrand], *, default_capture_type: str) -> list[CaptureBrand]:
    return [
        CaptureBrand(
            brand_name=brand.brand_name,
            website_url=brand.website_url,
            screenshot_path=brand.screenshot_path,
            capture_type=brand.capture_type or default_capture_type,
        )
        for brand in brands
    ]


def resolve_capture_path(project_root: Path, screenshot_path: str) -> Path:
    path = Path(screenshot_path)
    if not path.is_absolute():
        path = project_root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def capture_brand(
    *,
    capture_fn,
    brand: CaptureBrand,
    screenshot_path: Path,
    capture_both: bool,
    attempt_dismiss_obstructions: bool,
) -> tuple[str, dict, str | None, Path | None, dict | None]:
    primary_capture_type = _normalize_capture_type(brand.capture_type)
    metadata = invoke_capture_fn(
        capture_fn,
        brand.brand_name,
        brand.website_url,
        str(screenshot_path),
        primary_capture_type,
        attempt_dismiss_obstructions=attempt_dismiss_obstructions,
    )
    if not capture_both:
        return primary_capture_type, metadata, None, None, None

    secondary_capture_type = "full_page" if primary_capture_type == "viewport" else "viewport"
    secondary_path = _derived_capture_path(screenshot_path, secondary_capture_type)
    secondary_metadata = invoke_capture_fn(
        capture_fn,
        brand.brand_name,
        brand.website_url,
        str(secondary_path),
        secondary_capture_type,
        attempt_dismiss_obstructions=False,
    )
    return primary_capture_type, metadata, secondary_capture_type, secondary_path, secondary_metadata
