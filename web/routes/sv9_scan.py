"""Internal SV9 scan result view: the scored TLDR canvas, shadow phase.

Team-only preview of what the public result screen becomes after the engine
is validated (design doc sections 8 and 12). Read-only.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.config import BRAND3_DB_PATH
from src.sv9.rubric import COMPONENTS, component_max_points
from src.sv9.store import Sv9Store

from ..templates_env import templates
from .sv9_calibration import _require_team

router = APIRouter()

# Canvas layout (briefing section 6): crown on top, base at the bottom,
# Coherencia as the frame connecting the boxes.
_CANVAS_ROWS = [
    ["core_purpose", "magnetism"],
    ["value_proposition", "personality", "brand_idea"],
    ["attributes", "values"],
    ["mission", "vision"],
]


@router.get("/sv9/scan/{scan_id}")
async def sv9_scan_view(request: Request, scan_id: int):
    _require_team(request)
    store = Sv9Store(BRAND3_DB_PATH)
    try:
        scan = store.get_scan(scan_id)
    finally:
        store.close()
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")

    by_component = {c["component"]: c for c in scan["components"]}

    def _box(key: str) -> dict:
        component = by_component.get(key) or {}
        spec = COMPONENTS[key]
        return {
            "key": key,
            "label": spec["label"],
            "scale": spec["scale"],
            "multiplier": spec["multiplier"],
            "max_points": component_max_points(key),
            "score": component.get("score", 0),
            "points": component.get("points", 0),
            "status": component.get("status", "not_evaluated"),
            "content": component.get("detected_content") or "",
            "is_chip": key in ("attributes", "values"),
        }

    canvas = [[_box(key) for key in row] for row in _CANVAS_ROWS]
    coherencia = _box("coherencia")
    gap = scan.get("most_painful_gap")
    gap_label = COMPONENTS[gap]["label"] if gap in COMPONENTS else None

    return templates.TemplateResponse(
        request,
        "sv9_scan.html.j2",
        {
            "scan": scan,
            "canvas": canvas,
            "coherencia": coherencia,
            "gap_label": gap_label,
            "ui_lang": "es",
        },
    )
