"""Read-only Visual Signature routes for the local Brand3 platform."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Query, Request
from ..visual_signature_data_support import artifact_file_response_payload
from ..visual_signature_data_support import screenshot_file_response_payload
from ..visual_signature_human_review_data import build_human_review_model
from ..visual_signature_overview_data import build_screenshot_preview_model_for_lang
from ..visual_signature_overview_data import build_visual_signature_model
from ..visual_signature_route_support import file_response_or_not_found
from ..visual_signature_route_support import render_template
from ..visual_signature_route_support import render_template_or_not_found

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
    return await file_response_or_not_found(
        request,
        payload_builder=artifact_file_response_payload,
        payload_args=(artifact_key,),
        lang=lang,
        resource=f"visual signature artifact {artifact_key}",
        filename_from_path=True,
        to_thread_fn=asyncio.to_thread,
    )


@router.get("/visual-signature/screenshots/{filename}/preview")
async def visual_signature_screenshot_preview(
    request: Request,
    filename: str,
    lang: Literal["es", "en"] = Query("es"),
):
    return await render_template_or_not_found(
        request,
        template_name="visual_signature_screenshot_preview.html.j2",
        model_builder=build_screenshot_preview_model_for_lang,
        builder_args=(filename, lang),
        lang=lang,
        resource=f"visual signature screenshot preview {filename}",
        to_thread_fn=asyncio.to_thread,
    )


@router.get("/visual-signature/screenshots/{filename}")
async def visual_signature_screenshot(
    request: Request,
    filename: str,
    lang: Literal["es", "en"] = Query("es"),
):
    return await file_response_or_not_found(
        request,
        payload_builder=screenshot_file_response_payload,
        payload_args=(filename,),
        lang=lang,
        resource=f"visual signature screenshot {filename}",
        to_thread_fn=asyncio.to_thread,
    )


async def _render(request: Request, section: str, lang: str):
    model = await asyncio.to_thread(build_visual_signature_model, section, lang)
    return await render_template(
        request,
        template_name="visual_signature.html.j2",
        model_builder=lambda *_args: model,
        builder_args=(),
        lang=lang,
    )


async def _render_human_review(request: Request, brand: str | None, lang: str):
    return await render_template_or_not_found(
        request,
        template_name="visual_signature_human_review.html.j2",
        model_builder=build_human_review_model,
        builder_args=(brand, lang),
        lang=lang,
        resource="visual signature human review evidence",
        to_thread_fn=asyncio.to_thread,
    )
