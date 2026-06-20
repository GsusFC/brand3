"""SQLite persistence for Brand3 Scoring runs."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from ..dimensions import DIMENSIONS
from ..models.brand import BrandScore, FeatureValue
from .analysis_jobs import AnalysisJobsStoreMixin
from .brand_profiles import (
    brand_profile_from_record as _brand_profile_from_record,
    build_brand_profile as _build_brand_profile,
    extract_domain as _extract_domain,
)
from .json_payloads import (
    MalformedJSONPayload as _MalformedJSONPayload,
    json_dumps as _json_dumps,
    safe_json_loads as _safe_json_loads,
    to_jsonable as _to_jsonable,
)
from .raw_inputs import RawInputsStoreMixin
from .time_utils import duration_seconds as _duration_seconds


class SQLiteStore(AnalysisJobsStoreMixin, RawInputsStoreMixin):
    """Persists runs, raw collector inputs, features, and scores in SQLite."""

    _schema_init_lock = threading.Lock()
    _schema_initialized: set[tuple[str, tuple[int, int], tuple[tuple[str, int, int], ...]]] = set()
    _schema_init_metrics: dict[str, int | float] = {
        "runs": 0,
        "skips": 0,
        "run_seconds": 0.0,
    }

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._configure_connection()
        self._ensure_schema_initialized()

    @classmethod
    def reset_schema_init_metrics(cls) -> None:
        cls._schema_initialized.clear()
        cls._schema_init_metrics = {
            "runs": 0,
            "skips": 0,
            "run_seconds": 0.0,
        }

    @classmethod
    def schema_init_metrics(cls) -> dict[str, int | float]:
        return dict(cls._schema_init_metrics)

    def _configure_connection(self) -> None:
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")

    def _ensure_schema_initialized(self) -> None:
        """Run DDL/migrations once per process for a concrete database file.

        The cache key includes the database file identity, so a deleted and
        recreated database at the same path is initialized again.
        """
        with self._schema_init_lock:
            cache_key = self._schema_cache_key()
            if cache_key in self._schema_initialized and self._schema_is_ready():
                self._schema_init_metrics["skips"] += 1
                return
            start = time.perf_counter()
            self._init_schema()
            self._ensure_inline_table_columns()
            self._apply_file_migrations()
            elapsed = time.perf_counter() - start
            self._schema_initialized.add(self._schema_cache_key())
            self._schema_init_metrics["runs"] += 1
            self._schema_init_metrics["run_seconds"] += elapsed

    def _schema_is_ready(self) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'runs'"
        ).fetchone()
        return row is not None

    def _schema_cache_key(self) -> tuple[str, tuple[int, int], tuple[tuple[str, int, int], ...]]:
        stat = self.db_path.stat()
        return (
            str(self.db_path.resolve()),
            (stat.st_dev, stat.st_ino),
            self._migration_signature(),
        )

    @staticmethod
    def _migration_signature() -> tuple[tuple[str, int, int], ...]:
        project_root = Path(__file__).resolve().parents[2]
        migrations_dir = project_root / "migrations"
        if not migrations_dir.is_dir():
            return ()
        signature: list[tuple[str, int, int]] = []
        for path in sorted(migrations_dir.glob("*.sql")):
            stat = path.stat()
            signature.append((path.name, stat.st_mtime_ns, stat.st_size))
        return tuple(signature)

    def _apply_file_migrations(self) -> None:
        """Run idempotent `.sql` files in migrations/ in filename order.

        Migrations coexist with the inline schema in `_init_schema` — they
        are meant for tables added after the engine shipped (e.g. the web
        app's `web_requests`). Every migration must be re-runnable.
        """
        project_root = Path(__file__).resolve().parents[2]
        migrations_dir = project_root / "migrations"
        if not migrations_dir.is_dir():
            return
        for path in sorted(migrations_dir.glob("*.sql")):
            sql = path.read_text(encoding="utf-8")
            self.conn.executescript(sql)
        self._ensure_file_migration_columns()

    def _ensure_inline_table_columns(self) -> None:
        """Additive columns for tables owned by the inline schema.

        Same contract as `_ensure_file_migration_columns`: re-runnable on
        every open, so older databases pick up new columns.
        """
        self._ensure_columns("runs", {"status": "TEXT"})
        # Pre-status rows: completed runs are complete, the rest died mid-run.
        self.conn.execute(
            "UPDATE runs SET status = CASE WHEN completed_at IS NULL "
            "THEN 'interrupted' ELSE 'complete' END WHERE status IS NULL"
        )
        self.conn.commit()

    def _ensure_file_migration_columns(self) -> None:
        """Backfill columns for tables owned by SQL migrations.

        The `.sql` migrations are intentionally re-runnable. SQLite has no
        portable `ALTER TABLE ADD COLUMN IF NOT EXISTS`, so existing migrated
        databases get additive columns through this guarded Python path.
        """
        tables = {
            row["name"]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "web_requests" in tables:
            self._ensure_columns(
                "web_requests",
                {
                    "phase": "TEXT NOT NULL DEFAULT 'queued'",
                    "phase_updated_at": "TIMESTAMP",
                },
            )
            self.conn.commit()
        if "magnetism_scans" in tables:
            self._ensure_columns(
                "magnetism_scans",
                {
                    "status": "TEXT NOT NULL DEFAULT 'ready'",
                    "token": "TEXT",
                    "phase": "TEXT",
                    "phase_updated_at": "TIMESTAMP",
                    "error_message": "TEXT",
                    "input_type": "TEXT",
                    "input_value": "TEXT",
                    "source_run_id": "INTEGER",
                    "started_at": "TIMESTAMP",
                    "completed_at": "TIMESTAMP",
                },
            )
            self.conn.commit()
        if "brand_profiles" in tables:
            self._ensure_columns(
                "brand_profiles",
                {
                    "logo_url": "TEXT",
                    "profile_overrides_json": "TEXT NOT NULL DEFAULT '{}'",
                    "updated_by": "TEXT",
                },
            )
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS brands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL,
                url TEXT NOT NULL,
                domain TEXT,
                logo_key TEXT,
                logo_url TEXT,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                UNIQUE(brand_name, url)
            );

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_id INTEGER NOT NULL,
                brand_name TEXT NOT NULL,
                url TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                use_llm INTEGER NOT NULL,
                use_social INTEGER NOT NULL,
                llm_used INTEGER,
                social_scraped INTEGER,
                predicted_niche TEXT,
                predicted_subtype TEXT,
                niche_confidence REAL,
                niche_evidence_json TEXT,
                niche_alternatives_json TEXT,
                calibration_profile TEXT,
                profile_source TEXT,
                composite_score REAL,
                result_path TEXT,
                summary TEXT,
                status TEXT,
                FOREIGN KEY (brand_id) REFERENCES brands(id)
            );

            CREATE TABLE IF NOT EXISTS raw_inputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                dimension_name TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                value REAL NOT NULL,
                raw_value TEXT,
                confidence REAL NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                dimension_name TEXT NOT NULL,
                score REAL NOT NULL,
                insights_json TEXT NOT NULL,
                rules_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                dimension_name TEXT,
                feature_name TEXT,
                expected_score REAL,
                actual_score REAL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS reviewed_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                computed_composite_score REAL NOT NULL,
                reviewed_composite_score REAL NOT NULL,
                score_delta REAL NOT NULL,
                affected_dimensions_json TEXT NOT NULL,
                reason TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                created_at TEXT NOT NULL,
                based_on_score_integrity TEXT NOT NULL,
                review_status TEXT NOT NULL,
                technical_override INTEGER NOT NULL DEFAULT 0,
                technical_override_reason TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS evidence_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                url TEXT,
                quote TEXT,
                feature_name TEXT,
                dimension_name TEXT,
                confidence REAL NOT NULL DEFAULT 0,
                freshness_days REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE INDEX IF NOT EXISTS idx_evidence_items_run ON evidence_items(run_id);
            CREATE INDEX IF NOT EXISTS idx_evidence_items_dimension ON evidence_items(run_id, dimension_name);
            CREATE INDEX IF NOT EXISTS idx_reviewed_scores_run ON reviewed_scores(run_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS llm_cache (
                cache_key TEXT PRIMARY KEY,
                prompt_version TEXT NOT NULL,
                model TEXT NOT NULL,
                response_type TEXT NOT NULL,
                response_json TEXT,
                response_text TEXT,
                created_at TEXT NOT NULL,
                hit_count INTEGER NOT NULL DEFAULT 0,
                last_hit_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_llm_cache_model ON llm_cache(model, prompt_version);

            CREATE TABLE IF NOT EXISTS calibration_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT,
                scope TEXT NOT NULL,
                target TEXT NOT NULL,
                proposal_json TEXT NOT NULL,
                rationale TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'proposed',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL,
                url TEXT NOT NULL,
                before_run_id INTEGER NOT NULL,
                after_run_id INTEGER NOT NULL,
                candidate_ids_json TEXT NOT NULL,
                summary_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (before_run_id) REFERENCES runs(id),
                FOREIGN KEY (after_run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS calibration_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                dimensions_content TEXT NOT NULL,
                engine_content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS calibration_version_gate_configs (
                version_id INTEGER PRIMARY KEY,
                gate_config_json TEXT NOT NULL,
                FOREIGN KEY (version_id) REFERENCES calibration_versions(id)
            );

            CREATE TABLE IF NOT EXISTS applied_calibrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                version_before_id INTEGER NOT NULL,
                version_after_id INTEGER NOT NULL,
                applied_at TEXT NOT NULL,
                FOREIGN KEY (candidate_id) REFERENCES calibration_candidates(id),
                FOREIGN KEY (version_before_id) REFERENCES calibration_versions(id),
                FOREIGN KEY (version_after_id) REFERENCES calibration_versions(id)
            );

            CREATE TABLE IF NOT EXISTS experiment_versions (
                experiment_id INTEGER PRIMARY KEY,
                version_before_id INTEGER NOT NULL,
                version_after_id INTEGER NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id),
                FOREIGN KEY (version_before_id) REFERENCES calibration_versions(id),
                FOREIGN KEY (version_after_id) REFERENCES calibration_versions(id)
            );

            CREATE TABLE IF NOT EXISTS calibration_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                promoted_at TEXT NOT NULL,
                FOREIGN KEY (version_id) REFERENCES calibration_versions(id)
            );

            CREATE TABLE IF NOT EXISTS calibration_gate_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                gate_config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS run_audits (
                run_id INTEGER PRIMARY KEY,
                scoring_state_fingerprint TEXT NOT NULL,
                audit_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS experiment_audits (
                experiment_id INTEGER PRIMARY KEY,
                before_scoring_state_fingerprint TEXT,
                after_scoring_state_fingerprint TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            );

            CREATE TABLE IF NOT EXISTS analysis_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                brand_name TEXT,
                brand_domain TEXT,
                brand_logo_key TEXT,
                brand_logo_url TEXT,
                predicted_niche TEXT,
                predicted_subtype TEXT,
                niche_confidence REAL,
                calibration_profile TEXT,
                profile_source TEXT,
                use_llm INTEGER NOT NULL,
                use_social INTEGER NOT NULL,
                status TEXT NOT NULL,
                phase TEXT,
                cancel_requested INTEGER NOT NULL DEFAULT 0,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                requested_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                run_id INTEGER,
                error TEXT,
                result_json TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS analysis_job_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                phase TEXT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES analysis_jobs(id)
            );
            """
        )
        self._ensure_columns(
            "runs",
            {
                "predicted_niche": "TEXT",
                "predicted_subtype": "TEXT",
                "niche_confidence": "REAL",
                "niche_evidence_json": "TEXT",
                "niche_alternatives_json": "TEXT",
                "calibration_profile": "TEXT",
                "profile_source": "TEXT",
            },
        )
        self._ensure_columns(
            "brands",
            {
                "domain": "TEXT",
                "logo_key": "TEXT",
                "logo_url": "TEXT",
            },
        )
        self._ensure_columns(
            "analysis_jobs",
            {
                "brand_domain": "TEXT",
                "brand_logo_key": "TEXT",
                "brand_logo_url": "TEXT",
                "predicted_niche": "TEXT",
                "predicted_subtype": "TEXT",
                "niche_confidence": "REAL",
                "calibration_profile": "TEXT",
                "profile_source": "TEXT",
                "phase": "TEXT",
                "cancel_requested": "INTEGER NOT NULL DEFAULT 0",
                "attempt_count": "INTEGER NOT NULL DEFAULT 0",
            },
        )
        self.conn.commit()

    def _ensure_columns(self, table_name: str, columns: dict[str, str]) -> None:
        existing = {
            row["name"]
            for row in self.conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name in existing:
                continue
            self.conn.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )

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
        domain = _extract_domain(url)
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

    def save_features(self, run_id: int, features_by_dim: dict[str, dict[str, FeatureValue]]) -> None:
        rows = []
        now = datetime.now().isoformat()
        for dimension_name, features in features_by_dim.items():
            for feature_name, feature in features.items():
                rows.append(
                    (
                        run_id,
                        dimension_name,
                        feature_name,
                        float(feature.value),
                        None if feature.raw_value is None else str(feature.raw_value),
                        float(feature.confidence),
                        feature.source,
                        now,
                    )
                )
        self.conn.executemany(
            """
            INSERT INTO features (
                run_id, dimension_name, feature_name, value,
                raw_value, confidence, source, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def save_scores(self, run_id: int, brand_score: BrandScore) -> None:
        rows = []
        now = datetime.now().isoformat()
        for dimension_name, dimension_score in brand_score.dimensions.items():
            if dimension_score.score is None:
                continue
            rows.append(
                (
                    run_id,
                    dimension_name,
                    float(dimension_score.score),
                    _json_dumps(dimension_score.insights),
                    _json_dumps(dimension_score.rules_applied),
                    now,
                )
            )
        if rows:
            self.conn.executemany(
                """
                INSERT INTO scores (run_id, dimension_name, score, insights_json, rules_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
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

    def save_run_audit(self, run_id: int, audit: dict[str, Any]) -> None:
        fingerprint = str(audit["scoring_state_fingerprint"])
        self.conn.execute(
            """
            INSERT INTO run_audits (run_id, scoring_state_fingerprint, audit_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                scoring_state_fingerprint=excluded.scoring_state_fingerprint,
                audit_json=excluded.audit_json,
                created_at=excluded.created_at
            """,
            (
                run_id,
                fingerprint,
                _json_dumps(audit),
                datetime.now().isoformat(),
            ),
        )
        self.conn.commit()

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

    def _load_reviewed_score_row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if not row:
            return None
        item = dict(row)
        affected_dimensions, affected_dimensions_error = _safe_json_loads(
            item.pop("affected_dimensions_json", None),
            field="reviewed_scores.affected_dimensions_json",
            fallback=[],
        )
        evidence_refs, evidence_refs_error = _safe_json_loads(
            item.pop("evidence_refs_json", None),
            field="reviewed_scores.evidence_refs_json",
            fallback=[],
        )
        item["affected_dimensions"] = affected_dimensions
        item["evidence_refs"] = evidence_refs
        if affected_dimensions_error:
            item["affected_dimensions_error"] = affected_dimensions_error
        if evidence_refs_error:
            item["evidence_refs_error"] = evidence_refs_error
        item["technical_override"] = bool(item.get("technical_override"))
        return item

    def save_reviewed_score(
        self,
        run_id: int,
        reviewed_composite_score: float,
        *,
        reason: str,
        evidence_refs: list[str],
        reviewer: str,
        affected_dimensions: list[str],
        review_status: str,
        technical_override: bool = False,
        technical_override_reason: str | None = None,
    ) -> int:
        from ..scoring.replay import build_score_replay_audit

        reason_text = str(reason or "").strip()
        reviewer_text = str(reviewer or "").strip()
        review_status_text = str(review_status or "").strip()
        if not reason_text:
            raise ValueError("reviewed score reason is required")
        if not reviewer_text:
            raise ValueError("reviewer is required")
        if not review_status_text:
            raise ValueError("review_status is required")

        if reviewed_composite_score is None:
            raise ValueError("reviewed_composite_score is required")
        reviewed_value = float(reviewed_composite_score)
        if not 0.0 <= reviewed_value <= 100.0:
            raise ValueError("reviewed_composite_score must be between 0 and 100")

        dimensions = []
        seen_dimensions = set()
        for dimension_name in affected_dimensions or []:
            dimension_text = str(dimension_name or "").strip()
            if not dimension_text:
                continue
            if dimension_text not in DIMENSIONS:
                raise ValueError(f"unknown affected dimension: {dimension_text}")
            if dimension_text not in seen_dimensions:
                seen_dimensions.add(dimension_text)
                dimensions.append(dimension_text)
        if not dimensions:
            raise ValueError("affected_dimensions must include at least one known scoring dimension")

        evidence_list = []
        for ref in evidence_refs or []:
            ref_text = str(ref or "").strip()
            if ref_text:
                evidence_list.append(ref_text)

        snapshot = self.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"run_id {run_id} could not be replayed for review")
        run = snapshot.get("run") or {}
        computed_composite = run.get("composite_score")
        if computed_composite is None:
            raise ValueError("computed composite score is missing for this run")
        computed_value = float(computed_composite)
        score_delta = round(reviewed_value - computed_value, 1)

        if score_delta != 0.0 and not evidence_list:
            raise ValueError("evidence_refs are required when reviewed score changes the computed score")

        replay_audit = build_score_replay_audit(self, run_id, snapshot=snapshot)
        based_on_score_integrity = str(replay_audit.get("score_integrity") or "unverifiable")
        if based_on_score_integrity == "drift_detected" and not technical_override:
            raise ValueError("technical override is required when replay integrity is drift_detected")
        if technical_override and not str(technical_override_reason or "").strip():
            raise ValueError("technical_override_reason is required when technical_override is set")

        cursor = self.conn.execute(
            """
            INSERT INTO reviewed_scores (
                run_id, computed_composite_score, reviewed_composite_score, score_delta,
                affected_dimensions_json, reason, evidence_refs_json, reviewer,
                created_at, based_on_score_integrity, review_status,
                technical_override, technical_override_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                computed_value,
                reviewed_value,
                score_delta,
                _json_dumps(dimensions),
                reason_text,
                _json_dumps(evidence_list),
                reviewer_text,
                datetime.now().isoformat(),
                based_on_score_integrity,
                review_status_text,
                int(bool(technical_override)),
                str(technical_override_reason).strip() if technical_override_reason is not None else None,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_reviewed_score(self, run_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT rs.id, rs.run_id, runs.brand_name, runs.url,
                   rs.computed_composite_score, rs.reviewed_composite_score, rs.score_delta,
                   rs.affected_dimensions_json, rs.reason, rs.evidence_refs_json,
                   rs.reviewer, rs.created_at, rs.based_on_score_integrity,
                   rs.review_status, rs.technical_override, rs.technical_override_reason
            FROM reviewed_scores rs
            JOIN runs ON runs.id = rs.run_id
            WHERE rs.run_id = ?
            ORDER BY rs.created_at DESC, rs.id DESC
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
        return self._load_reviewed_score_row(row)

    def list_reviewed_scores(
        self,
        brand_name: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if brand_name:
            clauses.append("runs.brand_name = ?")
            params.append(brand_name)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT rs.id, rs.run_id, runs.brand_name, runs.url,
                   rs.computed_composite_score, rs.reviewed_composite_score, rs.score_delta,
                   rs.affected_dimensions_json, rs.reason, rs.evidence_refs_json,
                   rs.reviewer, rs.created_at, rs.based_on_score_integrity,
                   rs.review_status, rs.technical_override, rs.technical_override_reason
            FROM reviewed_scores rs
            JOIN runs ON runs.id = rs.run_id
            {where}
            ORDER BY rs.created_at DESC, rs.id DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        return [item for row in rows if (item := self._load_reviewed_score_row(row)) is not None]

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

    def save_calibration_candidate(
        self,
        scope: str,
        target: str,
        proposal: dict[str, Any],
        rationale: str,
        brand_name: str | None = None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO calibration_candidates (
                brand_name, scope, target, proposal_json, rationale, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, 'proposed', ?)
            """,
            (
                brand_name,
                scope,
                target,
                _json_dumps(proposal),
                rationale,
                datetime.now().isoformat(),
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_calibration_candidates(
        self,
        brand_name: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses = []
        params = []
        if brand_name:
            clauses.append("(brand_name = ? OR brand_name IS NULL)")
            params.append(brand_name)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT id, brand_name, scope, target, proposal_json, rationale, status, created_at
            FROM calibration_candidates
            {where}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        parsed = []
        for row in rows:
            item = dict(row)
            item["proposal"] = json.loads(item.pop("proposal_json"))
            parsed.append(item)
        return parsed

    def get_calibration_candidate(self, candidate_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT id, brand_name, scope, target, proposal_json, rationale, status, created_at
            FROM calibration_candidates
            WHERE id = ?
            """,
            (candidate_id,),
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["proposal"] = json.loads(item.pop("proposal_json"))
        return item

    def update_calibration_candidate_status(self, candidate_id: int, status: str) -> None:
        self.conn.execute(
            """
            UPDATE calibration_candidates
            SET status = ?
            WHERE id = ?
            """,
            (status, candidate_id),
        )
        self.conn.commit()

    def save_experiment(
        self,
        brand_name: str,
        url: str,
        before_run_id: int,
        after_run_id: int,
        candidate_ids: list[int],
        summary: dict[str, Any],
        version_before_id: int | None = None,
        version_after_id: int | None = None,
        before_scoring_state_fingerprint: str | None = None,
        after_scoring_state_fingerprint: str | None = None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO experiments (
                brand_name, url, before_run_id, after_run_id,
                candidate_ids_json, summary_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brand_name,
                url,
                before_run_id,
                after_run_id,
                _json_dumps(candidate_ids),
                _json_dumps(summary),
                datetime.now().isoformat(),
            ),
        )
        experiment_id = int(cursor.lastrowid)
        if version_before_id is not None and version_after_id is not None:
            self.conn.execute(
                """
                INSERT INTO experiment_versions (experiment_id, version_before_id, version_after_id)
                VALUES (?, ?, ?)
                """,
                (experiment_id, version_before_id, version_after_id),
            )
        if before_scoring_state_fingerprint is not None or after_scoring_state_fingerprint is not None:
            self.conn.execute(
                """
                INSERT INTO experiment_audits (
                    experiment_id, before_scoring_state_fingerprint,
                    after_scoring_state_fingerprint, created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    before_scoring_state_fingerprint,
                    after_scoring_state_fingerprint,
                    datetime.now().isoformat(),
                ),
            )
        self.conn.commit()
        return experiment_id

    def list_experiments(self, brand_name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        clauses = []
        params = []
        if brand_name:
            clauses.append("brand_name = ?")
            params.append(brand_name)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT id, brand_name, url, before_run_id, after_run_id,
                   candidate_ids_json, summary_json, created_at
            FROM experiments
            {where}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        experiments = []
        for row in rows:
            item = dict(row)
            item["candidate_ids"] = json.loads(item.pop("candidate_ids_json"))
            item["summary"] = json.loads(item.pop("summary_json"))
            version_row = self.conn.execute(
                """
                SELECT version_before_id, version_after_id
                FROM experiment_versions
                WHERE experiment_id = ?
                """,
                (item["id"],),
            ).fetchone()
            if version_row:
                item["version_before_id"] = int(version_row["version_before_id"])
                item["version_after_id"] = int(version_row["version_after_id"])
            audit_row = self.conn.execute(
                """
                SELECT before_scoring_state_fingerprint, after_scoring_state_fingerprint
                FROM experiment_audits
                WHERE experiment_id = ?
                """,
                (item["id"],),
            ).fetchone()
            if audit_row:
                item["before_scoring_state_fingerprint"] = audit_row["before_scoring_state_fingerprint"]
                item["after_scoring_state_fingerprint"] = audit_row["after_scoring_state_fingerprint"]
            experiments.append(item)
        return experiments

    def get_latest_experiment_for_version(
        self,
        version_id: int,
        brand_name: str | None = None,
    ) -> dict[str, Any] | None:
        clauses = ["experiment_versions.version_after_id = ?"]
        params: list[Any] = [version_id]
        if brand_name:
            clauses.append("experiments.brand_name = ?")
            params.append(brand_name)
        where = " AND ".join(clauses)
        row = self.conn.execute(
            f"""
            SELECT experiments.id, experiments.brand_name, experiments.url,
                   experiments.before_run_id, experiments.after_run_id,
                   experiments.candidate_ids_json, experiments.summary_json,
                   experiments.created_at, experiment_versions.version_before_id,
                   experiment_versions.version_after_id
            FROM experiments
            JOIN experiment_versions ON experiment_versions.experiment_id = experiments.id
            WHERE {where}
            ORDER BY experiments.created_at DESC
            LIMIT 1
            """,
            params,
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["candidate_ids"] = json.loads(item.pop("candidate_ids_json"))
        item["summary"] = json.loads(item.pop("summary_json"))
        audit_row = self.conn.execute(
            """
            SELECT before_scoring_state_fingerprint, after_scoring_state_fingerprint
            FROM experiment_audits
            WHERE experiment_id = ?
            """,
            (item["id"],),
        ).fetchone()
        if audit_row:
            item["before_scoring_state_fingerprint"] = audit_row["before_scoring_state_fingerprint"]
            item["after_scoring_state_fingerprint"] = audit_row["after_scoring_state_fingerprint"]
        return item

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
