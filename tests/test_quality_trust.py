import unittest

from src.quality.trust import (
    build_trust_summary,
    dimension_status_counts_from_confidence,
    quality_label,
    trust_status_label,
    trust_overall_reason,
    trust_overall_status,
)


class TrustQualityTests(unittest.TestCase):
    def test_quality_label_boundaries(self):
        self.assertEqual(quality_label(0.75), "alta")
        self.assertEqual(quality_label(0.45), "media")
        self.assertEqual(quality_label(0.44), "baja")

    def test_status_label(self):
        self.assertEqual(trust_status_label("good"), "bueno")
        self.assertEqual(trust_status_label("degraded"), "degradado")
        self.assertEqual(trust_status_label("insufficient_data"), "datos insuficientes")

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
        self.assertEqual(
            trust_overall_reason(
                data_quality="good",
                context_status="good",
                dimension_status_counts=counts,
                locale="es",
            ),
            "multiples dimensiones con datos insuficientes",
        )

    def test_build_trust_summary_includes_labels_and_sources(self):
        summary = build_trust_summary(
            data_quality="good",
            context_summary={"status": "good", "coverage": 0.8},
            evidence_summary={"total": 4},
            dimension_status_counts={"good": 5, "degraded": 0, "insufficient_data": 0},
        )

        self.assertEqual(summary["overall_status"], "good")
        self.assertEqual(summary["overall_status_label"], "bueno")
        self.assertEqual(summary["overall_reason"], "all_trust_checks_passed")
        self.assertEqual(summary["overall_reason_label"], "todas las comprobaciones de confianza pasaron")
        self.assertEqual(summary["context"]["coverage"], 0.8)
        self.assertEqual(summary["evidence"]["total"], 4)


if __name__ == "__main__":
    unittest.main()
