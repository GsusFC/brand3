"""Read-only Visual Signature routes for the local Brand3 platform."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from ..templates_env import templates
from ..visual_signature_data import artifact_file_response_payload
from ..visual_signature_data import build_human_review_model
from ..visual_signature_data import build_screenshot_preview_model
from ..visual_signature_data import build_visual_signature_model
from ..visual_signature_data import screenshot_file_response_payload

router = APIRouter()


@router.get("/visual-signature")
async def visual_signature_index(request: Request, lang: Literal["es", "en"] = Query("es")):
    return await _render(request, "overview", lang)


@router.get("/visual-signature/governance")
async def visual_signature_governance(request: Request, lang: Literal["es", "en"] = Query("es")):
    return await _render(request, "governance", lang)


@router.get("/visual-signature/calibration")
async def visual_signature_calibration(request: Request, lang: Literal["es", "en"] = Query("es")):
    return await _render(request, "calibration", lang)


@router.get("/visual-signature/corpus")
async def visual_signature_corpus(request: Request, lang: Literal["es", "en"] = Query("es")):
    return await _render(request, "corpus", lang)


@router.get("/visual-signature/reviewer")
async def visual_signature_reviewer(request: Request, lang: Literal["es", "en"] = Query("es")):
    return await _render(request, "reviewer", lang)


@router.get("/visual-signature/reviewer/human-review")
async def visual_signature_human_review(request: Request, lang: Literal["es", "en"] = Query("es")):
    return await _render_human_review(request, None, lang)


@router.get("/visual-signature/reviewer/human-review/{brand}")
async def visual_signature_human_review_brand(
    request: Request,
    brand: str,
    lang: Literal["es", "en"] = Query("es"),
):
    return await _render_human_review(request, brand, lang)


@router.get("/visual-signature/artifacts/{artifact_key}")
async def visual_signature_artifact(
    request: Request,
    artifact_key: str,
    lang: Literal["es", "en"] = Query("es"),
):
    payload = await asyncio.to_thread(artifact_file_response_payload, artifact_key)
    if payload is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"visual signature artifact {artifact_key}", "ui_lang": lang},
            status_code=404,
        )
    path, media_type = payload
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/visual-signature/screenshots/{filename}/preview")
async def visual_signature_screenshot_preview(
    request: Request,
    filename: str,
    lang: Literal["es", "en"] = Query("es"),
):
    model = await asyncio.to_thread(build_screenshot_preview_model, filename)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"visual signature screenshot preview {filename}", "ui_lang": lang},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "visual_signature_screenshot_preview.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/visual-signature/screenshots/{filename:path}")
async def visual_signature_screenshot(
    request: Request,
    filename: str,
    lang: Literal["es", "en"] = Query("es"),
):
    payload = await asyncio.to_thread(screenshot_file_response_payload, filename)
    if payload is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"visual signature screenshot {filename}", "ui_lang": lang},
            status_code=404,
        )
    path, media_type = payload
    return FileResponse(path, media_type=media_type)


async def _render(request: Request, section: str, lang: str):
    model = await asyncio.to_thread(build_visual_signature_model, section, lang)
    return templates.TemplateResponse(
        request,
        "visual_signature.html.j2",
        {"model": model, "ui_lang": lang},
    )


async def _render_human_review(request: Request, brand: str | None, lang: str):
    model = await asyncio.to_thread(build_human_review_model, brand)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": "visual signature human review evidence", "ui_lang": lang},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "visual_signature_human_review.html.j2",
        {"model": model, "ui_lang": lang},
    )
