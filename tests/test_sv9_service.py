import unittest

from src.sv9.rubric import COMPONENTS, MODEL_LABEL, RUBRIC_VERSION
from src.sv9.service import run_sv9_from_audit_snapshot
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


if __name__ == "__main__":
    unittest.main()
