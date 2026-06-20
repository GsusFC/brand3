"""GET /brand/{domain} — per-brand history + ASCII evolution chart."""

import asyncio
from typing import Literal

from fastapi import APIRouter, Query, Request

from src.config import BRAND3_DB_PATH

from ..observatory_index import build_observatory_brand_history
from ..templates_env import templates

router = APIRouter()


@router.get("/brand/{domain}")
async def brand_history(request: Request, domain: str, lang: Literal["es", "en"] = Query("es")):
    history = await asyncio.to_thread(
        build_observatory_brand_history,
        domain,
        db_path=BRAND3_DB_PATH,
        lang=lang,
    )
    return templates.TemplateResponse(
        request,
        "brand_history.html.j2",
        {
            "domain": domain,
            "history": history,
            "analyses": history["rows"],
            "ui_lang": lang,
        },
    )
