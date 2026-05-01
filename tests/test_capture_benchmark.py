import unittest

from experiments.capture_benchmark import (
    CaptureRow,
    classify_surface,
    format_table,
    should_score,
)


class CaptureBenchmarkTests(unittest.TestCase):
    def test_classify_surface_is_conservative(self):
        self.assertEqual(
            classify_surface("https://claude.ai", "https://claude.ai"),
            ("primary", 1.0),
        )
        self.assertEqual(
            classify_surface("https://claude.ai", "https://claude.ai/pricing"),
            ("same_domain_candidate", 0.95),
        )
        self.assertEqual(
            classify_surface("https://claude.ai", "https://docs.claude.ai"),
            ("official_related_candidate", 0.75),
        )
        self.assertEqual(
            classify_surface("https://claude.ai", "https://example.com/claude"),
            ("third_party_candidate", 0.2),
        )

    def test_should_score_requires_usable_owned_capture(self):
        third_party = CaptureRow(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://example.com/claude",
            method="exa",
            usable=True,
            ownership_confidence=0.2,
            capture_confidence=0.95,
        )
        owned = CaptureRow(
            brand="Claude",
            input_url="https://claude.ai",
            candidate_url="https://claude.ai",
            method="browser_playwright",
            usable=True,
            ownership_confidence=1.0,
            capture_confidence=0.8,
        )

        self.assertFalse(should_score([third_party]))
        self.assertTrue(should_score([third_party, owned]))

    def test_format_table_contains_required_columns_and_boolean_values(self):
        table = format_table([
            CaptureRow(
                brand="Claude",
                input_url="https://claude.ai",
                candidate_url="https://claude.ai",
                method="browser_playwright",
                status="200",
                text_chars=3190,
                html_chars=12000,
                usable=True,
                title="Claude",
                surface_type="primary",
                ownership_confidence=1.0,
                capture_confidence=0.95,
            )
        ])

        self.assertIn("brand", table)
        self.assertIn("candidate_url", table)
        self.assertIn("browser_playwright", table)
        self.assertIn("true", table)
        self.assertIn("0.95", table)


if __name__ == "__main__":
    unittest.main()
