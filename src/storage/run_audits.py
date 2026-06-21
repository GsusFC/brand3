"""Run audit persistence helpers for SQLiteStore."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .json_payloads import json_dumps as _json_dumps


class RunAuditsStoreMixin:
    """Persists score provenance audits for runs."""

    def save_run_audit(self, run_id: int, audit: dict[str, Any]) -> None:
        fingerprint = str(audit["scoring_state_fingerprint"])
        self.conn.execute(
            """
            INSERT INTO run_audits (run_id, scoring_state_fingerprint, audit_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                scoring_state_fingerprint=excluded.scoring_state_fingerprint,
                audit_json=excluded.audit_json,
                created_at=excluded.created_at
            """,
            (
                run_id,
                fingerprint,
                _json_dumps(audit),
                datetime.now().isoformat(),
            ),
        )
        self.conn.commit()
