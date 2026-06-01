"""GET /brand-audit — dedicated Brand Audit hub."""

from fastapi import APIRouter, Request

from ..presenters import enrich
from ..storage import list_latest_public
from ..templates_env import templates

router = APIRouter()


@router.get("/brand-audit")
async def brand_audit(request: Request):
    rows = enrich(list_latest_public(limit=5))
    return templates.TemplateResponse(
        request,
        "brand_audit.html.j2",
        {
            "title": "Brand Audit",
            "recent_audits": rows,
        },
    )
