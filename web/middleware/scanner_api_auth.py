"""Authentication gate for the Scanner API routes."""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from ..config import settings

SCANNER_API_PREFIX = "/api/v1/scanner"


def scanner_api_error_response(
    status_code: int,
    *,
    code: str,
    message: str,
    status: dict | None = None,
) -> JSONResponse:
    error: dict = {"code": code, "message": message}
    if status is not None:
        error["status"] = status
    return JSONResponse({"error": error}, status_code=status_code)


def scanner_api_auth_error(request: Request) -> JSONResponse | None:
    token = settings.scanner_api_token.strip()
    if not token:
        return scanner_api_error_response(
            503,
            code="scanner_api_not_configured",
            message="Scanner API token is not configured.",
        )

    authorization = request.headers.get("authorization", "")
    supplied = ""
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        supplied = value.strip()
    else:
        supplied = request.headers.get("x-brand3-scanner-key", "").strip()

    if not supplied or not secrets.compare_digest(supplied, token):
        return scanner_api_error_response(
            401,
            code="scanner_api_unauthorized",
            message="Missing or invalid Scanner API token.",
        )
    return None


async def scanner_api_auth_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.url.path == SCANNER_API_PREFIX or request.url.path.startswith(f"{SCANNER_API_PREFIX}/"):
        auth_error = scanner_api_auth_error(request)
        if auth_error is not None:
            return auth_error
    return await call_next(request)
