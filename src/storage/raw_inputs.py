"""Raw input persistence mixin for SQLiteStore."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .json_payloads import MalformedJSONPayload, json_dumps, safe_json_loads, to_jsonable
from src.visual_signature.acquisition_contract import VISUAL_ACQUISITION_RAW_SOURCE


class RawInputsStoreMixin:
    def save_raw_input(self, run_id: int, source: str, payload: Any) -> None:
        self.conn.execute(
            """
            INSERT INTO raw_inputs (run_id, source, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, source, json_dumps(to_jsonable(payload)), datetime.now().isoformat()),
        )
        self.conn.commit()

    def save_report_translation(self, run_id: int, target_lang: str, payload: Any) -> None:
        stored = dict(payload) if isinstance(payload, dict) else {"payload": payload}
        stored["target_lang"] = target_lang
        self.save_raw_input(run_id, "report_translation", stored)

    def get_report_translation(self, run_id: int, target_lang: str) -> dict[str, Any] | None:
        rows = self.conn.execute(
            """
            SELECT payload_json
            FROM raw_inputs
            WHERE run_id = ? AND source = 'report_translation'
            ORDER BY created_at DESC
            """,
            (run_id,),
        ).fetchall()
        for row in rows:
            payload, error = safe_json_loads(
                row["payload_json"],
                field="raw_inputs.payload_json",
                fallback=None,
            )
            if error:
                continue
            if isinstance(payload, dict) and payload.get("target_lang") == target_lang:
                return payload
        return None

    def save_visual_signature_evidence(self, run_id: int, payload: Any) -> None:
        self.save_visual_acquisition_evidence(run_id, payload)

    def save_visual_acquisition_evidence(self, run_id: int, payload: Any) -> None:
        self.save_raw_input(run_id, VISUAL_ACQUISITION_RAW_SOURCE, payload)

    def get_latest_raw_input(
        self,
        brand_name: str,
        url: str,
        source: str,
        max_age_hours: int = 24,
    ) -> Any | None:
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
        rows = self.conn.execute(
            """
            SELECT raw_inputs.payload_json
            FROM raw_inputs
            JOIN runs ON runs.id = raw_inputs.run_id
            WHERE runs.brand_name = ?
              AND runs.url = ?
              AND raw_inputs.source = ?
              AND raw_inputs.created_at >= ?
            ORDER BY raw_inputs.created_at DESC
            """,
            (brand_name, url, source, cutoff_iso),
        ).fetchall()
        for row in rows:
            payload, error = safe_json_loads(
                row["payload_json"],
                field="raw_inputs.payload_json",
                fallback=None,
            )
            if error:
                return MalformedJSONPayload(
                    field=error["field"],
                    raw_json=str(error["raw_json"]),
                    error=error["error"],
                )
            # Derived re-saves (payload["derived"]) are run-scoped evidence,
            # never a cross-run cache source: fall through to the original capture.
            if isinstance(payload, dict) and payload.get("derived"):
                continue
            return payload
        return None

    def get_latest_visual_signature_evidence(
        self,
        brand_name: str,
        url: str,
        max_age_hours: int = 24,
    ) -> Any | None:
        return self.get_latest_visual_acquisition_evidence(
            brand_name,
            url,
            max_age_hours=max_age_hours,
        )

    def get_latest_visual_acquisition_evidence(
        self,
        brand_name: str,
        url: str,
        max_age_hours: int = 24,
    ) -> Any | None:
        latest = self.get_latest_raw_input(
            brand_name,
            url,
            VISUAL_ACQUISITION_RAW_SOURCE,
            max_age_hours=max_age_hours,
        )
        if latest is not None:
            return latest
        return self.get_latest_raw_input(brand_name, url, "visual_signature", max_age_hours=max_age_hours)
