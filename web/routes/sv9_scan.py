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

    def _next_rung(key: str, component: dict) -> dict | None:
        """First rung not yet earned: the diagnosis line the TLDR cannot give."""
        spec = COMPONENTS[key]
        score = int(component.get("score") or 0)
        if component.get("status") == "not_evaluated" or score >= spec["scale"]:
            return None
        rung = spec["ladder"][score]  # ladder is 0-indexed; rung score+1
        return {"rung": rung["rung"], "criterion": rung["criterion"]}

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
            "message": component.get("message") or "",
            "is_chip": key in ("attributes", "values"),
            "next_rung": _next_rung(key, component),
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
            "magnetism_scan_id": _magnetism_scan_id(scan.get("source_run_id")),
            "ui_lang": "es",
        },
    )


def _magnetism_scan_id(source_run_id: int | None) -> int | None:
    """Latest scanner entry for the same audit run, to link back into the flow."""
    if not source_run_id:
        return None
    store = Sv9Store(BRAND3_DB_PATH)
    try:
        row = store.conn.execute(
            """
            SELECT id FROM magnetism_scans
            WHERE source_run_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (source_run_id,),
        ).fetchone()
        return int(row["id"]) if row else None
    except Exception:
        return None
    finally:
        store.close()
