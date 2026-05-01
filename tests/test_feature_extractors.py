import unittest
from unittest.mock import patch

from src.collectors.competitor_collector import ComparisonResult, CompetitorData
from src.collectors.exa_collector import ExaData, ExaResult
from src.collectors.exa_collector import ExaCollector
from src.collectors.social_collector import PlatformMetrics, SocialData
from src.collectors.web_collector import WebData
from src.collectors.web_collector import WebCollector
from src.features.coherencia import CoherenciaExtractor
from src.features.diferenciacion import DiferenciacionExtractor
from src.features.llm_analyzer import LLMAnalyzer
from src.features.percepcion import PercepcionExtractor
from src.features.presencia import PresenciaExtractor
from src.features.vitalidad import VitalidadExtractor


class PercepcionExtractorTests(unittest.TestCase):
    """Covers the 4 percepcion features after the refactor with dict raw_value."""

    def _make_llm(self, sentiment_payload=None, older_payload=None, newer_payload=None, sequence=None):
        class FakeLLM:
            api_key = "sk-test"
            _calls = 0
            def analyze_brand_sentiment(self, mentions, brand_name):
                if sequence is not None:
                    idx = FakeLLM._calls
                    FakeLLM._calls += 1
                    if idx < len(sequence):
                        return sequence[idx]
                    return sequence[-1]
                # Two-call trend case
                if older_payload is not None and newer_payload is not None:
                    idx = FakeLLM._calls
                    FakeLLM._calls += 1
                    return older_payload if idx == 0 else newer_payload
                return sentiment_payload
        return FakeLLM()

    # ── brand_sentiment ────────────────────────────────────────────────

    def test_brand_sentiment_without_llm_uses_normalized_heuristic(self):
        exa = ExaData(
            brand_name="Test Brand",
            mentions=[
                ExaResult(url="https://x/1", title="t", text="excellent amazing outstanding"),
                ExaResult(url="https://x/2", title="t", text="great innovative reliable"),
            ],
        )
        feature = PercepcionExtractor()._brand_sentiment(exa)
        self.assertEqual(feature.source, "heuristic_fallback")
        self.assertEqual(feature.raw_value["reason"], "llm_unavailable")
        self.assertGreater(feature.raw_value["pos_count"], 0)

    def test_brand_sentiment_without_mentions_returns_neutral(self):
        feature = PercepcionExtractor()._brand_sentiment(ExaData(brand_name="X"))
        self.assertEqual(feature.value, 50.0)
        self.assertEqual(feature.raw_value["reason"], "no_mentions")

    def test_brand_sentiment_with_llm_uses_structured_verdict(self):
        exa = ExaData(brand_name="X", mentions=[
            ExaResult(url="https://x/1", title="t", text="a"),
            ExaResult(url="https://x/2", title="t", text="b"),
            ExaResult(url="https://x/3", title="t", text="c"),
        ])
        llm = self._make_llm(sentiment_payload={
            "sentiment_score": 82,
            "verdict": "positive",
            "overall_tone": "People praise reliability",
            "positive_themes": ["reliability", "speed"],
            "negative_themes": [],
            "evidence": [
                {"quote": "they ship fast", "source_url": "https://x/1", "signal": "positive"},
            ],
            "controversy_detected": False,
            "controversy_details": None,
            "reasoning": "Positive across mentions.",
        })
        feature = PercepcionExtractor(llm=llm)._brand_sentiment(exa)
        self.assertEqual(feature.source, "llm")
        self.assertEqual(feature.value, 82.0)
        self.assertEqual(feature.raw_value["verdict"], "positive")
        self.assertFalse(feature.raw_value["controversy_detected"])
        self.assertEqual(len(feature.raw_value["evidence"]), 1)

    def test_brand_sentiment_with_controversy_caps_score(self):
        exa = ExaData(brand_name="X", mentions=[
            ExaResult(url="https://x/1", title="t", text="a"),
            ExaResult(url="https://x/2", title="t", text="b"),
            ExaResult(url="https://x/3", title="t", text="c"),
        ])
        llm = self._make_llm(sentiment_payload={
            "sentiment_score": 80,  # LLM gave high score but flagged controversy
            "verdict": "mixed",
            "overall_tone": "Mixed with legal concerns",
            "positive_themes": [],
            "negative_themes": ["lawsuit"],
            "evidence": [
                {"quote": "filed a class action", "source_url": "https://x/1", "signal": "negative"},
            ],
            "controversy_detected": True,
            "controversy_details": "Class action lawsuit filed Q2 2026.",
            "reasoning": "Legal issue dominates.",
        })
        feature = PercepcionExtractor(llm=llm)._brand_sentiment(exa)
        self.assertLessEqual(feature.value, 35.0)
        self.assertTrue(feature.raw_value["controversy_detected"])
        self.assertTrue(feature.raw_value["controversy_cap_applied"])
        self.assertEqual(feature.raw_value["capped_from_score"], 80.0)
        self.assertEqual(feature.raw_value["controversy_details"], "Class action lawsuit filed Q2 2026.")

    def test_brand_sentiment_invalid_verdict_falls_back(self):
        exa = ExaData(brand_name="X", mentions=[
            ExaResult(url="https://x/1", title="t", text="a"),
        ])
        llm = self._make_llm(sentiment_payload={
            "sentiment_score": 70, "verdict": "glowing", "evidence": [],
        })
        feature = PercepcionExtractor(llm=llm)._brand_sentiment(exa)
        self.assertEqual(feature.source, "heuristic_fallback")
        self.assertEqual(feature.raw_value["reason"], "llm_invalid_verdict")

    def test_brand_sentiment_malformed_evidence_is_filtered(self):
        exa = ExaData(brand_name="X", mentions=[
            ExaResult(url="https://x/1", title="t", text="a"),
            ExaResult(url="https://x/2", title="t", text="b"),
        ])
        llm = self._make_llm(sentiment_payload={
            "sentiment_score": 72,
            "verdict": "positive",
            "positive_themes": [],
            "negative_themes": [],
            "evidence": [
                {"quote": "solid", "source_url": "https://x/1", "signal": "positive"},
                {"quote": 123, "source_url": "https://x/2", "signal": "positive"},  # malformed
                "not a dict",
            ],
            "controversy_detected": False,
            "reasoning": "ok",
        })
        feature = PercepcionExtractor(llm=llm)._brand_sentiment(exa)
        self.assertEqual(feature.source, "llm")
        self.assertEqual(len(feature.raw_value["evidence"]), 1)
        self.assertEqual(feature.confidence, 0.5)
        self.assertEqual(feature.raw_value["reason"], "llm_partial_evidence")

    def test_brand_sentiment_non_bool_controversy_is_treated_as_false_with_warning(self):
        exa = ExaData(brand_name="X", mentions=[
            ExaResult(url="https://x/1", title="t", text="a"),
        ])
        llm = self._make_llm(sentiment_payload={
            "sentiment_score": 72,
            "verdict": "positive",
            "evidence": [
                {"quote": "ok", "source_url": "https://x/1", "signal": "positive"},
            ],
            "controversy_detected": "yes",  # wrong type
            "reasoning": "ok",
        })
        feature = PercepcionExtractor(llm=llm)._brand_sentiment(exa)
        self.assertFalse(feature.raw_value["controversy_detected"])
        self.assertEqual(feature.raw_value["controversy_detected_type_warning"], "str")
        self.assertEqual(feature.value, 72.0)

    # ── mention_volume ─────────────────────────────────────────────────

    def test_mention_volume_returns_dict_with_tier_and_top_domains(self):
        exa = ExaData(brand_name="X", mentions=[
            ExaResult(url="https://techcrunch.com/a", title="t", text="..."),
            ExaResult(url="https://techcrunch.com/b", title="t", text="..."),
            ExaResult(url="https://theverge.com/a", title="t", text="..."),
        ], news=[
            ExaResult(url="https://news.example.com/a", title="t", text="..."),
        ])
        feature = PercepcionExtractor()._mention_volume(exa)
        self.assertEqual(feature.raw_value["total_mentions"], 4)
        self.assertEqual(feature.raw_value["volume_tier"], "low")
        self.assertEqual(feature.raw_value["top_domains"][0], "techcrunch.com")

    def test_mention_volume_without_exa_reports_none(self):
        feature = PercepcionExtractor()._mention_volume(exa=None)
        self.assertEqual(feature.raw_value["volume_tier"], "none")
        self.assertEqual(feature.raw_value["total_mentions"], 0)

    # ── sentiment_trend ────────────────────────────────────────────────

    def test_sentiment_trend_insufficient_dated_returns_neutral(self):
        exa = ExaData(brand_name="X", mentions=[
            ExaResult(url="https://x/1", title="t", text="great", published_date=""),
            ExaResult(url="https://x/2", title="t", text="great", published_date="2026-04-01"),
            ExaResult(url="https://x/3", title="t", text="bad", published_date=""),
        ])
        feature = PercepcionExtractor()._sentiment_trend(exa)
        self.assertEqual(feature.value, 50.0)
        self.assertEqual(feature.raw_value["reason"], "insufficient_dated_mentions")

    def test_sentiment_trend_with_llm_compares_halves(self):
        exa = ExaData(brand_name="X", mentions=[
            ExaResult(url="https://x/1", title="t", text="lawsuit trouble", published_date="2024-01-01"),
            ExaResult(url="https://x/2", title="t", text="controversy", published_date="2024-02-01"),
            ExaResult(url="https://x/3", title="t", text="great recovery", published_date="2026-03-01"),
            ExaResult(url="https://x/4", title="t", text="amazing growth", published_date="2026-04-01"),
        ])
        llm = self._make_llm(
            older_payload={"sentiment_score": 30, "verdict": "negative", "evidence": []},
            newer_payload={"sentiment_score": 80, "verdict": "positive", "evidence": []},
        )
        feature = PercepcionExtractor(llm=llm)._sentiment_trend(exa)
        self.assertEqual(feature.source, "llm")
        self.assertEqual(feature.raw_value["trend"], "improving")
        self.assertEqual(feature.raw_value["delta"], 50.0)

    def test_sentiment_trend_without_llm_uses_normalized_heuristic(self):
        exa = ExaData(brand_name="X", mentions=[
            ExaResult(url="https://x/1", title="t", text="lawsuit trouble", published_date="2024-01-01"),
            ExaResult(url="https://x/2", title="t", text="fraud scam", published_date="2024-02-01"),
            ExaResult(url="https://x/3", title="t", text="great innovative", published_date="2026-03-01"),
            ExaResult(url="https://x/4", title="t", text="amazing reliable", published_date="2026-04-01"),
        ])
        feature = PercepcionExtractor()._sentiment_trend(exa)
        self.assertEqual(feature.source, "heuristic_fallback")
        self.assertEqual(feature.raw_value["method"], "heuristic_fallback")
        self.assertEqual(feature.raw_value["trend"], "improving")

    # ── review_quality ─────────────────────────────────────────────────

    def test_review_quality_without_platforms_returns_absent(self):
        exa = ExaData(brand_name="X", mentions=[
            ExaResult(url=f"https://example.com/{i}", title="t", text="strong") for i in range(4)
        ], news=[ExaResult(url="https://news.example.com/item", title="t", text="launch")])
        feature = PercepcionExtractor()._review_quality(exa)
        self.assertEqual(feature.raw_value["review_signal"], "absent")
        self.assertEqual(feature.raw_value["total_review_results"], 0)

    def test_review_quality_rewards_professional_platforms(self):
        exa = ExaData(brand_name="X", mentions=[
            ExaResult(url="https://www.g2.com/products/example/reviews", title="G2", text="..."),
            ExaResult(url="https://www.trustpilot.com/review/example.com", title="TP", text="..."),
        ])
        feature = PercepcionExtractor()._review_quality(exa)
        self.assertTrue(feature.raw_value["has_professional_reviews"])
        self.assertFalse(feature.raw_value["has_consumer_reviews"])
        self.assertGreaterEqual(feature.value, 60.0)
        self.assertIn(feature.raw_value["review_signal"], {"moderate", "strong"})
        domains = [p["domain"] for p in feature.raw_value["platforms_with_reviews"]]
        self.assertIn("g2.com", domains)
        self.assertIn("trustpilot.com", domains)

    # ── contract ───────────────────────────────────────────────────────

    def test_extract_always_returns_four_features(self):
        features = PercepcionExtractor().extract(web=None, exa=None)
        self.assertEqual(
            set(features.keys()),
            {"brand_sentiment", "mention_volume", "sentiment_trend", "review_quality"},
        )


class DiferenciacionExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = DiferenciacionExtractor()

    @staticmethod
    def _competitor_data():
        return CompetitorData(
            brand_name="Example",
            brand_url="https://example.com",
            comparisons=[
                ComparisonResult(
                    competitor_name="ClosestCo",
                    competitor_url="https://closest.example",
                    overall_distance=0.22,
                    brand_unique_terms=["deterministic", "control", "governance"],
                ),
                ComparisonResult(
                    competitor_name="FarCo",
                    competitor_url="https://far.example",
                    overall_distance=0.81,
                    brand_unique_terms=["deterministic", "control", "governance", "audit"],
                ),
            ],
        )

    @staticmethod
    def _make_llm(positioning=None, uniqueness=None):
        llm = LLMAnalyzer(api_key="test")
        llm.analyze_positioning_clarity = lambda *args, **kwargs: positioning or {}
        llm.analyze_uniqueness = lambda *args, **kwargs: uniqueness or {}
        return llm

    def test_positioning_clarity_without_llm_uses_heuristic_fallback(self):
        web = WebData(
            url="https://priorlabs.ai",
            title="One Model, Infinite Predictions",
            markdown_content=(
                "# One Model, Infinite Predictions\n\n"
                "We are building tabular foundation models for developers.\n"
                "Built for teams making predictions on structured data.\n"
            ),
        )

        feature = self.extractor.extract(web=web)["positioning_clarity"]

        self.assertEqual(feature.source, "heuristic_fallback")
        self.assertEqual(feature.confidence, 0.4)
        self.assertEqual(feature.raw_value["reason"], "llm_unavailable")
        self.assertIn("built for", feature.raw_value["signals_detected"])

    def test_positioning_clarity_with_llm_uses_structured_output(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content=("word " * 600),
        )
        extractor = DiferenciacionExtractor(
            llm=self._make_llm(
                positioning={
                    "clarity_score": 82,
                    "verdict": "clear",
                    "stated_position": "Deterministic infrastructure for enterprise AI.",
                    "target_audience": "Enterprise AI teams",
                    "differentiator_claimed": "A deterministic control layer",
                    "evidence": [
                        {"quote": "Deterministic infrastructure for enterprise AI.", "signal": "clear"}
                    ],
                    "reasoning": "The statement is concrete and repeated.",
                }
            )
        )

        feature = extractor.extract(web=web)["positioning_clarity"]

        self.assertEqual(feature.source, "llm")
        self.assertEqual(feature.value, 82)
        self.assertEqual(feature.raw_value["verdict"], "clear")
        self.assertEqual(len(feature.raw_value["evidence"]), 1)
        self.assertEqual(feature.confidence, 0.85)

    def test_positioning_clarity_invalid_verdict_falls_back(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content=("word " * 600),
        )
        extractor = DiferenciacionExtractor(
            llm=self._make_llm(
                positioning={
                    "clarity_score": 82,
                    "verdict": "sharp",
                    "stated_position": "x",
                    "target_audience": "y",
                    "differentiator_claimed": "z",
                    "evidence": [{"quote": "x", "signal": "clear"}],
                    "reasoning": "bad verdict",
                }
            )
        )

        feature = extractor.extract(web=web)["positioning_clarity"]

        self.assertEqual(feature.source, "heuristic_fallback")
        self.assertEqual(feature.raw_value["reason"], "llm_invalid_verdict")

    def test_positioning_clarity_malformed_evidence_degrades_confidence(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content=("word " * 600),
        )
        extractor = DiferenciacionExtractor(
            llm=self._make_llm(
                positioning={
                    "clarity_score": 78,
                    "verdict": "clear",
                    "stated_position": "x",
                    "target_audience": "y",
                    "differentiator_claimed": "z",
                    "evidence": [{"quote": "x"}],
                    "reasoning": "partial evidence",
                }
            ),
        )

        feature = extractor.extract(web=web)["positioning_clarity"]

        self.assertEqual(feature.source, "llm")
        self.assertEqual(feature.confidence, 0.5)
        self.assertEqual(feature.raw_value["reason"], "llm_partial_evidence")
        self.assertEqual(feature.raw_value["evidence"], [])

    def test_uniqueness_without_llm_uses_normalized_ratio_fallback(self):
        web = WebData(
            url="https://generic.example",
            title="Generic SaaS",
            markdown_content=(
                "# Generic SaaS\n\n"
                "We help businesses grow and improve efficiency.\n"
                "Save time. Save money. Better results. Cutting edge workflows.\n"
            ),
        )

        feature = self.extractor.extract(web=web)["uniqueness"]

        self.assertEqual(feature.source, "heuristic_fallback")
        self.assertEqual(feature.raw_value["reason"], "llm_unavailable")
        self.assertGreater(feature.raw_value["ratio"], 0.0)
        self.assertGreater(feature.raw_value["sentence_count"], 0)

    def test_uniqueness_with_llm_uses_structured_output(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content=("word " * 600),
        )
        extractor = DiferenciacionExtractor(
            llm=self._make_llm(
                uniqueness={
                    "uniqueness_score": 76,
                    "verdict": "moderately_unique",
                    "unique_phrases": ["deterministic layer"],
                    "generic_phrases": ["cutting edge"],
                    "brand_vocabulary": ["frontier intelligence"],
                    "competitor_overlap_signals": ["shares some enterprise framing"],
                    "reasoning": "Some ownable language exists.",
                }
            )
        )

        feature = extractor.extract(web=web)["uniqueness"]

        self.assertEqual(feature.source, "llm")
        self.assertEqual(feature.value, 76)
        self.assertEqual(feature.raw_value["verdict"], "moderately_unique")
        self.assertIn("deterministic layer", feature.raw_value["unique_phrases"])
        self.assertEqual(feature.confidence, 0.85)

    def test_uniqueness_invalid_verdict_falls_back(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content=("word " * 600),
        )
        extractor = DiferenciacionExtractor(
            llm=self._make_llm(
                uniqueness={
                    "uniqueness_score": 90,
                    "verdict": "iconic",
                    "unique_phrases": [],
                    "generic_phrases": [],
                    "brand_vocabulary": [],
                    "competitor_overlap_signals": [],
                    "reasoning": "bad verdict",
                }
            )
        )

        feature = extractor.extract(web=web)["uniqueness"]

        self.assertEqual(feature.source, "heuristic_fallback")
        self.assertEqual(feature.raw_value["reason"], "llm_invalid_verdict")

    def test_competitor_distance_uses_structured_raw_value(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content="Deterministic infrastructure for AI teams.",
        )
        feature = self.extractor.extract(
            web=web,
            competitor_data=self._competitor_data(),
        )["competitor_distance"]

        self.assertEqual(feature.source, "competitor_web_comparison")
        self.assertEqual(feature.raw_value["closest_competitor"]["name"], "ClosestCo")
        self.assertEqual(feature.raw_value["most_different"]["name"], "FarCo")
        self.assertEqual(feature.raw_value["competitors_analyzed"], 2)
        self.assertIsInstance(feature.raw_value["brand_unique_terms"], list)

    def test_content_authenticity_and_brand_personality_return_structured_raw_value(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content=(
                "We're building a deterministic layer for enterprise AI. "
                "We believe teams deserve control instead of generic copilots. "
                "Learn more about our platform and how we help teams move faster."
            ),
        )
        exa = ExaData(
            brand_name="Example",
            mentions=[
                ExaResult(
                    url="https://example.com/coverage",
                    title="Coverage",
                    text="Opinionated founder-led product.",
                )
            ],
        )

        features = self.extractor.extract(web=web, exa=exa)
        authenticity = features["content_authenticity"]
        personality = features["brand_personality"]

        self.assertIsInstance(authenticity.raw_value, dict)
        self.assertIn("authenticity_verdict", authenticity.raw_value)
        self.assertIsInstance(personality.raw_value, dict)
        self.assertIn("signals_detected", personality.raw_value)


class PresenciaExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = PresenciaExtractor()

    def _exa_mentions(self, brand_name: str = "Acme") -> ExaData:
        return ExaData(
            brand_name=brand_name,
            mentions=[
                ExaResult(
                    url="https://acme.com/blog/launch",
                    title="Acme launches new product",
                    text="Acme expands its launch motion with a new platform release.",
                    summary="Acme expands with a product release.",
                    score=0.9,
                ),
                ExaResult(
                    url="https://techcrunch.com/acme-funding",
                    title="Acme raises funding",
                    text="Acme is highlighted as a growing company.",
                    summary="Growing company profile.",
                    score=0.8,
                ),
                ExaResult(
                    url="https://random.com/roundup",
                    title="AI roundup",
                    text="Many vendors are covered in this roundup.",
                    summary="General roundup with many names.",
                    score=0.3,
                ),
            ],
            ai_visibility_results=[
                ExaResult(
                    url="https://example.com/acme-best-tools",
                    title="Acme in top AI tools",
                    text="Acme is recommended for enterprise teams.",
                    score=0.8,
                ),
                ExaResult(
                    url="https://example.com/general-roundup",
                    title="General AI roundup",
                    text="Acme appears in a broader list.",
                    score=0.5,
                ),
            ],
        )

    def test_web_presence_placeholder_page_scores_minimal(self):
        web = WebData(
            url="http://placeholder.example",
            title="Coming Soon",
            markdown_content="Coming soon. Buy this domain today.",
        )

        feature = self.extractor._web_presence(web)

        self.assertEqual(feature.value, 5.0)
        self.assertEqual(feature.raw_value["page_status"], "placeholder")
        self.assertIn("placeholder_detected", feature.raw_value["signals_detected"])

    def test_web_presence_normal_site_scores_high_with_structured_raw_value(self):
        web = WebData(
            url="https://example.com",
            title="Example Platform",
            meta_description="Example Platform helps finance teams move faster.",
            markdown_content=(
                "# Example Platform\n\n"
                "Example Platform helps finance teams move faster with approvals, docs, and automation.\n"
                "Pricing About Contact Docs Features Get started Privacy Terms.\n"
            ),
        )

        feature = self.extractor._web_presence(web)

        self.assertGreaterEqual(feature.value, 75.0)
        self.assertTrue(feature.raw_value["has_https"])
        self.assertEqual(feature.raw_value["page_status"], "live")
        self.assertIsInstance(feature.raw_value["evidence_snippet"], str)
        self.assertIn("https", feature.raw_value["signals_detected"])

    def test_web_presence_without_https_loses_signal(self):
        secure = WebData(
            url="https://example.com",
            title="Example",
            meta_description="Example is a real product site.",
            markdown_content="# Example\n\nExample is a real product site with pricing and contact.",
        )
        insecure = WebData(
            url="http://example.com",
            title="Example",
            meta_description="Example is a real product site.",
            markdown_content="# Example\n\nExample is a real product site with pricing and contact.",
        )

        secure_feature = self.extractor._web_presence(secure)
        insecure_feature = self.extractor._web_presence(insecure)

        self.assertGreater(secure_feature.value, insecure_feature.value)
        self.assertFalse(insecure_feature.raw_value["has_https"])

    def test_web_presence_without_meaningful_content_stays_low(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content="Login",
        )

        feature = self.extractor._web_presence(web)

        self.assertLessEqual(feature.value, 35.0)
        self.assertEqual(feature.raw_value["page_status"], "minimal")

    def test_social_footprint_without_social_data_degrades_gracefully(self):
        feature = self.extractor._social_footprint(social=None)

        self.assertEqual(feature.value, 15.0)
        self.assertEqual(feature.confidence, 0.3)
        self.assertEqual(feature.raw_value["reason"], "no_social_data")

    def test_social_footprint_with_multiple_platforms_is_structured(self):
        social = SocialData(
            brand_name="Example",
            platforms={
                "linkedin": PlatformMetrics(
                    platform="linkedin",
                    profile_url="https://linkedin.com/company/example",
                    followers_count=12000,
                    verified=True,
                    last_post_date="2026-04-10",
                    posts_last_30_days=6,
                ),
                "instagram": PlatformMetrics(
                    platform="instagram",
                    profile_url="https://instagram.com/example",
                    followers_count=8000,
                    verified=False,
                    last_post_date="2026-04-12",
                    posts_last_30_days=8,
                ),
            },
            total_followers=20000,
            avg_post_frequency=3,
        )

        feature = self.extractor._social_footprint(social=social)

        self.assertGreaterEqual(feature.value, 55.0)
        self.assertEqual(feature.raw_value["total_followers"], 20000)
        self.assertEqual(feature.raw_value["active_platforms_count"], 2)
        self.assertTrue(feature.raw_value["professional_presence"])
        self.assertTrue(feature.raw_value["consumer_presence"])
        self.assertEqual(len(feature.raw_value["platforms"]), 2)

    def test_social_footprint_rewards_verified_accounts(self):
        unverified = SocialData(
            brand_name="Example",
            platforms={
                "linkedin": PlatformMetrics(
                    platform="linkedin",
                    profile_url="https://linkedin.com/company/example",
                    followers_count=12000,
                    verified=False,
                    last_post_date="2026-04-10",
                    posts_last_30_days=3,
                )
            },
            total_followers=12000,
            avg_post_frequency=2,
        )
        verified = SocialData(
            brand_name="Example",
            platforms={
                "linkedin": PlatformMetrics(
                    platform="linkedin",
                    profile_url="https://linkedin.com/company/example",
                    followers_count=12000,
                    verified=True,
                    last_post_date="2026-04-10",
                    posts_last_30_days=3,
                )
            },
            total_followers=12000,
            avg_post_frequency=2,
        )

        unverified_feature = self.extractor._social_footprint(social=unverified)
        verified_feature = self.extractor._social_footprint(social=verified)

        self.assertGreater(verified_feature.value, unverified_feature.value)
        self.assertTrue(verified_feature.raw_value["platforms"][0]["verified"])

    def test_search_visibility_without_results_returns_low_neutral(self):
        feature = self.extractor._search_visibility(exa=None)

        self.assertEqual(feature.value, 15.0)
        self.assertEqual(feature.raw_value["search_results_count"], 0)
        self.assertEqual(feature.raw_value["evidence"], [])

    def test_search_visibility_with_few_results_stays_mid_low(self):
        exa = ExaData(
            brand_name="Acme",
            mentions=[
                ExaResult(
                    url="https://acme.com/about",
                    title="Acme",
                    text="Acme builds software for teams.",
                    score=0.7,
                ),
                ExaResult(
                    url="https://news.example.com/acme",
                    title="Acme profile",
                    text="Acme is covered in a profile.",
                    score=0.5,
                ),
            ],
        )

        feature = self.extractor._search_visibility(exa)

        self.assertGreaterEqual(feature.value, 20.0)
        self.assertLess(feature.value, 50.0)
        self.assertEqual(feature.raw_value["relevant_results_count"], 2)

    def test_search_visibility_rewards_many_results_and_own_url_top3(self):
        exa = self._exa_mentions()
        exa.mentions.extend(
            [
                ExaResult(
                    url=f"https://coverage{i}.example.com/acme",
                    title=f"Acme mention {i}",
                    text="Acme is the main subject of this article.",
                    score=0.7,
                )
                for i in range(6)
            ]
        )

        feature = self.extractor._search_visibility(exa)

        self.assertGreaterEqual(feature.value, 70.0)
        self.assertTrue(feature.raw_value["own_url_in_top3"])
        self.assertGreaterEqual(feature.raw_value["ai_visibility_signals"], 1)
        self.assertEqual(len(feature.raw_value["evidence"]), 3)

    def test_search_visibility_filters_low_subject_relevance(self):
        exa = ExaData(
            brand_name="Acme",
            mentions=[
                ExaResult(
                    url="https://roundup.example.com",
                    title="General software roundup",
                    text="Many brands are discussed here without focusing on one.",
                    score=0.8,
                ),
                ExaResult(
                    url="https://acme.com",
                    title="Acme",
                    text="Acme is the main subject here.",
                    score=0.8,
                ),
            ],
        )

        feature = self.extractor._search_visibility(exa)

        self.assertEqual(feature.raw_value["search_results_count"], 2)
        self.assertEqual(feature.raw_value["relevant_results_count"], 1)
        self.assertEqual(len(feature.raw_value["evidence"]), 1)

    def test_directory_presence_without_directories_is_zero(self):
        exa = ExaData(
            brand_name="Acme",
            mentions=[ExaResult(url="https://acme.com", title="Acme", text="Owned site")],
        )

        feature = self.extractor._directory_presence(exa)

        self.assertEqual(feature.value, 0.0)
        self.assertEqual(feature.raw_value["total_points"], 0)

    def test_directory_presence_with_only_tier2_is_limited(self):
        exa = ExaData(
            brand_name="Acme",
            mentions=[
                ExaResult(
                    url="https://producthunt.com/posts/acme",
                    title="Acme on Product Hunt",
                    text="Listing",
                ),
                ExaResult(
                    url="https://trustpilot.com/review/acme.com",
                    title="Acme reviews",
                    text="Review listing",
                ),
            ],
        )

        feature = self.extractor._directory_presence(exa)

        self.assertEqual(feature.value, 16.0)
        self.assertEqual(len(feature.raw_value["tier2_found"]), 2)
        self.assertEqual(feature.raw_value["tier1_found"], [])

    def test_directory_presence_with_tier1_and_tier2_mix_scores_higher(self):
        exa = ExaData(
            brand_name="Acme",
            mentions=[
                ExaResult(url="https://crunchbase.com/organization/acme", title="Crunchbase", text="Listing"),
                ExaResult(url="https://linkedin.com/company/acme", title="LinkedIn", text="Listing"),
                ExaResult(url="https://producthunt.com/posts/acme", title="Product Hunt", text="Listing"),
            ],
        )

        feature = self.extractor._directory_presence(exa)

        self.assertEqual(feature.value, 48.0)
        self.assertEqual(len(feature.raw_value["tier1_found"]), 2)
        self.assertEqual(len(feature.raw_value["tier2_found"]), 1)


class VitalidadExtractorTests(unittest.TestCase):
    """Cover the 3 features (content_recency, publication_cadence, momentum)."""

    def setUp(self):
        self.extractor = VitalidadExtractor()

    # ── content_recency ────────────────────────────────────────────────

    def _exa_with_dates(self, days_ago_list: list[int]) -> ExaData:
        from datetime import datetime, timedelta
        base = datetime.now()
        mentions = [
            ExaResult(
                url=f"https://example.com/article-{i}",
                title=f"Article {i}",
                text="content",
                published_date=(base - timedelta(days=d)).strftime("%Y-%m-%d"),
            )
            for i, d in enumerate(days_ago_list)
        ]
        return ExaData(brand_name="Test", mentions=mentions)

    def test_content_recency_recent_publication_scores_high(self):
        exa = self._exa_with_dates([3])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["content_recency"].value, 100.0)

    def test_content_recency_30_days_is_mid_high(self):
        exa = self._exa_with_dates([25])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["content_recency"].value, 85.0)

    def test_content_recency_6_months_drops_to_mid(self):
        exa = self._exa_with_dates([150])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["content_recency"].value, 40.0)

    def test_content_recency_past_year_is_low(self):
        exa = self._exa_with_dates([250])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["content_recency"].value, 20.0)

    def test_content_recency_over_365_days_is_very_low(self):
        exa = self._exa_with_dates([400])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["content_recency"].value, 10.0)

    def test_content_recency_no_dates_returns_neutral_with_reason(self):
        import json
        features = self.extractor.extract(exa=None)
        fv = features["content_recency"]
        self.assertEqual(fv.value, 30.0)
        self.assertEqual(fv.source, "none")
        payload = fv.raw_value
        self.assertIsNone(payload["most_recent_date"])
        self.assertIsNone(payload["days_ago"])
        self.assertIsNone(payload["evidence_url"])
        self.assertEqual(payload["reason"], "no_dates_found")

    # ── publication_cadence ────────────────────────────────────────────

    def test_publication_cadence_fewer_than_2_dates_is_low(self):
        import json
        exa = self._exa_with_dates([15])
        features = self.extractor.extract(exa=exa)
        fv = features["publication_cadence"]
        self.assertEqual(fv.value, 20.0)
        payload = fv.raw_value
        self.assertEqual(payload["reason"], "insufficient_dates_12m")

    def test_publication_cadence_regular_rhythm_scores_high(self):
        # 3 dates roughly ~20 days apart → mean_gap < 30 → 90
        exa = self._exa_with_dates([10, 35, 60])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["publication_cadence"].value, 90.0)

    def test_publication_cadence_moderate_rhythm_scores_mid(self):
        # 3 dates ~100 days apart → 90 <= mean < 180 → 50
        exa = self._exa_with_dates([5, 110, 215])
        features = self.extractor.extract(exa=exa)
        self.assertEqual(features["publication_cadence"].value, 50.0)

    # ── momentum ───────────────────────────────────────────────────────

    def test_momentum_without_llm_returns_heuristic_fallback(self):
        import json
        exa = self._exa_with_dates([30, 60])
        features = self.extractor.extract(exa=exa)
        fv = features["momentum"]
        self.assertEqual(fv.value, 50.0)
        self.assertEqual(fv.source, "heuristic_fallback")
        self.assertEqual(fv.confidence, 0.3)
        payload = fv.raw_value
        self.assertEqual(payload["reason"], "llm_unavailable")

    def test_momentum_with_llm_uses_structured_verdict(self):
        import json

        class FakeLLM:
            api_key = "sk-test"

            def analyze_momentum(self, mentions, brand_name):
                return {
                    "momentum_score": 82,
                    "verdict": "building",
                    "evidence": [
                        {
                            "quote": "shipped a new inference runtime",
                            "source_url": "https://example.com/article-0",
                            "signal": "positive",
                        }
                    ],
                    "reasoning": "Fresh product launches in the last quarter.",
                }

        extractor = VitalidadExtractor(llm=FakeLLM())
        exa = self._exa_with_dates([10, 40])
        features = extractor.extract(exa=exa)

        fv = features["momentum"]
        self.assertEqual(fv.value, 82.0)
        self.assertEqual(fv.source, "llm")
        self.assertEqual(fv.confidence, 0.85)
        payload = fv.raw_value
        self.assertEqual(payload["verdict"], "building")
        self.assertEqual(len(payload["evidence"]), 1)
        self.assertIn("shipped a new inference runtime", payload["evidence"][0]["quote"])

    def test_momentum_with_unclear_verdict_has_lower_confidence(self):
        import json

        class FakeLLM:
            api_key = "sk-test"

            def analyze_momentum(self, mentions, brand_name):
                return {
                    "momentum_score": 50,
                    "verdict": "unclear",
                    "evidence": [],
                    "reasoning": "Evidence insufficient.",
                }

        extractor = VitalidadExtractor(llm=FakeLLM())
        exa = self._exa_with_dates([20])
        features = extractor.extract(exa=exa)
        fv = features["momentum"]
        self.assertEqual(fv.confidence, 0.5)
        self.assertEqual(fv.raw_value["verdict"], "unclear")

    def test_momentum_with_no_recent_mentions_returns_fallback(self):
        import json

        class FakeLLM:
            api_key = "sk-test"

            def analyze_momentum(self, mentions, brand_name):
                raise AssertionError("should not be called when no recent mentions")

        extractor = VitalidadExtractor(llm=FakeLLM())
        # Only old mentions, outside the 6-month window
        exa = self._exa_with_dates([400, 500])
        features = extractor.extract(exa=exa)
        fv = features["momentum"]
        self.assertEqual(fv.source, "heuristic_fallback")
        self.assertEqual(fv.raw_value["reason"], "no_recent_mentions_6m")

    def test_extract_always_returns_three_features(self):
        features = self.extractor.extract(web=None, exa=None)
        self.assertEqual(
            set(features.keys()),
            {"content_recency", "publication_cadence", "momentum"},
        )

    # ── momentum — LLM contract negative tests ─────────────────────────

    def _make_momentum_llm(self, payload):
        """Helper: fake LLMAnalyzer that returns a fixed payload from analyze_momentum."""

        class FakeLLM:
            api_key = "sk-test"

            def analyze_momentum(self, mentions, brand_name):
                return payload

        return FakeLLM()

    def test_momentum_with_invalid_verdict_falls_back(self):
        import json

        llm = self._make_momentum_llm({
            "momentum_score": 80,
            "verdict": "thriving",  # not in the enum
            "evidence": [
                {
                    "quote": "shipped v2",
                    "source_url": "https://example.com/article-0",
                    "signal": "positive",
                }
            ],
            "reasoning": "Good stuff.",
        })
        extractor = VitalidadExtractor(llm=llm)
        features = extractor.extract(exa=self._exa_with_dates([10]))
        fv = features["momentum"]
        self.assertEqual(fv.source, "heuristic_fallback")
        self.assertEqual(fv.value, 50.0)
        payload = fv.raw_value
        self.assertEqual(payload["reason"], "llm_invalid_verdict")
        self.assertEqual(payload["got"], "thriving")

    def test_momentum_with_non_list_evidence_degrades_confidence(self):
        import json

        llm = self._make_momentum_llm({
            "momentum_score": 72,
            "verdict": "building",
            "evidence": "they shipped a lot",  # should be list
            "reasoning": "Clearly active.",
        })
        extractor = VitalidadExtractor(llm=llm)
        features = extractor.extract(exa=self._exa_with_dates([10]))
        fv = features["momentum"]
        # Still source=llm because verdict is valid, but degraded confidence.
        self.assertEqual(fv.source, "llm")
        self.assertEqual(fv.value, 72.0)
        self.assertEqual(fv.confidence, 0.5)
        payload = fv.raw_value
        self.assertEqual(payload["reason"], "llm_partial_evidence")
        self.assertEqual(payload["evidence"], [])

    def test_momentum_with_malformed_evidence_items_are_filtered(self):
        import json

        llm = self._make_momentum_llm({
            "momentum_score": 82,
            "verdict": "building",
            "evidence": [
                # Missing signal → dropped.
                {"quote": "launched new runtime", "source_url": "https://x.com/1"},
                # Wrong signal value → dropped.
                {"quote": "grew 3x", "source_url": "https://x.com/2", "signal": "bullish"},
                # Non-str quote → dropped.
                {"quote": 123, "source_url": "https://x.com/3", "signal": "positive"},
                # Valid → kept.
                {"quote": "hired 40 engineers",
                 "source_url": "https://x.com/4",
                 "signal": "positive"},
                # Non-dict → dropped.
                "random string",
            ],
            "reasoning": "Mix.",
        })
        extractor = VitalidadExtractor(llm=llm)
        features = extractor.extract(exa=self._exa_with_dates([10]))
        fv = features["momentum"]
        self.assertEqual(fv.source, "llm")
        self.assertEqual(fv.confidence, 0.5)
        payload = fv.raw_value
        self.assertEqual(len(payload["evidence"]), 1)
        self.assertEqual(payload["evidence"][0]["quote"], "hired 40 engineers")
        self.assertEqual(payload["reason"], "llm_partial_evidence")

    def test_momentum_with_all_evidence_items_malformed_flags_partial(self):
        import json

        llm = self._make_momentum_llm({
            "momentum_score": 64,
            "verdict": "maintaining",
            "evidence": [
                {"quote": "something"},  # missing fields → dropped
                "not a dict",
            ],
            "reasoning": "Little signal.",
        })
        extractor = VitalidadExtractor(llm=llm)
        features = extractor.extract(exa=self._exa_with_dates([10]))
        fv = features["momentum"]
        self.assertEqual(fv.source, "llm")
        self.assertEqual(fv.value, 64.0)
        self.assertEqual(fv.confidence, 0.5)
        payload = fv.raw_value
        self.assertEqual(payload["reason"], "llm_partial_evidence")
        self.assertEqual(payload["evidence"], [])


class WebCollectorTests(unittest.TestCase):
    def test_clean_markdown_removes_cookie_banner_noise(self):
        collector = WebCollector()
        raw = """
![Revisit consent button](https://example.com/revisit.svg)
We value your privacy
Accept All
Reject All
Customise

# Prior Labs

Tabular foundation models for real-world data.
"""
        cleaned = collector._clean_markdown_content(raw)

        self.assertNotIn("We value your privacy", cleaned)
        self.assertNotIn("Accept All", cleaned)
        self.assertIn("# Prior Labs", cleaned)
        self.assertIn("Tabular foundation models", cleaned)

    def test_clean_markdown_trims_leading_ui_preamble(self):
        collector = WebCollector()
        raw = """
NecessaryAlways Active

Functional

Analytics

[Deploy now](https://example.com/deploy)

One Model, Infinite Predictions

Tabular foundation models for real-world data.
"""

        cleaned = collector._clean_markdown_content(raw)

        self.assertTrue(cleaned.startswith("One Model, Infinite Predictions"))
        self.assertNotIn("NecessaryAlways Active", cleaned)
        self.assertNotIn("Functional", cleaned)

    def test_clean_markdown_discards_firecrawl_auth_prompt(self):
        collector = WebCollector()
        raw = """
Turn websites into LLM-ready data

Welcome! To get started, authenticate with your Firecrawl account.

1. Login with browser
2. Enter API key manually
"""

        cleaned = collector._clean_markdown_content(raw)

        self.assertEqual(cleaned, "")

    def test_trim_to_title_drops_navigation_before_detected_title(self):
        collector = WebCollector()
        content = """
Models

Deployment

One Model, Infinite Predictions

Tabular foundation models for real-world data.
"""

        trimmed = collector._trim_to_title(content.strip(), "One Model, Infinite Predictions")

        self.assertTrue(trimmed.startswith("One Model, Infinite Predictions"))
        self.assertNotIn("Models", trimmed)

    def test_html_to_markdown_fallback_extracts_title_meta_and_body(self):
        collector = WebCollector()
        html = """
<html>
  <head>
    <title>CTGT</title>
    <meta name="description" content="Deterministic intelligence control for frontier AI." />
  </head>
  <body>
    <nav>Home Pricing Docs</nav>
    <h1>Deterministic control for frontier AI</h1>
    <p>Runtime policy enforcement, steering, and audit trails for production systems.</p>
    <script>console.log("ignore me")</script>
  </body>
</html>
"""

        content = collector._html_to_markdown_fallback(html)

        self.assertIn("# CTGT", content)
        self.assertIn("Deterministic intelligence control for frontier AI.", content)
        self.assertIn("Runtime policy enforcement, steering, and audit trails", content)
        self.assertNotIn("ignore me", content)

    def test_extract_canonical_metadata_captures_alternate_domains(self):
        collector = WebCollector()
        html = """
<html>
  <head>
    <link rel="canonical" href="https://movements.dev/en" />
    <link rel="alternate" href="https://movements.dev/es" hreflang="es" />
    <meta property="og:url" content="https://movements.dev/en" />
    <script type="application/ld+json">{"url":"https://movements.dev/en/search?q=test"}</script>
  </head>
</html>
"""

        canonical_url, alternate_domains = collector._extract_canonical_metadata(html)

        self.assertEqual(canonical_url, "https://movements.dev/en")
        self.assertIn("movements.dev", alternate_domains)

    def test_scrape_uses_html_fallback_when_firecrawl_is_empty(self):
        collector = WebCollector()
        html = """
<html>
  <head>
    <title>Poetiq</title>
    <meta name="description" content="The fastest path to safe super intelligence." />
  </head>
  <body>
    <h1>The fastest path to safe super intelligence</h1>
    <p>Better reasoning systems for aligned advanced AI. Better reasoning systems for aligned advanced AI.
    Better reasoning systems for aligned advanced AI. Better reasoning systems for aligned advanced AI.
    Better reasoning systems for aligned advanced AI.</p>
  </body>
</html>
"""

        with patch.object(WebCollector, "_run_firecrawl", return_value={"content": ""}):
            with patch.object(WebCollector, "_fetch_html_fallback", return_value=(html, "")):
                with patch.object(WebCollector, "_fetch_browser_fallback") as browser_fallback:
                    data = collector.scrape("https://poetiq.ai/")

        self.assertEqual(data.title, "Poetiq")
        self.assertIn("safe super intelligence", data.markdown_content.lower())
        self.assertEqual(data.meta_description, "The fastest path to safe super intelligence.")
        self.assertEqual(data.error, "")
        browser_fallback.assert_not_called()

    def test_scrape_uses_browser_fallback_when_firecrawl_and_html_are_unusable(self):
        collector = WebCollector()
        browser_text = (
            "Meet Claude. Claude is an AI assistant for problem solving, coding, writing, "
            "analysis, enterprise workflows, team collaboration, and safe deployment. "
            "Choose Pro, Team, or Enterprise plans for advanced usage. "
        ) * 4
        payload = {
            "status": 200,
            "title": "Claude",
            "meta_description": "Claude is an AI assistant from Anthropic.",
            "canonical_url": "https://claude.ai/",
            "body_text": browser_text,
            "html": "<html><body>Claude</body></html>",
            "links": ["https://claude.ai/pricing", "https://claude.ai/security"],
        }

        with patch.object(WebCollector, "_run_firecrawl", return_value={"error": "blocked"}):
            with patch.object(WebCollector, "_fetch_html_fallback", return_value=("", "403")):
                with patch.object(WebCollector, "_fetch_browser_fallback", return_value=(payload, "")):
                    data = collector.scrape("https://claude.ai/")

        self.assertEqual(data.title, "Claude")
        self.assertEqual(data.content_source, "browser_fallback")
        self.assertEqual(data.browser_status, 200)
        self.assertEqual(data.canonical_url, "https://claude.ai/")
        self.assertIn("Claude is an AI assistant", data.markdown_content)
        self.assertIn("https://claude.ai/pricing", data.links)
        self.assertEqual(data.error, "")

    def test_scrape_does_not_crash_when_browser_fallback_is_unavailable(self):
        collector = WebCollector()

        with patch.object(WebCollector, "_run_firecrawl", return_value={"error": "blocked"}):
            with patch.object(WebCollector, "_fetch_html_fallback", return_value=("", "403")):
                with patch.object(WebCollector, "_fetch_browser_fallback", return_value=({}, "playwright unavailable")):
                    data = collector.scrape("https://blocked.example/")

        self.assertEqual(data.markdown_content, "")
        self.assertEqual(data.content_source, "")
        self.assertIn(data.error, {"blocked", "playwright unavailable"})

    def test_scrape_does_not_call_browser_when_firecrawl_is_usable(self):
        collector = WebCollector()
        content = "# Claude\n\nClaude helps people solve problems with AI. " * 8

        with patch.object(WebCollector, "_run_firecrawl", return_value={"content": content}):
            with patch.object(WebCollector, "_fetch_html_fallback") as html_fallback:
                with patch.object(WebCollector, "_fetch_browser_fallback") as browser_fallback:
                    data = collector.scrape("https://claude.ai/")

        self.assertIn("Claude helps people solve problems", data.markdown_content)
        html_fallback.assert_not_called()
        browser_fallback.assert_not_called()

    def test_claude_like_browser_text_is_not_treated_as_cookie_banner(self):
        collector = WebCollector()
        content = collector._body_text_to_markdown(
            (
                "Claude\n"
                "Claude is an AI assistant for coding, writing, analysis, and business workflows.\n"
                "Explore Pro, Team, Enterprise, pricing, security, docs, and support for Claude.\n"
            ) * 5,
            title="Claude",
            meta_description="Claude is an AI assistant from Anthropic.",
        )

        self.assertGreaterEqual(len(content), 200)
        self.assertFalse(collector._looks_like_cookie_banner("Claude", content))


class ExaCollectorTests(unittest.TestCase):
    def test_brand_query_includes_domain_anchor_when_available(self):
        collector = ExaCollector(api_key="test")

        query = collector._brand_query("Movements", "https://movements.mov/en", "news")

        self.assertIn('"Movements"', query)
        self.assertIn('"movements.mov"', query)
        self.assertTrue(query.endswith("news"))

    def test_brand_query_works_without_domain(self):
        collector = ExaCollector(api_key="test")

        query = collector._brand_query("CTGT", None, "brand company")

        self.assertEqual(query, '"CTGT" brand company')


class CoherenciaExtractorTests(unittest.TestCase):
    """Covers the 4 coherencia features with dict raw_value."""

    def test_visual_consistency_skip_flag_emits_structured_fallback(self):
        web = WebData(url="https://example.com", title="Example",
                      markdown_content="Brand guidelines and logo usage live here.")
        extractor = CoherenciaExtractor(skip_visual_analysis=True)
        feature = extractor._visual_consistency(web)
        self.assertEqual(feature.source, "web_scrape_heuristic")
        self.assertEqual(feature.raw_value["reason"], "visual_analysis_skipped")
        self.assertTrue(feature.raw_value["heuristic_score_used"])
        self.assertIn("brand_in_header", feature.raw_value["heuristic_signals"])

    def test_visual_consistency_without_web_returns_zero_with_reason(self):
        feature = CoherenciaExtractor(skip_visual_analysis=True)._visual_consistency(web=None)
        self.assertEqual(feature.value, 0.0)
        self.assertEqual(feature.raw_value["reason"], "no_web_data")

    def test_messaging_consistency_without_llm_uses_heuristic_category_matching(self):
        web = WebData(
            url="https://priorlabs.ai",
            title="One Model, Infinite Predictions",
            markdown_content=(
                "# One Model, Infinite Predictions\n\n"
                "Pre-trained tabular foundation models for making predictions on structured data.\n"
            ),
        )
        exa = ExaData(
            brand_name="Prior Labs",
            mentions=[ExaResult(
                url="https://example.com/post-1",
                title="Prior Labs launches tabular foundation model",
                text="The company builds pre-trained foundation models for structured data prediction.",
            )],
        )
        feature = CoherenciaExtractor()._messaging_consistency(web, exa)
        self.assertEqual(feature.source, "heuristic_fallback")
        self.assertGreater(feature.value, 60.0)
        self.assertEqual(feature.raw_value["reason"], "llm_unavailable")

    def test_messaging_consistency_without_exa_degrades_gracefully(self):
        web = WebData(
            url="https://example.com",
            title="Deterministic AI",
            markdown_content="# Deterministic AI\n\nA deterministic policy layer for enterprise AI governance.\n",
        )
        feature = CoherenciaExtractor()._messaging_consistency(web, exa=None)
        self.assertEqual(feature.value, 55.0)
        self.assertEqual(feature.raw_value["reason"], "llm_unavailable")

    def _make_coherence_llm(self, messaging_payload=None, tone_payload=None):
        class FakeLLM:
            api_key = "sk-test"
            def analyze_messaging_consistency(self, web_content, mentions, brand_name):
                return messaging_payload
            def analyze_tone_consistency(self, web_content, snippets, brand_name):
                return tone_payload
        return FakeLLM()

    def test_messaging_consistency_with_llm_uses_structured_verdict(self):
        web = WebData(url="https://example.com", title="Example",
                      markdown_content="We are predictive infrastructure for structured data.")
        exa = ExaData(brand_name="Example", mentions=[
            ExaResult(url="https://x.com/a", title="launches", text="Example is building predictive infra."),
            ExaResult(url="https://x.com/b", title="take", text="Example, a predictive data company."),
        ])
        llm = self._make_coherence_llm(messaging_payload={
            "consistency_score": 88, "verdict": "aligned",
            "self_category": "predictive infrastructure",
            "third_party_category": "predictive data company",
            "aligned_themes": ["prediction", "structured data"],
            "gaps": [], "reasoning": "Aligned.",
        })
        feature = CoherenciaExtractor(llm=llm)._messaging_consistency(web, exa)
        self.assertEqual(feature.source, "llm")
        self.assertEqual(feature.value, 88.0)
        self.assertEqual(feature.confidence, 0.85)
        self.assertEqual(feature.raw_value["verdict"], "aligned")
        self.assertIn("prediction", feature.raw_value["aligned_themes"])

    def test_messaging_consistency_with_invalid_verdict_falls_back(self):
        web = WebData(url="https://example.com", title="Example", markdown_content="x")
        exa = ExaData(brand_name="Example", mentions=[ExaResult(url="https://x/1", title="t", text="t")])
        llm = self._make_coherence_llm(messaging_payload={
            "consistency_score": 70, "verdict": "harmonious", "gaps": [],
        })
        feature = CoherenciaExtractor(llm=llm)._messaging_consistency(web, exa)
        self.assertEqual(feature.source, "heuristic_fallback")
        self.assertEqual(feature.raw_value["reason"], "llm_invalid_verdict")

    def test_messaging_consistency_malformed_gaps_are_filtered(self):
        web = WebData(url="https://example.com", title="Example",
                      markdown_content="We are a data platform for teams.")
        exa = ExaData(brand_name="Example", mentions=[
            ExaResult(url="https://x/1", title="t", text="t"),
            ExaResult(url="https://x/2", title="u", text="u"),
        ])
        llm = self._make_coherence_llm(messaging_payload={
            "consistency_score": 55, "verdict": "partial_gap",
            "gaps": [
                {"self_says": "data platform", "third_party_says": "analytics tool", "source_url": "https://x/1"},
                {"self_says": "platform", "third_party_says": 123, "source_url": "https://x/2"},
                "not a dict",
            ],
            "reasoning": "Mismatch.",
        })
        feature = CoherenciaExtractor(llm=llm)._messaging_consistency(web, exa)
        self.assertEqual(feature.source, "llm")
        self.assertEqual(len(feature.raw_value["gaps"]), 1)
        self.assertNotIn("reason", feature.raw_value)

    def test_messaging_consistency_partial_gap_all_dropped_degrades_confidence(self):
        web = WebData(url="https://example.com", title="Example",
                      markdown_content="We are a data platform.")
        exa = ExaData(brand_name="Example", mentions=[ExaResult(url="https://x/1", title="t", text="t")])
        llm = self._make_coherence_llm(messaging_payload={
            "consistency_score": 50, "verdict": "partial_gap",
            "gaps": [{"self_says": 123, "third_party_says": "analytics"}],
            "reasoning": "Mismatch.",
        })
        feature = CoherenciaExtractor(llm=llm)._messaging_consistency(web, exa)
        self.assertEqual(feature.source, "llm")
        self.assertEqual(feature.confidence, 0.5)
        self.assertEqual(feature.raw_value["reason"], "llm_partial_evidence")

    def test_tone_consistency_with_llm_uses_structured_gap_signal(self):
        web = WebData(url="https://example.com", title="Example",
                      markdown_content="We build deterministic policy layers.")
        exa = ExaData(brand_name="Example", mentions=[
            ExaResult(url="https://x/1", title="t", text="Example is a rigorous enterprise platform."),
        ])
        llm = self._make_coherence_llm(tone_payload={
            "tone_consistency_score": 78,
            "self_tone": "formal technical", "third_party_tone": "formal enterprise",
            "gap_signal": "mild",
            "examples": [{"source": "web", "quote": "deterministic policy layers",
                          "tone_marker": "technical precision"}],
            "reasoning": "Both lean formal.",
        })
        feature = CoherenciaExtractor(llm=llm)._tone_consistency(web, exa)
        self.assertEqual(feature.source, "llm")
        self.assertEqual(feature.value, 78.0)
        self.assertEqual(feature.raw_value["gap_signal"], "mild")
        self.assertEqual(len(feature.raw_value["examples"]), 1)

    def test_tone_consistency_without_llm_falls_back_to_heuristic(self):
        web = WebData(url="https://example.com", title="Example",
                      markdown_content="Hey! This is gonna be awesome. Let's go!")
        feature = CoherenciaExtractor()._tone_consistency(web, exa=None)
        self.assertEqual(feature.source, "heuristic_fallback")
        self.assertEqual(feature.raw_value["reason"], "llm_unavailable")
        self.assertGreater(feature.raw_value["heuristic_signals"]["informal_markers"], 0)

    def test_cross_channel_coherence_counts_social_platforms_explicitly(self):
        web = WebData(
            url="https://poetiq.ai/", title="Poetiq",
            markdown_content=(
                "# Poetiq\n\nFollow us at https://twitter.com/poetiq and https://linkedin.com/company/poetiq.\n"
                "Get in touch. Privacy Policy. About us.\n"
            ),
        )
        exa = ExaData(brand_name="Poetiq", mentions=[
            ExaResult(url="https://poetiq.ai/blog/launch", title="launch", text="..."),
        ])
        feature = CoherenciaExtractor()._cross_channel_coherence(web, exa)
        self.assertGreaterEqual(feature.value, 50.0)
        self.assertTrue(feature.raw_value["has_social_links"])
        self.assertIn("twitter", feature.raw_value["social_platforms_detected"])
        self.assertIn("linkedin", feature.raw_value["social_platforms_detected"])
        self.assertTrue(feature.raw_value["brand_url_mentioned_in_exa"])

    def test_cross_channel_coherence_stays_low_on_minimal_landing(self):
        web = WebData(url="https://example.com/", title="Example",
                      markdown_content="# Example\n\nMinimal landing page.\n")
        feature = CoherenciaExtractor()._cross_channel_coherence(web, exa=None)
        self.assertLessEqual(feature.value, 25.0)
        self.assertFalse(feature.raw_value["has_social_links"])
        self.assertEqual(feature.raw_value["social_platforms_detected"], [])

    def test_cross_channel_coherence_accepts_alternate_domains(self):
        web = WebData(
            url="https://movements.mov/en",
            canonical_url="https://movements.dev/en",
            alternate_domains=["movements.dev"],
            title="MOVEMENTS",
            markdown_content="# MOVEMENTS\n\nJoin the movement.\n",
        )
        exa = ExaData(brand_name="Movements", mentions=[
            ExaResult(url="https://movements.dev/en/blog/launch", title="launch", text="..."),
        ])
        feature = CoherenciaExtractor()._cross_channel_coherence(web, exa)
        self.assertTrue(feature.raw_value["brand_url_mentioned_in_exa"])
        self.assertIn("movements.dev", feature.raw_value["brand_domains"])

    def test_extract_always_returns_four_features(self):
        features = CoherenciaExtractor(skip_visual_analysis=True).extract(web=None, exa=None)
        self.assertEqual(
            set(features.keys()),
            {"visual_consistency", "messaging_consistency", "tone_consistency", "cross_channel_coherence"},
        )


if __name__ == "__main__":
    unittest.main()
