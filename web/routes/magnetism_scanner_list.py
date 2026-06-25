"""List and evidence-vNext routes for the Magnetism Scanner."""

from __future__ import annotations

import asyncio
import secrets

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ..storage import insert_magnetism_job
from ..templates_env import templates
from ..workers.queue import get_queue
from ..workers.slug import slug_from_url

from .magnetism_scanner import (
    _Lang,
    _with_lang,
)
from . import magnetism_scanner as _magnetism_scanner
from .magnetism_scanner_vnext import _load_evidence_vnext_diagnostic, _load_evidence_vnext_llm_shadow
from .magnetism_scanner_list_copy import _build_not_found_response, _build_scanner_index_context, _build_vnext_view_context

router = APIRouter()


@router.get("/magnetism-scanner")
async def magnetism_scanner_index(
    request: Request,
    lang: _Lang = Query("es"),
    q: str | None = Query(None),
    sort: str = Query("newest"),
    category: str | None = Query(None),
    tag: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    """Render index page of Magnetism Scanner showing past analyses and inputs."""
    sort = {"recent": "newest", "score": "score_desc"}.get(sort, sort)
    if sort not in {"newest", "score_desc", "score_asc", "scans_desc"}:
        sort = "newest"
    index_data = await asyncio.to_thread(
        _magnetism_scanner._load_magnetism_index_data,
        query=q,
        sort=sort,
        category=category,
        tag=tag,
        page=page,
        lang=lang,
    )
    observatory = index_data["observatory"]
    audit_runs = index_data["audit_runs"]

    return templates.TemplateResponse(
        request,
        "magnetism_scanner.html.j2",
        _build_scanner_index_context(
            observatory=observatory,
            audit_runs=audit_runs,
            lang=lang,
            q=q,
            sort=sort,
            category=category,
        ),
    )


@router.post("/magnetism-scanner/analyze")
async def magnetism_scanner_analyze(
    request: Request,
    url: str = Form(None),
    manual_text: str = Form(None),
    lang: _Lang = Form("es"),
):
    """Queue analysis on the provided URL or copy-pasted text block."""
    url_val = (url or "").strip()
    manual_val = (manual_text or "").strip()

    if not url_val and not manual_val:
        return templates.TemplateResponse(
            request,
            "error.html.j2",
            {
                "status_code": 400,
                "error": "Input required: Please provide either a website URL to scan or paste manual text content.",
                "ui_lang": lang,
            },
            status_code=400,
        )

    normalized_url = ""
    if url_val:
        from . import magnetism_scanner

        valid, result = magnetism_scanner.validate_url(url_val)
        if not valid:
            return templates.TemplateResponse(
                request,
                "error.html.j2",
                {"status_code": 400, "error": f"URL rejected: {result}", "ui_lang": lang},
                status_code=400,
            )
        normalized_url = result

    token = secrets.token_urlsafe(12)
    if normalized_url:
        input_type = "url"
        input_value = normalized_url
        brand_name = slug_from_url(normalized_url)
        display_url = normalized_url
    else:
        input_type = "manual"
        input_value = manual_val
        brand_name = "Manual Upload Brand"
        display_url = "Manual Upload"

    await asyncio.to_thread(
        insert_magnetism_job,
        token=token,
        brand_name=brand_name,
        url=display_url,
        input_type=input_type,
        input_value=input_value,
    )
    await get_queue().enqueue_magnetism(token)
    return RedirectResponse(_with_lang(f"/magnetism-scanner/{token}/status", lang), status_code=303)


@router.post("/magnetism-scanner/from-run")
async def magnetism_scanner_from_run(
    request: Request,
    run_id: int = Form(...),
    lang: _Lang = Form("es"),
):
    """Queue a Magnetism scan from an existing Brand Audit run snapshot."""
    run = await asyncio.to_thread(_magnetism_scanner._load_run_summary, run_id)

    if run is None:
        return _build_not_found_response(request, f"Brand Audit run #{run_id}", lang)

    token = secrets.token_urlsafe(12)
    await asyncio.to_thread(
        insert_magnetism_job,
        token=token,
        brand_name=str(run.get("brand_name") or f"Brand Audit run #{run_id}"),
        url=str(run.get("url") or "Brand Audit snapshot"),
        input_type="audit_run",
        input_value=str(run_id),
        source_run_id=run_id,
    )
    await get_queue().enqueue_magnetism(token)
    return RedirectResponse(_with_lang(f"/magnetism-scanner/{token}/status", lang), status_code=303)


@router.get("/magnetism-scanner/run/{run_id}/evidence-vnext")
async def magnetism_scanner_evidence_vnext(run_id: int):
    """Return read-only evidence vNext diagnostics for a Brand Audit run."""
    diagnostic = await asyncio.to_thread(_load_evidence_vnext_diagnostic, run_id)
    if diagnostic is None:
        raise HTTPException(status_code=404, detail=f"Brand Audit run #{run_id} not found")
    return JSONResponse(diagnostic)


@router.get("/api/v1/scanner/run/{run_id}/evidence-vnext/llm-shadow")
async def scanner_api_evidence_vnext_llm_shadow(
    run_id: int,
    no_cache: bool = Query(False),
):
    """Run read-only evidence vNext LLM shadow diagnostics for a Brand Audit run."""
    diagnostic = await asyncio.to_thread(_load_evidence_vnext_llm_shadow, run_id, no_cache=no_cache)
    if diagnostic is None:
        raise HTTPException(status_code=404, detail=f"Brand Audit run #{run_id} not found")
    return JSONResponse(diagnostic)


@router.get("/magnetism-scanner/run/{run_id}/evidence-vnext/view")
async def magnetism_scanner_evidence_vnext_view(
    request: Request,
    run_id: int,
    lang: _Lang = Query("es"),
):
    """Render read-only evidence vNext diagnostics for a Brand Audit run."""
    diagnostic = await asyncio.to_thread(_load_evidence_vnext_diagnostic, run_id)
    if diagnostic is None:
        return _build_not_found_response(request, f"Brand Audit run #{run_id}", lang)
    context = _build_vnext_view_context(run_id, lang, diagnostic)
    context["model"]["back_href"] = _with_lang("/magnetism-scanner", lang)
    return templates.TemplateResponse(
        request,
        "magnetism_evidence_vnext.html.j2",
        context,
    )
