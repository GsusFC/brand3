"""Internal scanner stability audit route."""

from __future__ import annotations

import asyncio
import secrets
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from src.config import BRAND3_DB_PATH
from src.services.scanner_stability_audit import (
    StabilityAuditOptions,
    analyze_scanner_stability,
    render_stability_markdown,
)

from ..config import settings

router = APIRouter()


@router.get("/internal/scanner-stability-audit", response_model=None)
async def scanner_stability_audit(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    version: str = Query(""),
    min_repeats: int = Query(2, ge=2, le=20),
    limit_groups: int = Query(20, ge=1, le=50),
    group_by_day: bool = Query(False),
    full: bool = Query(False),
    format: Literal["json", "md"] = Query("json"),
):
    _require_team_token(request)
    report = await asyncio.to_thread(
        analyze_scanner_stability,
        BRAND3_DB_PATH,
        options=StabilityAuditOptions(
            min_repeats=min_repeats,
            days=days,
            version=version or None,
            limit_groups=limit_groups,
            group_by_day=group_by_day,
        ),
    )
    if not full:
        report = _compact_report(report)
    if format == "md":
        return PlainTextResponse(render_stability_markdown(report))
    return report


def _require_team_token(request: Request) -> None:
    expected = settings.team_token.strip()
    if not expected:
        raise HTTPException(status_code=503, detail="team access not configured")
    supplied = request.headers.get("x-brand3-team-token", "").strip()
    if not supplied:
        scheme, _, value = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() == "bearer":
            supplied = value.strip()
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="team access required")


def _compact_report(report: dict) -> dict:
    compact = dict(report)
    compact["groups"] = [_compact_group(group) for group in report.get("groups") or []]
    return compact


def _compact_group(group: dict) -> dict:
    item = dict(group)
    examples = item.pop("examples", []) or []
    item["example_scan_ids"] = [example.get("scan_id") for example in examples[:5]]
    return item
