import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.online_presence_inventory import (
    BENCHMARK_SUMMARY_FIELDS,
    OUTPUT_FIELDS,
    common_path_candidates,
    enrich_official_rows,
    format_table,
    recommended_analysis_mode,
    make_row,
    run_benchmark,
    summarize_brand,
    summarize_inventory,
    write_benchmark_outputs,
    write_outputs,
    main,
)
from src.collectors.web_collector import WebData


class OnlinePresenceInventoryTests(unittest.TestCase):
    class FakeCollector:
        def __init__(self, text_by_url=None):
            self.text_by_url = text_by_url or {}
            self.urls = []

        def scrape(self, url):
            self.urls.append(url)
            text = self.text_by_url.get(url, "")
            return WebData(
                url=url,
                title=f"Title for {url}",
                markdown_content=text,
                content_source="browser_fallback",
                browser_status=200 if text else 404,
                error="" if text else "not found",
            )

    def test_claude_primary_is_primary(self):
        row = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://claude.ai",
            source="input",
            text_chars=500,
        )

        self.assertEqual(row.page_type, "primary")
        self.assertEqual(row.relation_to_brand, "primary_domain")
        self.assertEqual(row.confidence, 1.0)
        self.assertTrue(row.usable_for_brand_evidence)

    def test_claude_pricing_is_same_domain_page(self):
        row = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://claude.ai/pricing",
            source="common_path",
            text_chars=500,
        )

        self.assertEqual(row.page_type, "same_domain_page")
        self.assertEqual(row.relation_to_brand, "same_domain")
        self.assertTrue(row.usable_for_brand_evidence)

    def test_docs_anthropic_is_docs_official_related_for_claude(self):
        row = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://docs.anthropic.com/en/docs/claude-code",
            source="exa",
            title_or_snippet="Claude Code documentation by Anthropic",
            collection_method="exa_metadata",
            snippet_is_search_metadata=True,
        )

        self.assertEqual(row.page_type, "docs")
        self.assertEqual(row.relation_to_brand, "official_related")
        self.assertFalse(row.usable_for_brand_evidence)

    def test_anthropic_news_is_news_official_related_for_claude(self):
        row = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://www.anthropic.com/news/claude-3-5-sonnet",
            source="exa",
            title_or_snippet="Anthropic news about Claude",
            collection_method="exa_metadata",
            snippet_is_search_metadata=True,
        )

        self.assertEqual(row.page_type, "news_or_blog")
        self.assertEqual(row.relation_to_brand, "official_related")

    def test_random_press_article_is_third_party(self):
        row = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://example-news.com/ai/claude-launch",
            source="exa",
            title_or_snippet="A press article about Claude",
            collection_method="exa_metadata",
            snippet_is_search_metadata=True,
        )

        self.assertEqual(row.page_type, "third_party")
        self.assertEqual(row.relation_to_brand, "third_party")
        self.assertFalse(row.usable_for_brand_evidence)
        self.assertTrue(row.usable_for_perception_evidence)

    def test_common_path_generation_works(self):
        candidates = common_path_candidates("https://claude.ai")

        self.assertIn("https://claude.ai/about", candidates)
        self.assertIn("https://claude.ai/case-studies", candidates)
        self.assertEqual(len(candidates), 12)

    def test_json_tsv_output_includes_required_columns(self):
        row = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://claude.ai",
            source="input",
            title_or_snippet="Claude",
            collection_method="browser_fallback",
            status="200",
            text_chars=1200,
        )
        table = format_table([row])
        self.assertIn("usable_for_brand_evidence", table)
        self.assertIn("browser_fallback", table)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "inventory.json"
            tsv_path = Path(tmpdir) / "inventory.tsv"
            write_outputs([row], json_out=json_path, tsv_out=tsv_path)

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(set(OUTPUT_FIELDS), set(payload["rows"][0]))
            self.assertIn("summary", payload)

            with tsv_path.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                self.assertEqual(reader.fieldnames, list(OUTPUT_FIELDS))
                first = next(reader)
            self.assertEqual(first["candidate_url"], "https://claude.ai")

    def test_enrich_official_enriches_owned_public_candidates(self):
        official = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://docs.anthropic.com/en/docs/claude-code",
            source="exa",
            title_or_snippet="Claude documentation by Anthropic",
            collection_method="exa_metadata",
            snippet_is_search_metadata=True,
        )
        collector = self.FakeCollector({
            official.candidate_url: "Claude docs public content. " * 20,
        })

        count = enrich_official_rows([official], collector=collector, max_enrich=12)

        self.assertEqual(count, 1)
        self.assertEqual(collector.urls, [official.candidate_url])
        self.assertEqual(official.collection_method, "browser_fallback")
        self.assertEqual(official.status, "200")
        self.assertGreaterEqual(official.text_chars, 200)
        self.assertTrue(official.usable_for_brand_evidence)

    def test_max_enrich_limits_collection_count(self):
        rows = [
            make_row(
                brand="Claude",
                input_url="https://claude.ai",
                candidate_url=f"https://claude.ai/{path}",
                source="common_path",
            )
            for path in ("pricing", "docs", "support")
        ]
        collector = self.FakeCollector({
            row.candidate_url: "Public content. " * 20 for row in rows
        })

        count = enrich_official_rows(rows, collector=collector, max_enrich=2)

        self.assertEqual(count, 2)
        self.assertEqual(len(collector.urls), 2)
        self.assertEqual(sum(1 for row in rows if row.enriched), 2)

    def test_third_party_is_not_enriched_by_default(self):
        third_party = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://example-news.com/ai/claude",
            source="exa",
            title_or_snippet="Press article about Claude",
            collection_method="exa_metadata",
            snippet_is_search_metadata=True,
        )
        official = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://claude.ai/pricing",
            source="common_path",
        )
        collector = self.FakeCollector({
            third_party.candidate_url: "Third party text. " * 20,
            official.candidate_url: "Official public text. " * 20,
        })

        enrich_official_rows([third_party, official], collector=collector, max_enrich=12)

        self.assertEqual(collector.urls, [official.candidate_url])
        self.assertFalse(third_party.enriched)
        self.assertFalse(third_party.usable_for_brand_evidence)
        self.assertTrue(third_party.usable_for_perception_evidence)

    def test_summary_counts_and_recommendation_for_two_owned_pages(self):
        primary = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://claude.ai",
            source="input",
            text_chars=300,
        )
        docs = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://docs.anthropic.com/en/docs/claude-code",
            source="exa",
            title_or_snippet="Claude docs by Anthropic",
            text_chars=300,
        )
        third_party = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://example.com/claude",
            source="exa",
            title_or_snippet="Article about Claude",
            snippet_is_search_metadata=True,
        )
        primary.enriched = True
        docs.enriched = True

        summary = summarize_inventory([primary, docs, third_party])

        self.assertEqual(summary["total_candidates"], 3)
        self.assertEqual(summary["owned_or_official_candidates"], 2)
        self.assertEqual(summary["enriched_candidates"], 2)
        self.assertEqual(summary["usable_brand_evidence_pages"], 2)
        self.assertEqual(summary["usable_perception_evidence_pages"], 1)
        self.assertTrue(summary["recommended_brand_evidence_base"])

    def test_recommended_brand_evidence_base_requires_enough_owned_content(self):
        thin_primary = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://claude.ai",
            source="input",
            text_chars=1000,
        )
        strong_primary = make_row(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://claude.ai",
            source="input",
            text_chars=1500,
        )

        self.assertFalse(summarize_inventory([thin_primary])["recommended_brand_evidence_base"])
        self.assertTrue(summarize_inventory([strong_primary])["recommended_brand_evidence_base"])

    def test_benchmark_mode_with_multiple_brands(self):
        def fake_collect(brand, url, *, enrich_official=False, max_enrich=12, **_kwargs):
            return [
                make_row(
                    brand=brand,
                    input_url=url,
                    candidate_url=url,
                    source="input",
                    collection_method="browser_fallback",
                    text_chars=1800,
                )
            ]

        targets = [
            {"brand": "Claude", "url": "https://claude.ai"},
            {"brand": "Uber", "url": "https://uber.com"},
        ]
        with patch("experiments.online_presence_inventory.collect_inventory", side_effect=fake_collect):
            result = run_benchmark(targets, include_official_pages=True, max_pages_per_brand=12)

        self.assertEqual(result["brand_count"], 2)
        self.assertEqual(len(result["summary_by_brand"]), 2)
        self.assertEqual(len(result["rows"]), 2)
        self.assertIn("generated_at", result)

    def test_summary_by_brand_generation(self):
        rows = [
            make_row(
                brand="Claude",
                input_url="https://claude.ai",
                candidate_url="https://claude.ai",
                source="input",
                collection_method="browser_fallback",
                text_chars=1800,
            ),
            make_row(
                brand="Claude",
                input_url="https://claude.ai",
                candidate_url="https://docs.anthropic.com/en/docs/claude-code",
                source="exa",
                title_or_snippet="Claude docs by Anthropic",
                collection_method="browser_fallback",
                text_chars=500,
            ),
        ]
        rows[1].enriched = True

        summary = summarize_brand(rows, brand="Claude", input_url="https://claude.ai")

        self.assertEqual(summary["brand"], "Claude")
        self.assertEqual(summary["total_public_pages_found"], 2)
        self.assertEqual(summary["official_pages_found"], 2)
        self.assertEqual(summary["primary_page_read_method"], "browser_fallback")
        self.assertEqual(summary["primary_page_text_chars"], 1800)
        self.assertEqual(summary["official_related_usable_count"], 1)
        self.assertTrue(summary["recommended_evidence_base"])

    def test_recommended_analysis_mode_primary_page_only(self):
        rows = [
            make_row(
                brand="Example",
                input_url="https://example.com",
                candidate_url="https://example.com",
                source="input",
                text_chars=1800,
            )
        ]

        self.assertEqual(recommended_analysis_mode(rows), "primary_page_only")

    def test_recommended_analysis_mode_official_pages_bundle(self):
        rows = [
            make_row(
                brand="Example",
                input_url="https://example.com",
                candidate_url="https://example.com",
                source="input",
                text_chars=1800,
            ),
            make_row(
                brand="Example",
                input_url="https://example.com",
                candidate_url="https://example.com/docs",
                source="common_path",
                text_chars=500,
            ),
            make_row(
                brand="Example",
                input_url="https://example.com",
                candidate_url="https://example.com/support",
                source="common_path",
                text_chars=500,
            ),
        ]

        self.assertEqual(recommended_analysis_mode(rows), "official_pages_bundle")

    def test_recommended_analysis_mode_related_official_pages_bundle(self):
        rows = [
            make_row(
                brand="Claude",
                input_url="https://claude.ai",
                candidate_url="https://claude.ai",
                source="input",
                text_chars=50,
            ),
            make_row(
                brand="Claude",
                input_url="https://claude.ai",
                candidate_url="https://docs.anthropic.com/en/docs/claude-code",
                source="exa",
                title_or_snippet="Claude documentation by Anthropic",
                text_chars=500,
            ),
        ]

        self.assertEqual(recommended_analysis_mode(rows), "related_official_pages_bundle")

    def test_recommended_analysis_mode_not_enough_evidence(self):
        rows = [
            make_row(
                brand="Claude",
                input_url="https://claude.ai",
                candidate_url="https://claude.ai",
                source="input",
                text_chars=50,
            )
        ]

        self.assertEqual(recommended_analysis_mode(rows), "not_enough_evidence")

    def test_benchmark_max_pages_per_brand_is_respected(self):
        targets = [
            {"brand": "Claude", "url": "https://claude.ai"},
            {"brand": "Uber", "url": "https://uber.com"},
        ]
        calls = []

        def fake_collect(brand, url, *, enrich_official=False, max_enrich=12, **_kwargs):
            calls.append((brand, enrich_official, max_enrich))
            return [
                make_row(
                    brand=brand,
                    input_url=url,
                    candidate_url=url,
                    source="input",
                    text_chars=1800,
                )
            ]

        with patch("experiments.online_presence_inventory.collect_inventory", side_effect=fake_collect):
            run_benchmark(targets, include_official_pages=True, max_pages_per_brand=3)

        self.assertEqual(calls, [("Claude", True, 3), ("Uber", True, 3)])

    def test_benchmark_outputs_summary_rows(self):
        result = {
            "generated_at": "2026-05-01T00:00:00+00:00",
            "brand_count": 1,
            "rows": [],
            "summary_by_brand": [
                {
                    "brand": "Claude",
                    "input_url": "https://claude.ai",
                    "total_public_pages_found": 1,
                    "official_pages_found": 1,
                    "official_pages_read": 1,
                    "usable_brand_evidence_pages": 1,
                    "usable_public_perception_pages": 0,
                    "primary_page_read_method": "browser_fallback",
                    "primary_page_text_chars": 1800,
                    "official_related_usable_count": 0,
                    "docs_usable_count": 0,
                    "news_or_blog_usable_count": 0,
                    "support_usable_count": 0,
                    "recommended_evidence_base": True,
                    "recommended_analysis_mode": "primary_page_only",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "benchmark.json"
            tsv_path = Path(tmpdir) / "benchmark.tsv"
            write_benchmark_outputs(result, json_out=json_path, tsv_out=tsv_path)

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["brand_count"], 1)
            with tsv_path.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                self.assertEqual(reader.fieldnames, list(BENCHMARK_SUMMARY_FIELDS))
                first = next(reader)
            self.assertEqual(first["brand"], "Claude")

    def test_benchmark_cli_accepts_targets_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            targets_path = Path(tmpdir) / "brands.json"
            json_path = Path(tmpdir) / "out.json"
            tsv_path = Path(tmpdir) / "out.tsv"
            targets_path.write_text(
                json.dumps([
                    {"brand": "Claude", "url": "https://claude.ai"},
                    {"brand": "Uber", "url": "https://uber.com"},
                ]),
                encoding="utf-8",
            )

            def fake_collect(brand, url, *, enrich_official=False, max_enrich=12, **_kwargs):
                return [
                    make_row(
                        brand=brand,
                        input_url=url,
                        candidate_url=url,
                        source="input",
                        text_chars=1800,
                    )
                ]

            with patch("experiments.online_presence_inventory.collect_inventory", side_effect=fake_collect):
                rc = main([
                    "benchmark",
                    str(targets_path),
                    "--json-out",
                    str(json_path),
                    "--tsv-out",
                    str(tsv_path),
                    "--include-official-pages",
                    "--max-pages-per-brand",
                    "2",
                ])

            self.assertEqual(rc, 0)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["brand_count"], 2)
            self.assertTrue(tsv_path.exists())


if __name__ == "__main__":
    unittest.main()
