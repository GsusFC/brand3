"""GET /brand/{domain} — per-brand history + ASCII evolution chart."""

import asyncio
from typing import Literal
from urllib.parse import quote

import secrets

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from src.classification.market_taxonomy import GROUPS, tag_definition, tags_for_group
from src.config import BRAND3_DB_PATH

from ..config import settings
from ..middleware.team_cookie import create_serializer, is_team_request
from ..observatory_index import (
    build_observatory_brand_history,
    save_brand_market_classification,
    save_brand_profile_overrides,
)
from ..templates_env import templates

router = APIRouter()


class BrandProfileUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    canonical_url: str | None = None
    logo_url: str | None = None
    summary: str | None = None
    offer: str | None = None
    audience: str | None = None
    outcome: str | None = None
    category: str | None = None
    official_links: list[str] | str | None = None
    social_links: list[str] | str | None = None
    updated_by: str | None = None


class BrandMarketClassificationUpdate(BaseModel):
    business_model: list[str] | None = None
    sector_industry: list[str] | None = None
    technology_capability: list[str] | None = None
    market_signals: list[str] | None = None
    corporate_status: list[str] | None = None
    primary_category: str | None = None
    updated_by: str | None = None


PROFILE_EDIT_FIELDS = (
    "name",
    "domain",
    "canonical_url",
    "logo_url",
    "summary",
    "offer",
    "audience",
    "outcome",
    "category",
    "official_links",
    "social_links",
)


def _has_team_write_access(request: Request) -> bool:
    if not settings.team_token:
        return True
    if is_team_request(request, create_serializer(settings.cookie_secret)):
        return True
    supplied = request.headers.get("x-brand3-team-token", "").strip()
    if not supplied:
        scheme, _, value = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() == "bearer":
            supplied = value.strip()
    return bool(supplied and secrets.compare_digest(supplied, settings.team_token))


def _require_team_write(request: Request) -> None:
    if not _has_team_write_access(request):
        raise HTTPException(status_code=403, detail="team access required")


def _brand_not_found(history: dict) -> bool:
    return not history.get("rows")


def _brand_api_payload(history: dict) -> dict:
    return {
        "brand_key": history.get("brand_key"),
        "display_name": history.get("display_name"),
        "domain": history.get("domain"),
        "category_label": history.get("category_label"),
        "profile": history.get("profile") or {},
        "market_classification": history.get("market_classification") or {},
        "sv9_status": history.get("sv9_status") or {},
        "scans": history.get("rows") or [],
    }


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


@router.get("/api/brands/market-taxonomy")
async def brand_market_taxonomy_api() -> dict:
    groups = {}
    for group in GROUPS:
        tags = []
        for tag in tags_for_group(group):
            definition = tag_definition(group, tag)
            tags.append(
                {
                    "tag": definition.tag,
                    "definition": definition.definition,
                    "aliases": list(definition.aliases),
                }
            )
        groups[group] = tags
    return {
        "version": "brand3_market_classification_v0_1",
        "groups": groups,
        "write_policy": "manual_or_external_agent_selection_from_controlled_taxonomy",
        "score_policy": "classification_context_only_does_not_change_scores",
    }


@router.get("/api/brands/{domain}/profile")
@router.get("/api/brand/{domain}/profile")
async def brand_profile_api_get(
    domain: str,
    lang: Literal["es", "en"] = Query("es"),
):
    history = await asyncio.to_thread(
        build_observatory_brand_history,
        domain,
        db_path=BRAND3_DB_PATH,
        lang=lang,
    )
    _ensure_brand_history_defaults(history, domain)
    if _brand_not_found(history):
        raise HTTPException(status_code=404, detail="brand not found")
    return _brand_api_payload(history)


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
            "market_classification": history["market_classification"],
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


@router.patch("/api/brands/{domain}/profile")
@router.patch("/api/brand/{domain}/profile")
async def brand_profile_api_update(
    request: Request,
    domain: str,
    payload: BrandProfileUpdate,
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
    if _brand_not_found(history):
        raise HTTPException(status_code=404, detail="brand not found")
    current = history.get("profile") or {}
    updates = payload.model_dump(exclude_unset=True)
    updated_by = str(updates.pop("updated_by", "") or "").strip()
    overrides = {field: current.get(field, "") for field in PROFILE_EDIT_FIELDS}
    for field in PROFILE_EDIT_FIELDS:
        if field in updates:
            overrides[field] = updates[field]
    brand_key = await asyncio.to_thread(
        save_brand_profile_overrides,
        domain,
        overrides,
        db_path=BRAND3_DB_PATH,
        updated_by=updated_by,
    )
    updated = await asyncio.to_thread(
        build_observatory_brand_history,
        brand_key,
        db_path=BRAND3_DB_PATH,
        lang=lang,
    )
    _ensure_brand_history_defaults(updated, brand_key)
    return {
        "brand_key": brand_key,
        "profile": updated["profile"],
        "brand": _brand_api_payload(updated),
    }


@router.patch("/api/brands/{domain}/market-classification")
@router.patch("/api/brand/{domain}/market-classification")
async def brand_market_classification_api_update(
    request: Request,
    domain: str,
    payload: BrandMarketClassificationUpdate,
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
    if _brand_not_found(history):
        raise HTTPException(status_code=404, detail="brand not found")
    values = payload.model_dump(exclude_unset=True)
    updated_by = str(values.pop("updated_by", "") or "").strip()
    current_market = history.get("market_classification") or {}
    current_accepted = (
        current_market.get("accepted") if isinstance(current_market.get("accepted"), dict) else {}
    )
    form_values = {
        group: values[group] if group in values else list(current_accepted.get(group) or [])
        for group in GROUPS
    }
    form_values["primary_category"] = str(
        values.get("primary_category")
        if "primary_category" in values
        else current_market.get("primary_category") or ""
    )
    brand_key = await asyncio.to_thread(
        save_brand_market_classification,
        domain,
        form_values,
        db_path=BRAND3_DB_PATH,
        updated_by=updated_by,
    )
    updated = await asyncio.to_thread(
        build_observatory_brand_history,
        brand_key,
        db_path=BRAND3_DB_PATH,
        lang=lang,
    )
    _ensure_brand_history_defaults(updated, brand_key)
    return {
        "brand_key": brand_key,
        "market_classification": updated["market_classification"],
        "brand": _brand_api_payload(updated),
    }


@router.post("/brand/{domain}/market-classification")
async def brand_market_classification_submit(
    request: Request,
    domain: str,
    lang: Literal["es", "en"] = Query("es"),
):
    _require_team_write(request)
    form = await request.form()
    values = {
        "business_model": form.getlist("business_model"),
        "sector_industry": form.getlist("sector_industry"),
        "technology_capability": form.getlist("technology_capability"),
        "market_signals": form.getlist("market_signals"),
        "corporate_status": form.getlist("corporate_status"),
        "primary_category": str(form.get("primary_category") or ""),
    }
    updated_by = str(form.get("updated_by") or "").strip()
    brand_key = await asyncio.to_thread(
        save_brand_market_classification,
        domain,
        values,
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
        "market_classification",
        {
            "available": False,
            "accepted": {},
            "proposed": {},
            "primary_category": "",
            "requires_human_review": False,
            "groups": [],
            "options": {},
        },
    )
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
