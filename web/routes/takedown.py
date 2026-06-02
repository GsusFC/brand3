"""GET /takedown — static page with mailto for manual takedown."""

from typing import Literal

from fastapi import APIRouter, Query, Request

from ..templates_env import templates

router = APIRouter()


@router.get("/takedown")
async def takedown(
    request: Request,
    domain: str | None = None,
    lang: Literal["es", "en"] = Query("es"),
):
    return templates.TemplateResponse(
        request,
        "takedown.html.j2",
        {"domain": domain or "", "ui_lang": lang},
    )
