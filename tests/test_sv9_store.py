import tempfile
import unittest
from pathlib import Path

from src.sv9.aggregator import aggregate
from src.sv9.models import ComponentResult, RungVerdict, STATUS_NOT_EVALUATED, STATUS_SCORED
from src.sv9.rubric import COMPONENTS, RUBRIC_VERSION
from src.sv9.store import Sv9Store


def scored(key: str, score: int) -> ComponentResult:
    profile = [
        RungVerdict(rung=i, passed=i <= score, evidence="q" if i <= score else "")
        for i in range(1, COMPONENTS[key]["scale"] + 1)
    ]
    return ComponentResult(
        component=key,
        status=STATUS_SCORED,
        score=score,
        rung_profile=profile,
        detected_content=f"{key} text",
        detection_mode="literal",
        detection_confidence="high",
        evidence=[f"{key} quote"],
    )


class Sv9StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "sv9_test.sqlite3")
        self.store = Sv9Store(self.db_path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _result(self):
        components = {key: scored(key, 3) for key in COMPONENTS}
        components["values"] = ComponentResult(
            component="values", status=STATUS_NOT_EVALUATED, error="llm_timeout"
        )
        return aggregate(
            components, brand_name="Acme", url="https://acme.test", source_run_id=175
        )

    def test_scan_roundtrip(self):
        result = self._result()
        scan_id = self.store.save_scan(result)
        loaded = self.store.get_scan(scan_id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["brand_name"], "Acme")
        self.assertEqual(loaded["source_run_id"], 175)
        self.assertEqual(loaded["rubric_version"], RUBRIC_VERSION)
        self.assertEqual(loaded["brand3_score"], result.brand3_score)
        self.assertEqual(loaded["is_complete"], 0)
        self.assertEqual(len(loaded["components"]), 10)

        by_component = {c["component"]: c for c in loaded["components"]}
        self.assertEqual(by_component["mission"]["score"], 3)
        self.assertEqual(len(by_component["mission"]["rung_profile"]), 5)
        self.assertEqual(by_component["values"]["status"], STATUS_NOT_EVALUATED)
        self.assertEqual(by_component["values"]["error"], "llm_timeout")
        self.assertEqual(by_component["coherencia"]["points"], 6)

    def test_get_scan_for_run_returns_latest(self):
        first = self.store.save_scan(self._result())
        second = self.store.save_scan(self._result())
        loaded = self.store.get_scan_for_run(175)
        self.assertEqual(loaded["id"], second)
        self.assertNotEqual(loaded["id"], first)

    def test_calibration_label_computes_delta_and_traces_rubric(self):
        scan_id = self.store.save_scan(self._result())
        self.store.save_calibration_label(
            scan_id=scan_id,
            url="https://acme.test",
            component="mission",
            score_ia=3,
            score_humano=5,
            motivo="la misión está anclada al problema y publicada",
            flag_evidencia=False,
            evaluador="sergio",
            rubric_version=RUBRIC_VERSION,
        )
        labels = self.store.list_calibration_labels(component="mission")
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["delta"], 2)
        self.assertEqual(labels[0]["rubric_version"], RUBRIC_VERSION)
        self.assertEqual(labels[0]["flag_evidencia"], 0)

    def test_editorial_decision_roundtrip_and_replace(self):
        scan_id = self.store.save_scan(self._result())
        self.store.save_editorial_decision(
            scan_id=scan_id,
            component="mission",
            decision="v9",
            note="más pegado al score",
            evaluator="sergio",
        )
        decisions = self.store.list_editorial_decisions(scan_id)
        self.assertEqual(decisions["mission"]["decision"], "v9")
        self.assertEqual(decisions["mission"]["note"], "más pegado al score")

        self.store.save_editorial_decision(
            scan_id=scan_id,
            component="mission",
            decision="mix",
            note="v9 diagnóstico + v2 tono",
            evaluator="ana",
        )
        decisions = self.store.list_editorial_decisions(scan_id)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions["mission"]["decision"], "mix")
        self.assertEqual(decisions["mission"]["evaluator"], "ana")

    def test_detection_cache_roundtrip_and_replace(self):
        self.assertIsNone(self.store.get_detection(175))
        self.store.save_detection(175, {"tldr_brand3": {"mission": {"content": "v1"}}})
        self.assertEqual(
            self.store.get_detection(175)["tldr_brand3"]["mission"]["content"], "v1"
        )
        self.store.save_detection(175, {"tldr_brand3": {"mission": {"content": "v2"}}})
        self.assertEqual(
            self.store.get_detection(175)["tldr_brand3"]["mission"]["content"], "v2"
        )

    def test_migration_is_idempotent(self):
        again = Sv9Store(self.db_path)
        again.close()
        self.assertEqual(self.store.list_scans(), [])


if __name__ == "__main__":
    unittest.main()
