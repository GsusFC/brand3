"""Internal SV9 calibration UI: team gating, listing, and label capture."""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


def _install_env(db_path: Path) -> None:
    os.environ["BRAND3_DB_PATH"] = str(db_path)
    os.environ["BRAND3_COOKIE_SECRET"] = "t" * 40
    os.environ["BRAND3_TEAM_TOKEN"] = "team"
    os.environ["BRAND3_MAX_CONCURRENT_ANALYSES"] = "1"


class Sv9CalibrationWebTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "brand3.sqlite3"
        _install_env(self.db)

        for mod_name in list(sys.modules):
            if mod_name.startswith("web") or mod_name in ("src.config", "src.sv9.store"):
                importlib.reload(sys.modules[mod_name])

        from fastapi.testclient import TestClient

        from web.app import app
        from web.workers.queue import set_run_analysis_override

        set_run_analysis_override(lambda _u: {"run_id": None})
        self.client = TestClient(app)
        self.client.__enter__()
        self.scan_id = self._seed_scan()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self._tmp.cleanup()

    def _seed_scan(self) -> int:
        from src.sv9.aggregator import aggregate
        from src.sv9.models import ComponentResult, RungVerdict, STATUS_SCORED
        from src.sv9.rubric import COMPONENTS
        from src.sv9.store import Sv9Store

        components = {}
        for key, spec in COMPONENTS.items():
            profile = [
                RungVerdict(rung=i, passed=i <= 3, evidence="q" if i <= 3 else "")
                for i in range(1, spec["scale"] + 1)
            ]
            components[key] = ComponentResult(
                component=key,
                status=STATUS_SCORED,
                score=3,
                rung_profile=profile,
                detected_content=f"{key} text",
            )
        result = aggregate(
            components, brand_name="Acme", url="https://acme.test", source_run_id=1
        )
        store = Sv9Store(str(self.db))
        try:
            return store.save_scan(result)
        finally:
            store.close()

    def _seed_failed_scan(self) -> int:
        from src.sv9.aggregator import aggregate
        from src.sv9.models import ComponentResult, STATUS_NOT_EVALUATED
        from src.sv9.rubric import COMPONENTS
        from src.sv9.store import Sv9Store

        components = {}
        for key in COMPONENTS:
            components[key] = ComponentResult(
                component=key,
                status=STATUS_NOT_EVALUATED,
                score=0,
                detected_content=f"{key} detected text" if key != "coherencia" else None,
                error="provider_http_error",
            )
        result = aggregate(
            components,
            brand_name="Failed Provider",
            url="https://failed-provider.test",
            source_run_id=42,
        )
        store = Sv9Store(str(self.db))
        try:
            return store.save_scan(result)
        finally:
            store.close()

    def _unlock(self):
        response = self.client.get(
            "/team/unlock", params={"token": "team"}, follow_redirects=False
        )
        self.assertEqual(response.status_code, 303)

    def test_routes_open_while_gating_is_disabled(self):
        # Team gating intentionally disabled for now (product decision,
        # 2026-06-11). When re-enabled, these become 403 without the cookie.
        for path in ("/sv9/calibration", f"/sv9/calibration/{self.scan_id}"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_list_and_detail_render_after_unlock(self):
        self._unlock()
        response = self.client.get("/sv9/calibration")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Acme", response.text)
        self.assertIn('class="table-wrap sv9-calibration-table-wrap"', response.text)

        response = self.client.get(f"/sv9/calibration/{self.scan_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("mission text", response.text)
        self.assertIn("score humano", response.text)
        self.assertIn("@media (max-width: 760px)", response.text)
        self.assertIn("grid-template-columns: repeat(auto-fit, minmax(44px, 1fr));", response.text)

    def test_submit_label_persists_with_delta(self):
        self._unlock()
        response = self.client.post(
            f"/sv9/calibration/{self.scan_id}/mission",
            data={
                "score_humano": 5,
                "motivo": "misión publicada y conectada",
                "flag_evidencia": "true",
                "evaluador": "sergio",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("evaluador=sergio", response.headers["location"])

        from src.sv9.store import Sv9Store

        store = Sv9Store(str(self.db))
        try:
            labels = store.list_calibration_labels(component="mission")
        finally:
            store.close()
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["score_ia"], 3)
        self.assertEqual(labels[0]["score_humano"], 5)
        self.assertEqual(labels[0]["delta"], 2)
        self.assertEqual(labels[0]["flag_evidencia"], 1)

        response = self.client.get(f"/sv9/calibration/{self.scan_id}")
        self.assertIn("Δ2", response.text)

    def test_scan_canvas_renders(self):
        response = self.client.get(f"/sv9/scan/{self.scan_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Brand3 Score", response.text)
        self.assertIn("Margen inmediato", response.text)
        self.assertIn("Coherencia", response.text)
        self.assertIn("3/10 ×2", response.text)
        self.assertIn("core_purpose text", response.text)
        self.assertIn("sv9-canvas-row sv9-canvas-row-2", response.text)
        self.assertIn("sv9-canvas-row sv9-canvas-row-3", response.text)
        self.assertIn("sv9-canvas-card", response.text)
        self.assertNotIn("grid-template-columns: repeat({{ row|length }}", response.text)

        response = self.client.get("/sv9/scan/99999")
        self.assertEqual(response.status_code, 404)

    def test_scan_canvas_explains_provider_failures(self):
        scan_id = self._seed_failed_scan()

        response = self.client.get(f"/sv9/scan/{scan_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("evaluación técnica fallida", response.text)
        self.assertIn("provider_http_error", response.text)
        self.assertIn("Este 0/100 no es un diagnóstico estratégico válido.", response.text)
        self.assertIn(f'action="/sv9/scan/{scan_id}/retry"', response.text)

    def test_retry_regenerates_sv9_scan_from_source_run(self):
        from src.sv9.aggregator import aggregate
        from src.sv9.models import ComponentResult, RungVerdict, STATUS_SCORED
        from src.sv9.rubric import COMPONENTS

        failed_scan_id = self._seed_failed_scan()
        components = {}
        for key, spec in COMPONENTS.items():
            profile = [
                RungVerdict(rung=i, passed=i <= 2, evidence="q" if i <= 2 else "")
                for i in range(1, spec["scale"] + 1)
            ]
            components[key] = ComponentResult(
                component=key,
                status=STATUS_SCORED,
                score=2,
                rung_profile=profile,
                detected_content=f"{key} retry text",
            )
        retry_result = aggregate(
            components,
            brand_name="Failed Provider",
            url="https://failed-provider.test",
            source_run_id=42,
        )

        with mock.patch(
            "web.routes.sv9_scan.run_sv9_from_audit_run",
            return_value=retry_result,
        ) as run_sv9:
            response = self.client.post(
                f"/sv9/scan/{failed_scan_id}/retry",
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 303)
        self.assertRegex(response.headers["location"], r"^/sv9/scan/\d+$")
        self.assertNotEqual(response.headers["location"], f"/sv9/scan/{failed_scan_id}")
        run_sv9.assert_called_once_with(42, db_path=str(self.db))

    def test_ranking_renders_and_category_can_be_confirmed(self):
        response = self.client.get("/sv9/ranking")
        self.assertEqual(response.status_code, 200)
        self.assertIn("acme.test", response.text)
        self.assertIn("/takedown", response.text)
        self.assertIn('class="table-wrap sv9-ranking-table-wrap"', response.text)

        response = self.client.post(
            "/sv9/ranking/brand/acme.test",
            data={"primary_category": "fintech", "evaluador": "sergio"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        response = self.client.get("/sv9/ranking?categoria=fintech")
        self.assertIn("acme.test", response.text)
        self.assertIn("confirmada", response.text)

        response = self.client.get("/sv9/ranking?categoria=nonsense")
        self.assertEqual(response.status_code, 404)

    def test_submit_validates_scale_and_component(self):
        self._unlock()
        response = self.client.post(
            f"/sv9/calibration/{self.scan_id}/mission",
            data={"score_humano": 9, "evaluador": "sergio"},
        )
        self.assertEqual(response.status_code, 422)
        response = self.client.post(
            f"/sv9/calibration/{self.scan_id}/nonsense",
            data={"score_humano": 3, "evaluador": "sergio"},
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
