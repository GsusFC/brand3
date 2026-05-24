"""Defensive Gemini Vision semantics for Visual Signature."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

from src.config import BRAND3_LLM_API_KEY, LLM_BASE_URL, VISION_MODEL
from src.features.llm_analyzer import LLM_CALL_TIMEOUT_SECONDS, _run_llm_http_call


def analyze_visual_semantics(screenshot_path: str | None, brand_name: str) -> dict[str, Any]:
    """Analyze a local screenshot with Gemini Vision and always return a stable contract."""
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
            timeout_seconds=LLM_CALL_TIMEOUT_SECONDS,
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
        "model": VISION_MODEL,
        "fallback_used": False,
        "error_type": None,
        "data": data,
    }


def fallback_semantics(error_type: str | None) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "model": VISION_MODEL,
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
    prompt = f"""Analyze the visual signature of the brand "{brand_name}" from its website screenshot.

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

    return {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are a senior design director auditing a rendered brand website. "
                            "Evaluate only visible visual evidence. "
                            f"{prompt}"
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{encoded_image}",
                        },
                    },
                ],
            }
        ],
        "max_tokens": 1200,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }


def normalize_semantics_data(payload: dict[str, Any]) -> dict[str, Any]:
    visual_polish = payload.get("visual_polish")
    score = payload.get("visual_polish_score")
    rationale = payload.get("visual_polish_rationale")
    if isinstance(visual_polish, dict):
        score = visual_polish.get("score", score)
        rationale = visual_polish.get("reasoning") or visual_polish.get("rationale") or rationale

    return {
        "aesthetic_style": _non_empty_text(payload.get("aesthetic_style")),
        "visual_mood": _non_empty_text(payload.get("visual_mood")),
        "visual_polish_score": _score_or_none(score),
        "visual_polish_rationale": str(rationale or "").strip(),
        "visual_coherence": _non_empty_text(payload.get("visual_coherence")),
    }


def _non_empty_text(value: Any) -> str:
    text = str(value or "").strip()
    return text or "not_detected"


def _score_or_none(value: Any) -> int | None:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return None
    return max(1, min(10, score))


def _strip_json_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _mime_type_for_path(path: Path) -> str:
    mime_type, _encoding = mimetypes.guess_type(os.fspath(path))
    if mime_type in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
        return mime_type
    return "image/png"
