"""Run summary and snapshot persistence helpers for SQLiteStore."""

from __future__ import annotations

from typing import Any

from .brand_profiles import brand_profile_from_record as _brand_profile_from_record
from .json_payloads import safe_json_loads as _safe_json_loads
from .time_utils import duration_seconds as _duration_seconds


class RunSnapshotsStoreMixin:
    """Loads run summaries and full report snapshots."""

    def get_latest_run_id(self, brand_name: str | None = None, url: str | None = None) -> int | None:
        clauses = []
        params = []
        if brand_name:
            clauses.append("brand_name = ?")
            params.append(brand_name)
        if url:
            clauses.append("url = ?")
            params.append(url)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        row = self.conn.execute(
            f"""
            SELECT id
            FROM runs
            {where}
            ORDER BY started_at DESC
            LIMIT 1
            """,
            params,
        ).fetchone()
        return int(row["id"]) if row else None

    def get_run_summary(self, run_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT runs.id, runs.brand_name, runs.url, runs.started_at, runs.completed_at,
                   runs.composite_score, runs.summary,
                   runs.use_llm, runs.use_social, runs.llm_used, runs.social_scraped, runs.result_path,
                   runs.predicted_niche, runs.predicted_subtype, runs.niche_confidence,
                   runs.calibration_profile, runs.profile_source,
                   brands.domain AS brand_domain, brands.logo_key AS brand_logo_key,
                   brands.logo_url AS brand_logo_url
            FROM runs
            LEFT JOIN brands ON brands.id = runs.brand_id
            WHERE runs.id = ?
            """,
            (run_id,),
        ).fetchone()
        if not row:
            return None
        run_payload = dict(row)
        run_payload["brand_profile"] = _brand_profile_from_record(run_payload)
        run_payload["run_duration_seconds"] = _duration_seconds(
            run_payload.get("started_at"),
            run_payload.get("completed_at"),
        )
        return run_payload

    def get_run_snapshot(self, run_id: int) -> dict[str, Any] | None:
        run = self.conn.execute(
            """
            SELECT runs.id, runs.brand_name, runs.url, runs.started_at, runs.completed_at,
                   runs.composite_score, runs.summary,
                   runs.use_llm, runs.use_social, runs.llm_used, runs.social_scraped, runs.result_path,
                   runs.predicted_niche, runs.predicted_subtype, runs.niche_confidence, runs.niche_evidence_json,
                   runs.niche_alternatives_json, runs.calibration_profile, runs.profile_source,
                   brands.domain AS brand_domain, brands.logo_key AS brand_logo_key,
                   brands.logo_url AS brand_logo_url,
                   run_audits.scoring_state_fingerprint AS scoring_state_fingerprint,
                   run_audits.audit_json AS audit_json
            FROM runs
            LEFT JOIN brands ON brands.id = runs.brand_id
            LEFT JOIN run_audits ON run_audits.run_id = runs.id
            WHERE runs.id = ?
            """,
            (run_id,),
        ).fetchone()
        if not run:
            return None

        scores = self.conn.execute(
            """
            SELECT dimension_name, score, insights_json, rules_json
            FROM scores
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchall()
        features = self.conn.execute(
            """
            SELECT dimension_name, feature_name, value, raw_value, confidence, source
            FROM features
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchall()
        annotations = self.conn.execute(
            """
            SELECT dimension_name, feature_name, expected_score, actual_score, note, created_at
            FROM annotations
            WHERE run_id = ?
            ORDER BY created_at ASC
            """,
            (run_id,),
        ).fetchall()
        raw_inputs = self.conn.execute(
            """
            SELECT source, payload_json, created_at
            FROM raw_inputs
            WHERE run_id = ?
            ORDER BY created_at ASC
            """,
            (run_id,),
        ).fetchall()
        evidence_items = self.conn.execute(
            """
            SELECT id, run_id, source, url, quote, feature_name, dimension_name,
                   confidence, freshness_days, created_at
            FROM evidence_items
            WHERE run_id = ?
            ORDER BY id ASC
            """,
            (run_id,),
        ).fetchall()

        run_payload = dict(run)
        audit_json = run_payload.pop("audit_json", None)
        audit, audit_error = _safe_json_loads(audit_json, field="run_audits.audit_json", fallback=None)
        if audit_error:
            run_payload["audit"] = None
            run_payload["audit_error"] = audit_error
        elif audit is not None:
            run_payload["audit"] = audit

        niche_evidence_json = run_payload.pop("niche_evidence_json")
        niche_evidence, niche_evidence_error = _safe_json_loads(
            niche_evidence_json,
            field="runs.niche_evidence_json",
            fallback=[],
        )
        run_payload["niche_evidence"] = niche_evidence
        if niche_evidence_error:
            run_payload["niche_evidence_error"] = niche_evidence_error

        niche_alternatives_json = run_payload.pop("niche_alternatives_json")
        niche_alternatives, niche_alternatives_error = _safe_json_loads(
            niche_alternatives_json,
            field="runs.niche_alternatives_json",
            fallback=[],
        )
        run_payload["niche_alternatives"] = niche_alternatives
        if niche_alternatives_error:
            run_payload["niche_alternatives_error"] = niche_alternatives_error
        run_payload["brand_profile"] = _brand_profile_from_record(run_payload)
        run_payload["run_duration_seconds"] = _duration_seconds(
            run_payload.get("started_at"),
            run_payload.get("completed_at"),
        )

        raw_input_payloads = []
        for row in raw_inputs:
            payload, payload_error = _safe_json_loads(
                row["payload_json"],
                field="raw_inputs.payload_json",
                fallback=None,
            )
            item = {
                "source": row["source"],
                "payload": payload,
                "created_at": row["created_at"],
            }
            if payload_error:
                item["payload_error"] = payload_error
            raw_input_payloads.append(item)

        return {
            "run": run_payload,
            "scores": [dict(row) for row in scores],
            "features": [dict(row) for row in features],
            "annotations": [dict(row) for row in annotations],
            "raw_inputs": raw_input_payloads,
            "evidence_items": [dict(row) for row in evidence_items],
        }
