"""Analysis job persistence mixin for SQLiteStore."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .brand_profiles import brand_profile_from_record, build_brand_profile
from .json_payloads import json_dumps, safe_json_loads
from .time_utils import duration_seconds


class AnalysisJobsStoreMixin:
    def create_analysis_job(
        self,
        url: str,
        brand_name: str | None,
        use_llm: bool,
        use_social: bool,
    ) -> int:
        profile = build_brand_profile(brand_name, url)
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
                json_dumps(result),
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
        result_json = item.pop("result_json", None)
        result, error = safe_json_loads(
            result_json,
            field="analysis_jobs.result_json",
            fallback=None,
        )
        if error:
            item["result"] = None
            item["result_error"] = error
        elif result is not None:
            item["result"] = result
        item["brand_profile"] = brand_profile_from_record(item)
        item["queue_duration_seconds"] = duration_seconds(item.get("requested_at"), item.get("started_at"))
        item["run_duration_seconds"] = duration_seconds(item.get("started_at"), item.get("completed_at"))
        item["total_duration_seconds"] = duration_seconds(item.get("requested_at"), item.get("completed_at"))
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
            result_json = item.pop("result_json", None)
            result, error = safe_json_loads(
                result_json,
                field="analysis_jobs.result_json",
                fallback=None,
            )
            if error:
                item["result"] = None
                item["result_error"] = error
            elif result is not None:
                item["result"] = result
            item["brand_profile"] = brand_profile_from_record(item)
            item["queue_duration_seconds"] = duration_seconds(item.get("requested_at"), item.get("started_at"))
            item["run_duration_seconds"] = duration_seconds(item.get("started_at"), item.get("completed_at"))
            item["total_duration_seconds"] = duration_seconds(item.get("requested_at"), item.get("completed_at"))
            jobs.append(item)
        return jobs
