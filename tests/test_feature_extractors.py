import unittest
from unittest.mock import patch

from src.collectors.exa_collector import ExaData, ExaResult
from src.collectors.exa_collector import ExaCollector
from src.collectors.web_collector import WebData
from src.collectors.web_collector import WebCollector
from src.features.coherencia import CoherenciaExtractor
from src.features.diferenciacion import DiferenciacionExtractor
from src.features.percepcion import PercepcionExtractor
from src.features.presencia import PresenciaExtractor
from src.features.vitalidad import VitalidadExtractor


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

    def test_review_quality_is_neutral_when_brand_has_mentions_but_no_review_platforms(self):
        exa = ExaData(
            brand_name="Test Brand",
            mentions=[
                ExaResult(url=f"https://example.com/{idx}", title="Mention", text="strong traction")
                for idx in range(4)
            ],
            news=[
                ExaResult(url="https://news.example.com/item", title="Launch", text="new launch")
            ],
        )

        feature = self.extractor._review_quality(exa)

        self.assertEqual(feature.value, 50.0)
        self.assertEqual(feature.confidence, 0.2)
        self.assertIn("mentions=5", feature.raw_value)

    def test_review_quality_uses_review_platforms_when_present(self):
        exa = ExaData(
            brand_name="Test Brand",
            mentions=[
                ExaResult(
                    url="https://www.producthunt.com/posts/test-brand",
                    title="Product Hunt",
                    text="great innovative reliable product",
                ),
            ],
        )

        feature = self.extractor._review_quality(exa)

        self.assertGreater(feature.value, 50.0)
        self.assertIn("1 review platforms", feature.raw_value)


class DiferenciacionExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = DiferenciacionExtractor()

    def test_unique_value_prop_rewards_specific_technical_positioning_and_proof(self):
        web = WebData(
            url="https://priorlabs.ai",
            title="One Model, Infinite Predictions",
            markdown_content=(
                "# One Model, Infinite Predictions\n\n"
                "Pre-trained tabular foundation models for making predictions on structured data.\n\n"
                "6K GITHUB STARS\n"
                "3M DOWNLOADS\n"
                "PUBLISHED IN NATURE\n"
            ),
        )

        feature = self.extractor._unique_value_prop(web)

        self.assertGreaterEqual(feature.value, 60.0)
        self.assertIn("specificity_hits=", feature.raw_value)
        self.assertIn("proof_points=", feature.raw_value)

    def test_unique_value_prop_stays_low_for_generic_claims_without_proof(self):
        web = WebData(
            url="https://generic.example",
            title="Generic SaaS",
            markdown_content=(
                "# Generic SaaS\n\n"
                "We help businesses grow and improve efficiency.\n"
                "Save time. Save money. Better results.\n"
            ),
        )

        feature = self.extractor._unique_value_prop(web)

        self.assertLessEqual(feature.value, 35.0)

    def test_unique_value_prop_rewards_signature_and_proof_language_for_frontier_brands(self):
        web = WebData(
            url="https://ricursive.com",
            title="Ricursive",
            markdown_content=(
                "# Ricursive\n\n"
                "We develop frontier AI methods to reinvent chip development.\n"
                "Ricursive Intelligence is a frontier AI lab focused on building self-improving systems.\n"
                "We are the team behind AlphaChip (Nature 2021) and DAC Best Paper 2023.\n"
            ),
        )

        feature = self.extractor._unique_value_prop(web)

        self.assertGreaterEqual(feature.value, 50.0)
        self.assertIn("proof_points=", feature.raw_value)
        self.assertIn("signature_hits=", feature.raw_value)

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

    def test_brand_vocabulary_detects_signature_phrases_and_repeated_acronyms(self):
        web = WebData(
            url="https://ctgt.ai",
            title="CTGT",
            markdown_content=(
                "# CTGT\n\n"
                "The deterministic layer for frontier intelligence.\n"
                "CTGT helps teams govern mission critical applications.\n"
                "CTGT introduces a deterministic layer for frontier intelligence.\n"
            ),
        )

        feature = self.extractor._brand_vocabulary(web, exa=None, competitor_data=None)

        self.assertGreaterEqual(feature.value, 20.0)
        self.assertIn("acronyms=", feature.raw_value)
        self.assertIn("signature_phrases=", feature.raw_value)


class PresenciaExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = PresenciaExtractor()

    def test_social_footprint_rewards_professional_and_builder_mix(self):
        web = WebData(
            url="https://example.dev",
            title="Example",
            markdown_content=(
                "# Example\n\n"
                "Follow us on LinkedIn and GitHub.\n"
                "https://linkedin.com/company/example\n"
                "https://github.com/example\n"
            ),
        )

        feature = self.extractor._social_footprint(web=web, exa=None, social=None)

        self.assertGreaterEqual(feature.value, 55.0)
        self.assertIn("weighted_presence=", feature.raw_value)
        self.assertIn("builder", feature.raw_value)
        self.assertIn("professional", feature.raw_value)

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
        self.assertLess(visibility.value, 70.0)
        self.assertIn("weighted=", visibility.raw_value)

    def test_ai_visibility_gets_neutral_boost_from_multiple_medium_results(self):
        exa = ExaData(
            brand_name="Acme AI",
            ai_visibility_results=[
                ExaResult(
                    url="https://example.com/tools/acme-ai",
                    title="Acme AI tooling",
                    text="Acme AI appears in an enterprise tooling roundup.",
                    score=0.45,
                ),
                ExaResult(
                    url="https://another.example.com/acme-ai",
                    title="Acme AI for teams",
                    text="Acme AI is mentioned as a relevant product for teams.",
                    score=0.4,
                ),
                ExaResult(
                    url="https://third.example.com/roundup",
                    title="AI roundup",
                    text="Acme AI appears among notable vendors.",
                    score=0.35,
                ),
            ],
        )

        visibility = self.extractor._ai_visibility(exa)

        self.assertGreaterEqual(visibility.value, 55.0)
        self.assertIn("medium_results=", visibility.raw_value)


class VitalidadExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = VitalidadExtractor()

    def test_tech_modernity_rewards_real_developer_surface_signals(self):
        web = WebData(
            url="https://example.dev",
            title="Example Devtool",
            markdown_content=(
                "# Predictive infrastructure\n\n"
                "API docs, playground, GitHub, and deployment options for AWS and Azure.\n"
            ),
        )

        feature = self.extractor._tech_modernity(web)

        self.assertGreater(feature.value, 60.0)
        self.assertIn("dev_surface=", feature.raw_value)

    def test_tech_modernity_does_not_inflate_from_framework_name_drops(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content=(
                "# Example\n\n"
                "We love React, Next.js, TypeScript, and Tailwind.\n"
            ),
        )

        feature = self.extractor._tech_modernity(web)

        self.assertLessEqual(feature.value, 55.0)


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
    <p>Better reasoning systems for aligned advanced AI.</p>
  </body>
</html>
"""

        with patch.object(WebCollector, "_run_firecrawl", return_value={"content": ""}):
            with patch.object(WebCollector, "_fetch_html_fallback", return_value=(html, "")):
                data = collector.scrape("https://poetiq.ai/")

        self.assertEqual(data.title, "Poetiq")
        self.assertIn("safe super intelligence", data.markdown_content.lower())
        self.assertEqual(data.meta_description, "The fastest path to safe super intelligence.")
        self.assertEqual(data.error, "")


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

    def test_messaging_consistency_extracts_category_from_hero_copy(self):
        web = WebData(
            url="https://priorlabs.ai",
            title="One Model, Infinite Predictions",
            markdown_content=(
                "# One Model, Infinite Predictions\n\n"
                "Pre-trained tabular foundation models for making predictions on structured data.\n\n"
                "Talk to sales\n"
            ),
        )
        exa = ExaData(
            brand_name="Prior Labs",
            mentions=[
                ExaResult(
                    url="https://example.com/post-1",
                    title="Prior Labs launches tabular foundation model",
                    text="The company builds pre-trained foundation models for structured data prediction.",
                )
            ],
        )
        extractor = CoherenciaExtractor()

        feature = extractor._messaging_consistency(web, exa)

        self.assertGreater(feature.value, 60.0)
        self.assertIn("tabular foundation models", feature.raw_value)

    def test_messaging_consistency_with_web_category_but_no_exa_data_is_not_default_failure(self):
        web = WebData(
            url="https://example.com",
            title="Deterministic AI",
            markdown_content=(
                "# Deterministic AI\n\n"
                "A deterministic policy layer for enterprise AI governance.\n"
            ),
        )
        extractor = CoherenciaExtractor()

        feature = extractor._messaging_consistency(web, exa=None)

        self.assertEqual(feature.value, 55.0)
        self.assertIn("policy layer", feature.raw_value)

    def test_cross_channel_coherence_is_not_overly_punitive_for_startup_touchpoints(self):
        web = WebData(
            url="https://poetiq.ai/",
            title="Poetiq",
            markdown_content=(
                "# Poetiq\n\n"
                "Secure your place for the next generation of reasoning.\n"
                "Your request has been received. We will be in touch shortly.\n"
            ),
        )
        exa = ExaData(
            brand_name="Poetiq",
            mentions=[
                ExaResult(
                    url="https://poetiq.ai/blog/launch",
                    title="Poetiq launch",
                    text="Poetiq launches reasoning research platform.",
                )
            ],
        )
        extractor = CoherenciaExtractor()

        feature = extractor._cross_channel_coherence(web, exa)

        self.assertGreaterEqual(feature.value, 50.0)
        self.assertIn("touchpoint=True", feature.raw_value)
        self.assertIn("brand_url_mentioned=True", feature.raw_value)

    def test_cross_channel_coherence_stays_low_when_site_has_no_touchpoints(self):
        web = WebData(
            url="https://example.com/",
            title="Example",
            markdown_content="# Example\n\nMinimal landing page.\n",
        )
        extractor = CoherenciaExtractor()

        feature = extractor._cross_channel_coherence(web, exa=None)

        self.assertLessEqual(feature.value, 25.0)


if __name__ == "__main__":
    unittest.main()
