"""Lab-only Hyperbrowser Fetch collector.

This collector intentionally stays outside the canonical Brand3 scoring flow.
It normalizes Hyperbrowser Fetch responses into a small comparable shape so we
can benchmark acquisition quality before deciding whether to promote it.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.config import HYPERBROWSER_API_KEY, HYPERBROWSER_API_URL


DEFAULT_TIMEOUT_SECONDS = 90


@dataclass
class HyperbrowserFetchData:
    url: str
    status: str = ""
    job_id: str = ""
    title: str = ""
    source_url: str = ""
    markdown: str = ""
    html: str = ""
    links: list[str] = field(default_factory=list)
    screenshot: str = ""
    branding: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: int = 0
    error: str = ""
    json_payload: dict[str, Any] | list[Any] | None = None

    @property
    def text_chars(self) -> int:
        return len(self.markdown or "")

    @property
    def html_chars(self) -> int:
        return len(self.html or "")

    @property
    def final_url(self) -> str:
        return self.source_url or self.url


class HyperbrowserCollector:
    """Fetches page data via Hyperbrowser Web API."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key if api_key is not None else HYPERBROWSER_API_KEY
        self.endpoint = endpoint or HYPERBROWSER_API_URL
        self.timeout_seconds = timeout_seconds
        self._base_url = self.endpoint.rsplit("/fetch", 1)[0]

    def fetch(
        self,
        url: str,
        *,
        include_html: bool = True,
        include_links: bool = True,
        include_branding: bool = True,
        include_screenshot: bool = False,
        stealth: str = "auto",
        wait_for_ms: int = 2000,
        cache_max_age_seconds: int | None = 86400,
        exclude_selectors: list[str] | None = None,
        include_selectors: list[str] | None = None,
        json_schema: dict[str, Any] | None = None,
        json_prompt: str | None = None,
        payload_overrides: dict[str, Any] | None = None,
    ) -> HyperbrowserFetchData:
        start = time.perf_counter()
        if not self.api_key:
            return HyperbrowserFetchData(
                url=url,
                elapsed_ms=_elapsed_ms(start),
                error="HYPERBROWSER_API_KEY not set",
            )

        formats: list[str | dict[str, Any]] = ["markdown"]
        if include_html:
            formats.append("html")
        if include_links:
            formats.append("links")
        if include_branding:
            formats.append("branding")
        if include_screenshot:
            formats.append({"type": "screenshot", "fullPage": False, "format": "png"})
        if json_schema:
            formats.append(
                {
                    "type": "json",
                    "schema": json_schema,
                    "prompt": json_prompt,
                }
            )

        outputs: dict[str, Any] = {"formats": formats}
        if exclude_selectors or include_selectors:
            sanitize: str = "advanced"
            if exclude_selectors:
                outputs["excludeSelectors"] = [item for item in exclude_selectors if item.strip()]
            if include_selectors:
                outputs["includeSelectors"] = [item for item in include_selectors if item.strip()]
            outputs["sanitize"] = sanitize

        payload: dict[str, Any] = {
            "url": url,
            "stealth": stealth,
            "outputs": outputs,
            "browser": {"screen": {"width": 1440, "height": 1200}},
            "navigation": {
                "waitUntil": "domcontentloaded",
                "waitFor": wait_for_ms,
                "timeoutMs": min(self.timeout_seconds * 1000, 60000),
            },
        }
        if payload_overrides:
            payload.update(payload_overrides)
        if cache_max_age_seconds is not None:
            payload["cache"] = {"maxAgeSeconds": cache_max_age_seconds}

        return self._fetch_payload(url, payload)

    def crawl(
        self,
        url: str,
        *,
        max_pages: int = 20,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        include_html: bool = True,
        include_links: bool = True,
        payload_overrides: dict[str, Any] | None = None,
    ) -> HyperbrowserFetchData:
        include = include or []
        exclude = exclude or []
        payload = {
            "url": url,
            "maxPages": max_pages,
            "stealth": "auto",
            "outputs": {
                "formats": [
                    "markdown",
                    *("html" for _ in [None] if include_html),
                    *("links" for _ in [None] if include_links),
                ]
            },
            "include": include,
            "exclude": exclude,
        }
        if payload_overrides:
            payload.update(payload_overrides)
        return self._crawl_payload(url, payload)

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        payload_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {"query": query, "limit": limit}
        if payload_overrides:
            payload.update(payload_overrides)
        return self._post(payload, endpoint=f"{self._base_url}/search")

    def extract(
        self,
        urls: list[str] | str,
        *,
        prompt: str | None = None,
        schema: dict[str, Any] | None = None,
        wait_for_completion: bool = True,
        max_wait_seconds: int = 90,
        poll_interval_seconds: float = 1.0,
        payload_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        urls_list = [url for url in ([urls] if isinstance(urls, str) else urls)]
        payload: dict[str, Any] = {"urls": urls_list}
        if prompt:
            payload["prompt"] = prompt
        if schema:
            payload["schema"] = schema
        if payload_overrides:
            payload.update(payload_overrides)

        started = self._post_with_extract_fallback(payload)
        if not isinstance(started, dict):
            return {"status": "error", "error": "Invalid extract response from Hyperbrowser"}

        if not wait_for_completion:
            return started

        status = str(started.get("status") or "").lower()
        job_id = str(started.get("jobId") or "")
        if status in {"completed", "failed", "stopped"}:
            return started
        if not job_id:
            return {
                "status": status or "error",
                "error": str(started.get("error") or "missing jobId for extract"),
            }

        start_endpoint = str(started.get("_hyperbrowser_extract_endpoint") or f"{self._base_url}/extract")

        return self._wait_for_job(
            job_id=job_id,
            endpoint=start_endpoint.rstrip("/") + f"/{job_id}",
            max_wait_seconds=max_wait_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    def _extract_endpoints(self) -> list[str]:
        base_candidates = [self._base_url]
        if "/web" in self._base_url:
            base_candidates.append(self._base_url.rsplit("/web", 1)[0])

        return [f"{base}/extract" for base in base_candidates]

    def _post_with_extract_fallback(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_response: dict[str, Any] = {
            "status": "error",
            "error": "Hyperbrowser extract returned no responses",
        }

        endpoints = self._extract_endpoints()
        for endpoint in endpoints:
            last_response = self._post(payload, endpoint=endpoint)
            if isinstance(last_response, dict):
                last_response["_hyperbrowser_extract_endpoint"] = endpoint
            if self._is_supported_extract_response(last_response):
                return last_response

            if not self._is_not_found_error(last_response):
                return last_response

        if isinstance(last_response, dict):
            error = str(last_response.get("error") or "")
            if "Cannot POST" in error:
                endpoints = ", ".join(endpoints)
                return {
                    **last_response,
                    "error": f"Hyperbrowser extract endpoint not available on {endpoints}. Last error: {error}",
                    "attempted_endpoints": endpoints,
                    "status": "error",
                }

        return last_response

    @staticmethod
    def _is_supported_extract_response(payload: dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False

        status = str(payload.get("status") or "").lower()
        if status == "error":
            return False
        if status in {"", "pending", "running", "queued", "completed", "failed", "stopped"}:
            return True
        return False

    @staticmethod
    def _is_not_found_error(payload: dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False
        error = str(payload.get("error") or "").lower()
        return "cannot post" in error or "not found" in error or "404" in error

    def _fetch_payload(self, url: str, payload: dict[str, Any]) -> HyperbrowserFetchData:
        parsed = self._post(payload, endpoint=self.endpoint)
        if parsed is None:
            return HyperbrowserFetchData(
                url=url,
                elapsed_ms=0,
                error="Unexpected empty response from Hyperbrowser",
            )
        return self._normalize_response(url, parsed, elapsed_ms=0)

    def _crawl_payload(self, url: str, payload: dict[str, Any]) -> HyperbrowserFetchData:
        parsed = self._post(payload, endpoint=f"{self._base_url}/crawl")
        if parsed is None:
            return HyperbrowserFetchData(
                url=url,
                elapsed_ms=0,
                error="Unexpected empty response from Hyperbrowser",
            )
        return self._normalize_response(url, parsed, elapsed_ms=0)

    def _post(self, payload: dict[str, Any], *, endpoint: str) -> dict[str, Any] | None:
        start = time.perf_counter()
        if not self.api_key:
            return {
                "url": payload.get("url"),
                "error": "HYPERBROWSER_API_KEY not set",
                "elapsedMs": 0,
            }

        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            return {
                "status": "error",
                "error": _http_error_message(exc),
                "elapsedMs": _elapsed_ms(start),
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc), "elapsedMs": _elapsed_ms(start)}

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "error": f"Invalid JSON response: {raw[:300]}",
                "elapsedMs": _elapsed_ms(start),
            }

        if isinstance(parsed, dict):
            parsed.setdefault("elapsedMs", _elapsed_ms(start))
        return parsed

    def _get(self, *, endpoint: str) -> dict[str, Any] | None:
        start = time.perf_counter()
        if not self.api_key:
            return {
                "error": "HYPERBROWSER_API_KEY not set",
                "elapsedMs": 0,
            }

        request = Request(
            endpoint,
            headers={
                "Accept": "application/json",
                "x-api-key": self.api_key,
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            return {
                "status": "error",
                "error": _http_error_message(exc),
                "elapsedMs": _elapsed_ms(start),
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc), "elapsedMs": _elapsed_ms(start)}

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "error": f"Invalid JSON response: {raw[:300]}",
                "elapsedMs": _elapsed_ms(start),
            }

        if isinstance(parsed, dict):
            parsed.setdefault("elapsedMs", _elapsed_ms(start))
        return parsed

    def _wait_for_job(
        self,
        *,
        job_id: str,
        endpoint: str,
        max_wait_seconds: int,
        poll_interval_seconds: float,
    ) -> dict[str, Any]:
        deadline = time.perf_counter() + max_wait_seconds
        while time.perf_counter() < deadline:
            payload = self._get(endpoint=endpoint)
            if not isinstance(payload, dict):
                return {"status": "error", "error": "Invalid job status response from Hyperbrowser"}
            if "status" not in payload:
                payload["status"] = "unknown"
            status = str(payload.get("status") or "").lower()
            if status in {"completed", "failed", "stopped"}:
                return payload
            if status in {"", "unknown", "pending", "running"}:
                if poll_interval_seconds > 0:
                    time.sleep(poll_interval_seconds)
                continue
            return payload

        return {
            "status": "error",
            "error": f"Timed out waiting for job {job_id} after {max_wait_seconds}s",
            "jobId": job_id,
        }

    def _normalize_response(
        self,
        requested_url: str,
        payload: dict[str, Any],
        *,
        elapsed_ms: int,
    ) -> HyperbrowserFetchData:
        if elapsed_ms <= 0:
            elapsed_ms = int(payload.get("elapsedMs") or 0)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        outputs = payload.get("outputs") if isinstance(payload.get("outputs"), dict) else {}
        if not data and isinstance(outputs, dict):
            data = outputs
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        error = payload.get("error") or ""
        status = str(payload.get("status") or "")
        if status and status != "completed" and not error:
            error = f"Hyperbrowser fetch status: {status}"

        json_payload = None
        raw_json = payload.get("json")
        if raw_json is None and isinstance(payload.get("data"), dict):
            json_candidates = [
                key
                for key in ("json", "jsonData", "jsonResult")
                if isinstance(payload.get("data", {}).get(key), (dict, list))
            ]
            if json_candidates:
                raw_json = payload["data"][json_candidates[0]]
            else:
                raw_json = data.get("json") if isinstance(data.get("json"), (dict, list)) else None

        if isinstance(raw_json, dict):
            raw_json = {k: v for k, v in raw_json.items() if k != "status"}

        return HyperbrowserFetchData(
            url=requested_url,
            status=status,
            job_id=str(payload.get("jobId") or ""),
            title=str(metadata.get("title") or ""),
            source_url=str(metadata.get("sourceURL") or metadata.get("url") or ""),
            markdown=str(data.get("markdown") or ""),
            html=str(data.get("html") or ""),
            links=_string_list(data.get("links")),
            screenshot=str(data.get("screenshot") or ""),
            branding=data.get("branding") if isinstance(data.get("branding"), dict) else {},
            json_payload=raw_json,
            metadata=metadata,
            raw_response=payload,
            elapsed_ms=elapsed_ms,
            error=str(error or ""),
        )


def branding_summary(branding: dict[str, Any]) -> dict[str, Any]:
    colors = branding.get("colors") if isinstance(branding.get("colors"), dict) else {}
    fonts = branding.get("fonts") if isinstance(branding.get("fonts"), list) else []
    images = branding.get("images") if isinstance(branding.get("images"), dict) else {}
    confidence = branding.get("confidence") if isinstance(branding.get("confidence"), dict) else {}
    logo = images.get("logo") or images.get("favicon") or ""
    return {
        "color_scheme": branding.get("colorScheme") or "",
        "color_count": len([value for value in colors.values() if value]),
        "font_count": len(fonts),
        "logo_detected": bool(logo),
        "overall_confidence": confidence.get("overall"),
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _http_error_message(exc: HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")
    except Exception:
        body = ""
    return f"{exc.reason}: {body[:500]}" if body else str(exc)
