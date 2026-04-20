"""Phase 1 of fix/report-narrative — evidence collection + verdict derivation."""

from __future__ import annotations

import unittest

from src.reports.derivation import (
    Evidence,
    collect_evidences,
    derive_data_quality,
    derive_verdict,
    group_by_dimension,
    _extract_domain,
    _infer_source_type,
)


def _feat(dimension: str, feature_name: str, source: str, raw: dict | str) -> dict:
    raw_value = raw if isinstance(raw, str) else repr(raw)
    return {
        "dimension_name": dimension,
        "feature_name": feature_name,
        "value": 0.0,
        "raw_value": raw_value,
        "confidence": 0.9,
        "source": source,
    }


def _snapshot(
    *,
    url: str = "https://example.com",
    llm_used: int = 1,
    features: list[dict] | None = None,
    scores: list[dict] | None = None,
) -> dict:
    return {
        "run": {
            "id": 1,
            "brand_name": "Example",
            "url": url,
            "llm_used": llm_used,
            "composite_score": 72.0,
        },
        "scores": scores or [],
        "features": features or [],
        "annotations": [],
    }


NETLIFY_SNAPSHOT = _snapshot(
    url="https://www.netlify.com",
    features=[
        # brand_sentiment — has evidence list with quote+source_url+signal
        _feat(
            "percepcion",
            "brand_sentiment",
            "llm",
            {
                "verdict": "positive",
                "evidence": [
                    {
                        "quote": "Netlify redefines modern web development.",
                        "source_url": "https://techcrunch.com/2025/netlify-series-d",
                        "signal": "positive",
                    },
                    {
                        "quote": "Serverless deployments at scale.",
                        "source_url": "https://www.netlify.com/blog/enterprise/",
                        "signal": "neutral",
                    },
                ],
            },
        ),
        # positioning_clarity — quote only, no URL
        _feat(
            "diferenciacion",
            "positioning_clarity",
            "llm",
            {
                "verdict": "clear",
                "evidence": [
                    {"quote": "Ship faster with serverless.", "signal": "clear"},
                ],
            },
        ),
        # search_visibility — evidence list with url+title+snippet
        _feat(
            "presencia",
            "search_visibility",
            "exa",
            {
                "evidence": [
                    {
                        "url": "https://en.wikipedia.org/wiki/Netlify",
                        "title": "Netlify - Wikipedia",
                        "snippet": "American cloud computing company",
                    },
                ],
            },
        ),
        # content_recency — single evidence_url
        _feat(
            "vitalidad",
            "content_recency",
            "exa",
            {
                "evidence_url": "https://www.netlify.com/blog/2026-04-01-release/",
                "days_ago": 5,
            },
        ),
        # web_presence — evidence_snippet only
        _feat(
            "presencia",
            "web_presence",
            "web_scrape",
            {
                "evidence_snippet": "Build the best web experiences ever. "
                "Netlify is the platform for web builders.",
                "has_https": True,
            },
        ),
        # tone_consistency — examples list
        _feat(
            "coherencia",
            "tone_consistency",
            "llm",
            {
                "examples": [
                    {"source": "web", "quote": "Build the best web experiences."},
                    {"source": "external", "quote": "Netlify powers the Jamstack."},
                ],
            },
        ),
        # uniqueness — no evidence shape we recognize (should produce nothing)
        _feat(
            "diferenciacion",
            "uniqueness",
            "llm",
            {
                "unique_phrases": ["serverless", "jamstack"],
                "verdict": "highly_unique",
            },
        ),
    ],
    scores=[
        {"dimension_name": "coherencia", "score": 78.0, "insights_json": "[]", "rules_json": "[]"},
        {"dimension_name": "presencia", "score": 82.0, "insights_json": "[]", "rules_json": "[]"},
        {"dimension_name": "percepcion", "score": 66.0, "insights_json": "[]", "rules_json": "[]"},
        {"dimension_name": "diferenciacion", "score": 54.0, "insights_json": "[]", "rules_json": "[]"},
        {"dimension_name": "vitalidad", "score": 71.0, "insights_json": "[]", "rules_json": "[]"},
    ],
)


class ExtractDomainTests(unittest.TestCase):
    def test_strips_www_and_lowercases(self):
        self.assertEqual(_extract_domain("https://WWW.Netlify.Com/foo"), "netlify.com")

    def test_handles_subdomain(self):
        self.assertEqual(_extract_domain("https://blog.cloudflare.com/x"), "blog.cloudflare.com")

    def test_empty_and_malformed(self):
        self.assertIsNone(_extract_domain(None))
        self.assertIsNone(_extract_domain(""))
        self.assertIsNone(_extract_domain("not-a-url"))


class InferSourceTypeTests(unittest.TestCase):
    def test_owned_wins_over_path_shape(self):
        st = _infer_source_type("https://netlify.com/about", "netlify.com")
        self.assertEqual(st, "owned")

    def test_changelog_on_own_domain(self):
        st = _infer_source_type("https://netlify.com/changelog/2026-04/", "netlify.com")
        self.assertEqual(st, "changelog")

    def test_encyclopedic_wikipedia(self):
        st = _infer_source_type("https://en.wikipedia.org/wiki/Netlify", "netlify.com")
        self.assertEqual(st, "encyclopedic")

    def test_social_linkedin(self):
        st = _infer_source_type("https://www.linkedin.com/company/netlify", "netlify.com")
        self.assertEqual(st, "social")

    def test_news_techcrunch(self):
        st = _infer_source_type("https://techcrunch.com/2025/netlify-series-d", "netlify.com")
        self.assertEqual(st, "news")

    def test_review_g2(self):
        st = _infer_source_type("https://g2.com/products/netlify/reviews", "netlify.com")
        self.assertEqual(st, "review")

    def test_other_when_unknown(self):
        st = _infer_source_type("https://random-blog.example/post", "netlify.com")
        self.assertEqual(st, "other")

    def test_no_url_is_other(self):
        self.assertEqual(_infer_source_type(None, "netlify.com"), "other")


class CollectEvidencesTests(unittest.TestCase):
    def test_extracts_from_netlify_snapshot(self):
        evidences = collect_evidences(NETLIFY_SNAPSHOT)
        self.assertGreater(len(evidences), 0)
        # Every evidence must have at least one of quote/url
        for ev in evidences:
            self.assertTrue(ev.quote or ev.url, f"bare evidence in {ev.feature_name}")

    def test_source_type_distribution_for_netlify(self):
        evidences = collect_evidences(NETLIFY_SNAPSHOT)
        types = {ev.source_type for ev in evidences}
        # We expect at least these to show up from the fixture
        self.assertIn("news", types)           # techcrunch
        self.assertIn("owned", types)          # netlify.com/blog
        self.assertIn("encyclopedic", types)   # wikipedia

    def test_sentiment_carried_from_signal(self):
        evidences = collect_evidences(NETLIFY_SNAPSHOT)
        sentiments = {ev.sentiment for ev in evidences if ev.sentiment}
        self.assertTrue(sentiments.issubset({"positive", "neutral", "clear"}))

    def test_dimension_preserved(self):
        evidences = collect_evidences(NETLIFY_SNAPSHOT)
        dims = {ev.dimension for ev in evidences}
        self.assertTrue(dims.issubset({
            "coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad",
        }))

    def test_discards_items_without_quote_or_url(self):
        # Construct a fixture where the evidence dicts have neither
        snap = _snapshot(features=[
            _feat(
                "coherencia",
                "tone_consistency",
                "llm",
                {"examples": [{"source": "web"}, {"unrelated": "key"}]},
            ),
            _feat(
                "diferenciacion",
                "uniqueness",
                "llm",
                {"unique_phrases": ["x"]},  # not an evidence key
            ),
        ])
        self.assertEqual(collect_evidences(snap), [])

    def test_owned_vs_external_classification(self):
        evidences = collect_evidences(NETLIFY_SNAPSHOT)
        owned = [ev for ev in evidences if ev.source_type == "owned"]
        for ev in owned:
            self.assertEqual(ev.source_domain, "netlify.com")


class DeriveVerdictTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(derive_verdict(80.0), ("solid", "cohesive"))
        self.assertEqual(derive_verdict(79.9), ("mixed", "mostly-solid"))
        self.assertEqual(derive_verdict(65.0), ("mixed", "mostly-solid"))
        self.assertEqual(derive_verdict(64.9), ("mixed", "uneven"))
        self.assertEqual(derive_verdict(50.0), ("mixed", "uneven"))
        self.assertEqual(derive_verdict(49.9), ("weak", "fragmented"))
        self.assertEqual(derive_verdict(35.0), ("weak", "fragmented"))
        self.assertEqual(derive_verdict(34.9), ("very weak", "broken"))

    def test_none_score(self):
        self.assertEqual(derive_verdict(None), ("n/a", "unknown"))


class GroupByDimensionTests(unittest.TestCase):
    def test_returns_five_dimensions_in_fixed_order(self):
        evidences = collect_evidences(NETLIFY_SNAPSHOT)
        grouped = group_by_dimension(evidences, NETLIFY_SNAPSHOT)
        self.assertEqual(
            [d.dimension for d in grouped],
            ["coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad"],
        )

    def test_scores_and_verdicts_attached(self):
        evidences = collect_evidences(NETLIFY_SNAPSHOT)
        grouped = group_by_dimension(evidences, NETLIFY_SNAPSHOT)
        pres = next(d for d in grouped if d.dimension == "presencia")
        self.assertEqual(pres.score, 82.0)
        self.assertEqual(pres.verdict, "solid")
        self.assertEqual(pres.verdict_adjective, "cohesive")

    def test_dimension_without_evidences_still_present(self):
        sparse = _snapshot(
            features=[
                _feat(
                    "presencia",
                    "web_presence",
                    "web_scrape",
                    {"evidence_snippet": "x" * 300},
                ),
            ],
            scores=[
                {"dimension_name": d, "score": 50.0, "insights_json": "[]", "rules_json": "[]"}
                for d in ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")
            ],
        )
        evidences = collect_evidences(sparse)
        grouped = group_by_dimension(evidences, sparse)
        self.assertEqual(len(grouped), 5)
        non_presencia = [d for d in grouped if d.dimension != "presencia"]
        for d in non_presencia:
            self.assertEqual(d.evidences, [])


class DeriveDataQualityTests(unittest.TestCase):
    def test_returns_explicit_value_when_valid(self):
        snap = _snapshot()
        snap["run"]["data_quality"] = "good"
        self.assertEqual(derive_data_quality(snap), "good")

    def test_ignores_unknown_and_falls_through(self):
        snap = _snapshot(
            features=[
                _feat("presencia", "web_presence", "web_scrape", {
                    "evidence_snippet": "x" * 400,
                }),
                _feat("coherencia", "messaging_consistency", "llm", {"verdict": "ok"}),
            ],
        )
        snap["run"]["data_quality"] = "unknown"
        self.assertEqual(derive_data_quality(snap), "good")

    def test_insufficient_when_llm_disabled(self):
        snap = _snapshot(llm_used=0)
        self.assertEqual(derive_data_quality(snap), "insufficient")

    def test_degraded_when_heuristic_majority(self):
        snap = _snapshot(features=[
            _feat("coherencia", "visual_consistency", "web_scrape_heuristic", {"x": 1}),
            _feat("diferenciacion", "content_authenticity", "fallback_heuristic", {"x": 1}),
            _feat("percepcion", "brand_sentiment", "llm", {"x": 1}),
            _feat("presencia", "web_presence", "web_scrape", {"evidence_snippet": "y" * 300}),
        ])
        self.assertEqual(derive_data_quality(snap), "degraded")

    def test_degraded_when_web_snippet_short(self):
        snap = _snapshot(features=[
            _feat("presencia", "web_presence", "web_scrape", {"evidence_snippet": "short"}),
            _feat("coherencia", "messaging_consistency", "llm", {"x": 1}),
        ])
        self.assertEqual(derive_data_quality(snap), "degraded")

    def test_good_path(self):
        snap = _snapshot(features=[
            _feat("presencia", "web_presence", "web_scrape", {"evidence_snippet": "y" * 400}),
            _feat("coherencia", "messaging_consistency", "llm", {"x": 1}),
            _feat("diferenciacion", "uniqueness", "llm", {"x": 1}),
        ])
        self.assertEqual(derive_data_quality(snap), "good")


if __name__ == "__main__":
    unittest.main()
