"""GET /_health — lightweight JSON probe for Fly health checks."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..workers.queue import get_queue

router = APIRouter()


@router.get("/_health", include_in_schema=False)
async def health() -> JSONResponse:
    stats = get_queue().stats()
    payload = {
        "status": "ok",
        "queue_size": stats.queued,
        "running": stats.running,
    }
    # Fly health checks should reflect process liveness, not internal DB state.
    return JSONResponse(payload, status_code=200)
