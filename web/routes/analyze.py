"""POST /analyze — validates URL, queues the request, redirects to status."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ..config import settings
from ..i18n import lang_suffix, normalize_lang
from ..middleware.rate_limit import get_client_ip
from ..middleware.team_cookie import create_serializer, is_team_request
from ..storage import insert_request
from ..templates_env import templates
from ..workers.queue import get_queue
from ..workers.slug import slug_from_url
from ..workers.url_validator import validate_url

router = APIRouter()


@router.post("/analyze")
async def analyze(request: Request, url: str = Form(...), lang: str = Form("es")):
    lang = normalize_lang(lang)
    valid, result = validate_url(url)
    if not valid:
        return templates.TemplateResponse(
            request,
            "error.html.j2",
            {"status_code": 400, "error": f"URL rejected: {result}", "ui_lang": lang},
            status_code=400,
        )

    normalized = result
    token = secrets.token_urlsafe(12)
    slug = slug_from_url(normalized)
    ip = get_client_ip(request)
    is_team = is_team_request(request, create_serializer(settings.cookie_secret))

    insert_request(
        token=token,
        url=normalized,
        brand_slug=slug,
        requester_ip=ip,
        requester_is_team=is_team,
    )
    await get_queue().enqueue(token)
    return RedirectResponse(f"/r/{token}/status{lang_suffix(lang)}", status_code=303)
