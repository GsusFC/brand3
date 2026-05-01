import csv
import json
import tempfile
import unittest
from pathlib import Path

from experiments.online_presence_inventory import (
    OUTPUT_FIELDS,
    common_path_candidates,
    format_table,
    make_row,
    write_outputs,
)


class OnlinePresenceInventoryTests(unittest.TestCase):
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
            self.assertEqual(set(OUTPUT_FIELDS), set(payload[0]))

            with tsv_path.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                self.assertEqual(reader.fieldnames, list(OUTPUT_FIELDS))
                first = next(reader)
            self.assertEqual(first["candidate_url"], "https://claude.ai")


if __name__ == "__main__":
    unittest.main()
