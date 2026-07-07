"""GET / — scanner-first landing."""

from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from src.config import BRAND3_DB_PATH

from ..i18n import magnetism_landing_copy, normalize_lang
from ..observatory_index import build_observatory_index
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
    observatory = build_observatory_index(
        db_path=BRAND3_DB_PATH,
        sort="newest",
        page=1,
        per_page=25,
        lang=ui_lang,
    )
    return templates.TemplateResponse(
        request,
        "index.html.j2",
        {
            "latest_analyses": observatory["rows"],
            "ui_lang": ui_lang,
            "landing": magnetism_landing_copy(ui_lang),
            "observatory": {
                "sort": sort,
                "category": category,
                "tag": "",
                "query": q or "",
                "categories": observatory["categories"],
                "tags": observatory["tags"],
                "page": observatory["page"],
                "total": observatory["total"],
                "total_pages": observatory["total_pages"],
                "has_prev": observatory["has_prev"],
                "has_next": observatory["has_next"],
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
