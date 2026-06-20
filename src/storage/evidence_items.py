"""Evidence item persistence mixin for SQLiteStore."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class EvidenceItemsStoreMixin:
    def save_evidence_items(self, run_id: int, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        now = datetime.now().isoformat()
        rows = [
            (
                run_id,
                item.get("source") or "",
                item.get("url"),
                item.get("quote"),
                item.get("feature_name"),
                item.get("dimension_name"),
                float(item.get("confidence") or 0.0),
                item.get("freshness_days"),
                item.get("created_at") or now,
            )
            for item in items
        ]
        self.conn.executemany(
            """
            INSERT INTO evidence_items (
                run_id, source, url, quote, feature_name, dimension_name,
                confidence, freshness_days, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def get_run_evidence(
        self,
        run_id: int,
        *,
        dimension_name: str | None = None,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = ["run_id = ?"]
        params: list[Any] = [run_id]
        if dimension_name:
            filters.append("dimension_name = ?")
            params.append(dimension_name)
        if source:
            filters.append("source = ?")
            params.append(source)
        rows = self.conn.execute(
            f"""
            SELECT id, run_id, source, url, quote, feature_name, dimension_name,
                   confidence, freshness_days, created_at
            FROM evidence_items
            WHERE {" AND ".join(filters)}
            ORDER BY id ASC
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]
