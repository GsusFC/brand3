import unittest

from src.sv9.aggregator import aggregate
from src.sv9.export_md import build_scan_markdown
from src.sv9.models import (
    ComponentResult,
    ESTADO_NO,
    ESTADO_OK,
    ESTADO_SIN_EVIDENCIA,
    STATUS_NOT_EVALUATED,
    STATUS_SCORED,
    TileVerdict,
)
from src.sv9.rubric import COMPONENTS, tile_ids


def component(key: str, *, ok: int = 0, blind: int = 0) -> ComponentResult:
    ids = tile_ids(key)
    profile = []
    for i, tid in enumerate(ids):
        if i < ok:
            profile.append(TileVerdict(tile_id=tid, estado=ESTADO_OK, evidencia="cita"))
        elif i < ok + blind:
            profile.append(
                TileVerdict(
                    tile_id=tid,
                    estado=ESTADO_SIN_EVIDENCIA,
                    motivo="el snapshot no contiene cohorte",
                    contexto_requerido="enlaces a competidores",
                )
            )
        else:
            profile.append(TileVerdict(tile_id=tid, estado=ESTADO_NO, motivo="no comunicado"))
    return ComponentResult(
        component=key,
        status=STATUS_SCORED,
        score=ok,
        tile_profile=profile,
        detected_content=f"{key} detected",
    )


class ExportMarkdownTests(unittest.TestCase):
    def _scan(self):
        components = {key: component(key, ok=3) for key in COMPONENTS}
        components["attributes"] = component("attributes", ok=2, blind=1)
        result = aggregate(components, brand_name="Acme", url="https://acme.test", source_run_id=1)
        return result.to_dict()

    def test_header_carries_brand_score_and_model(self):
        md = build_scan_markdown(self._scan())
        self.assertIn("# Brand3 Scanner — Acme", md)
        self.assertIn("Brand3 Score", md)
        self.assertIn("Modelo: v3.1", md)

    def test_off_tiles_are_the_work_plan(self):
        md = build_scan_markdown(self._scan())
        self.assertIn("Baldosas apagadas (plan de trabajo)", md)
        # mission with 3 lit leaves M4/M5 off
        self.assertIn("M4", md)
        self.assertIn("M5", md)

    def test_blind_spots_are_separated_with_context(self):
        md = build_scan_markdown(self._scan())
        self.assertIn("Puntos ciegos (contexto pendiente)", md)
        self.assertIn("el snapshot no contiene cohorte", md)
        self.assertIn("aporta contexto: enlaces a competidores", md)

    def test_off_tiles_and_blind_spots_are_distinct_sections(self):
        md = build_scan_markdown(self._scan())
        plan_idx = md.index("Baldosas apagadas (plan de trabajo)")
        blind_idx = md.index("Puntos ciegos (contexto pendiente)")
        self.assertLess(plan_idx, blind_idx)

    def test_technical_failure_is_flagged_not_listed_as_plan(self):
        components = {key: component(key, ok=3) for key in COMPONENTS}
        components["values"] = ComponentResult(
            component="values", status=STATUS_NOT_EVALUATED, error="provider_http_error"
        )
        scan = aggregate(components, brand_name="Acme", url="https://acme.test").to_dict()
        md = build_scan_markdown(scan)
        self.assertIn("Fallo técnico", md)
        self.assertIn("provider_http_error", md)

    def test_accepts_persisted_list_shape(self):
        scan = self._scan()
        scan["components"] = [
            {**c, "component": key} for key, c in scan["components"].items()
        ]
        md = build_scan_markdown(scan)
        self.assertIn("## Misión", md)


if __name__ == "__main__":
    unittest.main()
