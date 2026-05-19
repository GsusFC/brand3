"""Thin SQLite access for the `web_requests` table.

Opens its own connection per call — SQLite in WAL mode handles this fine and
we avoid threading the engine's SQLiteStore into middleware. Writes are rare
and short-lived, reads are bounded by a handful of queries per request.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.config import BRAND3_DB_PATH
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
