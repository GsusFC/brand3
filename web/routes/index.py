"""GET / — scanner-first landing + latest analyses."""

from typing import Literal

from fastapi import APIRouter, Query, Request

from ..presenters import enrich
from ..i18n import magnetism_landing_copy, normalize_lang
from ..storage import list_latest_public, list_magnetism_scans
from ..templates_env import templates

router = APIRouter()


def _parse_timestamp(value: str | None):
    from datetime import datetime

    if not value:
        return datetime.min
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00").replace(" ", "T")).replace(
            tzinfo=None
        )
    except ValueError:
        return datetime.min


def _brand_key(value: str | None) -> str:
    return (value or "").strip().lower()


def _recent_home_items(limit: int = 10) -> list[dict]:
    source_limit = max(limit * 4, 50)
    scans = []
    for scan in list_magnetism_scans(limit=source_limit):
        brand_name = scan.get("brand_name") or scan.get("url") or "unknown"
        scans.append(
            {
                "brand_key": _brand_key(brand_name),
                "brand_name": brand_name,
                "href": f"/magnetism-scanner/scan/{scan['id']}",
                "composite": scan.get("magnetism_score"),
                "kind": "Scanner",
                "completed_at": scan.get("created_at"),
                "_timestamp": _parse_timestamp(scan.get("created_at")),
            }
        )

    audits = []
    for audit in list_latest_public(limit=source_limit):
        brand_name = audit.get("brand_slug") or "unknown"
        audits.append(
            {
                "brand_key": _brand_key(brand_name),
                "brand_name": brand_name,
                "href": f"/r/{audit['token']}",
                "composite": audit.get("composite"),
                "kind": "Audit",
                "completed_at": audit.get("completed_at"),
                "_timestamp": _parse_timestamp(audit.get("completed_at")),
            }
        )

    rows = scans + audits
    rows.sort(key=lambda row: row["_timestamp"], reverse=True)
    unique_rows: list[dict] = []
    seen_keys: set[str] = set()
    for row in rows:
        brand_key = row.pop("brand_key", "")
        row.pop("_timestamp", None)
        if brand_key in seen_keys:
            continue
        seen_keys.add(brand_key)
        unique_rows.append(row)
        if len(unique_rows) >= limit:
            break
    return enrich(unique_rows)


@router.get("/")
async def index(request: Request, lang: Literal["es", "en"] = Query("es")):
    ui_lang = normalize_lang(lang)
    rows = _recent_home_items(limit=15)
    return templates.TemplateResponse(
        request,
        "index.html.j2",
        {
            "latest_analyses": rows,
            "ui_lang": ui_lang,
            "landing": magnetism_landing_copy(ui_lang),
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
