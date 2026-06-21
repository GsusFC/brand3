"""Persistence helper for report readiness."""

from __future__ import annotations

from typing import Any

from src.quality.publication_readiness import attach_report_publication_decision
from src.reports.derivation import build_report_readiness_from_snapshot


def _persist_report_readiness(
    store,
    run_id: int,
    audit: dict[str, Any],
) -> dict[str, Any] | None:
    snapshot = store.get_run_snapshot(run_id)
    if not snapshot:
        return None
    readiness = build_report_readiness_from_snapshot(snapshot)
    if not readiness:
        return None
    attach_report_publication_decision(audit, readiness)
    store.save_run_audit(run_id, audit)
    return readiness
