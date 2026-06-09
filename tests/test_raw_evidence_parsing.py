import unittest

from src.models.brand import FeatureValue
from src.quality.dimension_confidence import dimension_confidence_from_features
from src.quality.report_readiness import evaluate_report_readiness


def _scores():
    return {
        "coherencia": 80,
        "presencia": 80,
        "percepcion": 80,
        "diferenciacion": 80,
        "vitalidad": 80,
    }


def _confidence():
    return {
        "coherencia": {"status": "good", "confidence": 0.9, "missing_signals": [], "confidence_reason": []},
        "presencia": {"status": "good", "confidence": 0.9, "missing_signals": [], "confidence_reason": []},
        "percepcion": {"status": "good", "confidence": 0.9, "missing_signals": [], "confidence_reason": []},
        "diferenciacion": {"status": "good", "confidence": 0.9, "missing_signals": [], "confidence_reason": []},
        "vitalidad": {"status": "good", "confidence": 0.9, "missing_signals": [], "confidence_reason": []},
    }


def _ready_features(raw_value_visual_consistency):
    return {
        "coherencia": {
            "visual_consistency": {
                "feature_name": "visual_consistency",
                "value": 72,
                "confidence": 0.8,
                "source": "web_scrape",
                "raw_value": raw_value_visual_consistency,
            },
            "messaging_consistency": {
                "feature_name": "messaging_consistency",
                "value": 68,
                "confidence": 0.8,
                "source": "web_scrape",
                "raw_value": {"evidence_snippet": ["Clear message"]},
            },
            "tone_consistency": {
                "feature_name": "tone_consistency",
                "value": 70,
                "confidence": 0.8,
                "source": "llm_analysis",
                "raw_value": {"examples": ["Direct tone"]},
            },
            "cross_channel_coherence": {
                "feature_name": "cross_channel_coherence",
                "value": 66,
                "confidence": 0.8,
                "source": "exa",
                "raw_value": {"evidence": ["Cross-channel"]},
            },
        }
    }


def _confidence_features(raw_value_visual_consistency):
    return {
        "coherencia": {
            "visual_consistency": FeatureValue(
                "visual_consistency",
                72,
                raw_value=raw_value_visual_consistency,
                confidence=0.8,
                source="web_scrape",
            ),
            "messaging_consistency": FeatureValue(
                "messaging_consistency",
                68,
                raw_value={"evidence_snippet": ["Clear message"]},
                confidence=0.8,
                source="web_scrape",
            ),
            "tone_consistency": FeatureValue(
                "tone_consistency",
                70,
                raw_value={"examples": ["Direct tone"]},
                confidence=0.8,
                source="llm_analysis",
            ),
            "cross_channel_coherence": FeatureValue(
                "cross_channel_coherence",
                66,
                raw_value={"evidence": ["Cross-channel"]},
                confidence=0.8,
                source="exa",
            ),
        }
    }


class RawEvidenceParsingTests(unittest.TestCase):
    def test_evidence_bearing_raw_payload_is_detected_by_both_paths(self):
        stringified = "{'evidence': ['https://example.com'], 'quotes': ['Clear message']}"
        raw_features = _confidence_features(stringified)
        confidence = dimension_confidence_from_features(raw_features)
        readiness = evaluate_report_readiness(
            scores=_scores(),
            evidence_summary={
                "by_dimension": {
                    "coherencia": 4,
                    "presencia": 4,
                    "percepcion": 4,
                    "diferenciacion": 4,
                    "vitalidad": 4,
                },
                "entity_relevance_available": True,
            },
            confidence_summary=_confidence(),
            features_by_dimension=_ready_features(stringified),
        )

        self.assertGreater(confidence["coherencia"]["evidence_coverage"], 0)
        self.assertEqual(readiness["dimension_states"]["coherencia"], "ready")
        self.assertFalse(readiness["fallback_detected"].get("coherencia"))

    def test_fallback_like_raw_payload_is_detected_consistently(self):
        stringified = "{'fallback': True, 'reason': 'no data'}"
        confidence = dimension_confidence_from_features(_confidence_features(stringified))
        readiness = evaluate_report_readiness(
            scores={"coherencia": 50.0, "presencia": 80, "percepcion": 80, "diferenciacion": 80, "vitalidad": 80},
            evidence_summary={
                "by_dimension": {
                    "coherencia": 4,
                    "presencia": 4,
                    "percepcion": 4,
                    "diferenciacion": 4,
                    "vitalidad": 4,
                },
                "entity_relevance_available": True,
            },
            confidence_summary=_confidence(),
            features_by_dimension=_ready_features(stringified),
        )

        self.assertEqual(confidence["coherencia"]["evidence_coverage"], 0.75)
        self.assertTrue(readiness["fallback_detected"]["coherencia"])
        self.assertEqual(readiness["dimension_states"]["coherencia"], "technical_only")


if __name__ == "__main__":
    unittest.main()
