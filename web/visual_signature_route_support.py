"""Route helpers for the Visual Signature web views."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from fastapi import Request
from fastapi.responses import FileResponse

from .templates_env import templates


def not_found_response(request: Request, *, resource: str, lang: str):
    return templates.TemplateResponse(
        request,
        "not_found.html.j2",
        {"resource": resource, "ui_lang": lang},
        status_code=404,
    )


async def render_template(request: Request, *, template_name: str, model_builder: Callable, builder_args: tuple[Any, ...], lang: str):
    model = await asyncio.to_thread(model_builder, *builder_args)
    return templates.TemplateResponse(
        request,
        template_name,
        {"model": model, "ui_lang": lang},
    )


async def render_template_or_not_found(
    request: Request,
    *,
    template_name: str,
    model_builder: Callable,
    builder_args: tuple[Any, ...],
    lang: str,
    resource: str,
    to_thread_fn: Callable | None = None,
):
    thread_runner = to_thread_fn or asyncio.to_thread
    model = await thread_runner(model_builder, *builder_args)
    if model is None:
        return not_found_response(request, resource=resource, lang=lang)
    return templates.TemplateResponse(
        request,
        template_name,
        {"model": model, "ui_lang": lang},
    )


async def file_response_or_not_found(
    request: Request,
    *,
    payload_builder: Callable,
    payload_args: tuple[Any, ...],
    lang: str,
    resource: str,
    filename_from_path: bool = False,
    to_thread_fn: Callable | None = None,
):
    thread_runner = to_thread_fn or asyncio.to_thread
    payload = await thread_runner(payload_builder, *payload_args)
    if payload is None:
        return not_found_response(request, resource=resource, lang=lang)
    path, media_type = payload
    if filename_from_path:
        return FileResponse(path, media_type=media_type, filename=path.name)
    return FileResponse(path, media_type=media_type)
