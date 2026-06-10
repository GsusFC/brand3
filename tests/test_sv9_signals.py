import json
import unittest

from src.sv9.signals import (
    audit_visual_method,
    collect_signals,
    compute_vision_observations,
    merge_signals,
    screenshot_url_from_snapshot,
    vision_signals,
)


def snapshot_with(features=None, raw_inputs=None) -> dict:
    return {
        "brand_name": "Acme",
        "features": features or [],
        "raw_inputs": raw_inputs or [],
    }


def visual_feature(raw_value: str) -> dict:
    return {
        "dimension_name": "coherencia",
        "feature_name": "visual_consistency",
        "value": 70.0,
        "raw_value": raw_value,
        "confidence": 0.55,
        "source": "visual_analysis",
    }


class SignalCollectionTests(unittest.TestCase):
    def test_collect_signals_carries_raw_detail(self):
        snapshot = snapshot_with(
            features=[visual_feature("{'logo_detected': False, 'style': 'modern'}")]
        )
        signals = collect_signals(snapshot)
        self.assertIn("brand_idea", signals)
        self.assertIn("logo_detected", signals["brand_idea"][0]["detail"])

    def test_merge_signals_appends_without_mutating_base(self):
        base = {"brand_idea": [{"feature": "a"}]}
        merged = merge_signals(base, {"brand_idea": [{"feature": "b"}], "coherencia": [{"feature": "c"}]})
        self.assertEqual(len(merged["brand_idea"]), 2)
        self.assertEqual(len(base["brand_idea"]), 1)
        self.assertIn("coherencia", merged)
        self.assertIs(merge_signals(base, None), base)


class ScreenshotAndMethodTests(unittest.TestCase):
    def test_screenshot_url_extraction(self):
        snapshot = snapshot_with(
            raw_inputs=[
                {"source": "web", "payload_json": "{}"},
                {
                    "source": "screenshot_capture",
                    "payload_json": json.dumps(
                        {"capture": {"screenshot_url": "https://shots.test/a.png"}}
                    ),
                },
            ]
        )
        self.assertEqual(screenshot_url_from_snapshot(snapshot), "https://shots.test/a.png")
        self.assertIsNone(screenshot_url_from_snapshot(snapshot_with()))

    def test_screenshot_url_with_parsed_payload_shape(self):
        # get_run_snapshot returns raw inputs with `payload` already parsed.
        snapshot = snapshot_with(
            raw_inputs=[
                {
                    "source": "screenshot_capture",
                    "payload": {"capture": {"screenshot_url": "https://shots.test/b.png"}},
                    "created_at": "2026-06-10",
                }
            ]
        )
        self.assertEqual(screenshot_url_from_snapshot(snapshot), "https://shots.test/b.png")

    def test_audit_visual_method_detection(self):
        local = snapshot_with(features=[visual_feature("{'method': 'local_image_analysis'}")])
        vision = snapshot_with(features=[visual_feature("{'method': 'mixed', 'vision_method': 'vision_llm'}")])
        self.assertEqual(audit_visual_method(local), "local")
        self.assertEqual(audit_visual_method(vision), "vision")
        self.assertEqual(audit_visual_method(snapshot_with()), "absent")


class FakeVisionAnalyzer:
    def __init__(self, payload):
        self.vision_api_key = "k"
        self.payload = payload
        self.prompts = []

    def _download_image(self, url):
        return "/tmp/fake.png"

    def _encode_image_base64(self, path):
        return "AAA="

    def _call_vision_api(self, image_b64, prompt):
        self.prompts.append(prompt)
        return self.payload


class VisionObservationTests(unittest.TestCase):
    def _snapshot(self):
        return snapshot_with(
            raw_inputs=[
                {
                    "source": "screenshot_capture",
                    "payload_json": json.dumps(
                        {"capture": {"screenshot_url": "https://shots.test/a.png"}}
                    ),
                }
            ]
        )

    def test_compute_vision_observations_happy_path(self):
        analyzer = FakeVisionAnalyzer({"logo_detected": True, "design_verdict": "custom"})
        payload = compute_vision_observations(self._snapshot(), analyzer=analyzer)
        self.assertTrue(payload["logo_detected"])
        self.assertIn("Acme", analyzer.prompts[0])

    def test_compute_vision_observations_rejects_invalid_payload(self):
        analyzer = FakeVisionAnalyzer({})
        self.assertIsNone(compute_vision_observations(self._snapshot(), analyzer=analyzer))

    def test_compute_vision_observations_without_screenshot(self):
        analyzer = FakeVisionAnalyzer({"logo_detected": True})
        self.assertIsNone(compute_vision_observations(snapshot_with(), analyzer=analyzer))

    def test_vision_signals_reach_brand_idea_and_coherencia(self):
        signals = vision_signals({"logo_detected": True, "design_verdict": "custom"})
        self.assertEqual(set(signals), {"brand_idea", "coherencia"})
        self.assertIn("logo_detected", signals["brand_idea"][0]["detail"])
        self.assertEqual(signals["coherencia"][0]["value"], "custom")


if __name__ == "__main__":
    unittest.main()
