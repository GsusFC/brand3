"""Runtime utilities for client TLDR v2 support.

This module isolates analyzer/config bootstrap and env loading so the main
support module can stay focused on prompt and normalization semantics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from src.config import CLIENT_TLDR_V2_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.features.magnetism.client_tldr_v2_support_contract import (
    _safe_raw_response_preview,
)
from src.features.magnetism.client_tldr_v2_support_runtime_response import (
    call_client_tldr_v2_llm,
)

import os

_CLIENT_TLDR_RUNTIME_ENV_BOOTSTRAPPED = False


def _log_client_tldr_v2_runtime_context(llm: Any | None) -> None:
    model = getattr(llm, "model", None)
    base_url = getattr(llm, "base_url", None)
    final_url = None
    if isinstance(base_url, str) and base_url.strip():
        final_url = f"{base_url.rstrip('/')}/chat/completions"
    print(
        "[client_tldr_v2_runtime] "
        f"BRAND3_LLM_API_KEY_present={bool(os.getenv('BRAND3_LLM_API_KEY'))} "
        f"GEMINI_API_KEY_present={bool(os.getenv('GEMINI_API_KEY'))} "
        f"GOOGLE_API_KEY_present={bool(os.getenv('GOOGLE_API_KEY'))} "
        f"model={model!r} base_url={base_url!r} final_url={final_url!r} "
        f"analyzer={llm.__class__.__name__ if llm is not None else None}"
    )


def _default_analyzer() -> Any | None:
    _ensure_client_tldr_runtime_env_loaded()
    try:
        analyzer = LLMAnalyzer(model=_client_tldr_v2_model())
        return analyzer if getattr(analyzer, "api_key", None) else None
    except Exception:
        return None


def _client_tldr_v2_model() -> str:
    return os.environ.get("BRAND3_CLIENT_TLDR_V2_MODEL", CLIENT_TLDR_V2_MODEL)


def _ensure_client_tldr_runtime_env_loaded() -> None:
    global _CLIENT_TLDR_RUNTIME_ENV_BOOTSTRAPPED
    if _CLIENT_TLDR_RUNTIME_ENV_BOOTSTRAPPED:
        return

    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        _CLIENT_TLDR_RUNTIME_ENV_BOOTSTRAPPED = True
        return

    try:
        from dotenv import load_dotenv
    except Exception:
        load_dotenv = None

    try:
        if load_dotenv is not None:
            load_dotenv(dotenv_path=env_path, override=False)
            _CLIENT_TLDR_RUNTIME_ENV_BOOTSTRAPPED = True
            return
    except Exception:
        # Keep fallback behavior if dotenv is not usable in this environment.
        pass

    try:
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            if key.startswith("export "):
                key = key[len("export "):].strip()
            if not key:
                continue
            value = _normalize_dotenv_value(value)
            os.environ.setdefault(key.strip(), value.strip())
    except Exception:
        # Never fail the render path due to env-file parsing.
        pass
    _CLIENT_TLDR_RUNTIME_ENV_BOOTSTRAPPED = True


def _normalize_dotenv_value(raw_value: str) -> str:
    value = raw_value.strip()
    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2 and value[0] == value[-1]:
        value = value[1:-1]
    elif " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    elif "#" in value:
        value = value.split("#", 1)[0].rstrip()
    return value


def _normalize_choice(value: Any, allowed: set[str], *, fallback: str) -> str:
    text = "" if value is None else str(value).strip()
    return text if text in allowed else fallback


def run_client_tldr_v2_pass(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
    build_prompt_fn: Callable[..., str],
    compact_hints_fn: Callable[[dict[str, Any]], dict[str, Any]],
    normalize_response_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Call the LLM once and normalize the client TLDR v2 response."""
    if llm is None or not getattr(llm, "api_key", None):
        return {
            "analysis_error": {
                "reason": "llm_unavailable",
                "detail": "No LLM API key is available for the client TLDR v2 preview.",
            }
        }

    raw_response_preview: str | None
    metadata: dict[str, Any]
    raw, raw_response_preview, metadata = call_client_tldr_v2_llm(
        llm=llm,
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        lang=lang,
        build_prompt_fn=build_prompt_fn,
        compact_hints_fn=compact_hints_fn,
    )
    if raw is None:
        return {
            "analysis_error": metadata["analysis_error"],
            "raw": metadata.get("raw", {}),
            "raw_response_preview": metadata.get("raw_response_preview"),
        }

    perceptual_hints = compact_hints_fn(report_base)

    if normalize_response_fn is None:
        try:
            from src.features.magnetism import client_tldr_v2_support as _support
        except Exception:  # pragma: no cover - runtime fallback
            _support = None
        normalize_response_fn = getattr(_support, "normalize_client_tldr_v2_response", None)

    if not callable(normalize_response_fn):
        return {
            "analysis_error": {
                "reason": "normalizer_unavailable",
                "detail": "Client TLDR response normalization function is unavailable.",
            },
            "raw": raw,
            "raw_response_preview": raw_response_preview,
        }

    validated = normalize_response_fn(
        raw,
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        lang=lang,
        perceptual_guidance=perceptual_hints,
    )
    return {
        "validated": validated,
            "raw": raw,
            "raw_response_preview": raw_response_preview or _safe_raw_response_preview(llm),
        }
