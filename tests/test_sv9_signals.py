import json
import unittest

from src.sv9.signals import (
    audit_visual_method,
    collect_signals,
    compute_vision_observations,
    merge_signals,
    screenshot_url_from_snapshot,
    visual_signature_evidence_from_snapshot,
    visual_signature_shadow_signals,
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


class VisualSignatureShadowSignalTests(unittest.TestCase):
    def test_visual_signature_evidence_from_snapshot_returns_latest_packet(self):
        snapshot = snapshot_with(
            raw_inputs=[
                {
                    "source": "visual_signature",
                    "payload": {
                        "visual_signature_evidence": {
                            "schema_version": "visual-signature-evidence-v1",
                            "capture": {"status": "limited"},
                            "tile_signals": [],
                        }
                    },
                },
                {
                    "source": "visual_signature",
                    "payload": {
                        "visual_signature_evidence": {
                            "schema_version": "visual-signature-evidence-v1",
                            "capture": {"status": "usable"},
                            "tile_signals": [{"tile": "brand_idea.I1", "effect": "supports"}],
                        }
                    },
                },
            ]
        )
        evidence = visual_signature_evidence_from_snapshot(snapshot)
        self.assertEqual(evidence["capture"]["status"], "usable")

    def test_visual_signature_shadow_signals_group_tiles_by_component(self):
        evidence = {
            "schema_version": "visual-signature-evidence-v1",
            "capture": {"status": "usable", "first_fold_evaluable": True},
            "limitations": ["cookie_banner_present"],
            "evidence_health": {"warnings": ["copy_visual_alignment_missing"]},
            "tile_signals": [
                {
                    "tile": "brand_idea.I1",
                    "effect": "supports",
                    "confidence": "high",
                    "source": "heuristic",
                    "evidence_refs": ["visual_signature:identity"],
                    "rationale": "logo_detected:true",
                },
                {
                    "tile": "coherencia.C6",
                    "effect": "weakens",
                    "confidence": "medium",
                    "source": "heuristic",
                    "evidence_refs": ["visual_signature:consistency"],
                    "rationale": "consistency:0.33",
                },
            ],
        }
        signals = visual_signature_shadow_signals(evidence)
        self.assertEqual(set(signals), {"brand_idea", "coherencia"})
        self.assertEqual(signals["brand_idea"][0]["feature"], "visual_signature_shadow")
        self.assertEqual(signals["brand_idea"][0]["value"], "supports_present")
        self.assertIn("brand_idea.I1", signals["brand_idea"][0]["detail"])
        self.assertEqual(signals["coherencia"][0]["value"], "weakens_present")

    def test_visual_signature_shadow_signals_skip_non_usable_capture(self):
        evidence = {
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
        self.assertEqual(visual_signature_shadow_signals(evidence), {})


if __name__ == "__main__":
    unittest.main()
