"""Local web viewer for Visual Signature annotation review."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles


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
SUPPORTED_LANGS = {"en", "es"}

TRANSLATIONS = {
    "en": {
        "title": "visual signature annotation review",
        "intro": "Offline reviewer queue for screenshot-backed annotation calibration. Evidence-only; no scoring impact.",
        "review_sample": "review_sample",
        "cases": "cases",
        "brand": "brand",
        "category": "category",
        "reason": "reason",
        "confidence": "confidence",
        "status": "status",
        "reviewed": "reviewed",
        "pending": "pending",
        "case": "case",
        "url": "url",
        "sample": "sample",
        "annotation": "annotation",
        "review_saved": "review saved for this case.",
        "viewport_screenshot": "viewport_screenshot",
        "viewport_target": "1440x900 target",
        "quick_review": "quick_review",
        "local_save": "local JSON save",
        "annotation_targets": "annotation_targets",
        "target": "target",
        "label": "label",
        "conf": "conf",
        "evidence": "evidence",
        "limitations": "limitations",
        "back": "back to sample",
        "reviewer_id": "reviewer_id",
        "visually_supported": "visually_supported",
        "useful": "useful",
        "useful_value": "useful",
        "hallucination_or_overreach": "hallucination_or_overreach",
        "most_reliable_target": "most_reliable_target",
        "most_confusing_target": "most_confusing_target",
        "adds_value_beyond_heuristics": "adds_value_beyond_heuristics",
        "reviewer_notes": "reviewer_notes",
        "notes_placeholder": "Evidence-based note...",
        "save_review": "save review",
        "tool": "tool",
        "boundary": "boundary",
        "tool_name": "visual signature annotation review",
        "boundary_text": "offline evidence-only · no scoring impact",
        "language": "language",
        "yes": "yes",
        "partial": "partial",
        "no": "no",
        "neutral": "neutral",
        "not_useful": "not_useful",
        "unsure": "unsure",
        "targets_tag": "labels · evidence · limitations",
        "screenshot_alt": "Viewport screenshot for",
    },
    "es": {
        "title": "revisión de anotaciones de Visual Signature",
        "intro": "Cola local de revisión para calibrar anotaciones con captura de pantalla. Solo evidencia; sin impacto en scoring.",
        "review_sample": "muestra_revision",
        "cases": "casos",
        "brand": "marca",
        "category": "categoría",
        "reason": "motivo",
        "confidence": "confianza",
        "status": "estado",
        "reviewed": "revisado",
        "pending": "pendiente",
        "case": "caso",
        "url": "url",
        "sample": "muestra",
        "annotation": "anotación",
        "review_saved": "revisión guardada para este caso.",
        "viewport_screenshot": "captura_viewport",
        "viewport_target": "objetivo 1440x900",
        "quick_review": "revision_rapida",
        "local_save": "guardado JSON local",
        "annotation_targets": "objetivos_anotacion",
        "target": "objetivo",
        "label": "etiqueta",
        "conf": "conf",
        "evidence": "evidencia",
        "limitations": "limitaciones",
        "back": "volver a la muestra",
        "reviewer_id": "reviewer_id",
        "visually_supported": "soporte_visual",
        "useful": "utilidad",
        "useful_value": "útil",
        "hallucination_or_overreach": "alucinacion_o_exceso",
        "most_reliable_target": "objetivo_mas_fiable",
        "most_confusing_target": "objetivo_mas_confuso",
        "adds_value_beyond_heuristics": "aporta_valor_sobre_heuristicas",
        "reviewer_notes": "notas_revisor",
        "notes_placeholder": "Nota basada en evidencia...",
        "save_review": "guardar revisión",
        "tool": "herramienta",
        "boundary": "límite",
        "tool_name": "revisión de anotaciones visual signature",
        "boundary_text": "solo evidencia offline · sin impacto en scoring",
        "language": "idioma",
        "yes": "sí",
        "partial": "parcial",
        "no": "no",
        "neutral": "neutral",
        "not_useful": "no_útil",
        "unsure": "no_seguro",
        "targets_tag": "etiquetas · evidencia · limitaciones",
        "screenshot_alt": "Captura viewport de",
    },
}

TARGET_LABELS = {
    "es": {
        "logo_prominence": "prominencia_logo",
        "imagery_style": "estilo_imagenes",
        "product_presence": "presencia_producto",
        "human_presence": "presencia_humana",
        "template_likeness": "parecido_template",
        "visual_distinctiveness": "distintividad_visual",
        "category_fit": "encaje_categoria",
        "perceived_polish": "pulido_percibido",
        "category_cues": "senales_categoria",
    }
}


@dataclass(frozen=True)
class ReviewViewerCase:
    annotation_id: str
    index: int
    total: int
    brand_name: str
    website_url: str
    expected_category: str
    sampling_reasons: list[str]
    annotation_path: str
    screenshot_path: str | None
    annotation_status: str
    annotation_confidence: float | None
    targets: dict[str, dict[str, Any]]


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
        cases = load_review_cases(request.app.state.sample_path)
        records = load_viewer_review_records(request.app.state.review_records_path)
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
        cases = load_review_cases(request.app.state.sample_path)
        case = _case_by_id(cases, annotation_id)
        if case is None:
            raise HTTPException(status_code=404, detail="review case not found")
        existing = latest_review_for_case(request.app.state.review_records_path, annotation_id)
        return HTMLResponse(_page(title=f"review {case.brand_name}", body=_case_body(case, existing, language), lang=language))

    @app.get("/case/{annotation_id}/screenshot")
    async def screenshot(request: Request, annotation_id: str) -> Response:
        cases = load_review_cases(request.app.state.sample_path)
        case = _case_by_id(cases, annotation_id)
        if case is None or not case.screenshot_path:
            raise HTTPException(status_code=404, detail="screenshot not found")
        path = Path(case.screenshot_path)
        if not path.exists() or path.suffix.lower() != ".png":
            raise HTTPException(status_code=404, detail="screenshot missing")
        return Response(path.read_bytes(), media_type="image/png")

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
        cases = load_review_cases(request.app.state.sample_path)
        case = _case_by_id(cases, annotation_id)
        if case is None:
            raise HTTPException(status_code=404, detail="review case not found")
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
        append_viewer_review_record(request.app.state.review_records_path, record)
        return RedirectResponse(f"/case/{annotation_id}?saved=1&lang={language}", status_code=303)

    return app


def load_review_cases(sample_path: str | Path) -> list[ReviewViewerCase]:
    sample = _load_json(Path(sample_path))
    items = sample.get("items")
    if not isinstance(items, list):
        raise ValueError("review_sample.json must contain an items list")
    cases: list[ReviewViewerCase] = []
    total = len(items)
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        annotation_path = Path(str(item.get("annotation_path") or ""))
        payload = _load_json(annotation_path)
        annotations = payload.get("annotations") if isinstance(payload.get("annotations"), dict) else {}
        targets = annotations.get("targets") if isinstance(annotations.get("targets"), dict) else {}
        screenshot_path = _screenshot_path(payload)
        cases.append(
            ReviewViewerCase(
                annotation_id=str(item.get("annotation_id") or annotation_path.stem),
                index=index,
                total=total,
                brand_name=str(item.get("brand_name") or payload.get("brand_name") or ""),
                website_url=str(item.get("website_url") or payload.get("website_url") or ""),
                expected_category=str(item.get("expected_category") or _expected_category(payload) or ""),
                sampling_reasons=[str(reason) for reason in item.get("sampling_reasons") or []],
                annotation_path=str(annotation_path),
                screenshot_path=screenshot_path,
                annotation_status=str(annotations.get("status") or item.get("annotation_status") or ""),
                annotation_confidence=_float_or_none(
                    (annotations.get("overall_confidence") or {}).get("score")
                    if isinstance(annotations.get("overall_confidence"), dict)
                    else item.get("annotation_confidence")
                ),
                targets={str(key): dict(value) for key, value in targets.items() if isinstance(value, dict)},
            )
        )
    return cases


def load_viewer_review_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    payload = _load_json(source)
    rows = payload.get("viewer_records") or payload.get("records") or []
    return [dict(row) for row in rows if isinstance(row, dict)]


def latest_review_for_case(path: str | Path, annotation_id: str) -> dict[str, Any] | None:
    matches = [record for record in load_viewer_review_records(path) if record.get("annotation_id") == annotation_id]
    return matches[-1] if matches else None


def build_viewer_review_record(
    case: ReviewViewerCase,
    *,
    reviewer_id: str,
    visually_supported: str,
    useful: str,
    hallucination_or_overreach: str,
    most_reliable_target: str,
    most_confusing_target: str,
    adds_value_beyond_heuristics: str,
    reviewer_notes: str,
) -> dict[str, Any]:
    _validate_choice(visually_supported, {"yes", "partial", "no"}, "visually_supported")
    _validate_choice(useful, {"useful", "neutral", "not_useful"}, "useful")
    _validate_choice(hallucination_or_overreach, {"no", "yes"}, "hallucination_or_overreach")
    _validate_choice(adds_value_beyond_heuristics, {"yes", "no", "unsure"}, "adds_value_beyond_heuristics")
    return {
        "schema_version": "visual-signature-viewer-review-record-1",
        "reviewer_id": reviewer_id.strip() or "local_reviewer",
        "annotation_id": case.annotation_id,
        "brand_name": case.brand_name,
        "website_url": case.website_url,
        "expected_category": case.expected_category,
        "annotation_path": case.annotation_path,
        "screenshot_path": case.screenshot_path,
        "reviewed_at": datetime.now().isoformat(),
        "visually_supported": visually_supported,
        "useful": useful,
        "hallucination_or_overreach": hallucination_or_overreach,
        "most_reliable_target": most_reliable_target,
        "most_confusing_target": most_confusing_target,
        "adds_value_beyond_heuristics": adds_value_beyond_heuristics,
        "reviewer_notes": reviewer_notes.strip(),
    }


def append_viewer_review_record(path: str | Path, record: dict[str, Any]) -> None:
    destination = Path(path)
    rows = load_viewer_review_records(destination)
    rows.append(record)
    payload = {
        "schema_version": "visual-signature-viewer-review-records-1",
        "updated_at": datetime.now().isoformat(),
        "viewer_records": rows,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _index_body(cases: list[ReviewViewerCase], reviewed: set[Any], lang: str) -> str:
    rows = []
    for case in cases:
        status = _t(lang, "reviewed") if case.annotation_id in reviewed else _t(lang, "pending")
        rows.append(
            "<tr>"
            f"<td>{case.index}</td>"
            f"<td><a href=\"/case/{_esc(case.annotation_id)}?lang={lang}\">{_esc(case.brand_name)}</a></td>"
            f"<td>{_esc(case.expected_category)}</td>"
            f"<td>{_esc(', '.join(case.sampling_reasons) or '-')}</td>"
            f"<td class=\"num\">{_num(case.annotation_confidence)}</td>"
            f"<td>{status}</td>"
            "</tr>"
        )
    return (
        "<section>"
        f"{_language_selector(lang, '/')}"
        f"<h1 class=\"page-title\">{_esc(_t(lang, 'title'))}</h1>"
        f"<p class=\"prose dim intro-copy\">{_esc(_t(lang, 'intro'))}</p>"
        "</section><hr class=\"rule-thin\"><section>"
        f"<div class=\"section-head\"><span class=\"label\">{_esc(_t(lang, 'review_sample'))}</span>"
        f"<span class=\"tag\">// {len(cases)} {_esc(_t(lang, 'cases'))}</span></div>"
        f"<div class=\"table-wrap\"><table><thead><tr><th>#</th><th>{_esc(_t(lang, 'brand'))}</th><th>{_esc(_t(lang, 'category'))}</th><th>{_esc(_t(lang, 'reason'))}</th><th class=\"num\">{_esc(_t(lang, 'confidence'))}</th><th>{_esc(_t(lang, 'status'))}</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div></section>"
    )


def _case_body(case: ReviewViewerCase, existing: dict[str, Any] | None, lang: str) -> str:
    target_rows = []
    options = "".join(f"<option value=\"{_esc(target)}\">{_esc(_target_label(lang, target))}</option>" for target in case.targets)
    for target, value in case.targets.items():
        target_rows.append(
            "<tr>"
            f"<td>{_esc(_target_label(lang, target))}</td>"
            f"<td>{_esc(value.get('label'))}</td>"
            f"<td class=\"num\">{_num(value.get('confidence'))}</td>"
            f"<td>{_list(value.get('evidence'))}</td>"
            f"<td>{_list(value.get('limitations'))}</td>"
            "</tr>"
        )
    saved_note = f"<p class=\"small hl-ok\">{_esc(_t(lang, 'review_saved'))}</p>" if existing else ""
    return (
        "<section>"
        f"{_language_selector(lang, f'/case/{case.annotation_id}')}"
        f"<div class=\"section-head\"><span class=\"label\">{_esc(_t(lang, 'case'))} {case.index}/{case.total}</span><span class=\"tag\">// {_esc(case.annotation_id)}</span></div>"
        f"<h1 class=\"page-title\">{_esc(case.brand_name)}</h1>"
        f"<div class=\"kv\"><span class=\"k\">{_esc(_t(lang, 'url'))}</span><span class=\"v\"><a href=\"{_esc(case.website_url)}\">{_esc(case.website_url)}</a></span>"
        f"<span class=\"k\">{_esc(_t(lang, 'category'))}</span><span class=\"v\">{_esc(case.expected_category)}</span>"
        f"<span class=\"k\">{_esc(_t(lang, 'sample'))}</span><span class=\"v\">{_esc(', '.join(case.sampling_reasons) or '-')}</span>"
        f"<span class=\"k\">{_esc(_t(lang, 'annotation'))}</span><span class=\"v\">{_esc(case.annotation_status)} · {_esc(_t(lang, 'confidence'))} {_num(case.annotation_confidence)}</span></div>"
        f"{saved_note}"
        "</section><hr class=\"rule-thin\"><section>"
        "<div class=\"review-grid\">"
        "<div>"
        f"<div class=\"section-head\"><span class=\"label\">{_esc(_t(lang, 'viewport_screenshot'))}</span><span class=\"tag\">// {_esc(_t(lang, 'viewport_target'))}</span></div>"
        f"<div class=\"screenshot-frame\"><img src=\"/case/{_esc(case.annotation_id)}/screenshot\" alt=\"{_esc(_t(lang, 'screenshot_alt'))} {_esc(case.brand_name)}\"></div>"
        "</div><div>"
        f"<div class=\"section-head\"><span class=\"label\">{_esc(_t(lang, 'quick_review'))}</span><span class=\"tag\">// {_esc(_t(lang, 'local_save'))}</span></div>"
        f"{_review_form(case, options, lang)}"
        "</div></div>"
        "</section><hr class=\"rule-thin\"><section>"
        f"<div class=\"section-head\"><span class=\"label\">{_esc(_t(lang, 'annotation_targets'))}</span><span class=\"tag\">// {_esc(_t(lang, 'targets_tag'))}</span></div>"
        f"<div class=\"table-wrap\"><table><thead><tr><th>{_esc(_t(lang, 'target'))}</th><th>{_esc(_t(lang, 'label'))}</th><th class=\"num\">{_esc(_t(lang, 'conf'))}</th><th>{_esc(_t(lang, 'evidence'))}</th><th>{_esc(_t(lang, 'limitations'))}</th></tr></thead><tbody>"
        + "".join(target_rows)
        + "</tbody></table></div>"
        f"<p class=\"small block-note\"><a href=\"/?lang={lang}\">← {_esc(_t(lang, 'back'))}</a></p>"
        "</section>"
    )


def _review_form(case: ReviewViewerCase, target_options: str, lang: str) -> str:
    return (
        f"<form action=\"/case/{_esc(case.annotation_id)}/review\" method=\"post\" class=\"review-form\">"
        f"<input type=\"hidden\" name=\"lang\" value=\"{lang}\">"
        f"<label>{_esc(_t(lang, 'reviewer_id'))}<input type=\"text\" name=\"reviewer_id\" value=\"local_reviewer\"></label>"
        f"<label>{_esc(_t(lang, 'visually_supported'))}<select name=\"visually_supported\"><option value=\"yes\">{_esc(_t(lang, 'yes'))}</option><option value=\"partial\">{_esc(_t(lang, 'partial'))}</option><option value=\"no\">{_esc(_t(lang, 'no'))}</option></select></label>"
        f"<label>{_esc(_t(lang, 'useful'))}<select name=\"useful\"><option value=\"useful\">{_esc(_t(lang, 'useful_value'))}</option><option value=\"neutral\">{_esc(_t(lang, 'neutral'))}</option><option value=\"not_useful\">{_esc(_t(lang, 'not_useful'))}</option></select></label>"
        f"<label>{_esc(_t(lang, 'hallucination_or_overreach'))}<select name=\"hallucination_or_overreach\"><option value=\"no\">{_esc(_t(lang, 'no'))}</option><option value=\"yes\">{_esc(_t(lang, 'yes'))}</option></select></label>"
        f"<label>{_esc(_t(lang, 'most_reliable_target'))}<select name=\"most_reliable_target\"><option value=\"\">-</option>{target_options}</select></label>"
        f"<label>{_esc(_t(lang, 'most_confusing_target'))}<select name=\"most_confusing_target\"><option value=\"\">-</option>{target_options}</select></label>"
        f"<label>{_esc(_t(lang, 'adds_value_beyond_heuristics'))}<select name=\"adds_value_beyond_heuristics\"><option value=\"yes\">{_esc(_t(lang, 'yes'))}</option><option value=\"no\">{_esc(_t(lang, 'no'))}</option><option value=\"unsure\">{_esc(_t(lang, 'unsure'))}</option></select></label>"
        f"<label class=\"review-notes\">{_esc(_t(lang, 'reviewer_notes'))}<textarea name=\"reviewer_notes\" rows=\"6\" placeholder=\"{_esc(_t(lang, 'notes_placeholder'))}\"></textarea></label>"
        f"<button type=\"submit\">{_esc(_t(lang, 'save_review'))}</button>"
        "</form>"
    )


def _page(*, title: str, body: str, lang: str) -> str:
    return (
        f"<!DOCTYPE html><html lang=\"{lang}\"><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>Brand3 — {_esc(title)}</title>"
        "<link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/favicon.svg\">"
        "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
        "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>"
        "<link rel=\"stylesheet\" href=\"/static/main.css?v=visual-signature-review-viewer\">"
        f"<style>{_viewer_css()}</style>"
        "</head><body><div class=\"page\">"
        "<pre class=\"term-head\"><span class=\"prompt\">❯</span> brand3 <span class=\"hl-accent\">--mode</span> visual-signature-review <span class=\"dim\">· local offline</span></pre>"
        "<hr class=\"rule\">"
        f"{body}"
        f"<hr class=\"rule\"><footer class=\"footer\"><div class=\"kv\"><span class=\"k\">{_esc(_t(lang, 'tool'))}</span><span class=\"v\">{_esc(_t(lang, 'tool_name'))}</span><span class=\"k\">{_esc(_t(lang, 'boundary'))}</span><span class=\"v\">{_esc(_t(lang, 'boundary_text'))}</span></div><div class=\"footer-cursor\"><span class=\"prompt\">❯</span> _<span class=\"cursor\"></span></div></footer>"
        "</div></body></html>"
    )


def _viewer_css() -> str:
    return """
.review-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(340px, 0.75fr);
  gap: 24px;
}
.screenshot-frame {
  border: 1px solid var(--border);
  background: var(--surface-2);
  padding: 10px;
}
.screenshot-frame img {
  display: block;
  width: 100%;
  height: auto;
  border: 1px solid var(--border);
}
.review-form {
  display: grid;
  gap: 10px;
}
.review-form label {
  display: grid;
  gap: 4px;
  color: var(--text-muted);
  font-size: 11px;
  text-transform: uppercase;
}
.review-form input,
.review-form select,
.review-form textarea {
  width: 100%;
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 0;
  padding: 9px 10px;
  font-family: var(--font-mono);
  font-size: 12px;
  text-transform: none;
}
.review-form textarea { resize: vertical; }
.review-form button {
  min-height: 42px;
  background: var(--text);
  color: #f5f5f5;
  border: 1px solid var(--text);
  border-radius: 0;
  padding: 10px 18px;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  cursor: pointer;
}
.review-form button:hover {
  background: var(--accent);
  border-color: var(--accent);
}
.language-switch {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-bottom: 14px;
  color: var(--text-muted);
  font-size: 12px;
}
.language-switch a {
  text-transform: uppercase;
}
.language-switch a.is-active {
  color: var(--accent);
  text-decoration-color: var(--accent);
}
@media (max-width: 980px) {
  .review-grid { grid-template-columns: 1fr; }
}
"""


def _language(value: str) -> str:
    lang = str(value or "en").strip().lower()
    return lang if lang in SUPPORTED_LANGS else "en"


def _t(lang: str, key: str) -> str:
    language = _language(lang)
    return TRANSLATIONS[language].get(key) or TRANSLATIONS["en"].get(key) or key


def _target_label(lang: str, target: str) -> str:
    return TARGET_LABELS.get(_language(lang), {}).get(target, target)


def _language_selector(lang: str, base_path: str) -> str:
    current = _language(lang)
    en_class = " class=\"is-active\"" if current == "en" else ""
    es_class = " class=\"is-active\"" if current == "es" else ""
    return (
        "<div class=\"language-switch\">"
        f"<span>{_esc(_t(current, 'language'))}</span>"
        f"<a{en_class} href=\"{_esc(base_path)}?lang=en\">en</a>"
        f"<a{es_class} href=\"{_esc(base_path)}?lang=es\">es</a>"
        "</div>"
    )


def _case_by_id(cases: list[ReviewViewerCase], annotation_id: str) -> ReviewViewerCase | None:
    return next((case for case in cases if case.annotation_id == annotation_id), None)


def _screenshot_path(payload: dict[str, Any]) -> str | None:
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    screenshot = vision.get("screenshot") if isinstance(vision.get("screenshot"), dict) else {}
    path = screenshot.get("path")
    return str(path) if path else None


def _expected_category(payload: dict[str, Any]) -> str | None:
    calibration = payload.get("calibration") if isinstance(payload.get("calibration"), dict) else {}
    value = calibration.get("expected_category") or payload.get("category")
    return str(value) if value else None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _validate_choice(value: str, allowed: set[str], field: str) -> None:
    if value not in allowed:
        raise ValueError(f"{field} must be one of {sorted(allowed)}")


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _num(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "-"


def _list(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "-"
    return "<br>".join(_esc(str(item)) for item in value)


def _esc(value: Any) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
