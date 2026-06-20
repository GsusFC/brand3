"""GET /brand/{domain} — per-brand history + ASCII evolution chart."""

import asyncio
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from src.config import BRAND3_DB_PATH

from ..config import settings
from ..middleware.team_cookie import create_serializer, is_team_request
from ..observatory_index import build_observatory_brand_history, save_brand_profile_overrides
from ..templates_env import templates

router = APIRouter()


def _require_team_write(request: Request) -> None:
    if not settings.team_token:
        return
    if not is_team_request(request, create_serializer(settings.cookie_secret)):
        raise HTTPException(status_code=403, detail="team access required")


@router.get("/brand/{domain}")
async def brand_history(request: Request, domain: str, lang: Literal["es", "en"] = Query("es")):
    history = await asyncio.to_thread(
        build_observatory_brand_history,
        domain,
        db_path=BRAND3_DB_PATH,
        lang=lang,
    )
    _ensure_brand_history_defaults(history, domain)
    can_edit = (
        not settings.team_token
        or is_team_request(request, create_serializer(settings.cookie_secret))
    )
    return templates.TemplateResponse(
        request,
        "brand_history.html.j2",
        {
            "domain": domain,
            "history": history,
            "analyses": history["rows"],
            "can_edit_brand_profile": can_edit,
            "ui_lang": lang,
        },
    )


@router.get("/brand/{domain}/edit")
async def brand_profile_edit(
    request: Request,
    domain: str,
    lang: Literal["es", "en"] = Query("es"),
):
    _require_team_write(request)
    history = await asyncio.to_thread(
        build_observatory_brand_history,
        domain,
        db_path=BRAND3_DB_PATH,
        lang=lang,
    )
    _ensure_brand_history_defaults(history, domain)
    return templates.TemplateResponse(
        request,
        "brand_profile_edit.html.j2",
        {
            "domain": domain,
            "history": history,
            "profile": history["profile"],
            "ui_lang": lang,
        },
    )


@router.post("/brand/{domain}/edit")
async def brand_profile_edit_submit(
    request: Request,
    domain: str,
    lang: Literal["es", "en"] = Query("es"),
):
    _require_team_write(request)
    form = await request.form()
    overrides = {
        "name": str(form.get("name") or ""),
        "domain": str(form.get("domain") or ""),
        "canonical_url": str(form.get("canonical_url") or ""),
        "logo_url": str(form.get("logo_url") or ""),
        "summary": str(form.get("summary") or ""),
        "offer": str(form.get("offer") or ""),
        "audience": str(form.get("audience") or ""),
        "outcome": str(form.get("outcome") or ""),
        "category": str(form.get("category") or ""),
        "official_links": str(form.get("official_links") or ""),
        "social_links": str(form.get("social_links") or ""),
    }
    updated_by = str(form.get("updated_by") or "").strip()
    brand_key = await asyncio.to_thread(
        save_brand_profile_overrides,
        domain,
        overrides,
        db_path=BRAND3_DB_PATH,
        updated_by=updated_by,
    )
    return RedirectResponse(f"/brand/{quote(brand_key)}?lang={lang}", status_code=303)


def _ensure_brand_history_defaults(history: dict, domain: str) -> None:
    rows = history.get("rows") or []
    scores = [row.get("score") for row in rows if row.get("score") is not None]
    best_score = max(scores) if scores else None
    profile = history.setdefault("profile", {})
    profile.setdefault("name", history.get("display_name") or domain)
    profile.setdefault("domain", history.get("domain") or domain)
    profile.setdefault("logo_url", "")
    profile.setdefault("logo_source", "")
    profile.setdefault("summary", "")
    profile.setdefault("offer", "")
    profile.setdefault("audience", "")
    profile.setdefault("outcome", "")
    profile.setdefault("category", history.get("category_label") or "")
    profile.setdefault("official_links", [])
    profile.setdefault("analyzed_links", [])
    profile.setdefault("social_links", [])
    profile.setdefault("proof_points", [])
    profile.setdefault("evidence_gaps", [])
    profile.setdefault("confidence_notes", [])
    profile.setdefault("moodboard", {"available": False, "images": [], "image_count": 0, "role_counts": {}})
    profile.setdefault("models", sorted({str(row.get("score_model")) for row in rows if row.get("score_model")}))
    profile.setdefault("scan_count", len(rows))
    profile.setdefault("latest_date", rows[0].get("date") if rows else "")
    profile.setdefault("best_score", best_score)
    profile.setdefault("best_score_compact", str(round(best_score)) if best_score is not None else "-")
    history.setdefault(
        "sv9_status",
        {
            "available": False,
            "score": None,
            "score_compact": "-",
            "href": "",
            "date": "",
            "generate_scan_id": None,
            "source_run_id": None,
        },
    )
