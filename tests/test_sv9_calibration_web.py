"""Internal SV9 calibration UI (baldosas v3.1): listing, tile capture, ranking."""

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


def _seed_components(score: int):
    from src.sv9.models import ComponentResult, ESTADO_NO, ESTADO_OK, STATUS_SCORED, TileVerdict
    from src.sv9.rubric import COMPONENTS, tile_ids

    components = {}
    for key in COMPONENTS:
        profile = [
            TileVerdict(
                tile_id=tid,
                estado=ESTADO_OK if i < score else ESTADO_NO,
                evidencia="q" if i < score else "",
                motivo="" if i < score else "m",
            )
            for i, tid in enumerate(tile_ids(key))
        ]
        components[key] = ComponentResult(
            component=key,
            status=STATUS_SCORED,
            score=score,
            tile_profile=profile,
            detected_content=f"{key} text",
        )
    components["coherencia"].veredicto = "La marca cuenta una historia única."
    return components


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
        from src.sv9.store import Sv9Store

        result = aggregate(
            _seed_components(3), brand_name="Acme", url="https://acme.test", source_run_id=1
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
        for path in ("/sv9/calibration", f"/sv9/calibration/{self.scan_id}"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_list_and_detail_render(self):
        response = self.client.get("/sv9/calibration")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Acme", response.text)
        self.assertIn('class="table-wrap sv9-calibration-table-wrap"', response.text)

        response = self.client.get(f"/sv9/calibration/{self.scan_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("mission text", response.text)
        self.assertIn("calibración por baldosa", response.text)
        self.assertIn("estado__M1", response.text)  # per-tile state radio
        self.assertIn("@media (max-width: 760px)", response.text)

    def test_submit_tile_labels_persists_states(self):
        response = self.client.post(
            f"/sv9/calibration/{self.scan_id}/mission",
            data={
                "estado__M1": "ok",
                "estado__M2": "ok",
                "estado__M3": "no",
                "estado__M4": "sin_evidencia",
                "estado__M5": "no",
                "motivo__M4": "no hay forma de probarlo en la huella",
                "evaluador": "sergio",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("evaluador=sergio", response.headers["location"])

        from src.sv9.store import Sv9Store

        store = Sv9Store(str(self.db))
        try:
            labels = store.list_tile_calibration(scan_id=self.scan_id)
        finally:
            store.close()
        self.assertEqual(len(labels), 5)
        by_id = {row["baldosa_id"]: row for row in labels}
        # IA had M1-M3 ok, M4-M5 no.
        self.assertEqual(by_id["M3"]["estado_ia"], "ok")
        self.assertEqual(by_id["M3"]["estado_humano"], "no")
        self.assertEqual(by_id["M4"]["estado_humano"], "sin_evidencia")
        self.assertEqual(by_id["M4"]["motivo"], "no hay forma de probarlo en la huella")

    def test_submit_validates_state_and_component(self):
        response = self.client.post(
            f"/sv9/calibration/{self.scan_id}/mission",
            data={"estado__M1": "tal_vez", "evaluador": "sergio"},
        )
        self.assertEqual(response.status_code, 422)

        response = self.client.post(
            f"/sv9/calibration/{self.scan_id}/nonsense",
            data={"estado__M1": "ok", "evaluador": "sergio"},
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            f"/sv9/calibration/{self.scan_id}/mission",
            data={"estado__M1": "ok"},  # missing evaluador
        )
        self.assertEqual(response.status_code, 422)

    def test_scan_canvas_renders_tile_grid(self):
        response = self.client.get(f"/sv9/scan/{self.scan_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Brand3 Score", response.text)
        self.assertIn("Margen inmediato", response.text)
        self.assertIn("Coherencia", response.text)
        self.assertIn("3/10 ×2", response.text)
        self.assertIn("core_purpose text", response.text)
        self.assertIn("sv9-tile", response.text)
        self.assertIn("encendida", response.text)
        self.assertIn("punto ciego", response.text)
        self.assertIn("La marca cuenta una historia única.", response.text)  # coherencia verdict

        response = self.client.get("/sv9/scan/99999")
        self.assertEqual(response.status_code, 404)

    def test_scan_export_md_downloads(self):
        response = self.client.get(f"/sv9/scan/{self.scan_id}/export.md")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/markdown", response.headers["content-type"])
        self.assertIn("Baldosas apagadas (plan de trabajo)", response.text)
        self.assertIn("Puntos ciegos (contexto pendiente)", response.text)

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

        failed_scan_id = self._seed_failed_scan()
        retry_result = aggregate(
            _seed_components(2),
            brand_name="Failed Provider",
            url="https://failed-provider.test",
            source_run_id=42,
        )

        with mock.patch(
            "web.routes.sv9_scan.materialize_sv9_scan",
            return_value=(failed_scan_id + 1, retry_result),
        ) as materialize:
            response = self.client.post(
                f"/sv9/scan/{failed_scan_id}/retry",
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 303)
        self.assertRegex(response.headers["location"], r"^/sv9/scan/\d+$")
        materialize.assert_called_once_with(42, db_path=str(self.db))

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


if __name__ == "__main__":
    unittest.main()
