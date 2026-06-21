"""SQLite persistence for Brand3 Scoring runs."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from .analysis_jobs import AnalysisJobsStoreMixin
from .annotations_reports import AnnotationsReportsStoreMixin
from .brand_runs import BrandRunsStoreMixin
from .calibration_candidates import CalibrationCandidatesStoreMixin
from .calibration_versions import CalibrationVersionsStoreMixin
from .evidence_items import EvidenceItemsStoreMixin
from .experiments import ExperimentsStoreMixin
from .features_scores import FeaturesScoresStoreMixin
from .json_payloads import MalformedJSONPayload as _MalformedJSONPayload
from .llm_cache import LLMCacheStoreMixin
from .raw_inputs import RawInputsStoreMixin
from .reviewed_scores import ReviewedScoresStoreMixin
from .run_audits import RunAuditsStoreMixin
from .run_snapshots import RunSnapshotsStoreMixin


class SQLiteStore(
    AnalysisJobsStoreMixin,
    RawInputsStoreMixin,
    EvidenceItemsStoreMixin,
    LLMCacheStoreMixin,
    ReviewedScoresStoreMixin,
    CalibrationCandidatesStoreMixin,
    ExperimentsStoreMixin,
    CalibrationVersionsStoreMixin,
    FeaturesScoresStoreMixin,
    BrandRunsStoreMixin,
    RunAuditsStoreMixin,
    RunSnapshotsStoreMixin,
    AnnotationsReportsStoreMixin,
):
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
