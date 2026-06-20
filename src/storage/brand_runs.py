"""Brand and run lifecycle persistence helpers for SQLiteStore."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .brand_profiles import (
    brand_profile_from_record as _brand_profile_from_record,
    build_brand_profile as _build_brand_profile,
    extract_domain as _extract_domain,
)
from .json_payloads import json_dumps as _json_dumps


class BrandRunsStoreMixin:
    """Persists brands and basic audit run lifecycle state."""

    def upsert_brand(self, brand_name: str, url: str) -> int:
        now = datetime.now().isoformat()
        profile = _build_brand_profile(brand_name, url)
        cursor = self.conn.execute(
            """
            INSERT INTO brands (brand_name, url, domain, logo_key, logo_url, created_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(brand_name, url) DO UPDATE SET
                domain=excluded.domain,
                logo_key=excluded.logo_key,
                logo_url=excluded.logo_url,
                last_seen_at=excluded.last_seen_at
            RETURNING id
            """,
            (
                brand_name,
                url,
                profile["domain"],
                profile["logo_key"],
                profile["logo_url"],
                now,
                now,
            ),
        )
        brand_id = int(cursor.fetchone()["id"])
        self.conn.commit()
        return brand_id

    def get_brand_profile(self, brand_name: str | None, url: str | None) -> dict[str, Any]:
        _extract_domain(url)
        if brand_name and url:
            row = self.conn.execute(
                """
                SELECT brand_name, domain, logo_key, logo_url
                FROM brands
                WHERE brand_name = ? AND url = ?
                LIMIT 1
                """,
                (brand_name, url),
            ).fetchone()
            if row:
                item = dict(row)
                item["url"] = url
                return _brand_profile_from_record(
                    item,
                    name_field="brand_name",
                    url_field="url",
                    domain_field="domain",
                    logo_key_field="logo_key",
                    logo_url_field="logo_url",
                )
        return _build_brand_profile(brand_name, url)

    def create_run(self, brand_id: int, brand_name: str, url: str, use_llm: bool, use_social: bool) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO runs (brand_id, brand_name, url, started_at, use_llm, use_social, status)
            VALUES (?, ?, ?, ?, ?, ?, 'running')
            """,
            (brand_id, brand_name, url, datetime.now().isoformat(), int(use_llm), int(use_social)),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def mark_run_status(self, run_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE runs SET status=? WHERE id=?",
            (status, run_id),
        )
        self.conn.commit()

    def update_run_classification(
        self,
        run_id: int,
        niche_prediction: dict[str, Any],
        calibration_profile: str,
        profile_source: str,
    ) -> None:
        self.conn.execute(
            """
            UPDATE runs
            SET predicted_niche=?,
                predicted_subtype=?,
                niche_confidence=?,
                niche_evidence_json=?,
                niche_alternatives_json=?,
                calibration_profile=?,
                profile_source=?
            WHERE id=?
            """,
            (
                niche_prediction.get("predicted_niche"),
                niche_prediction.get("predicted_subtype"),
                float(niche_prediction.get("confidence") or 0.0),
                _json_dumps(niche_prediction.get("evidence", [])),
                _json_dumps(niche_prediction.get("alternatives", [])),
                calibration_profile,
                profile_source,
                run_id,
            ),
        )
        self.conn.commit()

    def finalize_run(
        self,
        run_id: int,
        composite_score: float | None,
        llm_used: bool,
        social_scraped: bool,
        result_path: str,
        summary: str,
    ) -> None:
        self.conn.execute(
            """
            UPDATE runs
            SET status='complete',
                completed_at=?,
                llm_used=?,
                social_scraped=?,
                composite_score=?,
                result_path=?,
                summary=?
            WHERE id=?
            """,
            (
                datetime.now().isoformat(),
                int(llm_used),
                int(social_scraped),
                float(composite_score) if composite_score is not None else None,
                result_path,
                summary,
                run_id,
            ),
        )
        self.conn.commit()
