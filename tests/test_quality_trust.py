import unittest

from src.quality.trust import (
    build_trust_summary,
    dimension_status_counts_from_confidence,
    limited_dimensions_from_confidence,
    limited_dimensions_from_report_dimensions,
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
            limited_dimensions=[{"name": "presencia", "status": "degraded"}],
        )

        self.assertEqual(summary["overall_status"], "good")
        self.assertEqual(summary["overall_status_label"], "bueno")
        self.assertEqual(summary["overall_reason"], "all_trust_checks_passed")
        self.assertEqual(summary["overall_reason_label"], "todas las comprobaciones de confianza pasaron")
        self.assertEqual(summary["context"]["coverage"], 0.8)
        self.assertEqual(summary["evidence"]["total"], 4)
        self.assertEqual(summary["limited_dimensions"][0]["name"], "presencia")

    def test_limited_dimensions_from_confidence_keeps_only_weak_dimensions(self):
        limited = limited_dimensions_from_confidence({
            "presencia": {
                "status": "good",
                "coverage": 0.9,
                "confidence": 0.8,
                "missing_signals": [],
            },
            "percepcion": {
                "status": "insufficient_data",
                "coverage": 0.2,
                "confidence": 0.3,
                "confidence_reason": ["low_coverage"],
                "missing_signals": ["reviews"],
                "recommended_next_steps": ["Recolectar reviews verificables."],
            },
        })

        self.assertEqual(len(limited), 1)
        self.assertEqual(limited[0]["name"], "percepcion")
        self.assertEqual(limited[0]["missing_signals"], ["reviews"])
        self.assertEqual(limited[0]["recommended_next_steps"], ["Recolectar reviews verificables."])

    def test_limited_dimensions_from_report_dimensions_keeps_labels(self):
        limited = limited_dimensions_from_report_dimensions([
            {"name": "presencia", "display_name": "Presence", "confidence_status": "good"},
            {
                "name": "vitalidad",
                "display_name": "Vitality",
                "confidence_status": "degraded",
                "coverage_label": "media",
                "confidence_label": "baja",
                "missing_signals": ["changelog"],
                "recommended_next_steps": ["Detectar changelog reciente."],
            },
        ])

        self.assertEqual(len(limited), 1)
        self.assertEqual(limited[0]["display_name"], "Vitality")
        self.assertEqual(limited[0]["confidence_label"], "baja")
        self.assertEqual(limited[0]["recommended_next_steps"], ["Detectar changelog reciente."])


if __name__ == "__main__":
    unittest.main()
