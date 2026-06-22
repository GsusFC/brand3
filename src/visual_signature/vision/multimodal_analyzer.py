"""Defensive Gemini Vision semantics for Visual Signature."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

from src.config import (
    BRAND3_LLM_API_KEY,
    BRAND3_VISUAL_SIGNATURE_MODEL,
    BRAND3_VISUAL_SIGNATURE_SKIP_MULTIMODAL,
    LLM_BASE_URL,
)
from src.visual_signature._internal.multimodal_client import (
    build_cache_key as _build_cache_key,
    build_multimodal_payload as _build_multimodal_payload,
    effective_timeout as _multimodal_effective_timeout,
    mime_type_for_path as _mime_type_for_path,
    run_multimodal_http_call as _run_multimodal_http_call,
)
from src.visual_signature._internal.multimodal_normalizer import normalize_semantics_data
from src.visual_signature.versions import MULTIMODAL_PROMPT_VERSION as PROMPT_VERSION

logger = logging.getLogger(__name__)

SYSTEM_PREAMBLE = (
    "You are a senior design director auditing a rendered brand website. "
    "Evaluate only visible visual evidence. "
)

PROMPT_TEMPLATE = """Analyze the visual signature of the brand "{brand_name}" from its website screenshot.

Return ONLY valid JSON with this exact shape:
{{
  "aesthetic_style": "primary design style, or not_detected",
  "visual_mood": "visual mood / emotional tone, or not_detected",
  "visual_polish_score": 1-10,
  "visual_polish_rationale": "one short justification",
  "visual_coherence": "how imagery/layout supports brand promises, or not_detected"
}}

Use not_detected for fields where the screenshot does not provide enough evidence.
Do not infer facts that are not visible in the image."""


def analyze_visual_semantics(screenshot_path: str | None, brand_name: str) -> dict[str, Any]:
    """Analyze a local screenshot with Gemini Vision and always return a stable contract."""
    if BRAND3_VISUAL_SIGNATURE_SKIP_MULTIMODAL:
        return fallback_semantics("multimodal_disabled")

    if not screenshot_path:
        return fallback_semantics("screenshot_path_missing")

    path = Path(screenshot_path)
    if not path.exists() or not path.is_file():
        return fallback_semantics("screenshot_file_not_found")

    if not BRAND3_LLM_API_KEY:
        return fallback_semantics("api_key_missing")

    try:
        encoded_image = encode_image_base64(path)
    except Exception:
        return fallback_semantics("screenshot_unreadable")

    if not encoded_image:
        return fallback_semantics("screenshot_empty")

    body = build_multimodal_payload(
        encoded_image=encoded_image,
        mime_type=_mime_type_for_path(path),
        brand_name=brand_name,
    )

    try:
        status, content = _run_llm_http_call(
            url=f"{LLM_BASE_URL}/chat/completions",
            payload=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {BRAND3_LLM_API_KEY}",
            },
            timeout_seconds=_multimodal_effective_timeout(),
        )
    except Exception:
        return fallback_semantics("llm_error")

    if status != "ok":
        error_type = "llm_timeout" if status == "timeout" else "llm_error"
        return fallback_semantics(error_type)

    if not content:
        return fallback_semantics("empty_response")

    try:
        parsed = json.loads(_strip_json_fence(content))
    except json.JSONDecodeError:
        return fallback_semantics("json_parse_error")

    if not isinstance(parsed, dict):
        return fallback_semantics("invalid_response")

    data = normalize_semantics_data(parsed)
    return {
        "status": "detected",
        "model": BRAND3_VISUAL_SIGNATURE_MODEL,
        "prompt_version": PROMPT_VERSION,
        "fallback_used": False,
        "error_type": None,
        "data": data,
    }


def fallback_semantics(error_type: str | None) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "model": BRAND3_VISUAL_SIGNATURE_MODEL,
        "prompt_version": PROMPT_VERSION,
        "fallback_used": True,
        "error_type": error_type,
        "data": {
            "aesthetic_style": "not_detected",
            "visual_mood": "not_detected",
            "visual_polish_score": None,
            "visual_polish_rationale": "",
            "visual_coherence": "not_detected",
        },
    }


def encode_image_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def build_multimodal_payload(*, encoded_image: str, mime_type: str, brand_name: str) -> dict[str, Any]:
    return _build_multimodal_payload(
        encoded_image=encoded_image,
        mime_type=mime_type,
        brand_name=brand_name,
        prompt_template=PROMPT_TEMPLATE,
        system_preamble=SYSTEM_PREAMBLE,
    )


def build_cache_key(*, brand_name: str, screenshot_bytes: bytes) -> str:
    """Stable cache key for multimodal calls. Bumps when PROMPT_VERSION changes."""
    return _build_cache_key(
        model=BRAND3_VISUAL_SIGNATURE_MODEL,
        prompt_version=PROMPT_VERSION,
        brand_name=brand_name,
        screenshot_bytes=screenshot_bytes,
    )


def _strip_json_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _run_llm_http_call(*, url: str, payload: bytes, headers: dict[str, str], timeout_seconds: int) -> tuple[str, str]:
    return _run_multimodal_http_call(
        url=url,
        payload=payload,
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
