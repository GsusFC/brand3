"""Reviewed score persistence helpers for SQLiteStore."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from ..dimensions import DIMENSIONS
from .json_payloads import json_dumps as _json_dumps
from .json_payloads import safe_json_loads as _safe_json_loads


class ReviewedScoresStoreMixin:
    """Persists manual score reviews and their replay provenance."""

    def _load_reviewed_score_row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if not row:
            return None
        item = dict(row)
        affected_dimensions, affected_dimensions_error = _safe_json_loads(
            item.pop("affected_dimensions_json", None),
            field="reviewed_scores.affected_dimensions_json",
            fallback=[],
        )
        evidence_refs, evidence_refs_error = _safe_json_loads(
            item.pop("evidence_refs_json", None),
            field="reviewed_scores.evidence_refs_json",
            fallback=[],
        )
        item["affected_dimensions"] = affected_dimensions
        item["evidence_refs"] = evidence_refs
        if affected_dimensions_error:
            item["affected_dimensions_error"] = affected_dimensions_error
        if evidence_refs_error:
            item["evidence_refs_error"] = evidence_refs_error
        item["technical_override"] = bool(item.get("technical_override"))
        return item

    def save_reviewed_score(
        self,
        run_id: int,
        reviewed_composite_score: float,
        *,
        reason: str,
        evidence_refs: list[str],
        reviewer: str,
        affected_dimensions: list[str],
        review_status: str,
        technical_override: bool = False,
        technical_override_reason: str | None = None,
    ) -> int:
        from ..scoring.replay import build_score_replay_audit

        reason_text = str(reason or "").strip()
        reviewer_text = str(reviewer or "").strip()
        review_status_text = str(review_status or "").strip()
        if not reason_text:
            raise ValueError("reviewed score reason is required")
        if not reviewer_text:
            raise ValueError("reviewer is required")
        if not review_status_text:
            raise ValueError("review_status is required")

        if reviewed_composite_score is None:
            raise ValueError("reviewed_composite_score is required")
        reviewed_value = float(reviewed_composite_score)
        if not 0.0 <= reviewed_value <= 100.0:
            raise ValueError("reviewed_composite_score must be between 0 and 100")

        dimensions = []
        seen_dimensions = set()
        for dimension_name in affected_dimensions or []:
            dimension_text = str(dimension_name or "").strip()
            if not dimension_text:
                continue
            if dimension_text not in DIMENSIONS:
                raise ValueError(f"unknown affected dimension: {dimension_text}")
            if dimension_text not in seen_dimensions:
                seen_dimensions.add(dimension_text)
                dimensions.append(dimension_text)
        if not dimensions:
            raise ValueError("affected_dimensions must include at least one known scoring dimension")

        evidence_list = []
        for ref in evidence_refs or []:
            ref_text = str(ref or "").strip()
            if ref_text:
                evidence_list.append(ref_text)

        snapshot = self.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"run_id {run_id} could not be replayed for review")
        run = snapshot.get("run") or {}
        computed_composite = run.get("composite_score")
        if computed_composite is None:
            raise ValueError("computed composite score is missing for this run")
        computed_value = float(computed_composite)
        score_delta = round(reviewed_value - computed_value, 1)

        if score_delta != 0.0 and not evidence_list:
            raise ValueError("evidence_refs are required when reviewed score changes the computed score")

        replay_audit = build_score_replay_audit(self, run_id, snapshot=snapshot)
        based_on_score_integrity = str(replay_audit.get("score_integrity") or "unverifiable")
        if based_on_score_integrity == "drift_detected" and not technical_override:
            raise ValueError("technical override is required when replay integrity is drift_detected")
        if technical_override and not str(technical_override_reason or "").strip():
            raise ValueError("technical_override_reason is required when technical_override is set")

        cursor = self.conn.execute(
            """
            INSERT INTO reviewed_scores (
                run_id, computed_composite_score, reviewed_composite_score, score_delta,
                affected_dimensions_json, reason, evidence_refs_json, reviewer,
                created_at, based_on_score_integrity, review_status,
                technical_override, technical_override_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                computed_value,
                reviewed_value,
                score_delta,
                _json_dumps(dimensions),
                reason_text,
                _json_dumps(evidence_list),
                reviewer_text,
                datetime.now().isoformat(),
                based_on_score_integrity,
                review_status_text,
                int(bool(technical_override)),
                str(technical_override_reason).strip() if technical_override_reason is not None else None,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_reviewed_score(self, run_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT rs.id, rs.run_id, runs.brand_name, runs.url,
                   rs.computed_composite_score, rs.reviewed_composite_score, rs.score_delta,
                   rs.affected_dimensions_json, rs.reason, rs.evidence_refs_json,
                   rs.reviewer, rs.created_at, rs.based_on_score_integrity,
                   rs.review_status, rs.technical_override, rs.technical_override_reason
            FROM reviewed_scores rs
            JOIN runs ON runs.id = rs.run_id
            WHERE rs.run_id = ?
            ORDER BY rs.created_at DESC, rs.id DESC
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
        return self._load_reviewed_score_row(row)

    def list_reviewed_scores(
        self,
        brand_name: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if brand_name:
            clauses.append("runs.brand_name = ?")
            params.append(brand_name)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT rs.id, rs.run_id, runs.brand_name, runs.url,
                   rs.computed_composite_score, rs.reviewed_composite_score, rs.score_delta,
                   rs.affected_dimensions_json, rs.reason, rs.evidence_refs_json,
                   rs.reviewer, rs.created_at, rs.based_on_score_integrity,
                   rs.review_status, rs.technical_override, rs.technical_override_reason
            FROM reviewed_scores rs
            JOIN runs ON runs.id = rs.run_id
            {where}
            ORDER BY rs.created_at DESC, rs.id DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        return [item for row in rows if (item := self._load_reviewed_score_row(row)) is not None]
