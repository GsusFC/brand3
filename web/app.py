"""FastAPI entrypoint for the Brand3 web app."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .logging_setup import access_log_middleware, configure_logging
from .middleware.rate_limit import rate_limit_middleware
from .routes import (
    analyze, brand, health, index, magnetism_scanner, report, reports_list, status, takedown, team,
    visual_signature,
)
from .storage import ensure_schema
from .templates_env import templates
from .workers.queue import get_queue

configure_logging()

log = logging.getLogger("brand3.web")

_STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_schema()
    queue = get_queue()
    await queue.start()
    log.info(
        "brand3.web starting — env=%s base_url=%s workers=%d",
        settings.environment,
        settings.base_url,
        queue.max_concurrent,
    )
    try:
        yield
    finally:
        await queue.stop()
        log.info("brand3.web shutting down")


app = FastAPI(
    title="Brand3",
    description="Public brand health scorer — FLOC",
    version="0.1.0",
    lifespan=lifespan,
)

app.middleware("http")(rate_limit_middleware)
app.middleware("http")(access_log_middleware)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

for module in (index, analyze, status, report, reports_list, brand, team, takedown, health, visual_signature, magnetism_scanner):
    app.include_router(module.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> HTMLResponse:
    if exc.status_code == 404:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": request.url.path},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "error.html.j2",
        {
            "status_code": exc.status_code,
            "error": exc.detail or "request failed",
        },
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> HTMLResponse:
    log.exception("unhandled error on %s", request.url.path)
    return templates.TemplateResponse(
        request,
        "error.html.j2",
        {
            "status_code": 500,
            "error": "internal server error",
        },
        status_code=500,
    )
