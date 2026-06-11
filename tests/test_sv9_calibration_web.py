"""Internal SV9 calibration UI: team gating, listing, and label capture."""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
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

        response = self.client.get(f"/sv9/calibration/{self.scan_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("mission text", response.text)
        self.assertIn("score humano", response.text)

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
        self.assertIn("coherencia 3/10", response.text)
        self.assertIn("core_purpose text", response.text)

        response = self.client.get("/sv9/scan/99999")
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
