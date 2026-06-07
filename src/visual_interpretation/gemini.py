"""Small native Gemini client for Lab-only visual interpretation."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from src.config import BRAND3_LLM_API_KEY, VISION_MODEL
from src.visual_interpretation.models import VisualEvidencePack, VisualInterpretation


DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_VISUAL_INTERPRETATION_MODEL = VISION_MODEL or "gemini-2.5-flash"
DEFAULT_VISUAL_ADJUDICATOR_MODEL = "gemini-2.5-pro"


class GeminiVisionClient:
    """Minimal Gemini generateContent wrapper.

    This is intentionally separate from the production OpenAI-compatible LLM
    analyzer because the Lab needs multimodal evidence and must not change
    Brand Audit or Scanner runtime behavior.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
    ):
        self.api_key = api_key or BRAND3_LLM_API_KEY
        self.base_url = (base_url or os.environ.get("BRAND3_GEMINI_BASE_URL") or DEFAULT_GEMINI_BASE_URL).rstrip("/")
        self.model = model or DEFAULT_VISUAL_INTERPRETATION_MODEL
        self.timeout_seconds = timeout_seconds
        self.last_failure: str | None = None
        self.last_usage_metadata: dict[str, Any] = {}

    def interpret(self, pack: VisualEvidencePack, *, system_prompt: str, user_prompt: str) -> VisualInterpretation:
        payload = self.build_request(pack, system_prompt=system_prompt, user_prompt=user_prompt)
        response = self._post_json(self.model, payload)
        self.last_usage_metadata = response.get("usageMetadata") if isinstance(response.get("usageMetadata"), dict) else {}
        parsed = _extract_json_response(response)
        return VisualInterpretation.from_dict(parsed, model=self.model)

    def build_request(
        self,
        pack: VisualEvidencePack,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        parts: list[dict[str, Any]] = [{"text": user_prompt}]
        image_part = _image_part(pack.screenshot_path, pack.screenshot_mime_type)
        if image_part:
            parts.append(image_part)

        return {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

    def _post_json(self, model: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            self.last_failure = "missing_api_key"
            self.last_usage_metadata = {}
            return {}

        encoded_model = urllib.parse.quote(model, safe="")
        url = f"{self.base_url}/models/{encoded_model}:generateContent?key={urllib.parse.quote(self.api_key)}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                self.last_failure = None
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            self.last_failure = f"HTTP {exc.code}: {body}"
            self.last_usage_metadata = {}
            return {}
        except Exception as exc:
            self.last_failure = str(exc)
            self.last_usage_metadata = {}
            return {}


def _image_part(path_value: str | None, mime_type: str | None) -> dict[str, Any] | None:
    path = _local_path(path_value)
    if not path or not path.exists() or not path.is_file():
        return None
    detected_mime = mime_type or mimetypes.guess_type(str(path))[0] or "image/png"
    return {
        "inlineData": {
            "mimeType": detected_mime,
            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
        }
    }


def _local_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    text = str(path_value)
    if text.startswith("file://"):
        text = text.removeprefix("file://")
    return Path(text)


def _extract_json_response(response: dict[str, Any]) -> dict[str, Any]:
    candidates = response.get("candidates") if isinstance(response, dict) else None
    if not isinstance(candidates, list) or not candidates:
        return {}
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        return {}
    text = "".join(str(part.get("text") or "") for part in parts if isinstance(part, dict)).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
