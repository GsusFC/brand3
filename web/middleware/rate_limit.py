"""Per-IP rate limit for POST /analyze.

Counts are persisted in `web_requests` — surviving restarts. The middleware
runs only on the analyze endpoint; everything else is untouched.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import HTMLResponse, Response

from ..config import settings
from ..storage import count_recent_analyses_for_ip
from ..templates_env import templates
from .team_cookie import create_serializer, is_team_request

log = logging.getLogger("brand3.web.ratelimit")

PROTECTED_PATH = "/analyze"


def get_client_ip(request: Request) -> str:
    """Resolve the requester IP, honouring X-Forwarded-For in production."""
    if settings.environment == "production":
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


def _rate_limit_bypass_ips() -> set[str]:
    return {
        item.strip()
        for item in settings.rate_limit_bypass_ips.split(",")
        if item.strip()
    }


async def rate_limit_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if not (request.method == "POST" and request.url.path == PROTECTED_PATH):
        return await call_next(request)

    if not settings.rate_limit_enabled:
        return await call_next(request)

    serializer = create_serializer(settings.cookie_secret)
    if is_team_request(request, serializer):
        return await call_next(request)

    ip = get_client_ip(request)
    if ip in _rate_limit_bypass_ips():
        return await call_next(request)

    count = count_recent_analyses_for_ip(ip, hours=settings.rate_limit_window_hours)
    if count >= settings.rate_limit_per_ip:
        log.info("rate_limit_hit ip=%s count=%d", ip, count)
        return templates.TemplateResponse(
            request,
            "error.html.j2",
            {
                "status_code": 429,
                "error": (
                    f"Rate limit reached — {settings.rate_limit_per_ip} analyses "
                    f"per IP every {settings.rate_limit_window_hours}h. "
                    "FLOC team members: unlock via /team/unlock?token=..."
                ),
            },
            status_code=429,
        )

    return await call_next(request)
