"""SQLite persistence for Brand3 Scoring runs."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..models.brand import BrandScore, FeatureValue


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _duration_seconds(start: str | None, end: str | None) -> float | None:
    start_dt = _parse_iso(start)
    end_dt = _parse_iso(end)
    if not start_dt or not end_dt:
        return None
    return round((end_dt - start_dt).total_seconds(), 3)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _slugify(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    slug = "-".join(part for part in cleaned.split("-") if part)
    return slug or None


def _infer_logo_key(brand_name: str | None, domain: str | None) -> str | None:
    brand_slug = _slugify(brand_name)
    if brand_slug:
        return brand_slug
    if not domain:
        return None
    root = domain.split(".")[0]
    return _slugify(root)


def _build_brand_profile(
    brand_name: str | None,
    url: str | None,
    logo_url: str | None = None,
) -> dict[str, Any]:
    domain = _extract_domain(url)
    return {
        "name": brand_name,
        "domain": domain,
        "logo_key": _infer_logo_key(brand_name, domain),
        "logo_url": logo_url,
    }


def _brand_profile_from_record(
    record: dict[str, Any],
    *,
    name_field: str = "brand_name",
    url_field: str = "url",
    domain_field: str = "brand_domain",
    logo_key_field: str = "brand_logo_key",
    logo_url_field: str = "brand_logo_url",
) -> dict[str, Any]:
    profile = _build_brand_profile(
        record.get(name_field),
        record.get(url_field),
        record.get(logo_url_field),
    )
    if record.get(domain_field):
        profile["domain"] = record[domain_field]
    if record.get(logo_key_field):
        profile["logo_key"] = record[logo_key_field]
    if record.get(logo_url_field):
        profile["logo_url"] = record[logo_url_field]
    return profile


class SQLiteStore:
    """Persists runs, raw collector inputs, features, and scores in SQLite."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;

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
            INSERT INTO runs (brand_id, brand_name, url, started_at, use_llm, use_social)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (brand_id, brand_name, url, datetime.now().isoformat(), int(use_llm), int(use_social)),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def save_raw_input(self, run_id: int, source: str, payload: Any) -> None:
        self.conn.execute(
            """
            INSERT INTO raw_inputs (run_id, source, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, source, _json_dumps(_to_jsonable(payload)), datetime.now().isoformat()),
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

    def get_latest_raw_input(
        self,
        brand_name: str,
        url: str,
        source: str,
        max_age_hours: int = 24,
    ) -> Any | None:
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
        row = self.conn.execute(
            """
            SELECT raw_inputs.payload_json
            FROM raw_inputs
            JOIN runs ON runs.id = raw_inputs.run_id
            WHERE runs.brand_name = ?
              AND runs.url = ?
              AND raw_inputs.source = ?
              AND raw_inputs.created_at >= ?
            ORDER BY raw_inputs.created_at DESC
            LIMIT 1
            """,
            (brand_name, url, source, cutoff_iso),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])

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
            SET completed_at=?,
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

    def create_analysis_job(
        self,
        url: str,
        brand_name: str | None,
        use_llm: bool,
        use_social: bool,
    ) -> int:
        profile = _build_brand_profile(brand_name, url)
        cursor = self.conn.execute(
            """
            INSERT INTO analysis_jobs (
                url, brand_name, brand_domain, brand_logo_key, brand_logo_url,
                use_llm, use_social, status, phase, requested_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', 'queued', ?)
            """,
            (
                url,
                brand_name,
                profile["domain"],
                profile["logo_key"],
                profile["logo_url"],
                int(use_llm),
                int(use_social),
                datetime.now().isoformat(),
            ),
        )
        self.conn.commit()
        job_id = int(cursor.lastrowid)
        self.add_analysis_job_event(job_id, phase="queued", level="info", message="Job queued")
        return job_id

    def start_analysis_job(self, job_id: int) -> None:
        self.conn.execute(
            """
            UPDATE analysis_jobs
            SET status='running',
                phase='collecting',
                started_at=?,
                completed_at=NULL,
                error=NULL,
                run_id=NULL,
                result_json=NULL,
                attempt_count=COALESCE(attempt_count, 0) + 1
            WHERE id=?
            """,
            (datetime.now().isoformat(), job_id),
        )
        self.conn.commit()
        self.add_analysis_job_event(job_id, phase="collecting", level="info", message="Job started")

    def claim_pending_job(
        self,
        job_id: int | None = None,
        worker_id: str | None = None,
    ) -> dict | None:
        """Atomically transition a queued job to running.

        If job_id is None, picks the oldest queued job. Returns the job row or None
        if nothing was claimable (no queued jobs, or another worker won the race).
        Safe for multiple workers against the same SQLite DB in WAL mode.
        """
        if job_id is None:
            row = self.conn.execute(
                """
                SELECT id FROM analysis_jobs
                WHERE status='queued' AND cancel_requested=0
                ORDER BY requested_at ASC, id ASC
                LIMIT 1
                """
            ).fetchone()
            if not row:
                return None
            job_id = int(row["id"])

        cursor = self.conn.execute(
            """
            UPDATE analysis_jobs
            SET status='running',
                phase='collecting',
                started_at=?,
                completed_at=NULL,
                error=NULL,
                run_id=NULL,
                result_json=NULL,
                attempt_count=COALESCE(attempt_count, 0) + 1
            WHERE id=? AND status='queued' AND cancel_requested=0
            """,
            (datetime.now().isoformat(), job_id),
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            return None

        suffix = f" by {worker_id}" if worker_id else ""
        self.add_analysis_job_event(
            job_id,
            phase="collecting",
            level="info",
            message=f"Job claimed{suffix}",
        )
        return self.get_analysis_job(job_id)

    def update_analysis_job_phase(self, job_id: int, phase: str) -> None:
        row = self.conn.execute(
            "SELECT phase FROM analysis_jobs WHERE id=?",
            (job_id,),
        ).fetchone()
        if row and row["phase"] == phase:
            return
        self.conn.execute(
            """
            UPDATE analysis_jobs
            SET phase=?
            WHERE id=?
            """,
            (phase, job_id),
        )
        self.conn.commit()
        self.add_analysis_job_event(job_id, phase=phase, level="info", message=f"Entered phase: {phase}")

    def request_analysis_job_cancel(self, job_id: int) -> None:
        row = self.conn.execute(
            "SELECT status FROM analysis_jobs WHERE id=?",
            (job_id,),
        ).fetchone()
        if not row:
            return
        status = row["status"]
        now = datetime.now().isoformat()
        if status == "queued":
            self.conn.execute(
                """
                UPDATE analysis_jobs
                SET status='cancelled',
                    phase='cancelled',
                    cancel_requested=1,
                    completed_at=?,
                    error='Cancelled by user'
                WHERE id=?
                """,
                (now, job_id),
            )
        elif status == "running":
            self.conn.execute(
                """
                UPDATE analysis_jobs
                SET cancel_requested=1
                WHERE id=?
                """,
                (job_id,),
            )
        self.conn.commit()
        self.add_analysis_job_event(job_id, phase="cancelled", level="warning", message="Cancellation requested")

    def cancel_analysis_job(self, job_id: int, reason: str = "Cancelled by user") -> None:
        self.conn.execute(
            """
            UPDATE analysis_jobs
            SET status='cancelled',
                phase='cancelled',
                cancel_requested=1,
                completed_at=?,
                error=?
            WHERE id=?
            """,
            (datetime.now().isoformat(), reason, job_id),
        )
        self.conn.commit()
        self.add_analysis_job_event(job_id, phase="cancelled", level="warning", message=reason)

    def requeue_analysis_job(self, job_id: int) -> None:
        self.conn.execute(
            """
            UPDATE analysis_jobs
            SET status='queued',
                phase='queued',
                cancel_requested=0,
                requested_at=?,
                started_at=NULL,
                completed_at=NULL,
                run_id=NULL,
                error=NULL,
                result_json=NULL
            WHERE id=?
            """,
            (datetime.now().isoformat(), job_id),
        )
        self.conn.commit()
        self.add_analysis_job_event(job_id, phase="queued", level="info", message="Job re-queued")

    def complete_analysis_job(self, job_id: int, run_id: int | None, result: dict[str, Any]) -> None:
        niche_prediction = result.get("niche_classification", {})
        niche_confidence = niche_prediction.get("confidence")
        self.conn.execute(
            """
            UPDATE analysis_jobs
            SET status='done',
                phase='done',
                cancel_requested=0,
                predicted_niche=?,
                predicted_subtype=?,
                niche_confidence=?,
                calibration_profile=?,
                profile_source=?,
                completed_at=?,
                run_id=?,
                result_json=?
            WHERE id=?
            """,
            (
                niche_prediction.get("predicted_niche"),
                niche_prediction.get("predicted_subtype"),
                None if niche_confidence is None else float(niche_confidence),
                result.get("calibration_profile"),
                result.get("profile_source"),
                datetime.now().isoformat(),
                run_id,
                _json_dumps(result),
                job_id,
            ),
        )
        self.conn.commit()
        self.add_analysis_job_event(job_id, phase="done", level="info", message="Job completed successfully")

    def fail_analysis_job(self, job_id: int, error: str) -> None:
        self.conn.execute(
            """
            UPDATE analysis_jobs
            SET status='failed',
                phase='failed',
                completed_at=?,
                error=?
            WHERE id=?
            """,
            (datetime.now().isoformat(), error, job_id),
        )
        self.conn.commit()
        self.add_analysis_job_event(job_id, phase="failed", level="error", message=error)

    def add_analysis_job_event(self, job_id: int, phase: str | None, level: str, message: str) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO analysis_job_events (job_id, phase, level, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, phase, level, message, datetime.now().isoformat()),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_analysis_job_events(self, job_id: int, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id, job_id, phase, level, message, created_at
            FROM analysis_job_events
            WHERE job_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (job_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_analysis_job(self, job_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT id, url, brand_name, brand_domain, brand_logo_key, brand_logo_url,
                   predicted_niche, predicted_subtype, niche_confidence, calibration_profile, profile_source,
                   use_llm, use_social, status, phase,
                   cancel_requested, attempt_count, requested_at, started_at,
                   completed_at, run_id, error, result_json
            FROM analysis_jobs
            WHERE id=?
            """,
            (job_id,),
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        if item.get("result_json"):
            item["result"] = json.loads(item.pop("result_json"))
        else:
            item.pop("result_json", None)
        item["brand_profile"] = _brand_profile_from_record(item)
        item["queue_duration_seconds"] = _duration_seconds(item.get("requested_at"), item.get("started_at"))
        item["run_duration_seconds"] = _duration_seconds(item.get("started_at"), item.get("completed_at"))
        item["total_duration_seconds"] = _duration_seconds(item.get("requested_at"), item.get("completed_at"))
        item["events"] = self.list_analysis_job_events(job_id)
        return item

    def list_analysis_jobs(
        self,
        brand_name: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if brand_name:
            clauses.append("brand_name = ?")
            params.append(brand_name)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT id, url, brand_name, brand_domain, brand_logo_key, brand_logo_url,
                   predicted_niche, predicted_subtype, niche_confidence, calibration_profile, profile_source,
                   use_llm, use_social, status, phase,
                   cancel_requested, attempt_count, requested_at, started_at,
                   completed_at, run_id, error, result_json
            FROM analysis_jobs
            {where}
            ORDER BY requested_at DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        jobs = []
        for row in rows:
            item = dict(row)
            if item.get("result_json"):
                item["result"] = json.loads(item.pop("result_json"))
            else:
                item.pop("result_json", None)
            item["brand_profile"] = _brand_profile_from_record(item)
            item["queue_duration_seconds"] = _duration_seconds(item.get("requested_at"), item.get("started_at"))
            item["run_duration_seconds"] = _duration_seconds(item.get("started_at"), item.get("completed_at"))
            item["total_duration_seconds"] = _duration_seconds(item.get("requested_at"), item.get("completed_at"))
            jobs.append(item)
        return jobs

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

        run_payload = dict(run)
        audit_json = run_payload.pop("audit_json", None)
        if audit_json:
            run_payload["audit"] = json.loads(audit_json)
        run_payload["niche_evidence"] = json.loads(run_payload.pop("niche_evidence_json") or "[]")
        run_payload["niche_alternatives"] = json.loads(run_payload.pop("niche_alternatives_json") or "[]")
        run_payload["brand_profile"] = _brand_profile_from_record(run_payload)
        run_payload["run_duration_seconds"] = _duration_seconds(
            run_payload.get("started_at"),
            run_payload.get("completed_at"),
        )

        return {
            "run": run_payload,
            "scores": [dict(row) for row in scores],
            "features": [dict(row) for row in features],
            "annotations": [dict(row) for row in annotations],
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
