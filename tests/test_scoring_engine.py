import unittest

from src.models.brand import FeatureValue
from src.scoring.engine import ScoringEngine


class ScoringEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = ScoringEngine()

    def test_weighted_average_and_composite_score(self):
        features_by_dim = {
            "coherencia": {
                "visual_consistency": FeatureValue("visual_consistency", 80.0),
                "messaging_consistency": FeatureValue("messaging_consistency", 60.0),
                "tone_consistency": FeatureValue("tone_consistency", 70.0),
                "cross_channel_coherence": FeatureValue("cross_channel_coherence", 50.0),
            },
            "presencia": {
                "web_presence": FeatureValue("web_presence", 90.0),
                "social_footprint": FeatureValue("social_footprint", 75.0),
                "search_visibility": FeatureValue("search_visibility", 80.0),
                "directory_presence": FeatureValue("directory_presence", 30.0),
            },
            "percepcion": {
                "brand_sentiment": FeatureValue("brand_sentiment", 70.0),
                "mention_volume": FeatureValue("mention_volume", 65.0),
                "sentiment_trend": FeatureValue("sentiment_trend", 55.0),
                "review_quality": FeatureValue("review_quality", 50.0),
            },
            "diferenciacion": {
                "positioning_clarity": FeatureValue("positioning_clarity", 75.0),
                "uniqueness": FeatureValue("uniqueness", 70.0),
                "competitor_distance": FeatureValue("competitor_distance", 70.0),
                "content_authenticity": FeatureValue("content_authenticity", 85.0),
                "brand_personality": FeatureValue("brand_personality", 80.0),
            },
            "vitalidad": {
                "content_recency": FeatureValue("content_recency", 90.0),
                "publication_cadence": FeatureValue("publication_cadence", 80.0),
                "momentum": FeatureValue("momentum", 60.0),
            },
        }

        brand = self.engine.score_brand("https://example.com", "Example", features_by_dim)

        self.assertAlmostEqual(brand.dimensions["coherencia"].score, 65.5)
        self.assertAlmostEqual(brand.dimensions["presencia"].score, 76.3)
        self.assertAlmostEqual(brand.dimensions["diferenciacion"].score, 74.8)
        # vitalidad = 0.40*90 + 0.35*80 + 0.25*60 = 79.0
        self.assertAlmostEqual(brand.dimensions["vitalidad"].score, 79.0)
        self.assertEqual(brand.composite_score, 70.9)

    def test_presence_ghost_brand_rule_caps_score(self):
        score = self.engine.score_dimension(
            "presencia",
            {
                "web_presence": FeatureValue("web_presence", 0.0),
                "social_footprint": FeatureValue("social_footprint", 0.0),
                "search_visibility": FeatureValue("search_visibility", 90.0),
                "directory_presence": FeatureValue("directory_presence", 90.0),
            },
        )

        self.assertEqual(score.score, 5.0)
        self.assertIn("marca_fantasma", score.rules_applied)

    def test_coherencia_one_active_channel_caps_score(self):
        score = self.engine.score_dimension(
            "coherencia",
            {
                "visual_consistency": FeatureValue("visual_consistency", 90.0),
                "messaging_consistency": FeatureValue("messaging_consistency", 85.0),
                "tone_consistency": FeatureValue("tone_consistency", 80.0),
                "cross_channel_coherence": FeatureValue("cross_channel_coherence", 75.0),
            },
            all_features={
                "coherencia": {},
                "presencia": {
                    "web_presence": FeatureValue("web_presence", 80.0),
                    "social_footprint": FeatureValue("social_footprint", 10.0),
                    "search_visibility": FeatureValue("search_visibility", 15.0),
                },
            },
        )

        self.assertEqual(score.score, 50.0)
        self.assertIn("solo_un_canal_activo", score.rules_applied)

    def test_percepcion_low_mentions_becomes_neutral(self):
        score = self.engine.score_dimension(
            "percepcion",
            {
                "brand_sentiment": FeatureValue("brand_sentiment", 90.0),
                "mention_volume": FeatureValue("mention_volume", 5.0),
                "sentiment_trend": FeatureValue("sentiment_trend", 80.0),
                "review_quality": FeatureValue("review_quality", 70.0),
            },
        )

        self.assertEqual(score.score, 50.0)
        self.assertIn("sin_datos_suficientes", score.rules_applied)

    def test_missing_features_default_to_neutral(self):
        score = self.engine.score_dimension("vitalidad", {})
        self.assertEqual(score.score, 50.0)

    def test_unavailable_dimensions_return_null_and_are_excluded_from_composite(self):
        features_by_dim = {
            "presencia": {
                "web_presence": FeatureValue("web_presence", 90.0),
                "social_footprint": FeatureValue("social_footprint", 75.0),
                "search_visibility": FeatureValue("search_visibility", 80.0),
                "directory_presence": FeatureValue("directory_presence", 30.0),
            },
            "percepcion": {
                "brand_sentiment": FeatureValue("brand_sentiment", 70.0),
                "mention_volume": FeatureValue("mention_volume", 65.0),
                "sentiment_trend": FeatureValue("sentiment_trend", 55.0),
                "review_quality": FeatureValue("review_quality", 50.0),
            },
            "vitalidad": {
                "content_recency": FeatureValue("content_recency", 90.0),
                "publication_cadence": FeatureValue("publication_cadence", 80.0),
                "momentum": FeatureValue("momentum", 60.0),
            },
        }

        brand = self.engine.score_brand(
            "https://example.com",
            "Example",
            features_by_dim,
            unavailable_dimensions={"coherencia", "diferenciacion"},
        )

        self.assertIsNone(brand.dimensions["coherencia"].score)
        self.assertIsNone(brand.dimensions["diferenciacion"].score)
        self.assertEqual(brand.dimensions["presencia"].score, 76.3)
        self.assertEqual(brand.dimensions["percepcion"].score, 62.8)
        self.assertEqual(brand.dimensions["vitalidad"].score, 79.0)
        self.assertEqual(brand.composite_score, 71.4)

    def test_frontier_ai_profile_prioritises_differentiation_and_vitality(self):
        base_engine = ScoringEngine()
        frontier_engine = ScoringEngine(calibration_profile="frontier_ai")

        features_by_dim = {
            "coherencia": {
                "visual_consistency": FeatureValue("visual_consistency", 70.0),
                "messaging_consistency": FeatureValue("messaging_consistency", 72.0),
                "tone_consistency": FeatureValue("tone_consistency", 68.0),
                "cross_channel_coherence": FeatureValue("cross_channel_coherence", 70.0),
            },
            "presencia": {
                "web_presence": FeatureValue("web_presence", 75.0),
                "social_footprint": FeatureValue("social_footprint", 25.0),
                "search_visibility": FeatureValue("search_visibility", 60.0),
                "directory_presence": FeatureValue("directory_presence", 20.0),
            },
            "percepcion": {
                "brand_sentiment": FeatureValue("brand_sentiment", 58.0),
                "mention_volume": FeatureValue("mention_volume", 8.0),
                "sentiment_trend": FeatureValue("sentiment_trend", 50.0),
                "review_quality": FeatureValue("review_quality", 42.0),
            },
            "diferenciacion": {
                "positioning_clarity": FeatureValue("positioning_clarity", 84.0),
                "uniqueness": FeatureValue("uniqueness", 60.0),
                "competitor_distance": FeatureValue("competitor_distance", 82.0),
                "content_authenticity": FeatureValue("content_authenticity", 88.0),
                "brand_personality": FeatureValue("brand_personality", 78.0),
            },
            "vitalidad": {
                "content_recency": FeatureValue("content_recency", 92.0),
                "publication_cadence": FeatureValue("publication_cadence", 82.0),
                "momentum": FeatureValue("momentum", 75.0),
            },
        }

        base_brand = base_engine.score_brand("https://example.com", "Example", features_by_dim)
        frontier_brand = frontier_engine.score_brand("https://example.com", "Example", features_by_dim)

        self.assertGreater(frontier_brand.composite_score, base_brand.composite_score)

    def test_profile_rule_override_tightens_generic_language_for_frontier_ai(self):
        base_engine = ScoringEngine()
        frontier_engine = ScoringEngine(calibration_profile="frontier_ai")

        features = {
            "positioning_clarity": FeatureValue("positioning_clarity", 90.0),
            "uniqueness": FeatureValue("uniqueness", 20.0),
            "competitor_distance": FeatureValue("competitor_distance", 85.0),
            "content_authenticity": FeatureValue("content_authenticity", 82.0),
            "brand_personality": FeatureValue("brand_personality", 76.0),
        }

        base_score = base_engine.score_dimension("diferenciacion", features)
        frontier_score = frontier_engine.score_dimension("diferenciacion", features)

        self.assertNotIn("lenguaje_generico", base_score.rules_applied)
        self.assertIn("lenguaje_generico", frontier_score.rules_applied)
        self.assertLess(frontier_score.score, base_score.score)


if __name__ == "__main__":
    unittest.main()
