"""Internal SV9 scan result view: the scored TLDR canvas (baldosas v3.1).

Team-only preview of what the public result screen becomes after the engine is
validated. Each component shows its grid of tiles with three visual states:
lit (encendida), off (apagada, fallo de marca) and blind spot (punto ciego,
límite del snapshot — never painted as a failure).
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from src.config import BRAND3_DB_PATH
from src.sv9.export_md import build_scan_markdown
from src.sv9.rubric import COMPONENTS, RUBRIC_VERSION, component_max_points
from src.sv9.service import materialize_sv9_scan
from src.sv9.store import Sv9Store

from ..templates_env import templates
from .magnetism_scanner import _ui
from .sv9_calibration import _require_team, _require_team_write

router = APIRouter()

_EDITORIAL_DECISIONS = {"v9", "v2", "mix", "rewrite", "reject_both"}

# Canvas layout: crown on top, base at the bottom, Coherencia as the frame
# connecting the boxes.
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
        editorial_decisions = store.list_editorial_decisions(scan_id)
        v2_blocks = _v2_reference_blocks(store, scan.get("source_run_id") if scan else None)
    finally:
        store.close()
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")

    is_legacy = str(scan.get("rubric_version")) != RUBRIC_VERSION
    by_component = {c["component"]: c for c in scan["components"]}

    def _tiles(key: str, component: dict) -> list[dict]:
        """Merge the rubric tiles with the component's verdicts for the grid."""
        spec = COMPONENTS[key]
        verdicts = {
            str(v.get("id") or ""): v for v in component.get("tile_profile") or []
        }
        tiles = []
        for tile in spec["tiles"]:
            verdict = verdicts.get(tile["id"]) or {}
            estado = str(verdict.get("estado") or "")
            tiles.append(
                {
                    "id": tile["id"],
                    "name": tile["name"],
                    "condition": tile["condition"],
                    "estado": estado,
                    "is_on": estado == "ok",
                    "is_off": estado == "no",
                    "is_blind": estado == "sin_evidencia",
                    "evidencia": str(verdict.get("evidencia") or ""),
                    "motivo": str(verdict.get("motivo") or ""),
                    "contexto_requerido": str(verdict.get("contexto_requerido") or ""),
                }
            )
        return tiles

    def _box(key: str) -> dict:
        component = by_component.get(key) or {}
        spec = COMPONENTS[key]
        status = component.get("status", "not_evaluated")
        error = component.get("error") or ""
        scored = status == "scored"
        return {
            "key": key,
            "label": spec["label"],
            "scale": spec["scale"],
            "multiplier": spec["multiplier"],
            "max_points": component_max_points(key),
            "score": component.get("score", 0),
            "points": component.get("points", 0),
            "status": status,
            "status_label": _status_label(status),
            "confidence": component.get("confidence") or "alta",
            "blind_spot_count": component.get("blind_spot_count") or 0,
            "veredicto": component.get("veredicto") or "",
            "is_technical_failure": status == "not_evaluated",
            "error": error,
            "content": component.get("detected_content") or "",
            "message": component.get("message") or "",
            "v2_reference": v2_blocks.get(key, {}),
            "editorial_decision": editorial_decisions.get(key, {}),
            "is_chip": key in ("attributes", "values"),
            "tiles": _tiles(key, component) if scored and not is_legacy else [],
        }

    canvas = [[_box(key) for key in row] for row in _CANVAS_ROWS]
    coherencia = _box("coherencia")
    flat_boxes = [box for row in canvas for box in row] + [coherencia]
    technical_failures = [box for box in flat_boxes if box["is_technical_failure"]]
    gap = scan.get("most_painful_gap")
    gap_label = COMPONENTS[gap]["label"] if gap in COMPONENTS else None

    magnetism_scan_id = _magnetism_scan_id(scan.get("source_run_id"))
    nav_model = None
    if magnetism_scan_id:
        nav_model = {
            "id": magnetism_scan_id,
            "lang_query": "?lang=es",
            "active_tab": "sv9",
            "back_href": "/",
            "t": _ui("es"),
            "sv9_scan_id": scan_id,
        }

    return templates.TemplateResponse(
        request,
        "sv9_scan.html.j2",
        {
            "scan": scan,
            "canvas": canvas,
            "coherencia": coherencia,
            "technical_failures": technical_failures,
            "gap_label": gap_label,
            "magnetism_scan_id": magnetism_scan_id,
            "model": nav_model,
            "is_legacy": is_legacy,
            "ui_lang": "es",
        },
    )


@router.get("/sv9/scan/{scan_id}/export.md")
async def sv9_scan_export(request: Request, scan_id: int):
    """Download the scan as a Brand3 .md report (work plan + pending context)."""
    _require_team(request)
    store = Sv9Store(BRAND3_DB_PATH)
    try:
        scan = store.get_scan(scan_id)
    finally:
        store.close()
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    markdown = build_scan_markdown(scan)
    filename = f"brand3-scan-{scan_id}.md"
    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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


def _v2_reference_blocks(store: Sv9Store, source_run_id: int | None) -> dict[str, dict]:
    """Persisted V2 editorial reference only; never generate it on page render."""
    if not source_run_id:
        return {}

    for payload in _magnetism_payloads_for_run(store, int(source_run_id)):
        client_v2 = payload.get("client_tldr_v2")
        if not isinstance(client_v2, dict):
            client_v2 = payload.get("client_strategic_reading")
        if not isinstance(client_v2, dict):
            continue

        blocks = _first_v2_blocks_with_text(
            client_v2.get("blocks"),
            client_v2.get("tldr_brand3_v2"),
            client_v2.get("legacy_tldr_brand3_v2"),
        )
        if not isinstance(blocks, dict):
            continue

        references: dict[str, dict] = {}
        for key in COMPONENTS:
            block = _normalize_v2_reference_block(blocks.get(key))
            references[key] = {
                "text": block["text"],
                "confidence": str(block.get("confidence") or "").strip(),
                "mode": str(block.get("mode") or block.get("claim_type") or "").strip(),
                "source": "client_tldr_v2_persisted",
            }
        return references
    return {}


def _first_v2_blocks_with_text(*candidates: object) -> dict | None:
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for value in candidate.values():
            if _normalize_v2_reference_block(value)["text"]:
                return candidate
    return None


def _normalize_v2_reference_block(value: object) -> dict[str, str]:
    if isinstance(value, str):
        return {"text": value.strip(), "confidence": "", "mode": "", "claim_type": ""}
    if not isinstance(value, dict):
        return {"text": "", "confidence": "", "mode": "", "claim_type": ""}
    text = str(value.get("text") or value.get("answer") or value.get("content") or "").strip()
    return {
        "text": text,
        "confidence": str(value.get("confidence") or "").strip(),
        "mode": str(value.get("mode") or "").strip(),
        "claim_type": str(value.get("claim_type") or "").strip(),
    }


def _magnetism_payloads_for_run(store: Sv9Store, source_run_id: int) -> list[dict]:
    try:
        rows = store.conn.execute(
            """
            SELECT raw_payload FROM magnetism_scans
            WHERE source_run_id = ?
            ORDER BY id DESC
            """,
            (source_run_id,),
        ).fetchall()
    except Exception:
        return []

    payloads: list[dict] = []
    for row in rows:
        try:
            payload = json.loads(row["raw_payload"] or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _status_label(status: str) -> str:
    return {
        "scored": "evaluado",
        "not_detected": "no detectado",
        "not_evaluated": "fallo técnico",
    }.get(status, status)


@router.post("/sv9/scan/{scan_id}/editorial-decision/{component}")
async def sv9_editorial_decision_submit(
    request: Request,
    scan_id: int,
    component: str,
    decision: str = Form(...),
    note: str = Form(""),
    evaluator: str = Form(""),
):
    _require_team_write(request)
    if component not in COMPONENTS:
        raise HTTPException(status_code=404, detail="component not found")
    if decision not in _EDITORIAL_DECISIONS:
        raise HTTPException(status_code=422, detail="invalid editorial decision")

    store = Sv9Store(BRAND3_DB_PATH)
    try:
        scan = store.get_scan(scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="scan not found")
        store.save_editorial_decision(
            scan_id=scan_id,
            component=component,
            decision=decision,
            note=note.strip() or None,
            evaluator=evaluator.strip() or None,
        )
    finally:
        store.close()
    return RedirectResponse(f"/sv9/scan/{scan_id}#sv9-card-{component}", status_code=303)


@router.post("/sv9/scan/{scan_id}/retry")
async def sv9_scan_retry(request: Request, scan_id: int):
    """Regenerate SV9 from the same persisted Brand Audit run.

    Retries create a new scan instead of mutating the failed one, so calibration
    keeps a trace of provider/API failures.
    """
    _require_team_write(request)
    store = Sv9Store(BRAND3_DB_PATH)
    try:
        scan = store.get_scan(scan_id)
    finally:
        store.close()
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    source_run_id = scan.get("source_run_id")
    if not source_run_id:
        raise HTTPException(status_code=409, detail="scan has no source_run_id")

    new_scan_id, _result = await asyncio.to_thread(
        materialize_sv9_scan,
        int(source_run_id),
        db_path=BRAND3_DB_PATH,
    )
    return RedirectResponse(f"/sv9/scan/{new_scan_id}", status_code=303)
