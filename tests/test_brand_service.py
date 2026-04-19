import unittest

from src.collectors.exa_collector import ExaData, ExaResult
from src.collectors.web_collector import WebData
from src.services.brand_service import (
    _aggregate_exa_content,
    _build_content_web,
    _compute_data_quality,
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


if __name__ == "__main__":
    unittest.main()
