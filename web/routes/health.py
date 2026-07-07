"""GET /_health — lightweight JSON probe for Fly health checks."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..workers.queue import get_queue

router = APIRouter()

_WARN_FREE_RATIO = 0.10
_CRITICAL_FREE_RATIO = 0.03


def _data_volume_path() -> Path:
    db_path = os.getenv("BRAND3_DB_PATH")
    if db_path:
        return Path(db_path).expanduser().parent
    return Path("/data")


def _disk_health(path: Path) -> dict[str, object]:
    try:
        usage = shutil.disk_usage(path)
    except OSError as exc:
        return {
            "path": str(path),
            "status": "unavailable",
            "error": exc.__class__.__name__,
        }

    free_ratio = usage.free / usage.total if usage.total else 0.0
    if free_ratio <= _CRITICAL_FREE_RATIO:
        status = "critical"
    elif free_ratio <= _WARN_FREE_RATIO:
        status = "warning"
    else:
        status = "ok"
    return {
        "path": str(path),
        "status": status,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "free_ratio": round(free_ratio, 4),
    }


@router.get("/_health", include_in_schema=False)
async def health() -> JSONResponse:
    stats = get_queue().stats()
    payload = {
        "status": "ok",
        "queue_size": stats.queued,
        "running": stats.running,
        "disk": _disk_health(_data_volume_path()),
    }
    # Fly health checks should reflect process liveness, not internal DB state.
    return JSONResponse(payload, status_code=200)
