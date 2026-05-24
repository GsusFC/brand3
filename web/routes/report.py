"""GET /r/{token} — serves the rendered HTML report using the engine renderer."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.reports.renderer import ReportRenderer

from ..storage import get_request
from ..templates_env import templates

router = APIRouter()


class _WebReportNarrativeFallback:
    """Force deterministic report prose for public web reads.

    Report generation can use LLM narrative during the audit pipeline. The
    public detail page should be a read path: fast, repeatable, and safe under
    health checks.
    """

    def _call(self, *args, **kwargs) -> str:
        return ""

    def _call_json(self, *args, **kwargs) -> dict:
        return {}


_WEB_REPORT_ANALYZER = _WebReportNarrativeFallback()


def _load_snapshot(run_id: int) -> dict | None:
    from src.config import BRAND3_DB_PATH
    from src.storage.sqlite_store import SQLiteStore

    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        return store.get_run_snapshot(run_id)
    finally:
        store.close()


@router.get("/r/{token}")
async def report(
    request: Request,
    token: str,
    theme: Literal["dark", "light"] = Query("light"),
):
    row = get_request(token)
    if row is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"report {token}"},
            status_code=404,
        )
    if row["status"] != "ready":
        return RedirectResponse(f"/r/{token}/status", status_code=303)
    if row.get("takedown_requested"):
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"report {token} (taken down)"},
            status_code=404,
        )

    run_id = row.get("run_id")
    if not run_id:
        return templates.TemplateResponse(
            request,
            "error.html.j2",
            {"status_code": 500, "error": "ready state without run_id"},
            status_code=500,
        )

    snapshot = _load_snapshot(int(run_id))
    if snapshot is None:
        return templates.TemplateResponse(
            request,
            "error.html.j2",
            {"status_code": 500, "error": f"run {run_id} missing from store"},
            status_code=500,
        )

    html = ReportRenderer().render(
        snapshot,
        theme=theme,
        analyzer=_WEB_REPORT_ANALYZER,
    )
    return HTMLResponse(content=html)
