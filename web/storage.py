"""Thin SQLite access for the `web_requests` table.

Opens its own connection per call — SQLite in WAL mode handles this fine and
we avoid threading the engine's SQLiteStore into middleware. Writes are rare
and short-lived, reads are bounded by a handful of queries per request.
"""

from __future__ import annotations

import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path

from src.config import BRAND3_DB_PATH
from src.features.magnetism.readiness import assess_scanner_readiness
from src.features.magnetism.scan_mode import (
    magnetism_input_type_from_payload,
    scan_mode_from_payload,
)
from src.quality.publication_readiness import attach_scanner_publication_decision
from src.storage.sqlite_store import SQLiteStore


def _db_path() -> Path:
    return Path(BRAND3_DB_PATH)


def ensure_schema() -> None:
    """Apply engine schema + file migrations. Call once on startup."""
    store = SQLiteStore(str(_db_path()))
    store.close()


@contextmanager
def _connect():
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def count_recent_analyses_for_ip(ip: str, hours: int = 24) -> int:
    """How many analyses this IP requested within the last `hours`."""
    if not ip:
        return 0
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM web_requests
            WHERE requester_ip = ?
              AND created_at > datetime('now', ?)
            """,
            (ip, f"-{hours} hours"),
        )
        row = cur.fetchone()
    return int(row["c"]) if row else 0


def insert_request(
    *,
    token: str,
    url: str,
    brand_slug: str,
    requester_ip: str,
    requester_is_team: bool,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO web_requests
              (token, url, brand_slug, requester_ip, requester_is_team, status)
            VALUES (?, ?, ?, ?, ?, 'queued')
            """,
            (token, url, brand_slug, requester_ip, 1 if requester_is_team else 0),
        )
        conn.commit()


def get_request(token: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM web_requests WHERE token = ?", (token,)
        ).fetchone()
    return dict(row) if row else None


_PUBLIC_FILTER = (
    "status = 'ready' AND is_public = 1 AND takedown_requested = 0 AND run_id IS NOT NULL"
)


def get_public_request_for_run(run_id: int) -> dict | None:
    """Return the public web request row for a run, if one exists."""
    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT *
            FROM web_requests
            WHERE run_id = ?
              AND {_PUBLIC_FILTER}
            ORDER BY completed_at DESC
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
    return dict(row) if row else None


def _attach_composite(rows: list[dict]) -> list[dict]:
    """Enrich web_requests rows with the engine's composite_score from `runs`."""
    if not rows:
        return rows
    run_ids = [r["run_id"] for r in rows if r.get("run_id")]
    if not run_ids:
        return rows
    placeholders = ",".join("?" * len(run_ids))
    with _connect() as conn:
        cur = conn.execute(
            f"SELECT id, composite_score FROM runs WHERE id IN ({placeholders})",
            run_ids,
        )
        score_by_id = {row["id"]: row["composite_score"] for row in cur.fetchall()}
    for r in rows:
        r["composite"] = score_by_id.get(r.get("run_id"))
    return rows


def _normalize_magnetism_listing_row(row: dict) -> dict:
    """Normalize listing rows whose canonical payload fields were selected by SQL."""
    normalized = dict(row)
    mode = normalized.pop("_scan_mode_mode", None)
    comparable = normalized.pop("_scan_mode_comparable", None)
    reason_codes_json = normalized.pop("_scan_mode_reason_codes", None)
    payload_source = normalized.pop("_payload_source", None)
    payload_extraction_mode = normalized.pop("_payload_extraction_mode", None)
    payload_direct_source_provider = normalized.pop("_payload_direct_source_provider", None)

    scan_mode_payload = None
    if mode in {"canonical_url", "from_audit_run", "legacy_manual", "unknown"} and comparable is not None:
        reason_codes = []
        if isinstance(reason_codes_json, str):
            try:
                parsed_reason_codes = json.loads(reason_codes_json)
            except Exception:
                parsed_reason_codes = []
            if isinstance(parsed_reason_codes, list):
                reason_codes = parsed_reason_codes
        scan_mode_payload = {
            "mode": mode,
            "comparable": bool(comparable),
            "reason_codes": reason_codes,
        }

    payload = {
        "source": payload_source,
        "extraction_mode": payload_extraction_mode,
        "direct_source_provider": payload_direct_source_provider,
        "url": normalized.get("url"),
    }
    if normalized.get("source_run_id"):
        payload["source_run_id"] = normalized.get("source_run_id")
    if scan_mode_payload:
        payload["scan_mode"] = scan_mode_payload

    normalized["scan_mode"] = scan_mode_from_payload(
        payload,
        source_run_id=normalized.get("source_run_id"),
    ).to_payload()
    return normalized


def list_latest_public(limit: int = 10) -> list[dict]:
    with _connect() as conn:
        cur = conn.execute(
            f"""
            SELECT token, url, brand_slug, completed_at, run_id
            FROM web_requests
            WHERE {_PUBLIC_FILTER}
            ORDER BY completed_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = [dict(r) for r in cur.fetchall()]
    return _attach_composite(rows)


_SORT_SQL = {
    "newest": "w.completed_at DESC",
    "score_desc": "r.composite_score DESC, w.completed_at DESC",
    "score_asc": "r.composite_score ASC, w.completed_at DESC",
}


def list_public_reports(
    *,
    query: str | None = None,
    sort: str = "newest",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict], int]:
    """Return (rows, total_count) for paginated public listing."""
    order_by = _SORT_SQL.get(sort, _SORT_SQL["newest"])
    params: list = []
    where = f"w.status='ready' AND w.is_public=1 AND w.takedown_requested=0 AND w.run_id IS NOT NULL"
    if query:
        where += " AND w.brand_slug LIKE ?"
        params.append(f"%{query.lower()}%")
    offset = max(0, (page - 1) * per_page)
    with _connect() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM web_requests w WHERE {where}",
            params,
        ).fetchone()["c"]
        rows = conn.execute(
            f"""
            SELECT w.token, w.url, w.brand_slug, w.completed_at, w.run_id,
                   r.composite_score AS composite
            FROM web_requests w
            LEFT JOIN runs r ON r.id = w.run_id
            WHERE {where}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (*params, per_page, offset),
        ).fetchall()
        rows = [dict(r) for r in rows]
    return rows, int(total)


def list_brand_history(domain_or_slug: str) -> list[dict]:
    """All public analyses for a brand slug (matches 'a16z' or 'a16z.com')."""
    slug = domain_or_slug.lower()
    if "." in slug:
        parts = slug.split(".")
        slug = parts[-2] if len(parts) >= 2 else parts[0]
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT w.token, w.url, w.brand_slug, w.completed_at, w.run_id,
                   r.composite_score AS composite
            FROM web_requests w
            LEFT JOIN runs r ON r.id = w.run_id
            WHERE w.brand_slug = ?
              AND w.status = 'ready'
              AND w.is_public = 1
              AND w.takedown_requested = 0
              AND w.run_id IS NOT NULL
            ORDER BY w.completed_at DESC
            """,
            (slug,),
        ).fetchall()
    return [dict(r) for r in rows]


def insert_magnetism_scan(
    *,
    brand_name: str,
    url: str,
    magnetism_score: int,
    coherence_score: int,
    quadrant: str,
    raw_payload: str,
    source_run_id: int | None = None,
) -> int:
    """Insert a new magnetism scan and return its primary key ID."""
    normalized_payload, status, error_message = _magnetism_payload_insert_state(
        raw_payload,
        source_run_id=source_run_id,
    )
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO magnetism_scans
              (brand_name, url, magnetism_score, coherence_score, quadrant, raw_payload,
               source_run_id, created_at, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
            """,
            (
                brand_name,
                url,
                magnetism_score,
                coherence_score,
                quadrant,
                normalized_payload,
                source_run_id,
                status,
                error_message,
            ),
        )
        conn.commit()
        last_id = cur.lastrowid
    return last_id


def _magnetism_payload_insert_state(
    raw_payload: str,
    *,
    source_run_id: int | None,
) -> tuple[str, str, str | None]:
    try:
        payload = json.loads(raw_payload)
    except Exception:
        return raw_payload, "ready", None
    if not isinstance(payload, dict):
        return raw_payload, "ready", None

    readiness = payload.get("scanner_readiness")
    if not isinstance(readiness, dict):
        input_type = magnetism_input_type_from_payload(
            payload,
            source_run_id=source_run_id,
        )
        readiness = assess_scanner_readiness(input_type, payload).to_payload()

    publication = attach_scanner_publication_decision(payload, readiness)
    input_type = magnetism_input_type_from_payload(
        payload,
        source_run_id=source_run_id,
    )
    payload["scan_mode"] = scan_mode_from_payload(
        payload,
        input_type=input_type,
        source_run_id=source_run_id,
    ).to_payload()
    if publication.status == "failed":
        reason_codes = list(publication.reason_codes)
        reason = str(reason_codes[0]) if reason_codes else "scanner_readiness_failed"
        return json.dumps(payload, ensure_ascii=False), "failed", f"failed:{reason}"

    return json.dumps(payload, ensure_ascii=False), "ready", None


def insert_magnetism_job(
    *,
    token: str,
    brand_name: str,
    url: str,
    input_type: str,
    input_value: str,
    source_run_id: int | None = None,
) -> int:
    """Insert a queued Magnetism scan job and return its primary key ID."""
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO magnetism_scans
              (brand_name, url, magnetism_score, coherence_score, quadrant, raw_payload,
               created_at, status, token, phase, phase_updated_at, input_type, input_value, source_run_id)
            VALUES (?, ?, 0, 0, 'pending', '{}', datetime('now'), 'queued', ?, 'queued',
                    datetime('now'), ?, ?, ?)
            """,
            (brand_name, url, token, input_type, input_value, source_run_id),
        )
        conn.commit()
        last_id = cur.lastrowid
    return int(last_id)


def insert_sv9_generation_job(
    *,
    token: str,
    scan_id: int,
    source_run_id: int,
    brand_name: str,
) -> int:
    """Insert an SV9 generation job and return its primary key ID."""
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO sv9_generation_jobs
              (token, scan_id, source_run_id, brand_name, created_at, status, phase, phase_updated_at)
            VALUES (?, ?, ?, ?, datetime('now'), 'queued', 'queued', datetime('now'))
            """,
            (token, scan_id, source_run_id, brand_name),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_sv9_generation_job(token: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sv9_generation_jobs WHERE token = ?",
            (token,),
        ).fetchone()
    return dict(row) if row else None


def get_sv9_generation_job_by_scan_id(scan_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sv9_generation_jobs WHERE scan_id = ? ORDER BY id DESC LIMIT 1",
            (scan_id,),
        ).fetchone()
    return dict(row) if row else None


def update_sv9_generation_job(token: str, **columns) -> None:
    if not columns:
        return
    allowed_columns = {
        "status",
        "phase",
        "phase_updated_at",
        "error_message",
        "sv9_scan_id",
        "started_at",
        "completed_at",
    }
    unexpected = set(columns) - allowed_columns
    if unexpected:
        raise ValueError(f"Unexpected SV9 generation job columns: {sorted(unexpected)}")
    assignments = ", ".join(f"{k} = ?" for k in columns)
    values = list(columns.values()) + [token]
    with _connect() as conn:
        conn.execute(
            f"UPDATE sv9_generation_jobs SET {assignments} WHERE token = ?",
            values,
        )
        conn.commit()


def get_magnetism_scan_by_token(token: str) -> dict | None:
    """Retrieve a Magnetism scan/job by public status token."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM magnetism_scans WHERE token = ?", (token,)
        ).fetchone()
    return dict(row) if row else None



def get_magnetism_scan(scan_id: int) -> dict | None:
    """Retrieve a specific magnetism scan by ID."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM magnetism_scans WHERE id = ?", (scan_id,)
        ).fetchone()
    return dict(row) if row else None


def update_magnetism_scan_payload(scan_id: int, raw_payload: str) -> None:
    """Update a scan payload without changing its scores or public metadata."""
    with _connect() as conn:
        conn.execute(
            "UPDATE magnetism_scans SET raw_payload = ? WHERE id = ?",
            (raw_payload, scan_id),
        )
        conn.commit()


def list_magnetism_scans(limit: int = 20) -> list[dict]:
    """List recent magnetism scans."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                COALESCE(
                    CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.brand_name') END,
                    brand_name
                ) AS brand_name,
                COALESCE(
                    CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.url') END,
                    url
                ) AS url,
                COALESCE(
                    CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.magnetism_score') END,
                    magnetism_score
                ) AS magnetism_score,
                COALESCE(
                    CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.coherence_score') END,
                    coherence_score
                ) AS coherence_score,
                COALESCE(
                    CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.quadrant') END,
                    quadrant
                ) AS quadrant,
                COALESCE(
                    CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.source_run_id') END,
                    source_run_id
                ) AS source_run_id,
                CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.source') END AS source,
                CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.scan_mode.mode') END AS _scan_mode_mode,
                CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.scan_mode.comparable') END AS _scan_mode_comparable,
                CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.scan_mode.reason_codes') END AS _scan_mode_reason_codes,
                CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.source') END AS _payload_source,
                CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.extraction_mode') END AS _payload_extraction_mode,
                CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.direct_source_provider') END AS _payload_direct_source_provider,
                created_at
            FROM magnetism_scans
            WHERE status = 'ready'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_normalize_magnetism_listing_row(dict(r)) for r in rows]
