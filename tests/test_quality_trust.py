import unittest

from src.quality.trust import (
    dimension_status_counts_from_confidence,
    quality_label,
    trust_overall_reason,
    trust_overall_status,
)


class TrustQualityTests(unittest.TestCase):
    def test_quality_label_boundaries(self):
        self.assertEqual(quality_label(0.75), "alta")
        self.assertEqual(quality_label(0.45), "media")
        self.assertEqual(quality_label(0.44), "baja")

    def test_dimension_status_counts_from_confidence(self):
        counts = dimension_status_counts_from_confidence({
            "presencia": {"status": "good"},
            "coherencia": {"status": "degraded"},
            "percepcion": {"status": "insufficient_data"},
        })

        self.assertEqual(counts, {"good": 1, "degraded": 1, "insufficient_data": 1})

    def test_overall_status_is_conservative(self):
        counts = {"good": 2, "degraded": 0, "insufficient_data": 3}

        self.assertEqual(
            trust_overall_status(
                data_quality="good",
                context_status="good",
                dimension_status_counts=counts,
            ),
            "insufficient_data",
        )
        self.assertEqual(
            trust_overall_reason(
                data_quality="good",
                context_status="good",
                dimension_status_counts=counts,
            ),
            "multiple_dimensions_insufficient",
        )


if __name__ == "__main__":
    unittest.main()
