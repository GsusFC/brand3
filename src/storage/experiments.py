"""Calibration experiment persistence helpers for SQLiteStore."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .json_payloads import json_dumps as _json_dumps


class ExperimentsStoreMixin:
    """Persists before/after calibration experiments and their version links."""

    def save_experiment(
        self,
        brand_name: str,
        url: str,
        before_run_id: int,
        after_run_id: int,
        candidate_ids: list[int],
        summary: dict[str, Any],
        version_before_id: int | None = None,
        version_after_id: int | None = None,
        before_scoring_state_fingerprint: str | None = None,
        after_scoring_state_fingerprint: str | None = None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO experiments (
                brand_name, url, before_run_id, after_run_id,
                candidate_ids_json, summary_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brand_name,
                url,
                before_run_id,
                after_run_id,
                _json_dumps(candidate_ids),
                _json_dumps(summary),
                datetime.now().isoformat(),
            ),
        )
        experiment_id = int(cursor.lastrowid)
        if version_before_id is not None and version_after_id is not None:
            self.conn.execute(
                """
                INSERT INTO experiment_versions (experiment_id, version_before_id, version_after_id)
                VALUES (?, ?, ?)
                """,
                (experiment_id, version_before_id, version_after_id),
            )
        if before_scoring_state_fingerprint is not None or after_scoring_state_fingerprint is not None:
            self.conn.execute(
                """
                INSERT INTO experiment_audits (
                    experiment_id, before_scoring_state_fingerprint,
                    after_scoring_state_fingerprint, created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    before_scoring_state_fingerprint,
                    after_scoring_state_fingerprint,
                    datetime.now().isoformat(),
                ),
            )
        self.conn.commit()
        return experiment_id

    def list_experiments(self, brand_name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        clauses = []
        params = []
        if brand_name:
            clauses.append("brand_name = ?")
            params.append(brand_name)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT id, brand_name, url, before_run_id, after_run_id,
                   candidate_ids_json, summary_json, created_at
            FROM experiments
            {where}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        experiments = []
        for row in rows:
            item = dict(row)
            item["candidate_ids"] = json.loads(item.pop("candidate_ids_json"))
            item["summary"] = json.loads(item.pop("summary_json"))
            version_row = self.conn.execute(
                """
                SELECT version_before_id, version_after_id
                FROM experiment_versions
                WHERE experiment_id = ?
                """,
                (item["id"],),
            ).fetchone()
            if version_row:
                item["version_before_id"] = int(version_row["version_before_id"])
                item["version_after_id"] = int(version_row["version_after_id"])
            audit_row = self.conn.execute(
                """
                SELECT before_scoring_state_fingerprint, after_scoring_state_fingerprint
                FROM experiment_audits
                WHERE experiment_id = ?
                """,
                (item["id"],),
            ).fetchone()
            if audit_row:
                item["before_scoring_state_fingerprint"] = audit_row["before_scoring_state_fingerprint"]
                item["after_scoring_state_fingerprint"] = audit_row["after_scoring_state_fingerprint"]
            experiments.append(item)
        return experiments

    def get_latest_experiment_for_version(
        self,
        version_id: int,
        brand_name: str | None = None,
    ) -> dict[str, Any] | None:
        clauses = ["experiment_versions.version_after_id = ?"]
        params: list[Any] = [version_id]
        if brand_name:
            clauses.append("experiments.brand_name = ?")
            params.append(brand_name)
        where = " AND ".join(clauses)
        row = self.conn.execute(
            f"""
            SELECT experiments.id, experiments.brand_name, experiments.url,
                   experiments.before_run_id, experiments.after_run_id,
                   experiments.candidate_ids_json, experiments.summary_json,
                   experiments.created_at, experiment_versions.version_before_id,
                   experiment_versions.version_after_id
            FROM experiments
            JOIN experiment_versions ON experiment_versions.experiment_id = experiments.id
            WHERE {where}
            ORDER BY experiments.created_at DESC
            LIMIT 1
            """,
            params,
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["candidate_ids"] = json.loads(item.pop("candidate_ids_json"))
        item["summary"] = json.loads(item.pop("summary_json"))
        audit_row = self.conn.execute(
            """
            SELECT before_scoring_state_fingerprint, after_scoring_state_fingerprint
            FROM experiment_audits
            WHERE experiment_id = ?
            """,
            (item["id"],),
        ).fetchone()
        if audit_row:
            item["before_scoring_state_fingerprint"] = audit_row["before_scoring_state_fingerprint"]
            item["after_scoring_state_fingerprint"] = audit_row["after_scoring_state_fingerprint"]
        return item
