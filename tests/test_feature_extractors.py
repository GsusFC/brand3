import unittest

from src.collectors.exa_collector import ExaData, ExaResult
from src.collectors.web_collector import WebData
from src.collectors.web_collector import WebCollector
from src.features.coherencia import CoherenciaExtractor
from src.features.diferenciacion import DiferenciacionExtractor
from src.features.percepcion import PercepcionExtractor
from src.features.presencia import PresenciaExtractor


class PercepcionExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = PercepcionExtractor()

    def test_sentiment_trend_uses_published_dates_not_result_order(self):
        exa = ExaData(
            brand_name="Test Brand",
            mentions=[
                ExaResult(
                    url="https://example.com/recent-1",
                    title="Recent positive",
                    text="excellent breakthrough",
                    published_date="2026-04-01",
                ),
                ExaResult(
                    url="https://example.com/old-1",
                    title="Old negative",
                    text="lawsuit outage",
                    published_date="2024-01-01",
                ),
                ExaResult(
                    url="https://example.com/recent-2",
                    title="Recent positive 2",
                    text="amazing reliable",
                    published_date="2026-03-15",
                ),
                ExaResult(
                    url="https://example.com/old-2",
                    title="Old negative 2",
                    text="fraud scam",
                    published_date="2024-02-01",
                ),
            ],
        )

        trend = self.extractor._sentiment_trend(exa)

        self.assertGreater(trend.value, 50.0)
        self.assertEqual(trend.confidence, 0.6)
        self.assertIn("dated_results=4", trend.raw_value)

    def test_sentiment_trend_returns_low_confidence_without_enough_dated_results(self):
        exa = ExaData(
            brand_name="Test Brand",
            mentions=[
                ExaResult(url="https://example.com/1", title="One", text="great", published_date=""),
                ExaResult(url="https://example.com/2", title="Two", text="great", published_date="2026-04-01"),
                ExaResult(url="https://example.com/3", title="Three", text="bad", published_date=""),
            ],
        )

        trend = self.extractor._sentiment_trend(exa)

        self.assertEqual(trend.value, 50.0)
        self.assertEqual(trend.confidence, 0.1)
        self.assertEqual(trend.raw_value, "insufficient dated mentions")


class DiferenciacionExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = DiferenciacionExtractor()

    def test_generic_language_is_normalized_by_content_length(self):
        short_web = WebData(
            url="https://short.example",
            title="Short",
            markdown_content=(
                "We are a leading provider. "
                "Our innovative solutions help teams save time. "
                "We deliver scalable solutions. "
                "We help businesses grow."
            ),
        )
        long_web = WebData(
            url="https://long.example",
            title="Long",
            markdown_content=(
                " ".join(
                    [
                        "This product helps finance teams reconcile multi-entity close workflows with auditable approvals."
                    ] * 24
                )
                + " Leading provider. Innovative solutions. Save time. We help businesses grow."
            ),
        )

        short_score = self.extractor._generic_language(short_web)
        long_score = self.extractor._generic_language(long_web)

        self.assertGreater(short_score.value, long_score.value)
        self.assertIn("ratio=", short_score.raw_value)
        self.assertIn("ratio=", long_score.raw_value)

    def test_generic_language_low_ratio_stays_low_even_with_some_generic_phrases(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content=(
                " ".join(
                    [
                        "This platform automates supplier onboarding across legal, procurement, and finance systems."
                    ] * 18
                )
                + " Save time."
            ),
        )

        score = self.extractor._generic_language(web)

        self.assertLessEqual(score.value, 30.0)


class PresenciaExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = PresenciaExtractor()

    def test_ai_visibility_weights_relevance_and_brand_centrality(self):
        exa = ExaData(
            brand_name="Acme AI",
            ai_visibility_results=[
                ExaResult(
                    url="https://example.com/acme-ai-best-tools",
                    title="Acme AI among top agent tools",
                    text="Acme AI is recommended for enterprise automation.",
                    score=0.9,
                ),
                ExaResult(
                    url="https://example.com/general-roundup",
                    title="General AI trends",
                    text="This article mentions Acme AI in passing alongside many vendors.",
                    score=0.3,
                ),
                ExaResult(
                    url="https://example.com/random",
                    title="Random AI roundup",
                    text="Vague references to models and tooling.",
                    score=0.2,
                ),
            ],
        )

        visibility = self.extractor._ai_visibility(exa)

        self.assertGreater(visibility.value, 20.0)
        self.assertLess(visibility.value, 60.0)
        self.assertIn("weighted=", visibility.raw_value)


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


class CoherenciaExtractorTests(unittest.TestCase):
    def test_skip_visual_analysis_uses_heuristic_fallback(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content="Brand guidelines and logo usage live here.",
        )
        extractor = CoherenciaExtractor(skip_visual_analysis=True)

        feature = extractor._visual_consistency(web)

        self.assertEqual(feature.source, "web_scrape_heuristic")
        self.assertIn("visual analysis skipped", feature.raw_value)


if __name__ == "__main__":
    unittest.main()
