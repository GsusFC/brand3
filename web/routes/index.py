"""GET / — scanner-first landing."""

from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from ..i18n import magnetism_landing_copy, normalize_lang
from ..templates_env import templates

router = APIRouter()


@router.get("/")
async def index(
    request: Request,
    lang: Literal["es", "en"] = Query("es"),
    sort: str = Query("newest"),
    category: str | None = Query(None),
    tag: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    ui_lang = normalize_lang(lang)
    sort = {"recent": "newest", "score": "score_desc"}.get(sort, sort)
    if q or category or tag or sort != "newest" or page != 1:
        params = {"lang": ui_lang, "sort": sort, "page": page}
        if q:
            params["q"] = q
        if category:
            params["category"] = category
        if tag:
            params["tag"] = tag
        return RedirectResponse(f"/reports?{urlencode(params)}", status_code=303)
    return templates.TemplateResponse(
        request,
        "index.html.j2",
        {
            "latest_analyses": [],
            "ui_lang": ui_lang,
            "landing": magnetism_landing_copy(ui_lang),
            "observatory": {
                "sort": sort,
                "category": category,
                "tag": "",
                "query": q or "",
                "categories": {},
                "tags": {},
                "page": 1,
                "total": 0,
                "total_pages": 1,
                "has_prev": False,
                "has_next": False,
            },
        },
    )


@router.get("/scanner-api")
async def scanner_api_page(request: Request, lang: Literal["es", "en"] = Query("es")):
    ui_lang = normalize_lang(lang)
    return templates.TemplateResponse(
        request,
        "scanner_api.html.j2",
        {
            "ui_lang": ui_lang,
        },
    )


@router.get("/t-rex")
async def t_rex_playground(request: Request, lang: Literal["es", "en"] = Query("es")):
    ui_lang = normalize_lang(lang)
    suffix = "?lang=en" if ui_lang == "en" else ""
    return templates.TemplateResponse(
        request,
        "t_rex.html.j2",
        {
            "ui_lang": ui_lang,
            "lang_suffix": suffix,
        },
    )
