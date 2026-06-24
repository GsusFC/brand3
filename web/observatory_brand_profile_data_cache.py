"""Caching helpers for observatory brand profiles."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.storage.sqlite_store import SQLiteStore

from web.observatory_index_support import _connect, _json_dict, _table_exists


def _brand_profile_source_fingerprint(brand: Any, *, db_path: str, schema_version: str) -> str:
    run_ids = sorted({int(source.source_run_id) for source in brand.sources if source.source_run_id is not None})
    raw_input_markers = _raw_input_markers_for_runs(run_ids, db_path=db_path)
    payload = {
        "version": schema_version,
        "brand_key": brand.brand_key,
        "display_name": brand.display_name,
        "domain": brand.domain,
        "category": brand.category,
        "category_label": brand.category_label,
        "classification_tags": sorted(brand.classification_tags),
        "profile_overrides": brand.profile_overrides,
        "sources": [
            {
                "source": source.source,
                "score": source.score,
                "created_at": source.created_at,
                "href": source.href,
                "brand_name": source.brand_name,
                "url": source.url,
                "quadrant": source.quadrant,
                "source_run_id": source.source_run_id,
                "sv9_scan_id": source.sv9_scan_id,
                "magnetism_scan_id": source.magnetism_scan_id,
                "audit_token": source.audit_token,
            }
            for source in sorted(
                brand.sources,
                key=lambda item: (
                    item.source,
                    item.source_run_id or 0,
                    item.sv9_scan_id or 0,
                    item.magnetism_scan_id or 0,
                    item.audit_token or "",
                    item.created_at,
                ),
            )
        ],
        "raw_inputs": raw_input_markers,
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _raw_input_markers_for_runs(run_ids: list[int], *, db_path: str) -> list[dict[str, Any]]:
    if not run_ids:
        return []
    with _connect(db_path) as conn:
        if not _table_exists(conn, "raw_inputs"):
            return []
        placeholders = ",".join("?" for _ in run_ids)
        rows = conn.execute(
            f"""
            SELECT run_id, COUNT(*) AS input_count, MAX(id) AS max_id,
                   MAX(created_at) AS latest_input_at
            FROM raw_inputs
            WHERE run_id IN ({placeholders})
            GROUP BY run_id
            ORDER BY run_id ASC
            """,
            run_ids,
        ).fetchall()
    return [
        {
            "run_id": int(row["run_id"]),
            "input_count": int(row["input_count"] or 0),
            "max_id": int(row["max_id"] or 0),
            "latest_input_at": row["latest_input_at"] or "",
        }
        for row in rows
    ]


def _load_cached_brand_profile(
    brand_key: str,
    *,
    source_fingerprint: str,
    schema_version: str,
    db_path: str,
) -> dict[str, Any] | None:
    store = SQLiteStore(db_path)
    try:
        row = store.conn.execute(
            """
            SELECT profile_json
            FROM brand_profile_cache
            WHERE brand_key = ?
              AND schema_version = ?
              AND source_fingerprint = ?
            """,
            (brand_key, schema_version, source_fingerprint),
        ).fetchone()
    finally:
        store.close()
    if not row:
        return None
    profile = _json_dict(row["profile_json"])
    return profile or None


def _save_cached_brand_profile(
    brand_key: str,
    profile: dict[str, Any],
    *,
    source_fingerprint: str,
    schema_version: str,
    db_path: str,
) -> None:
    now = datetime.now().isoformat()
    store = SQLiteStore(db_path)
    try:
        store.conn.execute(
            """
            INSERT INTO brand_profile_cache (
                brand_key, schema_version, source_fingerprint,
                profile_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(brand_key) DO UPDATE SET
                schema_version=excluded.schema_version,
                source_fingerprint=excluded.source_fingerprint,
                profile_json=excluded.profile_json,
                updated_at=excluded.updated_at
            """,
            (
                brand_key,
                schema_version,
                source_fingerprint,
                json.dumps(profile, ensure_ascii=True, sort_keys=True),
                now,
                now,
            ),
        )
        store.conn.commit()
    finally:
        store.close()


__all__ = [
    "_brand_profile_source_fingerprint",
    "_raw_input_markers_for_runs",
    "_load_cached_brand_profile",
    "_save_cached_brand_profile",
]
