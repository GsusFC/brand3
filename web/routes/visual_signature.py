"""Read-only Visual Signature routes for the local Brand3 platform."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from ..templates_env import templates
from ..visual_signature_data import artifact_file_response_payload
from ..visual_signature_data import build_human_review_model
from ..visual_signature_data import build_screenshot_preview_model
from ..visual_signature_data import build_visual_signature_model
from ..visual_signature_data import screenshot_file_response_payload

router = APIRouter()


@router.get("/visual-signature")
async def visual_signature_index(request: Request):
    return _render(request, "overview")


@router.get("/visual-signature/governance")
async def visual_signature_governance(request: Request):
    return _render(request, "governance")


@router.get("/visual-signature/calibration")
async def visual_signature_calibration(request: Request):
    return _render(request, "calibration")


@router.get("/visual-signature/corpus")
async def visual_signature_corpus(request: Request):
    return _render(request, "corpus")


@router.get("/visual-signature/reviewer")
async def visual_signature_reviewer(request: Request):
    return _render(request, "reviewer")


@router.get("/visual-signature/reviewer/human-review")
async def visual_signature_human_review(request: Request):
    return _render_human_review(request, None)


@router.get("/visual-signature/reviewer/human-review/{brand}")
async def visual_signature_human_review_brand(request: Request, brand: str):
    return _render_human_review(request, brand)


@router.get("/visual-signature/artifacts/{artifact_key}")
async def visual_signature_artifact(request: Request, artifact_key: str):
    payload = artifact_file_response_payload(artifact_key)
    if payload is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"visual signature artifact {artifact_key}"},
            status_code=404,
        )
    path, media_type = payload
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/visual-signature/screenshots/{filename}/preview")
async def visual_signature_screenshot_preview(request: Request, filename: str):
    model = build_screenshot_preview_model(filename)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"visual signature screenshot preview {filename}"},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "visual_signature_screenshot_preview.html.j2",
        {"model": model},
    )


@router.get("/visual-signature/screenshots/{filename:path}")
async def visual_signature_screenshot(request: Request, filename: str):
    payload = screenshot_file_response_payload(filename)
    if payload is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"visual signature screenshot {filename}"},
            status_code=404,
        )
    path, media_type = payload
    return FileResponse(path, media_type=media_type)


def _render(request: Request, section: str):
    return templates.TemplateResponse(
        request,
        "visual_signature.html.j2",
        {"model": build_visual_signature_model(section)},
    )


def _render_human_review(request: Request, brand: str | None):
    model = build_human_review_model(brand)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": "visual signature human review evidence"},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "visual_signature_human_review.html.j2",
        {"model": model},
    )
