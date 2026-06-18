"""Tests for the polling worker and atomic claim."""

import asyncio
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.services import brand_service
from src.storage.sqlite_store import SQLiteStore
from src.sv9.models import ComponentResult, Sv9ScanResult, STATUS_SCORED
from src.sv9.rubric import RUBRIC_VERSION
from src.sv9.store import Sv9Store
from src.workers import job_runner
from web.workers import queue as web_queue


class ClaimPendingJobTests(unittest.TestCase):
    def _store(self, tmpdir: str) -> SQLiteStore:
        return SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))

    def test_claims_oldest_queued_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self._store(tmpdir)
            first = store.create_analysis_job(url="https://a.com", brand_name="A", use_llm=False, use_social=False)
            second = store.create_analysis_job(url="https://b.com", brand_name="B", use_llm=False, use_social=False)

            claimed = store.claim_pending_job()
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["id"], first)
            self.assertEqual(claimed["status"], "running")
            self.assertEqual(claimed["attempt_count"], 1)

            next_claim = store.claim_pending_job()
            self.assertEqual(next_claim["id"], second)
            store.close()

    def test_returns_none_when_queue_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self._store(tmpdir)
            self.assertIsNone(store.claim_pending_job())
            store.close()

    def test_skips_cancel_requested_jobs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self._store(tmpdir)
            cancelled_id = store.create_analysis_job(url="https://a.com", brand_name="A", use_llm=False, use_social=False)
            good_id = store.create_analysis_job(url="https://b.com", brand_name="B", use_llm=False, use_social=False)
            store.request_analysis_job_cancel(cancelled_id)

            claimed = store.claim_pending_job()
            self.assertEqual(claimed["id"], good_id)
            store.close()

    def test_second_worker_on_same_job_gets_none(self):
        """Simulates two workers racing for the same specific job id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_a = self._store(tmpdir)
            store_b = self._store(tmpdir)
            job_id = store_a.create_analysis_job(url="https://a.com", brand_name="A", use_llm=False, use_social=False)

            first = store_a.claim_pending_job(job_id=job_id)
            second = store_b.claim_pending_job(job_id=job_id)

            self.assertIsNotNone(first)
            self.assertIsNone(second)
            store_a.close()
            store_b.close()

    def test_claim_by_id_only_claims_queued(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self._store(tmpdir)
            job_id = store.create_analysis_job(url="https://a.com", brand_name="A", use_llm=False, use_social=False)
            store.fail_analysis_job(job_id, "boom")

            claimed = store.claim_pending_job(job_id=job_id)
            self.assertIsNone(claimed)
            store.close()


class ExecuteAnalysisJobTests(unittest.TestCase):
    """Regression: legacy execute_analysis_job still works via claim_pending_job."""

    def test_execute_runs_pipeline_after_atomic_claim(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            job_id = store.create_analysis_job(
                url="https://example.com",
                brand_name="Example",
                use_llm=False,
                use_social=False,
            )
            store.close()

            with patch.object(brand_service, "BRAND3_DB_PATH", str(db_path)):
                with patch.object(
                    brand_service,
                    "run",
                    return_value={"brand": "Example", "url": "https://example.com", "run_id": 1, "composite_score": 50.0},
                ):
                    payload = brand_service.execute_analysis_job(job_id)

            self.assertEqual(payload["status"], "done")
            self.assertEqual(payload["attempt_count"], 1)


class Sv9MaterializationTests(unittest.TestCase):
    def _db_path(self, tmpdir: str) -> Path:
        db_path = Path(tmpdir) / "brand3.sqlite3"
        store = SQLiteStore(str(db_path))
        store.close()
        return db_path

    def _sv9_result(self, source_run_id: int, *, brand_name: str = "Acme") -> Sv9ScanResult:
        return Sv9ScanResult(
            brand_name=brand_name,
            url="https://acme.test",
            source_run_id=source_run_id,
            brand3_score=42,
            components={
                "mission": ComponentResult(
                    component="mission",
                    status=STATUS_SCORED,
                    score=2,
                    detected_content="A clear mission.",
                    evidence=["Owned page"],
                )
            },
        )

    def test_materializes_sv9_scan_for_completed_magnetism_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = self._db_path(tmpdir)

            def fake_materialize(run_id, *, db_path, **kwargs):
                # The real materialize_sv9_scan persists the scan and returns
                # (scan_id, result); the fake mirrors that contract.
                result = self._sv9_result(run_id)
                store = Sv9Store(db_path)
                try:
                    scan_id = store.save_scan(result)
                finally:
                    store.close()
                return scan_id, result

            with patch.object(web_queue, "_db_path", return_value=db_path):
                with patch(
                    "src.sv9.service.materialize_sv9_scan",
                    side_effect=fake_materialize,
                ) as materialize:
                    scan_id = web_queue._ensure_sv9_scan_for_magnetism_result(
                        {"source_run_id": 123}
                    )

            self.assertIsInstance(scan_id, int)
            materialize.assert_called_once_with(123, db_path=str(db_path))
            sv9_store = Sv9Store(str(db_path))
            try:
                scan = sv9_store.get_scan_for_run(123, rubric_version=RUBRIC_VERSION)
            finally:
                sv9_store.close()
            self.assertIsNotNone(scan)
            self.assertEqual(scan["brand_name"], "Acme")
            self.assertEqual(scan["brand3_score"], 42)

    def test_materialization_reuses_completed_magnetism_payload_as_sv9_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = self._db_path(tmpdir)
            magnetism_payload = {
                "source_run_id": 123,
                "brand_name": "Acme",
                "source_url": "https://acme.test",
                "tldr_brand3": {
                    "mission": {"detected": True, "content": "A clear mission."}
                },
            }

            def fake_materialize(run_id, *, db_path, **kwargs):
                store = Sv9Store(db_path)
                try:
                    detection = store.get_detection(run_id)
                    self.assertEqual(detection, magnetism_payload)
                    scan_id = store.save_scan(self._sv9_result(run_id))
                finally:
                    store.close()
                return scan_id, self._sv9_result(run_id)

            with patch.object(web_queue, "_db_path", return_value=db_path):
                with patch(
                    "src.sv9.service.materialize_sv9_scan",
                    side_effect=fake_materialize,
                ) as materialize:
                    scan_id = web_queue._ensure_sv9_scan_for_magnetism_result(magnetism_payload)

            self.assertIsInstance(scan_id, int)
            materialize.assert_called_once_with(123, db_path=str(db_path))

    def test_materialization_is_idempotent_for_current_rubric(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = self._db_path(tmpdir)
            sv9_store = Sv9Store(str(db_path))
            try:
                existing_id = sv9_store.save_scan(
                    self._sv9_result(123, brand_name="Existing")
                )
            finally:
                sv9_store.close()

            with patch.object(web_queue, "_db_path", return_value=db_path):
                with patch("src.sv9.service.materialize_sv9_scan") as materialize:
                    scan_id = web_queue._ensure_sv9_scan_for_magnetism_result(
                        {"source_run_id": 123}
                    )

            self.assertEqual(scan_id, existing_id)
            materialize.assert_not_called()
            with sqlite3.connect(str(db_path)) as conn:
                count = conn.execute("SELECT COUNT(*) FROM sv9_scans WHERE source_run_id = 123").fetchone()[0]
            self.assertEqual(count, 1)

    def test_materialization_failure_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = self._db_path(tmpdir)
            with patch.object(web_queue, "_db_path", return_value=db_path):
                with patch(
                    "src.sv9.service.materialize_sv9_scan",
                    side_effect=RuntimeError("llm unavailable"),
                ):
                    scan_id = web_queue._ensure_sv9_scan_for_magnetism_result({"source_run_id": 123})

            self.assertIsNone(scan_id)
            with sqlite3.connect(str(db_path)) as conn:
                count = conn.execute("SELECT COUNT(*) FROM sv9_scans").fetchone()[0]
            self.assertEqual(count, 0)


class MagnetismWorkerRoutingTests(unittest.TestCase):
    def tearDown(self):
        web_queue.set_run_magnetism_override(None)

    def test_url_magnetism_uses_service_role_router_without_injected_llm(self):
        captured = {}
        phases = []

        def fake_run(url, *, llm=None, progress_cb=None):
            captured["url"] = url
            captured["llm"] = llm
            captured["progress_cb"] = progress_cb
            return {"ok": True}

        with patch(
            "src.services.magnetism_service.run_magnetism_from_url",
            side_effect=fake_run,
        ):
            result = web_queue._call_magnetism_engine(
                {"input_type": "url", "input_value": "https://example.com"},
                progress_cb=phases.append,
            )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["url"], "https://example.com")
        self.assertIsNone(captured["llm"])
        self.assertIsNotNone(captured["progress_cb"])
        self.assertEqual(phases, ["collecting"])

    def test_audit_run_magnetism_uses_service_role_router_without_injected_llm(self):
        captured = {}
        phases = []

        def fake_run(run_id, *, llm=None):
            captured["run_id"] = run_id
            captured["llm"] = llm
            return {"ok": True}

        with patch(
            "src.services.magnetism_service.run_magnetism_from_audit_run",
            side_effect=fake_run,
        ):
            result = web_queue._call_magnetism_engine(
                {"input_type": "audit_run", "input_value": "123"},
                progress_cb=phases.append,
            )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["run_id"], 123)
        self.assertIsNone(captured["llm"])
        self.assertEqual(phases, ["interpreting"])

    def test_manual_magnetism_uses_service_role_router_without_injected_llm(self):
        captured = {}
        phases = []

        def fake_run(text, *, llm=None):
            captured["text"] = text
            captured["llm"] = llm
            return {"ok": True}

        with patch(
            "src.services.magnetism_service.run_legacy_manual_magnetism",
            side_effect=fake_run,
        ):
            result = web_queue._call_magnetism_engine(
                {"input_type": "manual", "input_value": "manual evidence"},
                progress_cb=phases.append,
            )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["text"], "manual evidence")
        self.assertIsNone(captured["llm"])
        self.assertEqual(phases, ["extracting"])


class WorkerLoopTests(unittest.TestCase):
    def _insert_running_rows(self, db_path: Path) -> None:
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                """
                INSERT INTO web_requests
                  (token, url, brand_slug, requester_ip, requester_is_team, status, phase, started_at)
                VALUES ('web-running', 'https://example.com', 'example', '127.0.0.1', 0,
                        'running', 'collecting', datetime('now'))
                """
            )
            conn.execute(
                """
                INSERT INTO magnetism_scans
                  (brand_name, url, magnetism_score, coherence_score, quadrant, raw_payload,
                   created_at, status, token, phase, input_type, input_value, started_at)
                VALUES ('Acme', 'https://acme.test', 0, 0, 'pending', '{}', datetime('now'),
                        'running', 'magnetism-running', 'collecting', 'url',
                        'https://acme.test', datetime('now'))
                """
            )
            conn.commit()

    def test_restart_in_flight_requeues_running_rows_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            store.close()
            self._insert_running_rows(db_path)

            queue = web_queue.AnalysisQueue(max_concurrent=1)
            with patch.object(web_queue, "_db_path", return_value=db_path):
                with patch.object(web_queue.settings, "requeue_in_flight_on_startup", True):
                    queue.restart_in_flight()

            self.assertEqual(queue._queue.qsize(), 2)
            queued = {queue._queue.get_nowait(), queue._queue.get_nowait()}
            self.assertEqual(
                queued,
                {"web-running", f"{web_queue.MAGNETISM_QUEUE_PREFIX}magnetism-running"},
            )
            with sqlite3.connect(str(db_path)) as conn:
                web_status = conn.execute(
                    "SELECT status, phase FROM web_requests WHERE token='web-running'"
                ).fetchone()
                magnetism_status = conn.execute(
                    "SELECT status, phase FROM magnetism_scans WHERE token='magnetism-running'"
                ).fetchone()
            self.assertEqual(web_status, ("queued", "queued"))
            self.assertEqual(magnetism_status, ("queued", "queued"))

    def test_restart_in_flight_can_interrupt_running_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            store.close()
            self._insert_running_rows(db_path)

            queue = web_queue.AnalysisQueue(max_concurrent=1)
            with patch.object(web_queue, "_db_path", return_value=db_path):
                with patch.object(web_queue.settings, "requeue_in_flight_on_startup", False):
                    queue.restart_in_flight()

            self.assertEqual(queue._queue.qsize(), 0)
            with sqlite3.connect(str(db_path)) as conn:
                web_status = conn.execute(
                    "SELECT status, phase, error_message FROM web_requests WHERE token='web-running'"
                ).fetchone()
                magnetism_status = conn.execute(
                    "SELECT status, phase, error_message FROM magnetism_scans WHERE token='magnetism-running'"
                ).fetchone()
            self.assertEqual(
                web_status,
                ("failed", "failed", "interrupted by application restart"),
            )
            self.assertEqual(
                magnetism_status,
                ("failed", "failed", "interrupted by application restart"),
            )

    def test_web_queue_process_uses_threadpool_for_db_and_engine_work(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            store.close()
            token = "queued-token"
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute(
                    """
                    INSERT INTO web_requests
                      (token, url, brand_slug, requester_ip, requester_is_team, status)
                    VALUES (?, ?, ?, ?, 0, 'queued')
                    """,
                    (token, "https://example.com", "example", "127.0.0.1"),
                )
                conn.commit()

            calls = []

            async def fake_to_thread(func, *args, **kwargs):
                calls.append((func, args, kwargs))
                return func(*args, **kwargs)

            web_queue.set_run_analysis_override(lambda _url, progress_cb=None: {"run_id": None})
            try:
                with patch.object(web_queue, "_db_path", return_value=db_path):
                    with patch.object(web_queue.asyncio, "to_thread", fake_to_thread):
                        asyncio.run(web_queue.AnalysisQueue(max_concurrent=1)._process(token))
            finally:
                web_queue.set_run_analysis_override(None)

            called = [call[0] for call in calls]
            self.assertIn(web_queue._load_request, called)
            self.assertIn(web_queue._call_engine, called)
            self.assertGreaterEqual(called.count(web_queue._set_status), 2)

            with sqlite3.connect(str(db_path)) as conn:
                status = conn.execute(
                    "SELECT status FROM web_requests WHERE token = ?",
                    (token,),
                ).fetchone()[0]
            self.assertEqual(status, "ready")

    def test_magnetism_process_materializes_sv9_before_marking_ready(self):
        from src.features.magnetism.readiness import ScannerReadiness
        from web.storage import insert_magnetism_job

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            store = SQLiteStore(str(db_path))
            store.close()
            token = "magnetism-token"
            with patch("web.storage.BRAND3_DB_PATH", str(db_path)):
                insert_magnetism_job(
                    token=token,
                    brand_name="Acme",
                    url="https://acme.test",
                    input_type="audit_run",
                    input_value="123",
                    source_run_id=123,
                )

            result = {
                "source_run_id": 123,
                "brand_name": "Acme",
                "url": "https://acme.test",
                "magnetism_score": 64,
                "coherence_score": 72,
                "quadrant": "High Magnetism - High Coherence",
                "source": "brand_audit_snapshot",
                "tldr_brand3": {},
            }
            calls = []

            async def fake_to_thread(func, *args, **kwargs):
                calls.append(func)
                return func(*args, **kwargs)

            def fake_ensure(payload):
                calls.append("ensure_sv9")
                self.assertEqual(payload, result)
                return 99

            def fake_complete(complete_token, payload):
                calls.append("complete_magnetism")
                self.assertEqual(complete_token, token)
                self.assertEqual(payload, result)

            web_queue.set_run_magnetism_override(lambda _job, progress_cb=None: result)
            try:
                with patch.object(web_queue, "_db_path", return_value=db_path):
                    with patch.object(web_queue.asyncio, "to_thread", fake_to_thread):
                        with patch.object(
                            web_queue,
                            "assess_scanner_readiness",
                            return_value=ScannerReadiness("publishable"),
                        ):
                            with patch.object(web_queue, "_ensure_sv9_scan_for_magnetism_result", side_effect=fake_ensure):
                                with patch.object(web_queue, "_complete_magnetism_scan", side_effect=fake_complete):
                                    asyncio.run(web_queue.AnalysisQueue(max_concurrent=1)._process_magnetism(token))
            finally:
                web_queue.set_run_magnetism_override(None)

            self.assertLess(calls.index("ensure_sv9"), calls.index("complete_magnetism"))

    def test_runs_claimed_job_and_stops_on_shutdown(self):
        claimed_jobs = [{"id": 7, "url": "https://a.com"}]
        ran = []

        flag = job_runner._ShutdownFlag()

        def fake_claim(_worker_id):
            if claimed_jobs:
                return claimed_jobs.pop(0)
            flag.request()
            return None

        def fake_runner(job):
            ran.append(job["id"])
            return job

        job_runner.run(
            poll_interval=0,
            shutdown=flag,
            claim=fake_claim,
            runner=fake_runner,
            sleep=lambda _s: None,
        )
        self.assertEqual(ran, [7])

    def test_sleeps_and_continues_when_claim_raises(self):
        """Claim failure should not crash the loop."""
        flag = job_runner._ShutdownFlag()
        calls = {"n": 0}

        def fake_claim(_worker_id):
            calls["n"] += 1
            if calls["n"] == 1:
                raise sqlite3.OperationalError("database is locked")
            flag.request()
            return None

        job_runner.run(
            poll_interval=0,
            shutdown=flag,
            claim=fake_claim,
            runner=lambda _j: None,
            sleep=lambda _s: None,
        )
        self.assertGreaterEqual(calls["n"], 2)


if __name__ == "__main__":
    unittest.main()
