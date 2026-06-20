"""Calibration candidate persistence helpers for SQLiteStore."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .json_payloads import json_dumps as _json_dumps


class CalibrationCandidatesStoreMixin:
    """Persists proposed calibration changes before approval/application."""

    def save_calibration_candidate(
        self,
        scope: str,
        target: str,
        proposal: dict[str, Any],
        rationale: str,
        brand_name: str | None = None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO calibration_candidates (
                brand_name, scope, target, proposal_json, rationale, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, 'proposed', ?)
            """,
            (
                brand_name,
                scope,
                target,
                _json_dumps(proposal),
                rationale,
                datetime.now().isoformat(),
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_calibration_candidates(
        self,
        brand_name: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses = []
        params = []
        if brand_name:
            clauses.append("(brand_name = ? OR brand_name IS NULL)")
            params.append(brand_name)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT id, brand_name, scope, target, proposal_json, rationale, status, created_at
            FROM calibration_candidates
            {where}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        parsed = []
        for row in rows:
            item = dict(row)
            item["proposal"] = json.loads(item.pop("proposal_json"))
            parsed.append(item)
        return parsed

    def get_calibration_candidate(self, candidate_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT id, brand_name, scope, target, proposal_json, rationale, status, created_at
            FROM calibration_candidates
            WHERE id = ?
            """,
            (candidate_id,),
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["proposal"] = json.loads(item.pop("proposal_json"))
        return item

    def update_calibration_candidate_status(self, candidate_id: int, status: str) -> None:
        self.conn.execute(
            """
            UPDATE calibration_candidates
            SET status = ?
            WHERE id = ?
            """,
            (status, candidate_id),
        )
        self.conn.commit()
