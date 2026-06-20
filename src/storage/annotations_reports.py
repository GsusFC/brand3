"""Annotation and catalog reporting helpers for SQLiteStore."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .brand_profiles import (
    brand_profile_from_record as _brand_profile_from_record,
    build_brand_profile as _build_brand_profile,
)
from .time_utils import duration_seconds as _duration_seconds


class AnnotationsReportsStoreMixin:
    """Persists reviewer annotations and loads run/brand catalog reports."""

    def add_annotation(
        self,
        run_id: int,
        note: str,
        dimension_name: str | None = None,
        feature_name: str | None = None,
        expected_score: float | None = None,
        actual_score: float | None = None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO annotations (
                run_id, dimension_name, feature_name, expected_score,
                actual_score, note, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                dimension_name,
                feature_name,
                expected_score,
                actual_score,
                note,
                datetime.now().isoformat(),
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_annotations(self, brand_name: str | None = None) -> list[dict[str, Any]]:
        clauses = []
        params = []
        if brand_name:
            clauses.append("runs.brand_name = ?")
            params.append(brand_name)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT annotations.run_id, runs.brand_name, runs.url, annotations.dimension_name,
                   annotations.feature_name, annotations.expected_score, annotations.actual_score,
                   annotations.note, annotations.created_at
            FROM annotations
            JOIN runs ON runs.id = annotations.run_id
            {where}
            ORDER BY annotations.created_at DESC
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def list_runs(
        self,
        brand_name: str | None = None,
        url: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        clauses = []
        params = []
        if brand_name:
            clauses.append("runs.brand_name = ?")
            params.append(brand_name)
        if url:
            clauses.append("runs.url = ?")
            params.append(url)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT runs.id, runs.brand_name, runs.url, runs.started_at, runs.completed_at,
                   runs.use_llm, runs.use_social, runs.llm_used, runs.social_scraped,
                   runs.composite_score, runs.result_path,
                   runs.predicted_niche, runs.predicted_subtype, runs.niche_confidence,
                   runs.calibration_profile, runs.profile_source,
                   brands.domain AS brand_domain, brands.logo_key AS brand_logo_key,
                   brands.logo_url AS brand_logo_url,
                   run_audits.scoring_state_fingerprint AS scoring_state_fingerprint
            FROM runs
            LEFT JOIN brands ON brands.id = runs.brand_id
            LEFT JOIN run_audits ON run_audits.run_id = runs.id
            {where}
            ORDER BY runs.started_at DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        payload = []
        for row in rows:
            item = dict(row)
            item["brand_profile"] = _brand_profile_from_record(item)
            item["run_duration_seconds"] = _duration_seconds(
                item.get("started_at"),
                item.get("completed_at"),
            )
            payload.append(item)
        return payload

    def list_brands(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT brands.id AS brand_id,
                   brands.brand_name,
                   brands.url,
                   brands.domain,
                   brands.logo_key,
                   brands.logo_url,
                   brands.last_seen_at,
                   COUNT(runs.id) AS run_count,
                   (
                       SELECT composite_score
                       FROM runs AS recent_runs
                       WHERE recent_runs.brand_id = brands.id
                       ORDER BY recent_runs.started_at DESC
                       LIMIT 1
                   ) AS latest_composite_score,
                   (
                       SELECT started_at
                       FROM runs AS recent_runs
                       WHERE recent_runs.brand_id = brands.id
                       ORDER BY recent_runs.started_at DESC
                       LIMIT 1
                   ) AS latest_run_started_at,
                   (
                       SELECT run_audits.scoring_state_fingerprint
                       FROM runs AS recent_runs
                       LEFT JOIN run_audits ON run_audits.run_id = recent_runs.id
                       WHERE recent_runs.brand_id = brands.id
                       ORDER BY recent_runs.started_at DESC
                       LIMIT 1
                   ) AS latest_scoring_state_fingerprint,
                   (
                       SELECT predicted_niche
                       FROM runs AS recent_runs
                       WHERE recent_runs.brand_id = brands.id
                       ORDER BY recent_runs.started_at DESC
                       LIMIT 1
                   ) AS latest_predicted_niche,
                   (
                       SELECT predicted_subtype
                       FROM runs AS recent_runs
                       WHERE recent_runs.brand_id = brands.id
                       ORDER BY recent_runs.started_at DESC
                       LIMIT 1
                   ) AS latest_predicted_subtype,
                   (
                       SELECT niche_confidence
                       FROM runs AS recent_runs
                       WHERE recent_runs.brand_id = brands.id
                       ORDER BY recent_runs.started_at DESC
                       LIMIT 1
                   ) AS latest_niche_confidence,
                   (
                       SELECT calibration_profile
                       FROM runs AS recent_runs
                       WHERE recent_runs.brand_id = brands.id
                       ORDER BY recent_runs.started_at DESC
                       LIMIT 1
                   ) AS latest_calibration_profile
            FROM brands
            LEFT JOIN runs ON runs.brand_id = brands.id
            GROUP BY brands.id
            ORDER BY brands.last_seen_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        payload = []
        for row in rows:
            item = dict(row)
            item["brand_profile"] = _brand_profile_from_record(
                item,
                name_field="brand_name",
                url_field="url",
                domain_field="domain",
                logo_key_field="logo_key",
                logo_url_field="logo_url",
            )
            payload.append(item)
        return payload

    def get_brand_report(self, brand_name: str, limit: int = 20) -> dict[str, Any]:
        runs = self.list_runs(brand_name=brand_name, limit=limit)
        if not runs:
            return {
                "brand_name": brand_name,
                "brand_profile": _build_brand_profile(brand_name, None),
                "runs": [],
                "dimension_series": {},
                "annotations": [],
            }

        run_ids = [run["id"] for run in runs]
        placeholders = ",".join("?" for _ in run_ids)

        scores = self.conn.execute(
            f"""
            SELECT run_id, dimension_name, score
            FROM scores
            WHERE run_id IN ({placeholders})
            ORDER BY run_id DESC, dimension_name ASC
            """,
            run_ids,
        ).fetchall()

        annotations = self.list_annotations(brand_name=brand_name)

        dimension_series: dict[str, list[dict[str, Any]]] = {}
        for row in scores:
            payload = dict(row)
            dimension_series.setdefault(payload["dimension_name"], []).append(payload)

        return {
            "brand_name": brand_name,
            "brand_profile": runs[0].get("brand_profile") or _build_brand_profile(brand_name, runs[0].get("url")),
            "runs": runs,
            "dimension_series": dimension_series,
            "annotations": annotations,
        }
