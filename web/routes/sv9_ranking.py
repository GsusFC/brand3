"""SV9 ranking routes.

The ranking view is meant to be public by design (briefing section 9: every
entry is outreach material, plain-text domains only). Category administration
goes through the team gate (currently disabled by product decision).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from src.config import BRAND3_DB_PATH
from src.sv9.categories import CATEGORIES
from src.sv9.ranking import build_ranking
from src.sv9.store import Sv9Store

from ..templates_env import templates
from .sv9_calibration import _require_team_write

router = APIRouter()


@router.get("/sv9/ranking")
async def sv9_ranking(request: Request, categoria: str | None = Query(None)):
    if categoria and categoria not in CATEGORIES:
        raise HTTPException(status_code=404, detail="unknown category")
    model = await asyncio.to_thread(_build_ranking_model, categoria)
    return templates.TemplateResponse(
        request,
        "sv9_ranking.html.j2",
        {"ranking": model, "categories": CATEGORIES, "ui_lang": "es"},
    )


def _build_ranking_model(categoria: str | None):
    store = Sv9Store(BRAND3_DB_PATH)
    try:
        return build_ranking(store, category=categoria)
    finally:
        store.close()


@router.post("/sv9/ranking/brand/{domain}")
async def sv9_ranking_set_category(
    request: Request,
    domain: str,
    primary_category: str = Form(""),
    evaluador: str = Form(""),
    exclude_from_ranking: bool = Form(False),
):
    _require_team_write(request)
    primary = primary_category.strip() or None
    if primary and primary not in CATEGORIES:
        raise HTTPException(status_code=422, detail="unknown category")
    await asyncio.to_thread(
        _save_brand_category,
        domain.strip().lower(),
        primary,
        evaluador.strip() or None,
        exclude_from_ranking,
    )
    return RedirectResponse("/sv9/ranking", status_code=303)


def _save_brand_category(
    domain: str,
    primary_category: str | None,
    evaluador: str | None,
    exclude_from_ranking: bool,
) -> None:
    store = Sv9Store(BRAND3_DB_PATH)
    try:
        store.upsert_brand_category(
            domain,
            primary_category=primary_category,
            source="confirmada",
            evaluador=evaluador,
            exclude_from_ranking=exclude_from_ranking,
        )
    finally:
        store.close()
