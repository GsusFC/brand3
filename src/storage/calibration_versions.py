"""Calibration version, gate, and baseline persistence helpers."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .json_payloads import json_dumps as _json_dumps


class CalibrationVersionsStoreMixin:
    """Persists calibration versions and promotion state."""

    def save_calibration_version(
        self,
        label: str,
        dimensions_content: str,
        engine_content: str,
        gate_config: dict[str, Any] | None = None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO calibration_versions (label, dimensions_content, engine_content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (label, dimensions_content, engine_content, datetime.now().isoformat()),
        )
        version_id = int(cursor.lastrowid)
        if gate_config is not None:
            self.conn.execute(
                """
                INSERT INTO calibration_version_gate_configs (version_id, gate_config_json)
                VALUES (?, ?)
                """,
                (version_id, _json_dumps(gate_config)),
            )
        self.conn.commit()
        return version_id

    def get_calibration_version(self, version_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT id, label, dimensions_content, engine_content, created_at
            FROM calibration_versions
            WHERE id = ?
            """,
            (version_id,),
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        gate_row = self.conn.execute(
            """
            SELECT gate_config_json
            FROM calibration_version_gate_configs
            WHERE version_id = ?
            """,
            (version_id,),
        ).fetchone()
        if gate_row:
            item["gate_config"] = json.loads(gate_row["gate_config_json"])
        return item

    def list_calibration_versions(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id, label, created_at
            FROM calibration_versions
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def upsert_gate_config(self, gate_config: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO calibration_gate_settings (id, gate_config_json, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                gate_config_json=excluded.gate_config_json,
                updated_at=excluded.updated_at
            """,
            (_json_dumps(gate_config), datetime.now().isoformat()),
        )
        self.conn.commit()

    def get_gate_config(self) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT gate_config_json
            FROM calibration_gate_settings
            WHERE id = 1
            """
        ).fetchone()
        if not row:
            return None
        return json.loads(row["gate_config_json"])

    def save_applied_calibration(self, candidate_id: int, version_before_id: int, version_after_id: int) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO applied_calibrations (
                candidate_id, version_before_id, version_after_id, applied_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (candidate_id, version_before_id, version_after_id, datetime.now().isoformat()),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_applied_calibrations(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT applied_calibrations.id, applied_calibrations.candidate_id,
                   applied_calibrations.version_before_id, applied_calibrations.version_after_id,
                   applied_calibrations.applied_at, calibration_candidates.scope,
                   calibration_candidates.target, calibration_candidates.brand_name
            FROM applied_calibrations
            JOIN calibration_candidates ON calibration_candidates.id = applied_calibrations.candidate_id
            ORDER BY applied_calibrations.applied_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def promote_baseline(self, version_id: int, label: str) -> int:
        self.conn.execute(
            """
            UPDATE calibration_baselines
            SET is_active = 0
            WHERE is_active = 1
            """
        )
        cursor = self.conn.execute(
            """
            INSERT INTO calibration_baselines (version_id, label, is_active, promoted_at)
            VALUES (?, ?, 1, ?)
            """,
            (version_id, label, datetime.now().isoformat()),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_active_baseline(self) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT calibration_baselines.id, calibration_baselines.version_id,
                   calibration_baselines.label, calibration_baselines.promoted_at,
                   calibration_versions.created_at AS version_created_at
            FROM calibration_baselines
            JOIN calibration_versions ON calibration_versions.id = calibration_baselines.version_id
            WHERE calibration_baselines.is_active = 1
            ORDER BY calibration_baselines.promoted_at DESC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None

    def list_baselines(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT calibration_baselines.id, calibration_baselines.version_id,
                   calibration_baselines.label, calibration_baselines.is_active,
                   calibration_baselines.promoted_at
            FROM calibration_baselines
            ORDER BY calibration_baselines.promoted_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
