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

    def test_context_readiness_from_raw_inputs_is_exposed(self):
        snapshot = _sample_snapshot()
        snapshot["raw_inputs"] = [
            {
                "source": "context",
                "payload": {
                    "sitemap_found": True,
                    "sitemap_url_count": 42,
                    "robots_found": True,
                    "llms_txt_found": False,
                    "schema_types": ["Organization", "WebSite"],
                    "key_pages": {"about": True, "blog": True},
                    "coverage": 0.75,
                    "confidence": 0.82,
                    "context_score": 78,
                },
                "created_at": "2026-04-19T09:40:39",
            }
        ]

        ctx = build_report_context(snapshot, theme="dark")

        self.assertTrue(ctx["context_readiness"]["available"])
        self.assertEqual(ctx["context_readiness"]["sitemap_url_count"], 42)
        self.assertEqual(ctx["context_readiness"]["confidence_label"], "alta")

    def test_cost_policy_from_snapshot_is_exposed(self):
        snapshot = _sample_snapshot()
        snapshot["run"]["use_llm"] = 0
        snapshot["run"]["use_social"] = 0
        snapshot["raw_inputs"] = [
            {"source": "context", "payload": {"coverage": 0.8, "confidence": 0.8}},
            {"source": "web", "payload": {"title": "Example"}},
            {"source": "exa", "payload": {"mentions": []}},
        ]

        ctx = build_report_context(snapshot, theme="dark")

        self.assertTrue(ctx["cost_policy"]["available"])
        self.assertEqual(ctx["cost_policy"]["persisted_raw_inputs"], 3)
        self.assertEqual(ctx["cost_policy"]["raw_input_sources"], ["context", "exa", "web"])
        self.assertEqual(ctx["cost_policy"]["skipped"]["llm"], "disabled_by_request")
        self.assertEqual(ctx["cost_policy"]["skipped"]["social"], "disabled_by_request")

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
        snapshot = _sample_snapshot()
        snapshot["evidence_items"] = [
            {
                "source": "context",
                "url": "https://a16z.com/sitemap.xml",
                "quote": "sitemap.xml found with 20 URLs",
                "feature_name": "site_structure",
                "dimension_name": "presencia",
                "confidence": 0.8,
            }
        ]
        ctx = build_report_context(snapshot, theme="dark")
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
        presencia = next(d for d in ctx["dimensions"] if d["name"] == "presencia")
        self.assertEqual(presencia["evidence"][0]["quote"], "sitemap.xml found with 20 URLs")
        self.assertEqual(presencia["evidence"][0]["source_url"], "https://a16z.com/sitemap.xml")
        self.assertEqual(ctx["evidence_summary"]["by_source"]["context"], 1)
        self.assertEqual(ctx["evidence_summary"]["by_quality"]["direct"], 2)
        self.assertEqual(ctx["trust_summary"]["evidence"]["by_source"]["context"], 1)
        self.assertEqual(ctx["trust_summary"]["limited_dimensions"][0]["display_name"], "Coherence")
        self.assertEqual(ctx["evaluation"]["trust_summary"]["overall_status_label"], "datos insuficientes")
        self.assertEqual(
            ctx["evaluation"]["overall_reason_label"],
            "pre-scan contextual insuficiente",
        )
        self.assertIn(coherencia["confidence_status"], {"degraded", "good", "insufficient_data"})
        self.assertEqual(coherencia["coverage_label"], "baja")
        # footer populated
        self.assertEqual(ctx["footer"]["fingerprint"], "abc123")
        self.assertEqual(ctx["footer"]["report_id"], "rpt_000042")


class ReportRendererTests(unittest.TestCase):
    def test_render_produces_valid_html(self):
        html = ReportRenderer().render(_sample_snapshot(), theme="dark")
        self.assertIn("<html", html)
        self.assertIn("</html>", html)
        self.assertIn("A16Z", html)
        self.assertIn("confianza", html)
        self.assertIn("cobertura", html)
        self.assertIn("Lectura condicionada por evidencia incompleta", html)
        self.assertIn("estado de confianza", html)
        self.assertIn("motivo", html)
        self.assertIn("dimensiones limitadas", html)
        self.assertIn("pre-scan contextual insuficiente", html)
        self.assertIn("siguiente:", html)
        self.assertIn("resumen de evidencia", html)
        self.assertIn("calidad", html)
        self.assertIn("faltan", html)
        self.assertIn("74", html)  # composite score display
        self.assertIn("a16z.com", html)  # URL chip / source list
        self.assertIn("#0e0f10", html)  # dark bg token

    def test_render_shows_cost_policy_when_available(self):
        snapshot = _sample_snapshot()
        snapshot["run"]["use_llm"] = 0
        snapshot["raw_inputs"] = [
            {"source": "context", "payload": {"coverage": 0.8, "confidence": 0.8}},
            {"source": "web", "payload": {"title": "Example"}},
        ]

        html = ReportRenderer().render(snapshot, theme="dark")

        self.assertIn("coste / ejecución", html)
        self.assertIn("inputs: context, web", html)
        self.assertIn("llm=disabled_by_request", html)

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
        self.assertIn("insufficient data to generate findings", html)

    def test_renders_actual_and_new_tabs(self):
        html = ReportRenderer().render(_sample_snapshot(), theme="dark")
        self.assertIn('id="tab-actual"', html)
        self.assertIn('id="tab-new"', html)
        self.assertIn('id="panel-actual"', html)
        self.assertIn('id="panel-new"', html)
        self.assertIn("§3A  current reading", html)
        self.assertIn("§3N  synthesis", html)

    def test_readiness_diagnostic_does_not_render_by_default(self):
        html = ReportRenderer().render(_sample_snapshot(), theme="dark")

        self.assertNotIn("Report readiness", html)

    def test_readiness_diagnostic_renders_when_flag_enabled(self):
        ctx = build_report_context(_sample_snapshot(), theme="dark")
        ctx["ui"]["show_readiness_diagnostic"] = True
        renderer = ReportRenderer()

        html = renderer.env.get_template("report.html.j2").render(**ctx)

        self.assertIn("Report readiness", html)
        self.assertIn("Insufficient evidence", html)
        self.assertIn("diagnostic-summary", html)
        self.assertIn(ctx["readiness"]["diagnostic_summary"], html)
        self.assertIn("dimensions", html)
        self.assertIn("Not evaluable", html)

    def test_readiness_diagnostic_omitted_when_missing(self):
        ctx = build_report_context(_sample_snapshot(), theme="dark")
        ctx.pop("readiness", None)
        renderer = ReportRenderer()

        html = renderer.env.get_template("report.html.j2").render(**ctx)

        self.assertNotIn("Report readiness", html)

    def test_header_and_score_strip_live_outside_tabs(self):
        html = ReportRenderer().render(_sample_snapshot(), theme="dark")
        self.assertEqual(html.count("SCORE_GLOBAL"), 1)
        self.assertEqual(html.count("§2  scores by dimension"), 1)
        self.assertEqual(html.count("analysis_date"), 1)

    def test_insufficient_data_quality_message_renders(self):
        snapshot = _sample_snapshot()
        snapshot["run"]["data_quality"] = "insufficient"
        snapshot["run"]["composite_score"] = None
        snapshot["scores"] = [dict(row, score=None) for row in snapshot["scores"]]
        html = ReportRenderer().render(snapshot, theme="dark")
        self.assertIn("Insufficient data.", html)
        self.assertIn("could not evaluate the full brand surface reliably", html)
        self.assertIn(">n/a<", html.replace(" ", ""))

    # Structural invariants that blindly protect against regressions on the
    # 9 report bugs the narrative refactor was meant to fix.

    def test_header_uses_dl_report_meta(self):
        """Bug 9 — no label+value concatenation; key/value live in <dl>."""
        html = ReportRenderer().render(_sample_snapshot(), theme="dark")
        self.assertIn('<dl class="report-meta">', html)
        self.assertIn("<dt>data_quality</dt>", html)
        # No accidental "analysis_date<date>" or "data_qualityunknown" blobs.
        self.assertNotIn("analysis_date2026", html)
        self.assertNotIn("data_qualityunknown", html)

    def test_data_quality_never_unknown(self):
        """Bug 7 — derive_data_quality replaces the 'unknown' sentinel."""
        snapshot = _sample_snapshot()
        snapshot["run"].pop("data_quality", None)
        html = ReportRenderer().render(snapshot, theme="dark")
        self.assertNotIn("data_quality: unknown", html)
        # The value should be one of the three valid strings.
        self.assertTrue(
            "data_quality: good" in html
            or "data_quality: degraded" in html
            or "data_quality: insufficient" in html,
        )

    def test_no_duplicate_verdict_string(self):
        """Bug 3 — verdict never rendered twice on the same line."""
        html = ReportRenderer().render(_sample_snapshot(), theme="dark")
        # In the scores table, verdict+adjective appear in separate <td>s.
        # A literal duplication like 'solid\nsolid' or 'mixed\nmixed' means
        # a regression.
        self.assertNotIn("mixed\nmixed", html)
        self.assertNotIn("solid\nsolid", html)

    def test_tensions_section_omitted_when_none(self):
        """Bug 8 — §4 disappears when tensions_prose is None (default)."""
        html = ReportRenderer().render(_sample_snapshot(), theme="dark")
        self.assertNotIn("§4  cross-dimension tensions", html)
        self.assertNotIn("(reservado — sin reglas", html)

    def test_tensions_section_appears_when_prose_present(self):
        """Complement of the previous test — §4 renders when it has content."""
        from src.reports.derivation import build_report_context
        from src.reports.renderer import ReportRenderer as _R
        ctx = build_report_context(_sample_snapshot(), theme="dark")
        ctx["tensions_prose"] = "Cross-dimensional tension detected in the analysis."
        ctx["narrative"]["tensions_prose"] = "Cross-dimensional tension detected in the analysis."
        renderer = _R()
        html = renderer.env.get_template("report.html.j2").render(**ctx)
        self.assertIn("§5N  cross-dimension tensions", html)
        self.assertIn("Cross-dimensional tension detected", html)

    def test_sources_section_is_collapsible(self):
        """§5 uses <details> + <summary> so it's closed by default."""
        html = ReportRenderer().render(_sample_snapshot(), theme="dark")
        self.assertIn('<details class="sources">', html)
        self.assertIn("<summary>", html)
        # details should NOT carry an 'open' attribute.
        self.assertNotIn('<details class="sources" open', html)

    def test_no_sin_cita_literal_placeholder(self):
        """Bug 5 — the stale '(sin cita literal)' string must not appear."""
        html = ReportRenderer().render(_sample_snapshot(), theme="dark")
        self.assertNotIn("(sin cita literal)", html)

    def test_none_composite_is_rendered_as_na(self):
        """Finding 2 — composite_score=None must propagate as n/a, not 0."""
        snapshot = _sample_snapshot()
        snapshot["run"]["composite_score"] = None
        snapshot["scores"] = [dict(row, score=None) for row in snapshot["scores"]]
        html = ReportRenderer().render(snapshot, theme="dark")
        self.assertIn(">n/a<", html.replace(" ", ""))
        self.assertIn("global score unavailable", html)
        # Must NOT fabricate 0/100 or pretend it's an F.
        self.assertNotIn("0/100", html)
        self.assertNotIn("band: F", html)

    def test_score_never_has_decimal(self):
        """Bug 2 — composite score displayed with 0 decimals consistently."""
        snapshot = _sample_snapshot()  # composite_score = 74.3
        html = ReportRenderer().render(snapshot, theme="dark")
        self.assertIn(">74<", html.replace(" ", ""))  # shows 74
        self.assertNotIn("74.3/100", html)
        self.assertNotIn("69.7", html)


if __name__ == "__main__":
    unittest.main()
