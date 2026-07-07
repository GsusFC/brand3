"""Support utilities for LLM analyzer transport and response validation."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

PROMPT_VERSION = "brand3-llm-v1"
LLM_CALL_TIMEOUT_SECONDS = int(os.environ.get("BRAND3_LLM_CALL_TIMEOUT_SECONDS", "35"))
STRUCTURED_RESEARCH_PACK_LIMIT = 6000


def _llm_prompt_input(value: str, *, default_limit: int) -> str:
    """Preserve structured evidence packs while keeping legacy raw markdown bounded."""
    text = value or ""
    limit = (
        STRUCTURED_RESEARCH_PACK_LIMIT
        if text.lstrip().startswith("Structured Brand Research Pack")
        else default_limit
    )
    return text[:limit]


def _looks_like_timeout(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    reason = getattr(exc, "reason", None)
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return True
    return "timed out" in str(exc).lower() or "timeout" in str(exc).lower()


def _llm_http_request_once(
    url: str,
    payload: bytes,
    headers: dict[str, str],
    timeout_seconds: int | None,
) -> tuple[str, str, dict | None]:
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            data = json.loads(resp.read())
            msg = data["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning") or ""
            usage = data.get("usage") if isinstance(data, dict) else None
            return "ok", content, usage if isinstance(usage, dict) else None
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")[:500]
        return "http_error", f"HTTP {exc.code}: {error_body}", None
    except Exception as exc:
        reason = "timeout" if _looks_like_timeout(exc) else "error"
        return reason, str(exc), None


def _gemini_http_request_once(
    url: str,
    payload: bytes,
    headers: dict[str, str],
    timeout_seconds: int | None,
) -> tuple[str, str, dict | None]:
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            data = json.loads(resp.read())
            candidates = data.get("candidates") if isinstance(data, dict) else None
            if not isinstance(candidates, list) or not candidates:
                return "error", "gemini_response_missing_candidates", None
            content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
            parts = content.get("parts") if isinstance(content, dict) else None
            if not isinstance(parts, list):
                return "error", "gemini_response_missing_parts", None
            text_parts = [str(part.get("text") or "") for part in parts if isinstance(part, dict) and part.get("text")]
            usage = data.get("usageMetadata") if isinstance(data, dict) else None
            return "ok", "".join(text_parts), usage if isinstance(usage, dict) else None
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")[:500]
        return "http_error", f"HTTP {exc.code}: {error_body}", None
    except Exception as exc:
        reason = "timeout" if _looks_like_timeout(exc) else "error"
        return reason, str(exc), None


def _llm_http_worker(
    output_queue,
    url: str,
    payload: bytes,
    headers: dict[str, str],
    timeout_seconds: int,
) -> None:
    output_queue.put(_llm_http_request_once(url, payload, headers, timeout_seconds))


def _run_llm_http_call(
    *,
    url: str,
    payload: bytes,
    headers: dict[str, str],
    timeout_seconds: int,
) -> tuple[str, str, dict | None]:
    if timeout_seconds <= 0:
        return _llm_http_request_once(url, payload, headers, None)
    return _llm_http_request_once(url, payload, headers, timeout_seconds)


def _run_gemini_http_call(
    *,
    url: str,
    payload: bytes,
    headers: dict[str, str],
    timeout_seconds: int,
) -> tuple[str, str, dict | None]:
    if timeout_seconds <= 0:
        return _gemini_http_request_once(url, payload, headers, None)
    return _gemini_http_request_once(url, payload, headers, timeout_seconds)


def _provider_error_payload(error: str) -> dict[str, object]:
    text = error or ""
    http_status = None
    body = text
    if text.startswith("HTTP "):
        prefix, _, rest = text.partition(":")
        parts = prefix.split()
        if len(parts) >= 2:
            try:
                http_status = int(parts[1])
            except ValueError:
                http_status = None
        body = rest.strip()

    provider_error_code = None
    provider_error_message = None
    try:
        parsed = json.loads(body) if body else {}
    except json.JSONDecodeError:
        parsed = {}
    if isinstance(parsed, dict):
        err = parsed.get("error")
        if isinstance(err, dict):
            provider_error_code = err.get("code") or err.get("status") or err.get("type")
            provider_error_message = err.get("message") or err.get("error")
        else:
            provider_error_code = parsed.get("code") or parsed.get("status") or parsed.get("type")
            provider_error_message = parsed.get("message") or parsed.get("error_description")

    return {
        "http_status": http_status,
        "provider_error_code": str(provider_error_code) if provider_error_code else None,
        "provider_error_message": str(provider_error_message)[:500] if provider_error_message else None,
    }


def _llm_error_type(reason: str, error: str) -> str:
    normalized = (error or "").lower()
    if reason == "llm_timeout" or "timeout" in normalized or "timed out" in normalized:
        return "timeout"
    if "llm_call_no_result" in normalized:
        return "transport_error"
    if _looks_like_transport_error(normalized):
        return "transport_error"
    if reason == "provider_http_error" or (error or "").startswith("HTTP "):
        return "http_error"
    return "provider_error"


def _transport_debug_enabled() -> bool:
    return os.environ.get("BRAND3_LLM_DEBUG_TRANSPORT", "").strip().lower() in {"1", "true", "yes", "on"}


def _chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


def _gemini_native_base_url(base_url: str) -> str:
    cleaned = (base_url or "").rstrip("/")
    if cleaned.endswith("/openai"):
        cleaned = cleaned[: -len("/openai")]
    return cleaned


def _gemini_generate_content_url(base_url: str, model: str) -> str:
    encoded_model = urllib.parse.quote(model, safe="")
    return f"{_gemini_native_base_url(base_url)}/models/{encoded_model}:generateContent"


def _redacted_headers(headers: dict[str, str]) -> dict[str, str]:
    out = {}
    for key, value in headers.items():
        if key.lower() == "authorization":
            out[key] = "Bearer [redacted]"
        else:
            out[key] = value
    return out


def _body_top_level_keys(payload: bytes) -> list[str]:
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except Exception:
        return []
    if isinstance(decoded, dict):
        return sorted(decoded.keys())
    return []


def _looks_like_transport_error(error: str) -> bool:
    normalized = (error or "").lower()
    transport_markers = (
        "urlopen error",
        "nodename nor servname provided",
        "name or service not known",
        "temporary failure in name resolution",
        "no address associated with hostname",
        "failed to establish a new connection",
        "connection refused",
        "connection reset by peer",
        "network is unreachable",
        "getaddrinfo failed",
        "dns",
    )
    return any(marker in normalized for marker in transport_markers)


def _json_type_matches(value: Any, schema_type: str) -> bool:
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "null":
        return value is None
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "object":
        return isinstance(value, dict)
    return True


def _validate_json_schema_value(value: Any, schema: dict[str, Any], path: str = "$") -> str | None:
    expected_type = schema.get("type")
    if expected_type and not _json_type_matches(value, expected_type):
        return f"{path}: expected {expected_type}"

    if expected_type == "object" and isinstance(value, dict):
        required = schema.get("required") or []
        missing = [name for name in required if name not in value]
        if missing:
            return f"{path}: missing required field(s): {', '.join(sorted(missing))}"

        properties = schema.get("properties") or {}
        if schema.get("additionalProperties") is False:
            extra = [key for key in value if key not in properties]
            if extra:
                return f"{path}: unexpected field(s): {', '.join(sorted(extra))}"

        for key, child_schema in properties.items():
            if key in value and isinstance(child_schema, dict):
                error = _validate_json_schema_value(value[key], child_schema, f"{path}.{key}")
                if error:
                    return error

    if expected_type == "array" and isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                error = _validate_json_schema_value(item, item_schema, f"{path}[{index}]")
                if error:
                    return error

    return None


def _validate_json_schema(value: Any, schema: dict[str, Any]) -> str | None:
    if not isinstance(schema, dict):
        return None
    return _validate_json_schema_value(value, schema)


def _json_response_format(
    *,
    json_schema: dict[str, Any] | None = None,
    schema_name: str | None = None,
    strict_schema: bool = True,
) -> dict[str, Any]:
    if not json_schema:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name or "brand3_json_response",
            "strict": bool(strict_schema),
            "schema": json_schema,
        },
    }


def _parse_json_content(content: str) -> Any:
    """Parse provider JSON, tolerating prose or fences around one JSON payload."""
    text = (content or "").strip()
    if not text:
        raise json.JSONDecodeError("empty json content", text, 0)

    try:
        return json.loads(text)
    except json.JSONDecodeError as original_error:
        decoder = json.JSONDecoder()
        starts = [index for index, char in enumerate(text) if char in "[{"]
        for index in starts:
            try:
                parsed, _end = decoder.raw_decode(text[index:])
                return parsed
            except json.JSONDecodeError:
                continue
        raise original_error


def _llm_cache_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

