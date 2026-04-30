import copy
import unittest

from src.quality.report_readiness import (
    DIMENSION_NOT_EVALUABLE,
    DIMENSION_TECHNICAL_ONLY,
    REPORT_MODE_INSUFFICIENT,
    REPORT_MODE_PUBLISHABLE,
    REPORT_MODE_TECHNICAL,
    evaluate_report_readiness,
)


DIMENSIONS = ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")


def _scores(value=80):
    return {dimension: value for dimension in DIMENSIONS}


def _evidence(count=3, *, by_quality=None):
    return {
        "total": count * len(DIMENSIONS),
        "by_dimension": {dimension: count for dimension in DIMENSIONS},
        "by_quality": by_quality or {"direct": count * len(DIMENSIONS)},
        "entity_relevance_available": True,
    }


def _confidence(status="good", value=0.82, *, missing=None, reasons=None):
    return {
        dimension: {
            "status": status,
            "confidence": value,
            "missing_signals": list(missing or []),
            "confidence_reason": list(reasons or []),
        }
        for dimension in DIMENSIONS
    }


class ReportReadinessTests(unittest.TestCase):
    def test_high_scores_with_weak_evidence_do_not_become_publishable(self):
        confidence = _confidence(status="degraded", value=0.52, reasons=["low_feature_confidence"])

        result = evaluate_report_readiness(
            scores=_scores(90),
            evidence_summary=_evidence(count=1, by_quality={"weak": 5}),
            confidence_summary=confidence,
        )

        self.assertEqual(result["report_mode"], REPORT_MODE_TECHNICAL)
        self.assertIn("insufficient_ready_core_dimensions", result["blockers"])

    def test_two_ready_core_and_one_observation_only_core_is_publishable(self):
        confidence = _confidence()
        confidence["coherencia"] = {
            "status": "degraded",
            "confidence": 0.52,
            "missing_signals": [],
            "confidence_reason": ["low_feature_confidence"],
        }

        result = evaluate_report_readiness(
            scores=_scores(82),
            evidence_summary=_evidence(count=3),
            confidence_summary=confidence,
        )

        self.assertEqual(result["report_mode"], REPORT_MODE_PUBLISHABLE)

    def test_one_ready_core_and_two_observation_only_core_is_technical_diagnostic(self):
        confidence = _confidence()
        for dimension in ("coherencia", "presencia"):
            confidence[dimension] = {
                "status": "degraded",
                "confidence": 0.52,
                "missing_signals": [],
                "confidence_reason": ["low_feature_confidence"],
            }

        result = evaluate_report_readiness(
            scores=_scores(82),
            evidence_summary=_evidence(count=3),
            confidence_summary=confidence,
        )

        self.assertEqual(result["report_mode"], REPORT_MODE_TECHNICAL)
        self.assertIn("insufficient_ready_core_dimensions", result["blockers"])

    def test_any_core_technical_only_is_technical_diagnostic(self):
        features = {
            "presencia": {
                "web_presence": {
                    "value": 50,
                    "source": "fallback",
                    "raw_value": {"fallback": True, "reason": "no data"},
                },
                "social_footprint": {"value": 75, "source": "social_media"},
                "search_visibility": {"value": 70, "source": "exa"},
                "directory_presence": {"value": 70, "source": "exa"},
            }
        }

        result = evaluate_report_readiness(
            scores=_scores(82),
            evidence_summary=_evidence(count=3),
            confidence_summary=_confidence(),
            features_by_dimension=features,
        )

        self.assertEqual(result["dimension_states"]["presencia"], DIMENSION_TECHNICAL_ONLY)
        self.assertEqual(result["report_mode"], REPORT_MODE_TECHNICAL)
        self.assertIn("core_dimensions_technical_only", result["blockers"])

    def test_one_core_not_evaluable_is_technical_diagnostic(self):
        evidence = _evidence(count=3)
        evidence["by_dimension"]["presencia"] = 0
        scores = _scores(70)
        scores["presencia"] = None
        confidence = _confidence()
        confidence["presencia"] = {"status": "insufficient_data", "confidence": 0.1}

        result = evaluate_report_readiness(
            scores=scores,
            evidence_summary=evidence,
            confidence_summary=confidence,
        )

        self.assertEqual(result["dimension_states"]["presencia"], DIMENSION_NOT_EVALUABLE)
        self.assertEqual(result["report_mode"], REPORT_MODE_TECHNICAL)
        self.assertIn("core_dimensions_not_evaluable", result["blockers"])

    def test_missing_perception_does_not_automatically_block_publication(self):
        evidence = _evidence(count=3)
        evidence["by_dimension"]["percepcion"] = 0
        scores = _scores(78)
        scores["percepcion"] = None
        confidence = _confidence()
        confidence["percepcion"] = {
            "status": "insufficient_data",
            "confidence": 0.1,
            "missing_signals": ["review_quality"],
            "confidence_reason": ["no_evidence"],
        }

        result = evaluate_report_readiness(
            scores=scores,
            evidence_summary=evidence,
            confidence_summary=confidence,
        )

        self.assertEqual(result["dimension_states"]["percepcion"], DIMENSION_NOT_EVALUABLE)
        self.assertEqual(result["report_mode"], REPORT_MODE_PUBLISHABLE)

    def test_multiple_not_evaluable_core_dimensions_are_insufficient_evidence(self):
        evidence = _evidence(count=3)
        evidence["by_dimension"]["coherencia"] = 0
        evidence["by_dimension"]["presencia"] = 0
        scores = _scores(70)
        scores["coherencia"] = None
        scores["presencia"] = None
        confidence = _confidence()
        confidence["coherencia"] = {"status": "insufficient_data", "confidence": 0.1}
        confidence["presencia"] = {"status": "insufficient_data", "confidence": 0.1}

        result = evaluate_report_readiness(
            scores=scores,
            evidence_summary=evidence,
            confidence_summary=confidence,
        )

        self.assertEqual(result["report_mode"], REPORT_MODE_INSUFFICIENT)
        self.assertIn("multiple_core_dimensions_not_evaluable", result["blockers"])

    def test_detectable_fallback_50_reduces_readiness(self):
        features = {
            "coherencia": {
                "messaging_consistency": {
                    "value": 50,
                    "source": "fallback",
                    "raw_value": {"fallback": True, "reason": "no data"},
                },
                "visual_consistency": {"value": 75, "source": "web_scrape"},
                "tone_consistency": {"value": 70, "source": "llm_analysis"},
                "cross_channel_coherence": {"value": 70, "source": "exa"},
            }
        }

        result = evaluate_report_readiness(
            scores=_scores(74),
            evidence_summary=_evidence(count=3),
            confidence_summary=_confidence(),
            features_by_dimension=features,
        )

        self.assertEqual(result["dimension_states"]["coherencia"], DIMENSION_TECHNICAL_ONLY)
        self.assertEqual(result["report_mode"], REPORT_MODE_TECHNICAL)
        self.assertTrue(result["fallback_detected"]["coherencia"])

    def test_readiness_output_does_not_modify_scores(self):
        scores = _scores(67)
        original = copy.deepcopy(scores)

        result = evaluate_report_readiness(
            scores=scores,
            evidence_summary=_evidence(count=3),
            confidence_summary=_confidence(),
        )

        self.assertEqual(scores, original)
        self.assertNotIn("scores", result)
        self.assertEqual(result["report_mode"], REPORT_MODE_PUBLISHABLE)

    def test_entity_relevance_absence_is_warning_not_invention(self):
        evidence = _evidence(count=3)
        evidence.pop("entity_relevance_available")

        result = evaluate_report_readiness(
            scores=_scores(80),
            evidence_summary=evidence,
            confidence_summary=_confidence(),
        )

        self.assertEqual(result["report_mode"], REPORT_MODE_PUBLISHABLE)
        self.assertIn(
            "entity_relevance_not_available: direct evidence may only mean URL presence",
            result["warnings"],
        )


if __name__ == "__main__":
    unittest.main()
