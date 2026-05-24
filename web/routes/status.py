"""GET /r/{token}/status — polling page for in-flight analyses."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ..storage import get_request
from ..templates_env import templates

router = APIRouter()

_PHASES = [
    ("queued", "Queued"),
    ("collecting", "Collecting public evidence"),
    ("extracting", "Extracting signals"),
    ("scoring", "Scoring dimensions"),
    ("finalizing", "Writing report"),
]

_PHASE_LABELS = {
    **{key: label for key, label in _PHASES},
    "ready": "Report ready",
    "failed": "Analysis failed",
}


@router.get("/r/{token}/status")
async def analysis_status(request: Request, token: str):
    row = get_request(token)
    if row is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"request {token}"},
            status_code=404,
        )
    if row["status"] == "ready":
        return RedirectResponse(f"/r/{token}", status_code=303)

    return templates.TemplateResponse(
        request,
        "status.html.j2",
        {
            "token": token,
            "brand_slug": row["brand_slug"],
            "status": row["status"],
            "elapsed_seconds": _elapsed(row["started_at"]),
            "elapsed_label": _elapsed_label(_elapsed(row["started_at"])),
            "error_message": row["error_message"],
            "phase": _phase(row),
            "phase_label": _PHASE_LABELS.get(_phase(row), "Working"),
            "phase_steps": _phase_steps(_phase(row), row["status"]),
        },
    )


def _elapsed(started_at: str | None) -> int:
    if not started_at:
        return 0
    try:
        dt = datetime.fromisoformat(started_at.replace(" ", "T"))
    except ValueError:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))


def _elapsed_label(seconds: int) -> str:
    minutes, rest = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{rest:02d}"


def _phase(row: dict) -> str:
    phase = row.get("phase") or row.get("status") or "queued"
    if row.get("status") == "queued":
        return "queued"
    if row.get("status") == "failed":
        return "failed"
    if row.get("status") == "ready":
        return "ready"
    return str(phase)


def _phase_steps(current_phase: str, status: str) -> list[dict]:
    if status == "failed":
        current_phase = "failed"
    if status == "ready":
        current_phase = "ready"

    current_index = next(
        (idx for idx, (key, _label) in enumerate(_PHASES) if key == current_phase),
        -1,
    )
    steps = []
    for idx, (key, label) in enumerate(_PHASES):
        if current_phase == "ready" or (current_index >= 0 and idx < current_index):
            state = "done"
        elif key == current_phase:
            state = "active"
        elif current_phase == "failed" and current_index >= 0 and idx == current_index:
            state = "failed"
        else:
            state = "pending"
        steps.append({"key": key, "label": label, "state": state})
    if current_phase == "failed":
        steps.append({"key": "failed", "label": "Analysis failed", "state": "failed"})
    if current_phase == "ready":
        steps.append({"key": "ready", "label": "Report ready", "state": "done"})
    return steps
