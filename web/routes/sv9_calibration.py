"""Internal SV9 calibration UI (design doc section 11; briefing section 7).

Team-only, never public: lists shadow scans and captures human scores per
component into sv9_calibration_labels. Read-only over everything else — it
never mutates scans, V5 data, or any public surface.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from src.config import BRAND3_DB_PATH
from src.sv9.rubric import COMPONENTS, PRESENTATION_ORDER, RUBRIC_VERSION
from src.sv9.store import Sv9Store

from ..config import settings
from ..middleware.team_cookie import create_serializer, is_team_request
from ..templates_env import templates

router = APIRouter()


def _require_team(request: Request) -> None:
    """Team gating intentionally disabled for now (product decision,
    2026-06-11): SV9 views are open while the team iterates. To re-enable,
    restore the cookie check below.

    if not settings.team_token:
        return
    if not is_team_request(request, create_serializer(settings.cookie_secret)):
        raise HTTPException(status_code=403, detail="team access required")
    """
    return


@router.get("/sv9/calibration")
async def sv9_calibration_index(request: Request):
    _require_team(request)
    store = Sv9Store(BRAND3_DB_PATH)
    try:
        scans = store.list_scans(limit=100)
        labels = store.list_calibration_labels(limit=2000)
    finally:
        store.close()
    labels_by_scan: dict[int, int] = {}
    for label in labels:
        labels_by_scan[label["scan_id"]] = labels_by_scan.get(label["scan_id"], 0) + 1
    return templates.TemplateResponse(
        request,
        "sv9_calibration_list.html.j2",
        {
            "scans": scans,
            "labels_by_scan": labels_by_scan,
            "rubric_version": RUBRIC_VERSION,
            "ui_lang": "es",
        },
    )


@router.get("/sv9/calibration/{scan_id}")
async def sv9_calibration_detail(request: Request, scan_id: int, evaluador: str = ""):
    _require_team(request)
    store = Sv9Store(BRAND3_DB_PATH)
    try:
        scan = store.get_scan(scan_id)
        labels = [
            label
            for label in store.list_calibration_labels(limit=2000)
            if label["scan_id"] == scan_id
        ]
    finally:
        store.close()
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")

    by_component = {c["component"]: c for c in scan["components"]}
    components = []
    for key in PRESENTATION_ORDER:
        component = by_component.get(key)
        if component is None:
            continue
        spec = COMPONENTS[key]
        verdicts = {v.get("rung"): v for v in component.get("rung_profile") or []}
        ladder = [
            {
                "rung": rung["rung"],
                "criterion": rung["criterion"],
                "verdict": verdicts.get(rung["rung"]),
            }
            for rung in spec["ladder"]
        ]
        components.append(
            {
                "key": key,
                "label": spec["label"],
                "scale": spec["scale"],
                "multiplier": spec["multiplier"],
                "result": component,
                "ladder": ladder,
                "labels": [l for l in labels if l["component"] == key],
            }
        )

    return templates.TemplateResponse(
        request,
        "sv9_calibration_detail.html.j2",
        {
            "scan": scan,
            "components": components,
            "evaluador": evaluador,
            "ui_lang": "es",
        },
    )


@router.post("/sv9/calibration/{scan_id}/{component}")
async def sv9_calibration_submit(
    request: Request,
    scan_id: int,
    component: str,
    score_humano: int = Form(...),
    motivo: str = Form(""),
    flag_evidencia: bool = Form(False),
    evaluador: str = Form(...),
):
    _require_team(request)
    if component not in COMPONENTS:
        raise HTTPException(status_code=404, detail="unknown component")
    evaluador = evaluador.strip()
    if not evaluador:
        raise HTTPException(status_code=422, detail="evaluador is required")
    scale = COMPONENTS[component]["scale"]
    if not 0 <= score_humano <= scale:
        raise HTTPException(
            status_code=422, detail=f"score_humano must be between 0 and {scale}"
        )

    store = Sv9Store(BRAND3_DB_PATH)
    try:
        scan = store.get_scan(scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="scan not found")
        result = next(
            (c for c in scan["components"] if c["component"] == component), None
        )
        if result is None:
            raise HTTPException(status_code=404, detail="component not in scan")
        store.save_calibration_label(
            scan_id=scan_id,
            url=scan["url"],
            component=component,
            score_ia=int(result["score"]),
            score_humano=score_humano,
            motivo=motivo.strip() or None,
            flag_evidencia=flag_evidencia,
            evaluador=evaluador,
            rubric_version=str(scan["rubric_version"]),
        )
    finally:
        store.close()
    return RedirectResponse(
        f"/sv9/calibration/{scan_id}?evaluador={evaluador}#{component}",
        status_code=303,
    )
