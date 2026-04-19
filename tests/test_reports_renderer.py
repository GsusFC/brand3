import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.reports.derivation import (
    ascii_bar,
    band_from_score,
    build_report_context,
    extract_evidence,
    parse_raw_value,
    slugify,
)
from src.reports.renderer import ReportRenderer


def _sample_snapshot() -> dict:
    return {
        "run": {
            "id": 42,
            "brand_name": "A16Z",
            "url": "https://a16z.com",
            "composite_score": 74.3,
            "calibration_profile": "base",
            "profile_source": "fallback",
            "started_at": "2026-04-19T09:40:38",
            "completed_at": "2026-04-19T09:40:42",
            "run_duration_seconds": 4.72,
            "data_quality": "good",
            "brand_profile": {"name": "A16Z", "domain": "a16z.com"},
            "audit": {"scoring_state_fingerprint": "abc123"},
            "summary": "A16Z brief summary.",
        },
        "scores": [
            {"dimension_name": "coherencia", "score": 66.8,
             "insights_json": "[\"Gap de messaging en /wholesale\"]", "rules_json": "[]"},
            {"dimension_name": "presencia", "score": 76.8,
             "insights_json": "[]", "rules_json": "[]"},
            {"dimension_name": "percepcion", "score": 61.2,
             "insights_json": "[]", "rules_json": "[]"},
            {"dimension_name": "diferenciacion", "score": 87.8,
             "insights_json": "[]", "rules_json": "[]"},
            {"dimension_name": "vitalidad", "score": 84.8,
             "insights_json": "[]", "rules_json": "[]"},
        ],
        "features": [
            {
                "dimension_name": "coherencia",
                "feature_name": "messaging_consistency",
                "value": 72.0,
                "raw_value": (
                    "{'verdict': 'consistent', "
                    "'evidence': [{'quote': 'Software is eating the world', "
                    "'source_url': 'https://a16z.com/software', "
                    "'signal': 'positive'}]}"
                ),
                "confidence": 0.85,
                "source": "llm",
            },
        ],
        "annotations": [],
    }


class DerivationHelperTests(unittest.TestCase):
    def test_band_from_score_ranges(self):
        self.assertEqual(band_from_score(15)[0], "F")
        self.assertEqual(band_from_score(25)[0], "D")
        self.assertEqual(band_from_score(45)[0], "C")
        self.assertEqual(band_from_score(62)[0], "C+")
        self.assertEqual(band_from_score(78)[0], "B")
        self.assertEqual(band_from_score(92)[0], "A")
        self.assertEqual(band_from_score(None), ("?", "n/a"))

    def test_ascii_bar_widths(self):
        bar = ascii_bar(62, width=20)
        self.assertTrue(bar.startswith("[") and bar.endswith("]"))
        self.assertEqual(bar.count("█") + bar.count("░"), 20)
        filled = bar.count("█")
        self.assertEqual(filled, 12)  # round(62/5) = 12
        self.assertEqual(ascii_bar(0, width=10), "[" + "░" * 10 + "]")
        self.assertEqual(ascii_bar(100, width=10), "[" + "█" * 10 + "]")

    def test_parse_raw_value_handles_dict_repr(self):
        result = parse_raw_value("{'verdict': 'building', 'score': 75}")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["verdict"], "building")
        self.assertEqual(result["score"], 75)

    def test_parse_raw_value_fallback_on_garbage(self):
        garbage = "not a dict {{ broken"
        self.assertEqual(parse_raw_value(garbage), garbage)
        self.assertIsNone(parse_raw_value(None))
        self.assertIsNone(parse_raw_value(""))

    def test_parse_raw_value_handles_json(self):
        result = parse_raw_value('{"verdict": "declining"}')
        self.assertEqual(result, {"verdict": "declining"})

    def test_extract_evidence_from_llm_feature(self):
        raw = {
            "verdict": "consistent",
            "evidence": [
                {"quote": "q1", "source_url": "u1", "signal": "positive"},
                {"quote": "q2", "source_url": "u2"},
                "plain string example",
            ],
        }
        evidence = extract_evidence(raw)
        self.assertEqual(len(evidence), 3)
        self.assertEqual(evidence[0]["quote"], "q1")
        self.assertEqual(evidence[0]["signal"], "positive")
        self.assertEqual(evidence[2]["quote"], "plain string example")
        self.assertEqual(evidence[2]["source_url"], "")

    def test_extract_evidence_returns_empty_for_non_dict(self):
        self.assertEqual(extract_evidence(None), [])
        self.assertEqual(extract_evidence("some string"), [])
        self.assertEqual(extract_evidence({"no_evidence_keys": 42}), [])

    def test_slugify_matches_brand_service_behavior(self):
        self.assertEqual(slugify("El Corte Inglés S.A."), "el-corte-inglés-s-a")
        self.assertEqual(slugify("A16Z"), "a16z")
        self.assertEqual(slugify(""), "brand")


class BuildReportContextTests(unittest.TestCase):
    def test_context_contains_all_dimensions_and_evidence(self):
        ctx = build_report_context(_sample_snapshot(), theme="dark")
        self.assertEqual(ctx["theme"], "dark")
        self.assertEqual(ctx["brand"]["name"], "A16Z")
        self.assertEqual(ctx["score"]["global"], 74.3)
        self.assertEqual(ctx["score"]["band_letter"], "B")
        names = [d["name"] for d in ctx["dimensions"]]
        self.assertEqual(
            sorted(names),
            sorted(["coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad"]),
        )
        # evidence flowed through for coherencia
        coherencia = next(d for d in ctx["dimensions"] if d["name"] == "coherencia")
        self.assertEqual(len(coherencia["evidence"]), 1)
        self.assertEqual(coherencia["evidence"][0]["quote"], "Software is eating the world")
        # footer populated
        self.assertEqual(ctx["footer"]["fingerprint"], "abc123")
        self.assertEqual(ctx["footer"]["report_id"], "rpt_000042")


class ReportRendererTests(unittest.TestCase):
    def test_render_produces_valid_html(self):
        html = ReportRenderer().render(_sample_snapshot(), theme="dark")
        self.assertIn("<html", html)
        self.assertIn("</html>", html)
        self.assertIn("A16Z", html)
        self.assertIn("74", html)  # composite score display
        self.assertIn("Software is eating", html)
        self.assertIn("#0e0f10", html)  # dark bg token

    def test_render_light_uses_different_palette(self):
        html_dark = ReportRenderer().render(_sample_snapshot(), theme="dark")
        html_light = ReportRenderer().render(_sample_snapshot(), theme="light")
        self.assertIn("#fafaf7", html_light)  # light bg token
        self.assertNotIn("#0e0f10", html_light)
        self.assertNotIn("#fafaf7", html_dark)

    def test_render_to_file_writes_expected_path(self):
        snapshot = _sample_snapshot()
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            path = ReportRenderer().render_to_file(snapshot, theme="dark", output_dir=base)
            self.assertTrue(path.exists())
            self.assertTrue(path.is_relative_to(base))
            self.assertEqual(path.parent.parent.name, "a16z")
            self.assertTrue(path.parent.name.startswith("42-"))
            self.assertEqual(path.name, "report.dark.html")
            content = path.read_text(encoding="utf-8")
            self.assertIn("A16Z", content)

    def test_render_handles_missing_evidence_gracefully(self):
        snapshot = _sample_snapshot()
        snapshot["features"] = [
            {
                "dimension_name": "coherencia",
                "feature_name": "messaging_consistency",
                "value": 40.0,
                "raw_value": "not a parseable dict at all",
                "confidence": 0.3,
                "source": "heuristic_fallback",
            }
        ]
        html = ReportRenderer().render(snapshot, theme="dark")
        self.assertIn("no evidence available", html)


if __name__ == "__main__":
    unittest.main()
