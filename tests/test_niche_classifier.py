import unittest

from src.niche.classifier import classify_brand_niche, select_calibration_profile


class NicheClassifierTests(unittest.TestCase):
    def test_frontier_model_lab_is_classified_to_frontier_ai(self):
        payload = classify_brand_niche(
            "Prior Labs",
            "https://priorlabs.ai",
            web_title="Prior Labs builds tabular foundation models",
            web_content=(
                "Pre-trained tabular foundation models for enterprise data. "
                "Open source research and benchmark results for foundation-model systems."
            ),
            exa_texts=["Tabular foundation model startup with open source research"],
            competitor_names=["Hugging Face", "Anthropic"],
        )

        self.assertEqual(payload["predicted_niche"], "frontier_ai")
        self.assertEqual(payload["predicted_subtype"], "model_lab")
        self.assertGreaterEqual(payload["confidence"], 0.65)
        self.assertTrue(any("foundation" in item.lower() or "research" in item.lower() for item in payload["evidence"]))

    def test_startup_studio_stays_on_base_profile_but_is_not_low_confidence_noise(self):
        payload = classify_brand_niche(
            "Jetty AI",
            "https://jettyai.cloud",
            web_title="Jetty AI startup foundry",
            web_content="A venture studio and startup foundry building AI products.",
        )

        profile, source = select_calibration_profile(payload, min_confidence=0.65)

        self.assertEqual(payload["predicted_niche"], "base")
        self.assertEqual(payload["predicted_subtype"], "startup_studio")
        self.assertEqual(profile, "base")
        self.assertEqual(source, "auto")

    def test_community_platform_stays_on_base_and_beats_noisy_exa_ai_signals(self):
        payload = classify_brand_niche(
            "Movements",
            "https://movements.mov/en",
            web_title="MOVEMENTS",
            web_content=(
                "Convert your cause into an unstoppable movement. "
                "MOVEMENTS offers petitions, community, content and subscriptions to drive change. "
                "We are the new platform for those who want to organize, scale and sustain their cause. "
                "No algorithms limiting your reach. You maintain complete control over your audience."
            ),
            exa_texts=["frontier hardware model startup"],
        )

        profile, source = select_calibration_profile(payload, min_confidence=0.65)

        self.assertEqual(payload["predicted_niche"], "base")
        self.assertEqual(payload["predicted_subtype"], "community_platform")
        self.assertGreaterEqual(payload["confidence"], 0.65)
        self.assertEqual(profile, "base")
        self.assertEqual(source, "auto")

    def test_low_confidence_prediction_falls_back_to_base_profile(self):
        payload = {
            "predicted_niche": "enterprise_ai",
            "confidence": 0.42,
        }

        profile, source = select_calibration_profile(payload, min_confidence=0.65)

        self.assertEqual(profile, "base")
        self.assertEqual(source, "fallback")


if __name__ == "__main__":
    unittest.main()
