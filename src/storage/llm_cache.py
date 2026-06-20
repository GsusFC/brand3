"""LLM cache persistence helpers for SQLiteStore."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from .json_payloads import json_dumps as _json_dumps
from .json_payloads import safe_json_loads as _safe_json_loads


class LLMCacheStoreMixin:
    """Persists and reads cached LLM responses."""

    def get_llm_cache(self, cache_key: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT cache_key, prompt_version, model, response_type, response_json,
                   response_text, created_at, hit_count, last_hit_at
            FROM llm_cache
            WHERE cache_key = ?
            """,
            (cache_key,),
        ).fetchone()
        if not row:
            return None
        now = datetime.now().isoformat()
        self._record_llm_cache_hit(cache_key, now)
        payload = dict(row)
        if payload.get("response_json"):
            response_json, error = _safe_json_loads(
                payload["response_json"],
                field="llm_cache.response_json",
                fallback=None,
            )
            if error:
                # Corrupt cache entry: treat as a miss so the caller re-queries
                # the LLM instead of crashing the run.
                return None
            payload["response_json"] = response_json
        return payload

    def _record_llm_cache_hit(self, cache_key: str, last_hit_at: str) -> None:
        try:
            self._update_llm_cache_hit_count(cache_key, last_hit_at)
            self.conn.commit()
        except sqlite3.OperationalError:
            self.conn.rollback()

    def _update_llm_cache_hit_count(self, cache_key: str, last_hit_at: str) -> None:
        self.conn.execute(
            """
            UPDATE llm_cache
            SET hit_count = hit_count + 1,
                last_hit_at = ?
            WHERE cache_key = ?
            """,
            (last_hit_at, cache_key),
        )

    def save_llm_cache(
        self,
        *,
        cache_key: str,
        prompt_version: str,
        model: str,
        response_type: str,
        response_json: Any | None = None,
        response_text: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO llm_cache (
                cache_key, prompt_version, model, response_type,
                response_json, response_text, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                prompt_version=excluded.prompt_version,
                model=excluded.model,
                response_type=excluded.response_type,
                response_json=excluded.response_json,
                response_text=excluded.response_text
            """,
            (
                cache_key,
                prompt_version,
                model,
                response_type,
                _json_dumps(response_json) if response_json is not None else None,
                response_text,
                datetime.now().isoformat(),
            ),
        )
        self.conn.commit()
