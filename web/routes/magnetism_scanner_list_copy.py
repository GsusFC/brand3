"""Helpers for Magnetism Scanner list routes."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from ..i18n import magnetism_landing_copy
from ..templates_env import templates
from .magnetism_scanner_impl import _lang_q, _magnetism_display_name, _ui


def _build_scanner_index_context(
    observatory: dict[str, Any],
    audit_runs: list[dict],
    lang: str,
    q: str | None,
    sort: str,
    category: str | None,
) -> dict[str, object]:
    scans = observatory["rows"]
    for run in audit_runs:
        run["display_name"] = _magnetism_display_name(
            str(run.get("brand_name") or ""),
            str(run.get("url") or ""),
        )

    return {
        "ui_lang": lang,
        "landing": magnetism_landing_copy(lang),
        "show_sv9_nav": True,
        "model": {
            "scans": scans,
            "audit_runs": audit_runs,
            "observatory": {
                "query": q or "",
                "sort": sort,
                "category": category,
                "tag": observatory["tag"],
                "categories": observatory["categories"],
                "tags": observatory["tags"],
                "page": observatory["page"],
                "total": observatory["total"],
                "total_pages": observatory["total_pages"],
                "has_prev": observatory["has_prev"],
                "has_next": observatory["has_next"],
            },
            "lang": lang,
            "other_lang": "en" if lang == "es" else "es",
            "lang_query": _lang_q(lang),
            "t": _ui(lang),
        },
    }


def _build_not_found_response(request: Request, resource: str, lang: str) -> object:
    return templates.TemplateResponse(
        request,
        "not_found.html.j2",
        {"resource": resource, "ui_lang": lang},
        status_code=404,
    )


def _build_vnext_view_context(run_id: int, lang: str, diagnostic: dict) -> dict[str, object]:
    report = diagnostic["report"]
    rows = report.get("rows") or []
    row = rows[0] if rows else {}
    return {
        "ui_lang": lang,
        "model": {
            "lang": lang,
            "lang_query": _lang_q(lang),
            "t": _ui(lang),
            "run_id": run_id,
            "brand_name": row.get("brand_name") or f"Brand Audit run #{run_id}",
            "url": row.get("url") or "",
            "diagnostic": diagnostic,
            "report": report,
            "row": row,
            "json_href": f"/magnetism-scanner/run/{run_id}/evidence-vnext",
            "back_href": f"/magnetism-scanner?lang={lang}",
        },
    }

