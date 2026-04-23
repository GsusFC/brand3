import unittest

from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData, ExaResult
from src.collectors.web_collector import WebData
from src.services.brand_service import (
    _aggregate_exa_content,
    _build_content_web,
    _compute_data_quality,
    _context_confidence_summary,
    _context_evidence_items,
    _llm_cache_summary,
)


class BrandServiceContentFallbackTests(unittest.TestCase):
    def test_build_content_web_prefers_usable_firecrawl_content(self):
        web = WebData(
            url="https://example.com",
            title="Example",
            markdown_content="A" * 250,
        )
        exa = ExaData(brand_name="Example")

        content_web, content_source, data_sources = _build_content_web(
            "https://example.com",
            "Example",
            web,
            exa,
        )

        self.assertIs(content_web, web)
        self.assertEqual(content_source, "firecrawl")
        self.assertEqual(data_sources["content_source"], "firecrawl")

    def test_aggregate_exa_content_requires_enough_mentions_and_text(self):
        exa = ExaData(
            brand_name="Example",
            mentions=[
                ExaResult(url="https://a.com", title="One", text="short"),
                ExaResult(url="https://b.com", title="Two", text="short"),
            ],
        )

        aggregate, used = _aggregate_exa_content(exa)

        self.assertEqual(aggregate, "")
        self.assertEqual(used, 0)

    def test_build_content_web_falls_back_to_exa_mentions(self):
        exa = ExaData(
            brand_name="Uber",
            mentions=[
                ExaResult(url=f"https://example{i}.com", title=f"Mention {i}", text="Uber is a mobility platform. " * 30)
                for i in range(4)
            ],
        )
        web = WebData(url="https://uber.com", title="", markdown_content="", error="")

        content_web, content_source, data_sources = _build_content_web(
            "https://uber.com",
            "Uber",
            web,
            exa,
        )

        self.assertIsNotNone(content_web)
        self.assertEqual(content_source, "exa_fallback")
        self.assertEqual(data_sources["content_source"], "exa_fallback")
        self.assertEqual(data_sources["exa_fallback_mentions_used"], 4)
        self.assertGreaterEqual(len(content_web.markdown_content), 300)
        self.assertEqual(content_web.title, "Mention 0")

    def test_build_content_web_returns_none_when_no_usable_sources_exist(self):
        web = WebData(url="https://example.com", markdown_content="", title="")
        exa = ExaData(brand_name="Example", mentions=[])

        content_web, content_source, data_sources = _build_content_web(
            "https://example.com",
            "Example",
            web,
            exa,
        )

        self.assertIsNone(content_web)
        self.assertEqual(content_source, "none")
        self.assertEqual(data_sources["content_source"], "none")

    def test_compute_data_quality_distinguishes_good_degraded_and_insufficient(self):
        rich_exa = ExaData(brand_name="Example", mentions=[ExaResult(url=f"https://e{i}.com", title="x") for i in range(5)])
        degraded_exa = ExaData(brand_name="Example", mentions=[ExaResult(url=f"https://e{i}.com", title="x") for i in range(3)])
        empty_exa = ExaData(brand_name="Example", mentions=[])

        self.assertEqual(_compute_data_quality(rich_exa, "firecrawl"), "good")
        self.assertEqual(_compute_data_quality(degraded_exa, "exa_fallback"), "degraded")
        self.assertEqual(_compute_data_quality(empty_exa, "none"), "insufficient")

    def test_context_confidence_summary_marks_low_coverage_insufficient(self):
        context = ContextData(
            url="https://example.com",
            coverage=0.2,
            confidence=0.5,
            confidence_reason=["low_coverage"],
        )

        summary = _context_confidence_summary(context)

        self.assertEqual(summary["status"], "insufficient_data")
        self.assertEqual(summary["coverage"], 0.2)
        self.assertIn("low_coverage", summary["confidence_reason"])

    def test_context_evidence_items_are_generated_from_context_signals(self):
        context = ContextData(
            url="https://example.com",
            robots_found=True,
            sitemap_found=True,
            sitemap_url_count=12,
            llms_txt_found=True,
            schema_types=["Organization", "WebSite"],
            key_pages={"about": True, "blog": True},
            coverage=0.8,
            confidence=0.85,
        )

        items = _context_evidence_items(context)

        self.assertGreaterEqual(len(items), 4)
        self.assertIn("sitemap.xml found with 12 URLs", [item["quote"] for item in items])
        self.assertIn("coherencia", {item["dimension_name"] for item in items})

    def test_llm_cache_summary_reports_hits_and_skip_reason(self):
        class FakeLLM:
            cache_hits = 2
            cache_misses = 1
            cache_writes = 1

        summary = _llm_cache_summary(FakeLLM())
        skipped = _llm_cache_summary(None, "insufficient_context_coverage")

        self.assertEqual(summary["cache_hits"], 2)
        self.assertEqual(summary["estimated_cost_saved_units"], 2)
        self.assertEqual(skipped["skipped_reason"], "insufficient_context_coverage")


if __name__ == "__main__":
    unittest.main()
