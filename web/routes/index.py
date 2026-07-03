"""GET / — scanner-first landing."""

import sqlite3
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from src.config import BRAND3_DB_PATH

from ..i18n import magnetism_landing_copy, normalize_lang
from ..observatory_index_support import _compact_date, _score_compact
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
    latest_rows = _load_latest_scanner_rows(BRAND3_DB_PATH, lang=ui_lang)
    return templates.TemplateResponse(
        request,
        "index.html.j2",
        {
            "latest_analyses": latest_rows,
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
                "total": len(latest_rows),
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


def _load_latest_scanner_rows(db_path: str, *, lang: str, limit: int = 25) -> list[dict]:
    """Load recent scanner rows for the landing without hydrating Observatory."""

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='magnetism_scans'"
            ).fetchone()
            if table is None:
                return []
            rows = conn.execute(
                """
                SELECT
                  id,
                  COALESCE(
                    CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.brand_name') END,
                    brand_name
                  ) AS brand_name,
                  COALESCE(
                    CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.url') END,
                    url
                  ) AS url,
                  COALESCE(
                    CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.magnetism_score') END,
                    magnetism_score
                  ) AS magnetism_score,
                  COALESCE(
                    CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.quadrant') END,
                    quadrant
                  ) AS quadrant,
                  COALESCE(
                    CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.source_run_id') END,
                    source_run_id
                  ) AS source_run_id,
                  created_at
                FROM magnetism_scans
                WHERE status = 'ready'
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (max(1, min(int(limit or 25), 50)),),
            ).fetchall()
    except sqlite3.Error:
        return []

    return [_scanner_row_payload(row, lang=lang) for row in rows]


def _scanner_row_payload(row: sqlite3.Row, *, lang: str) -> dict:
    brand_name = str(row["brand_name"] or "")
    url = str(row["url"] or "")
    display_name = brand_name or _domain_from_url(url) or f"Scan #{row['id']}"
    domain = _domain_from_url(url)
    href = f"/magnetism-scanner/scan/{row['id']}?lang={lang}"
    score = _float_or_none(row["magnetism_score"])
    return {
        "brand_key": domain or display_name.lower(),
        "display_name": display_name,
        "domain": domain,
        "brand_href": href,
        "latest_date": row["created_at"] or "",
        "compact_date": _compact_date(row["created_at"] or ""),
        "score": score,
        "score_compact": _score_compact(score),
        "score_model": "magnetism",
        "quadrant": row["quadrant"] or "",
        "category": None,
        "category_label": None,
        "classification_tags": [],
        "classification_tag_keys": [],
        "scan_count": 1,
        "primary_href": href,
        "needs_sv9": bool(row["source_run_id"]),
        "sv9_generate_scan_id": int(row["id"]) if row["source_run_id"] else None,
        "legacy_source_run_id": int(row["source_run_id"]) if row["source_run_id"] else None,
    }


def _domain_from_url(url: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or parsed.path).lower().removeprefix("www.").strip("/")


def _float_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
