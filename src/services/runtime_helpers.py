"""Runtime quality and screenshot helpers for Brand3 runs."""

from __future__ import annotations

import multiprocessing as mp
import os
import queue
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from src.config import BRAND3_SCREENSHOT_DIR, SCREENSHOT_PROVIDER

if TYPE_CHECKING:
    from src.collectors.context_collector import ContextData
    from src.collectors.exa_collector import ExaData
    from src.collectors.social_collector import SocialData
    from src.collectors.web_collector import WebData


_MIN_EXA_FOR_GOOD_QUALITY = 5
_MIN_EXA_FOR_DEGRADED_QUALITY = 3
_LLM_ALLOWED_CONTENT_SOURCES = {"firecrawl", "browser_fallback", "owned_fallback"}
_SOCIAL_COLLECTION_TIMEOUT_SECONDS = 30
_VISUAL_SCREENSHOT_TIMEOUT_SECONDS = 45


def _compute_data_quality(exa_data: "ExaData | None", content_source: str) -> str:
    mentions_count = len(exa_data.mentions) if exa_data else 0
    if content_source in ("firecrawl", "browser_fallback", "owned_fallback") and mentions_count >= _MIN_EXA_FOR_GOOD_QUALITY:
        return "good"
    if content_source == "exa_fallback" and mentions_count >= _MIN_EXA_FOR_DEGRADED_QUALITY:
        return "degraded"
    return "insufficient"


def _has_effective_owned_content_for_llm(
    content_web: "WebData | None",
    content_source: str,
) -> bool:
    return content_source in _LLM_ALLOWED_CONTENT_SOURCES and bool(content_web and len((content_web.markdown_content or "").strip()) >= 200)


def _should_skip_llm_for_low_context(
    context_data: "ContextData | None",
    content_web: "WebData | None",
    content_source: str,
) -> bool:
    if _has_effective_owned_content_for_llm(content_web, content_source):
        return False
    return bool(context_data and context_data.coverage < 0.3)


def _normalized_screenshot_provider(provider: str | None = None) -> str:
    value = (provider or SCREENSHOT_PROVIDER or "firecrawl").strip().lower()
    return value if value in {"firecrawl", "playwright"} else "firecrawl"


def _take_firecrawl_screenshot(url: str) -> dict[str, object]:
    from src.features.visual_analyzer import VisualAnalyzer

    data = VisualAnalyzer().take_screenshot(url)
    data.setdefault("screenshot_provider", "firecrawl_screenshot")
    return data


def _screenshot_has_capture(data: dict[str, object] | None) -> bool:
    return bool(isinstance(data, dict) and str(data.get("screenshot_url") or "").strip())


def _take_playwright_screenshot(url: str, *, timeout_ms: int = 30000) -> dict[str, object]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {
            "error": f"Playwright not available: {exc}",
            "error_type": "missing_dependency",
            "screenshot_provider": "playwright",
        }

    screenshot_dir = Path(BRAND3_SCREENSHOT_DIR)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    fd, screenshot_path = tempfile.mkstemp(prefix="brand3-screenshot-", suffix=".png", dir=str(screenshot_dir))
    os.close(fd)
    browser = None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1200},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            page.screenshot(path=screenshot_path, full_page=False, timeout=60000, animations="disabled")
            title = page.title()
            browser.close()
            browser = None
        return {
            "screenshot_url": Path(screenshot_path).as_uri(),
            "screenshot_path": screenshot_path,
            "metadata": {"title": title},
            "screenshot_provider": "playwright",
        }
    except PlaywrightTimeoutError as exc:
        return {"error": str(exc), "error_type": "timeout", "screenshot_provider": "playwright"}
    except Exception as exc:
        return {"error": str(exc), "error_type": "browser_error", "screenshot_provider": "playwright"}
    finally:
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass
        try:
            leftover = Path(screenshot_path)
            if leftover.exists() and leftover.stat().st_size == 0:
                leftover.unlink()
        except OSError:
            pass


def _take_playwright_screenshot_with_firecrawl_fallback(url: str) -> dict[str, object]:
    primary = _take_playwright_screenshot(url)
    if _screenshot_has_capture(primary):
        return primary

    fallback_reason = str(primary.get("error_type") or primary.get("error") or "missing_screenshot_url")
    try:
        fallback = _take_firecrawl_screenshot(url)
    except Exception as exc:
        primary["fallback_attempted"] = True
        primary["fallback_provider"] = "firecrawl_screenshot"
        primary["fallback_error"] = str(exc)
        return primary

    fallback["fallback_from_provider"] = "playwright"
    fallback["fallback_reason"] = fallback_reason
    if not _screenshot_has_capture(fallback) and primary.get("error"):
        fallback.setdefault("primary_error", primary.get("error"))
        fallback.setdefault("primary_error_type", primary.get("error_type"))
    return fallback


def _screenshot_capture_worker(output_queue, url: str, provider: str) -> None:
    try:
        if provider == "playwright":
            output_queue.put(("ok", _take_playwright_screenshot_with_firecrawl_fallback(url)))
            return
        output_queue.put(("ok", _take_firecrawl_screenshot(url)))
    except Exception as exc:
        output_queue.put(("error", str(exc)))


def _take_screenshot_with_budget(
    url: str,
    *,
    timeout_seconds: int = _VISUAL_SCREENSHOT_TIMEOUT_SECONDS,
    provider: str | None = None,
) -> tuple[dict[str, object], str | None]:
    provider_name = _normalized_screenshot_provider(provider)
    if timeout_seconds <= 0:
        if provider_name == "playwright":
            return _take_playwright_screenshot_with_firecrawl_fallback(url), None
        try:
            return _take_firecrawl_screenshot(url), None
        except Exception as exc:
            return {"error": str(exc), "screenshot_provider": "firecrawl_screenshot"}, "error"

    if provider_name == "playwright":
        return _take_playwright_screenshot_with_firecrawl_fallback(url), None

    import sys

    method = "spawn" if sys.platform == "darwin" else ("fork" if "fork" in mp.get_all_start_methods() else "spawn")
    ctx = mp.get_context(method)
    output_queue = ctx.Queue(maxsize=1)
    process = ctx.Process(target=_screenshot_capture_worker, args=(output_queue, url, provider_name))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join(2)
        return {
            "error": f"visual_screenshot_timeout_after_{timeout_seconds}s",
            "error_type": "timeout",
            "screenshot_provider": provider_name if provider_name == "playwright" else "firecrawl_screenshot",
        }, "timeout"

    try:
        status, payload = output_queue.get_nowait()
    except queue.Empty:
        return {
            "error": "visual_screenshot_no_result",
            "error_type": "unknown",
            "screenshot_provider": provider_name if provider_name == "playwright" else "firecrawl_screenshot",
        }, "error"

    if status == "ok" and isinstance(payload, dict):
        return payload, None
    return {
        "error": str(payload or "visual_screenshot_error"),
        "error_type": "browser_error" if provider_name == "playwright" else "capture_error",
        "screenshot_provider": provider_name if provider_name == "playwright" else "firecrawl_screenshot",
    }, "error"


def _classify_screenshot_error(error_message: str) -> str:
    normalized = (error_message or "").lower()
    if "timeout" in normalized or "timed out" in normalized:
        return "timeout"
    if "payment required" in normalized or "insufficient credit" in normalized:
        return "payment_required"
    if "api_key" in normalized or "api key" in normalized or "not set" in normalized:
        return "missing_api_key"
    if "no screenshot url" in normalized:
        return "missing_screenshot_url"
    return "browser_error"


def _screenshot_capture_diagnostic(
    *,
    attempted: bool,
    screenshot_data: dict[str, object] | None = None,
    limitation: str | None = None,
    skipped_reason: str | None = None,
) -> dict[str, object]:
    if not attempted:
        return {
            "attempted": False,
            "success": False,
            "status": "skipped",
            "reason": skipped_reason or "not_attempted",
        }

    data = screenshot_data or {}
    screenshot_url = str(data.get("screenshot_url") or "")
    source = str(data.get("screenshot_provider") or "firecrawl_screenshot")
    if screenshot_url:
        return {
            "attempted": True,
            "success": True,
            "status": "captured",
            "source": source,
            "error_type": None,
            "error_message": None,
            "screenshot_url": screenshot_url,
        }

    error_message = str(data.get("error") or limitation or "screenshot_capture_failed")
    error_type = str(data.get("error_type") or limitation or _classify_screenshot_error(error_message))
    return {
        "attempted": True,
        "success": False,
        "status": "error" if error_type != "timeout" else "timeout",
        "source": source,
        "error_type": error_type,
        "error_message": error_message[:300],
    }
