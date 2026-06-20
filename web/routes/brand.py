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
    _ensure_brand_history_defaults(history, domain)
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
