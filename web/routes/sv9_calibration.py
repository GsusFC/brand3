"""Internal SV9 calibration UI (baldosas v3.1).

Team-only, never public: lists shadow scans and captures human verdicts per
tile into sv9_tile_calibration. The form operates per tile (prompt técnico
step 7): the human evaluator confirms or corrects each tile state. Read-only
over everything else — it never mutates scans, V5 data, or any public surface.

DB access is offloaded to worker threads (asyncio.to_thread) so the event loop
stays responsive, matching the rest of the web layer.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from src.config import BRAND3_DB_PATH
from src.sv9.rubric import COMPONENTS, PRESENTATION_ORDER, RUBRIC_VERSION, TILE_ESTADOS
from src.sv9.store import Sv9Store

from ..config import settings
from ..middleware.team_cookie import create_serializer, is_team_request
from ..templates_env import templates

router = APIRouter()


def _require_team(request: Request) -> None:
    """Team gating intentionally disabled for now (product decision,
    2026-06-11): SV9 read views are open while the team iterates.
    """
    return


def _require_team_write(request: Request) -> None:
    if not settings.team_token:
        return
    if not is_team_request(request, create_serializer(settings.cookie_secret)):
        raise HTTPException(status_code=403, detail="team access required")


@router.get("/sv9/calibration")
async def sv9_calibration_index(request: Request):
    _require_team(request)
    scans, labels = await asyncio.to_thread(_load_calibration_index_data)
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


def _load_calibration_index_data() -> tuple[list[dict], list[dict]]:
    store = Sv9Store(BRAND3_DB_PATH)
    try:
        return store.list_scans(limit=100), store.list_tile_calibration(limit=5000)
    finally:
        store.close()


@router.get("/sv9/calibration/{scan_id}")
async def sv9_calibration_detail(request: Request, scan_id: int, evaluador: str = ""):
    _require_team(request)
    scan, labels = await asyncio.to_thread(_load_calibration_detail_data, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")

    is_legacy = str(scan.get("rubric_version")) != RUBRIC_VERSION
    by_component = {c["component"]: c for c in scan["components"]}
    components = []
    for key in PRESENTATION_ORDER:
        component = by_component.get(key)
        if component is None:
            continue
        spec = COMPONENTS[key]
        verdicts = {str(v.get("id") or ""): v for v in component.get("tile_profile") or []}
        tiles = []
        for tile in spec["tiles"]:
            verdict = verdicts.get(tile["id"]) or {}
            tiles.append(
                {
                    "id": tile["id"],
                    "name": tile["name"],
                    "condition": tile["condition"],
                    "note": tile.get("note"),
                    "estado_ia": str(verdict.get("estado") or ""),
                    "evidencia": str(verdict.get("evidencia") or ""),
                    "motivo": str(verdict.get("motivo") or ""),
                    "contexto_requerido": str(verdict.get("contexto_requerido") or ""),
                }
            )
        components.append(
            {
                "key": key,
                "label": spec["label"],
                "scale": spec["scale"],
                "multiplier": spec["multiplier"],
                "result": component,
                "tiles": tiles,
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
            "is_legacy": is_legacy,
            "estados": list(TILE_ESTADOS),
            "ui_lang": "es",
        },
    )


def _load_calibration_detail_data(scan_id: int) -> tuple[dict | None, list[dict]]:
    store = Sv9Store(BRAND3_DB_PATH)
    try:
        scan = store.get_scan(scan_id)
        if scan is None:
            return None, []
        labels = store.list_tile_calibration(scan_id=scan_id, limit=5000)
        return scan, labels
    finally:
        store.close()


@router.post("/sv9/calibration/{scan_id}/{component}")
async def sv9_calibration_submit(request: Request, scan_id: int, component: str):
    """Persist one human verdict per tile for a component.

    The form sends, per tile, `estado__<id>` and optional `motivo__<id>`, plus a
    single `evaluador`. One sv9_tile_calibration row is written per tile so the
    agreement rate can be measured tile by tile.
    """
    _require_team_write(request)
    if component not in COMPONENTS:
        raise HTTPException(status_code=404, detail="unknown component")

    form = await request.form()
    evaluador = str(form.get("evaluador") or "").strip()
    if not evaluador:
        raise HTTPException(status_code=422, detail="evaluador is required")

    # Parse and validate per-tile inputs before offloading: request.form() is
    # async, and validation errors must surface as HTTP 422 in request context.
    tile_inputs: dict[str, tuple[str, str | None]] = {}
    for tile in COMPONENTS[component]["tiles"]:
        estado_humano = str(form.get(f"estado__{tile['id']}") or "").strip()
        if not estado_humano:
            continue
        if estado_humano not in TILE_ESTADOS:
            raise HTTPException(status_code=422, detail=f"invalid estado for {tile['id']}")
        motivo = str(form.get(f"motivo__{tile['id']}") or "").strip() or None
        tile_inputs[tile["id"]] = (estado_humano, motivo)

    await asyncio.to_thread(
        _save_tile_calibration, scan_id, component, evaluador, tile_inputs
    )
    return RedirectResponse(
        f"/sv9/calibration/{scan_id}?evaluador={evaluador}#{component}",
        status_code=303,
    )


def _save_tile_calibration(
    scan_id: int,
    component: str,
    evaluador: str,
    tile_inputs: dict[str, tuple[str, str | None]],
) -> None:
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

        ia_by_id = {
            str(v.get("id") or ""): str(v.get("estado") or "")
            for v in result.get("tile_profile") or []
        }
        for baldosa_id, (estado_humano, motivo) in tile_inputs.items():
            store.save_tile_calibration(
                scan_id=scan_id,
                url=scan["url"],
                component=component,
                baldosa_id=baldosa_id,
                estado_ia=ia_by_id.get(baldosa_id, ""),
                estado_humano=estado_humano,
                motivo=motivo,
                evaluador=evaluador,
                rubric_version=str(scan["rubric_version"]),
            )
    finally:
        store.close()
