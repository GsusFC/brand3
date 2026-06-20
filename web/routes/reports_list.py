"""GET /reports — paginated public observatory list."""

import asyncio
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from src.config import BRAND3_DB_PATH

from ..observatory_index import build_observatory_index
from ..templates_env import templates

router = APIRouter()

_PER_PAGE = 20
_ALLOWED_SORTS = ("newest", "score_desc", "score_asc", "scans_desc")


@router.get("/reports")
async def reports_list(
    request: Request,
    q: str | None = Query(None),
    sort: str = Query("newest"),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    lang: Literal["es", "en"] = Query("es"),
):
    if sort not in _ALLOWED_SORTS:
        sort = "newest"
    observatory = await asyncio.to_thread(
        build_observatory_index,
        db_path=BRAND3_DB_PATH,
        query=q,
        sort=sort,
        category=category,
        page=page,
        per_page=_PER_PAGE,
        lang=lang,
    )
    return templates.TemplateResponse(
        request,
        "reports_list.html.j2",
        {
            "rows": observatory["rows"],
            "query": q or "",
            "sort": sort,
            "category": category,
            "categories": observatory["categories"],
            "page": observatory["page"],
            "total_pages": observatory["total_pages"],
            "total": observatory["total"],
            "has_prev": observatory["has_prev"],
            "has_next": observatory["has_next"],
            "ui_lang": lang,
        },
    )


@router.get("/latest_brand_audits")
async def latest_brand_audits_alias(lang: Literal["es", "en"] = Query("es")):
    target = "/reports"
    if lang == "en":
        target += "?lang=en"
    return RedirectResponse(target, status_code=303)
