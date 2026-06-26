"""Local web viewer for Visual Signature annotation review."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .viewer_data_support import ReviewViewerCase
from .viewer_data_support import _case_by_id
from .viewer_data_support import _safe_path_under_root
from .viewer_data_support import _screenshot_root
from .viewer_data_support import append_viewer_review_record
from .viewer_data_support import build_viewer_review_record
from .viewer_data_support import latest_review_for_case
from .viewer_data_support import load_review_cases
from .viewer_data_support import load_viewer_review_records
from .viewer_render_support import _case_body
from .viewer_render_support import _index_body
from .viewer_render_support import _language
from .viewer_render_support import _page
from .viewer_render_support import _t


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_REVIEW_ROOT = (
    PROJECT_ROOT
    / "examples"
    / "visual_signature"
    / "calibration_corpus"
    / "annotations"
    / "multimodal"
    / "review"
)
DEFAULT_SAMPLE_PATH = DEFAULT_REVIEW_ROOT / "review_sample.json"
DEFAULT_RECORDS_PATH = DEFAULT_REVIEW_ROOT / "review_records.json"
WEB_STATIC_DIR = PROJECT_ROOT / "web" / "static"


def create_review_viewer_app(
    *,
    sample_path: str | Path = DEFAULT_SAMPLE_PATH,
    review_records_path: str | Path = DEFAULT_RECORDS_PATH,
) -> FastAPI:
    app = FastAPI(
        title="Brand3 Visual Signature Review Viewer",
        description="Local/offline annotation review tool.",
        version="0.1.0",
    )
    app.state.sample_path = Path(sample_path)
    app.state.review_records_path = Path(review_records_path)
    app.mount("/static", StaticFiles(directory=str(WEB_STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request, lang: str = "en") -> HTMLResponse:
        language = _language(lang)
        cases, records = await asyncio.to_thread(
            _load_index_data,
            request.app.state.sample_path,
            request.app.state.review_records_path,
        )
        reviewed = {record.get("annotation_id") for record in records}
        return HTMLResponse(
            _page(
                title=_t(language, "title"),
                body=_index_body(cases, reviewed, language),
                lang=language,
            )
        )

    @app.get("/case/{annotation_id}", response_class=HTMLResponse)
    async def case_detail(request: Request, annotation_id: str, lang: str = "en") -> HTMLResponse:
        language = _language(lang)
        cases, existing = await asyncio.to_thread(
            _load_case_detail_data,
            request.app.state.sample_path,
            request.app.state.review_records_path,
            annotation_id,
        )
        case = _case_by_id(cases, annotation_id)
        if case is None:
            raise HTTPException(status_code=404, detail="review case not found")
        return HTMLResponse(_page(title=f"review {case.brand_name}", body=_case_body(case, existing, language), lang=language))

    @app.get("/case/{annotation_id}/screenshot")
    async def screenshot(request: Request, annotation_id: str) -> Response:
        image = await asyncio.to_thread(_load_case_screenshot, request.app.state.sample_path, annotation_id)
        if image is None:
            raise HTTPException(status_code=404, detail="screenshot not found")
        return Response(image, media_type="image/png")

    @app.post("/case/{annotation_id}/review")
    async def save_review(
        request: Request,
        annotation_id: str,
        visually_supported: str = Form(...),
        useful: str = Form(...),
        hallucination_or_overreach: str = Form(...),
        most_reliable_target: str = Form(""),
        most_confusing_target: str = Form(""),
        adds_value_beyond_heuristics: str = Form(...),
        reviewer_notes: str = Form(""),
        reviewer_id: str = Form("local_reviewer"),
        lang: str = Form("en"),
    ) -> RedirectResponse:
        language = _language(lang)
        saved = await asyncio.to_thread(
            _save_viewer_review,
            request.app.state.sample_path,
            request.app.state.review_records_path,
            annotation_id,
            reviewer_id=reviewer_id,
            visually_supported=visually_supported,
            useful=useful,
            hallucination_or_overreach=hallucination_or_overreach,
            most_reliable_target=most_reliable_target,
            most_confusing_target=most_confusing_target,
            adds_value_beyond_heuristics=adds_value_beyond_heuristics,
            reviewer_notes=reviewer_notes,
        )
        if not saved:
            raise HTTPException(status_code=404, detail="review case not found")
        return RedirectResponse(f"/case/{annotation_id}?saved=1&lang={language}", status_code=303)

    return app


def _load_index_data(sample_path: str | Path, review_records_path: str | Path) -> tuple[list[ReviewViewerCase], list[dict[str, Any]]]:
    return load_review_cases(sample_path), load_viewer_review_records(review_records_path)


def _load_case_detail_data(
    sample_path: str | Path,
    review_records_path: str | Path,
    annotation_id: str,
) -> tuple[list[ReviewViewerCase], dict[str, Any] | None]:
    cases = load_review_cases(sample_path)
    return cases, latest_review_for_case(review_records_path, annotation_id)


def _load_case_screenshot(sample_path: str | Path, annotation_id: str) -> bytes | None:
    cases = load_review_cases(sample_path)
    case = _case_by_id(cases, annotation_id)
    if case is None or not case.screenshot_path:
        return None
    path = _safe_path_under_root(case.screenshot_path, _screenshot_root(sample_path))
    if path is None:
        return None
    if not path.exists() or path.suffix.lower() != ".png":
        return None
    return path.read_bytes()


def _save_viewer_review(
    sample_path: str | Path,
    review_records_path: str | Path,
    annotation_id: str,
    *,
    reviewer_id: str,
    visually_supported: str,
    useful: str,
    hallucination_or_overreach: str,
    most_reliable_target: str,
    most_confusing_target: str,
    adds_value_beyond_heuristics: str,
    reviewer_notes: str,
) -> bool:
    cases = load_review_cases(sample_path)
    case = _case_by_id(cases, annotation_id)
    if case is None:
        return False
    record = build_viewer_review_record(
        case,
        reviewer_id=reviewer_id,
        visually_supported=visually_supported,
        useful=useful,
        hallucination_or_overreach=hallucination_or_overreach,
        most_reliable_target=most_reliable_target,
        most_confusing_target=most_confusing_target,
        adds_value_beyond_heuristics=adds_value_beyond_heuristics,
        reviewer_notes=reviewer_notes,
    )
    append_viewer_review_record(review_records_path, record)
    return True
