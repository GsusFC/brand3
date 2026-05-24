"""Visual Signature extraction pipeline.

The module returns structured evidence about a brand's observable visual
behavior. It is not a scoring dimension and does not change rubric weights.
Firecrawl is an acquisition layer; Brand3 owns normalization, taxonomy,
interpretation, and extraction-confidence logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.visual_signature.adapters.firecrawl_adapter import (
    FirecrawlVisualSignatureAdapter,
    acquisition_from_web_data,
)
from src.visual_signature.normalizers.assets import normalize_asset_signals
from src.visual_signature.normalizers.colors import normalize_colors
from src.visual_signature.normalizers.components import normalize_component_signals
from src.visual_signature.normalizers.consistency import normalize_consistency_signals
from src.visual_signature.normalizers.layout import normalize_layout_signals
from src.visual_signature.normalizers.logo import normalize_logo_signals
from src.visual_signature.normalizers.typography import normalize_typography
from src.visual_signature.scoring.extraction_confidence import calculate_extraction_confidence
from src.visual_signature.types import (
    VisualAcquisitionAdapter,
    VisualSignature,
    VisualSignatureInput,
)
from src.visual_signature.vision.viewport_obstruction import analyze_viewport_obstruction
from src.visual_signature.vision.screenshot_quality import resolve_screenshot_path
from src.visual_signature.vision.multimodal_analyzer import analyze_visual_semantics, fallback_semantics


def extract_visual_signature(
    *,
    brand_name: str,
    website_url: str,
    web_data: Any | None = None,
    content_web: Any | None = None,
    screenshot_payload: dict[str, Any] | None = None,
    adapter: VisualAcquisitionAdapter | None = None,
) -> dict[str, Any]:
    """Extract structured visual behavior signals as a JSON-serializable dict.

    Existing Brand3 `content_web`/`web_data` is preferred to avoid duplicate
    Firecrawl calls during the main analysis pipeline. The adapter is used only
    when no existing web payload is provided.
    """
    input_data = VisualSignatureInput(brand_name=brand_name, website_url=website_url)
    _validate_input(input_data)
    source_web = content_web or web_data
    if source_web is not None:
        acquisition = acquisition_from_web_data(
            source_web,
            adapter="existing_web_data",
            screenshot_payload=screenshot_payload,
        )
        if not acquisition.requested_url:
            acquisition.requested_url = website_url
        if not acquisition.final_url:
            acquisition.final_url = website_url
    else:
        acquisition_adapter = adapter or FirecrawlVisualSignatureAdapter()
        acquisition = acquisition_adapter.acquire(input_data)

    colors = normalize_colors(acquisition)
    typography = normalize_typography(acquisition)
    logo = normalize_logo_signals(acquisition, brand_name)
    layout = normalize_layout_signals(acquisition)
    components = normalize_component_signals(acquisition)
    assets = normalize_asset_signals(acquisition)
    consistency = normalize_consistency_signals(
        colors=colors,
        typography=typography,
        components=components,
        assets=assets,
    )
    extraction_confidence = calculate_extraction_confidence(
        acquisition=acquisition,
        colors=colors,
        typography=typography,
        logo=logo,
        layout=layout,
        components=components,
        assets=assets,
        consistency=consistency,
    )
    screenshot_path = resolve_screenshot_path(screenshot_payload=screenshot_payload)
    screenshot_for_semantics = (
        screenshot_path
        if screenshot_path and Path(screenshot_path).exists()
        else None
    )
    try:
        semantics = analyze_visual_semantics(
            screenshot_path=screenshot_for_semantics,
            brand_name=brand_name,
        )
    except Exception:
        semantics = fallback_semantics("vision_analysis_exception")

    viewport_obstruction = analyze_viewport_obstruction(
        dom_html="\n".join([acquisition.rendered_html or "", acquisition.raw_html or ""]),
    ).to_dict()
    signature = VisualSignature(
        brand_name=brand_name,
        website_url=website_url,
        analyzed_url=acquisition.final_url or acquisition.requested_url or website_url,
        interpretation_status=_interpretation_status(acquisition),
        acquisition={
            "adapter": acquisition.adapter,
            "status_code": acquisition.status_code,
            "acquired_at": acquisition.acquired_at,
            "warnings": acquisition.warnings,
            "errors": acquisition.errors,
            "viewport_obstruction": viewport_obstruction,
        },
        colors=colors,
        typography=typography,
        logo=logo,
        layout=layout,
        components=components,
        assets=assets,
        consistency=consistency,
        extraction_confidence=extraction_confidence,
        semantics=semantics,
    )
    return signature.to_dict()


def _interpretation_status(acquisition: Any) -> str:
    if acquisition.errors:
        return "not_interpretable"
    return "interpretable"


def _validate_input(input_data: VisualSignatureInput) -> None:
    if not (input_data.brand_name or "").strip():
        raise ValueError("brand_name is required")
    if not (input_data.website_url or "").strip():
        raise ValueError("website_url is required")
    parsed = urlparse(input_data.website_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("website_url must be a valid http(s) URL")
