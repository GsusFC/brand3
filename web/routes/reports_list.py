"""GET /reports — paginated public observatory list."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from ..presenters import enrich
from ..storage import list_public_reports
from ..templates_env import templates

router = APIRouter()

_PER_PAGE = 20
_ALLOWED_SORTS = ("newest", "score_desc", "score_asc")


@router.get("/reports")
async def reports_list(
    request: Request,
    q: str | None = Query(None),
    sort: str = Query("newest"),
    page: int = Query(1, ge=1),
):
    if sort not in _ALLOWED_SORTS:
        sort = "newest"
    rows, total = list_public_reports(
        query=q,
        sort=sort,
        page=page,
        per_page=_PER_PAGE,
    )
    rows = enrich(rows)
    total_pages = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)
    return templates.TemplateResponse(
        request,
        "reports_list.html.j2",
        {
            "rows": rows,
            "query": q or "",
            "sort": sort,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        },
    )


@router.get("/latest_brand_audits")
async def latest_brand_audits_alias():
    return RedirectResponse("/reports", status_code=303)
