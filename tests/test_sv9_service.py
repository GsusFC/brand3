import unittest
from unittest.mock import patch

from src.sv9.rubric import COMPONENTS, MODEL_LABEL, RUBRIC_VERSION
from src.sv9.service import materialize_sv9_scan, run_sv9_from_audit_snapshot
from tests.test_sv9_evaluator import FakeLLM, full_tldr


def synthetic_snapshot() -> dict:
    return {
        "id": 175,
        "brand_name": "Acme",
        "url": "https://acme.test",
        "composite_score": 62.5,
        "features": [
            {
                "dimension_name": "coherencia",
                "feature_name": "messaging_consistency",
                "value": 64.0,
                "raw_value": None,
                "confidence": 0.8,
                "source": "llm_analysis",
            },
            {
                "dimension_name": "percepcion",
                "feature_name": "brand_sentiment",
                "value": 70.0,
                "raw_value": None,
                "confidence": 0.7,
                "source": "llm_analysis",
            },
        ],
    }


class Sv9ServiceTests(unittest.TestCase):
    def test_full_chain_from_snapshot_with_injected_detection(self):
        llm = FakeLLM(ok_up_to=4)
        result = run_sv9_from_audit_snapshot(
            synthetic_snapshot(),
            llm=llm,
            magnetism_result={
                "brand_name": "Acme",
                "source_url": "https://acme.test",
                "source_run_id": 175,
                "tldr_brand3": full_tldr(),
            },
        )

        self.assertEqual(result.brand_name, "Acme")
        self.assertEqual(result.source_run_id, 175)
        self.assertEqual(result.rubric_version, RUBRIC_VERSION)
        self.assertEqual(result.model, MODEL_LABEL)
        self.assertEqual(set(result.components), set(COMPONENTS))
        self.assertTrue(result.is_complete)
        # ok_up_to=4: base avg = 6 -> no cap; score:
        # 4 five-scales (4) + 4 ten-scales (4) + magnetism 4x2 + coherencia 4x2
        self.assertEqual(result.brand3_score, 4 * 4 + 4 * 4 + 8 + 8)
        self.assertFalse(result.magnetism_capped)

        coherencia_call = next(
            c for c in llm.calls if c.get("schema_name") == "baldosas_coherencia"
        )
        self.assertIn("messaging_consistency", coherencia_call["user"])
        magnetism_call = next(
            c for c in llm.calls if c.get("schema_name") == "baldosas_magnetism"
        )
        self.assertIn("brand_sentiment", magnetism_call["user"])

        # Coherencia carries its synthesis verdict; a single client labels all
        # components with its own model.
        self.assertTrue(result.components["coherencia"].veredicto)
        self.assertEqual(result.evaluator_model, llm.model)

    def test_model_routing_through_service(self):
        base = FakeLLM(ok_up_to=3, model="flash-tier")
        reasoning = FakeLLM(ok_up_to=3, model="reasoning-tier")
        result = run_sv9_from_audit_snapshot(
            synthetic_snapshot(),
            llm=base,
            reasoning_llm=reasoning,
            magnetism_result={
                "brand_name": "Acme",
                "source_url": "https://acme.test",
                "source_run_id": 175,
                "tldr_brand3": full_tldr(),
            },
        )
        self.assertEqual(result.components["magnetism"].evaluation_model, "reasoning-tier")
        self.assertEqual(result.components["coherencia"].evaluation_model, "reasoning-tier")
        self.assertEqual(result.components["mission"].evaluation_model, "flash-tier")
        self.assertEqual(result.evaluator_model, "flash-tier")

    def test_materialize_uses_sv9_editorial_model_for_editorial_voice(self):
        result = run_sv9_from_audit_snapshot(
            synthetic_snapshot(),
            llm=FakeLLM(ok_up_to=3),
            magnetism_result={
                "brand_name": "Acme",
                "source_url": "https://acme.test",
                "source_run_id": 175,
                "tldr_brand3": full_tldr(),
            },
        )

        class FakeStore:
            def __init__(self, db_path):
                self.db_path = db_path

            def get_detection(self, run_id):
                return {
                    "brand_name": "Acme",
                    "source_url": "https://acme.test",
                    "source_run_id": run_id,
                    "tldr_brand3": full_tldr(),
                }

            def save_detection(self, run_id, payload):
                raise AssertionError("detection should be reused")

            def get_visual_evidence(self, run_id):
                return None

            def save_visual_evidence(self, run_id, payload):
                raise AssertionError("visual evidence should not be saved")

            def save_scan(self, scan_result):
                return 99

            def save_editorial(self, scan_id, *, component_messages, executive_reading):
                self.saved_editorial = (scan_id, component_messages, executive_reading)

            def close(self):
                pass

        created_models = []

        class FakeAnalyzer:
            api_key = "test-key"

            def __init__(self, model):
                self.model = model
                created_models.append(model)

        with patch("src.sv9.service.SV9_EDITORIAL_MODEL", "editorial-tier"):
            with patch("src.sv9.service.LLMAnalyzer", FakeAnalyzer):
                with patch("src.sv9.service.Sv9Store", FakeStore):
                    with patch("src.sv9.service.load_brand_audit_snapshot", return_value=synthetic_snapshot()):
                        with patch("src.sv9.service.compute_vision_observations", return_value=None):
                            with patch("src.sv9.service.run_sv9_from_audit_snapshot", return_value=result):
                                with patch(
                                    "src.sv9.service.build_editorial",
                                    return_value={
                                        "component_messages": {"mission": "Editorial."},
                                        "executive_reading": "Reading.",
                                    },
                                ) as build_editorial:
                                    scan_id, materialized = materialize_sv9_scan(
                                        175,
                                        db_path=":memory:",
                                    )

        self.assertEqual(scan_id, 99)
        self.assertIs(materialized, result)
        self.assertEqual(created_models, ["editorial-tier"])
        editorial_llm = build_editorial.call_args.kwargs["llm"]
        self.assertEqual(editorial_llm.model, "editorial-tier")

    def test_materialize_merges_visual_signature_shadow_signals(self):
        result = run_sv9_from_audit_snapshot(
            synthetic_snapshot(),
            llm=FakeLLM(ok_up_to=3),
            magnetism_result={
                "brand_name": "Acme",
                "source_url": "https://acme.test",
                "source_run_id": 175,
                "tldr_brand3": full_tldr(),
            },
        )

        class FakeStore:
            def __init__(self, db_path):
                self.db_path = db_path

            def get_detection(self, run_id):
                return {
                    "brand_name": "Acme",
                    "source_url": "https://acme.test",
                    "source_run_id": run_id,
                    "tldr_brand3": full_tldr(),
                }

            def save_detection(self, run_id, payload):
                raise AssertionError("detection should be reused")

            def get_visual_evidence(self, run_id):
                return None

            def save_visual_evidence(self, run_id, payload):
                raise AssertionError("visual evidence should not be saved")

            def save_scan(self, scan_result):
                return 99

            def save_editorial(self, scan_id, *, component_messages, executive_reading):
                raise AssertionError("editorial should be disabled")

            def close(self):
                pass

        snapshot = synthetic_snapshot()
        snapshot["raw_inputs"] = [
            {
                "source": "visual_signature",
                "payload": {
                    "visual_signature_evidence": {
                        "schema_version": "visual-signature-evidence-v1",
                        "capture": {"status": "usable", "first_fold_evaluable": True},
                        "limitations": [],
                        "evidence_health": {"warnings": []},
                        "tile_signals": [
                            {
                                "tile": "brand_idea.I1",
                                "effect": "supports",
                                "confidence": "high",
                                "source": "heuristic",
                                "evidence_refs": ["visual_signature:identity"],
                                "rationale": "logo_detected:true",
                            }
                        ],
                    }
                },
                "created_at": "2026-06-27T10:00:00",
            }
        ]

        with patch("src.sv9.service.Sv9Store", FakeStore):
            with patch("src.sv9.service.load_brand_audit_snapshot", return_value=snapshot):
                with patch("src.sv9.service.compute_vision_observations", return_value=None):
                    with patch(
                        "src.sv9.service.run_sv9_from_audit_snapshot",
                        return_value=result,
                    ) as run_snapshot:
                        scan_id, materialized = materialize_sv9_scan(
                            175,
                            db_path=":memory:",
                            editorial=False,
                        )

        self.assertEqual(scan_id, 99)
        self.assertIs(materialized, result)
        extra_signals = run_snapshot.call_args.kwargs["extra_signals"]
        self.assertIn("brand_idea", extra_signals)
        self.assertEqual(extra_signals["brand_idea"][0]["feature"], "visual_signature_shadow")

    def test_materialize_skips_visual_signature_shadow_signals_for_blocked_capture(self):
        result = run_sv9_from_audit_snapshot(
            synthetic_snapshot(),
            llm=FakeLLM(ok_up_to=3),
            magnetism_result={
                "brand_name": "Acme",
                "source_url": "https://acme.test",
                "source_run_id": 175,
                "tldr_brand3": full_tldr(),
            },
        )

        class FakeStore:
            def __init__(self, db_path):
                self.db_path = db_path

            def get_detection(self, run_id):
                return {
                    "brand_name": "Acme",
                    "source_url": "https://acme.test",
                    "source_run_id": run_id,
                    "tldr_brand3": full_tldr(),
                }

            def save_detection(self, run_id, payload):
                raise AssertionError("detection should be reused")

            def get_visual_evidence(self, run_id):
                return None

            def save_visual_evidence(self, run_id, payload):
                raise AssertionError("visual evidence should not be saved")

            def save_scan(self, scan_result):
                return 99

            def save_editorial(self, scan_id, *, component_messages, executive_reading):
                raise AssertionError("editorial should be disabled")

            def close(self):
                pass

        snapshot = synthetic_snapshot()
        snapshot["raw_inputs"] = [
            {
                "source": "visual_signature",
                "payload": {
                    "visual_signature_evidence": {
                        "schema_version": "visual-signature-evidence-v1",
                        "capture": {"status": "blocked", "first_fold_evaluable": False},
                        "limitations": ["visual_obstruction:cookie_banner"],
                        "evidence_health": {"warnings": ["capture_status:blocked"]},
                        "tile_signals": [
                            {
                                "tile": "coherencia.C6",
                                "effect": "insufficient_evidence",
                                "confidence": "high",
                                "source": "heuristic",
                                "evidence_refs": ["visual_signature:capture"],
                                "rationale": "capture_unreliable:blocked",
                            }
                        ],
                    }
                },
                "created_at": "2026-06-27T10:00:00",
            }
        ]

        with patch("src.sv9.service.Sv9Store", FakeStore):
            with patch("src.sv9.service.load_brand_audit_snapshot", return_value=snapshot):
                with patch("src.sv9.service.compute_vision_observations", return_value=None):
                    with patch(
                        "src.sv9.service.run_sv9_from_audit_snapshot",
                        return_value=result,
                    ) as run_snapshot:
                        materialize_sv9_scan(
                            175,
                            db_path=":memory:",
                            editorial=False,
                        )

        self.assertIsNone(run_snapshot.call_args.kwargs["extra_signals"])


if __name__ == "__main__":
    unittest.main()
