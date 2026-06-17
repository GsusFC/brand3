"""GET / — scanner-first landing + latest analyses."""

import asyncio
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Query, Request

from src.config import BRAND3_DB_PATH
from src.sv9.categories import CATEGORIES
from src.sv9.ranking import build_ranking
from src.sv9.store import Sv9Store

from ..i18n import magnetism_landing_copy, normalize_lang
from ..presenters import enrich
from ..scan_links import primary_scan_href
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


def _display_company_name(value: str | None, url: str | None = None) -> str:
    raw = (value or "").strip()
    candidate = raw
    if _looks_like_url_or_domain(candidate):
        candidate = _host_label(candidate)
    if not candidate and url:
        candidate = _host_label(url)
    return _titleize_company_name(candidate or raw or "unknown")


def _looks_like_url_or_domain(value: str) -> bool:
    text = value.strip().lower()
    return "://" in text or "/" in text or "." in text


def _host_label(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.netloc or parsed.path).split("/", 1)[0].split(":", 1)[0].lower()
    if host.startswith("www."):
        host = host[4:]
    return host.split(".", 1)[0]


def _titleize_company_name(value: str) -> str:
    text = value.strip().replace("-", " ").replace("_", " ")
    if not text:
        return "unknown"
    return " ".join(part.upper() if len(part) <= 3 and part.isalpha() else part.capitalize() for part in text.split())


def _sv9_observatory_metadata() -> dict[int, dict]:
    store = Sv9Store(BRAND3_DB_PATH)
    try:
        ranking = build_ranking(store)
    finally:
        store.close()
    return {
        int(entry["scan_id"]): {
            "category": entry.get("category"),
            "category_label": entry.get("category_label"),
            "needs_rescan": entry.get("needs_rescan"),
        }
        for entry in ranking.get("entries", [])
    }


def _recent_home_items(
    limit: int = 10,
    *,
    lang: str = "es",
    sort: str = "recent",
    category: str | None = None,
) -> list[dict]:
    source_limit = max(limit * 4, 50)
    sv9_by_scan_id = _sv9_observatory_metadata()
    scans = []
    for scan in list_magnetism_scans(limit=source_limit):
        brand_name = scan.get("brand_name") or scan.get("url") or "unknown"
        href = primary_scan_href(scan, db_path=BRAND3_DB_PATH, lang=lang)
        sv9_id = None
        if href.startswith("/sv9/scan/"):
            try:
                sv9_id = int(href.split("/sv9/scan/", 1)[1].split("?", 1)[0].split("/", 1)[0])
            except ValueError:
                sv9_id = None
        sv9_meta = sv9_by_scan_id.get(sv9_id or -1, {})
        scans.append(
            {
                "brand_key": _brand_key(brand_name),
                "brand_name": brand_name,
                "display_name": _display_company_name(brand_name, scan.get("url")),
                "href": href,
                "composite": scan.get("magnetism_score"),
                "kind": "Scanner",
                "completed_at": scan.get("created_at"),
                "category": sv9_meta.get("category"),
                "category_label": sv9_meta.get("category_label"),
                "status_icon": "↻" if sv9_meta.get("needs_rescan") else "●",
                "status_label": "needs rescan" if sv9_meta.get("needs_rescan") else "ready",
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
                "display_name": _display_company_name(brand_name, audit.get("url")),
                "href": f"/r/{audit['token']}",
                "composite": audit.get("composite"),
                "kind": "Audit",
                "completed_at": audit.get("completed_at"),
                "category": None,
                "category_label": None,
                "status_icon": "●",
                "status_label": "ready",
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
    if category:
        unique_rows = [row for row in unique_rows if row.get("category") == category]
    if sort == "score":
        unique_rows.sort(
            key=lambda row: (
                row.get("composite") is None,
                -(float(row.get("composite") or 0)),
                row.get("completed_at") or "",
            )
        )
    return enrich(unique_rows[:limit])


@router.get("/")
async def index(
    request: Request,
    lang: Literal["es", "en"] = Query("es"),
    sort: Literal["recent", "score"] = Query("recent"),
    category: str | None = Query(None),
):
    ui_lang = normalize_lang(lang)
    active_category = category if category in CATEGORIES else None
    rows = await asyncio.to_thread(
        _recent_home_items,
        limit=15,
        lang=ui_lang,
        sort=sort,
        category=active_category,
    )
    return templates.TemplateResponse(
        request,
        "index.html.j2",
        {
            "latest_analyses": rows,
            "ui_lang": ui_lang,
            "landing": magnetism_landing_copy(ui_lang),
            "observatory": {
                "sort": sort,
                "category": active_category,
                "categories": CATEGORIES,
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
