"""Phase 1 of fix/report-narrative — evidence collection + verdict derivation."""

from __future__ import annotations

import unittest

from src.reports.derivation import (
    Evidence,
    build_report_context,
    collect_evidences,
    derive_data_quality,
    derive_verdict,
    group_by_dimension,
    _extract_domain,
    _infer_source_type,
)
from src.quality.report_readiness import (
    REPORT_MODE_INSUFFICIENT,
    REPORT_MODE_PUBLISHABLE,
    REPORT_MODE_TECHNICAL,
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
    evidence_items: list[dict] | None = None,
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
        "evidence_items": evidence_items or [],
        "annotations": [],
    }


def _score_rows(value: float = 80.0) -> list[dict]:
    return [
        {"dimension_name": dimension, "score": value, "insights_json": "[]", "rules_json": "[]"}
        for dimension in ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")
    ]


def _supported_feature(dimension: str, feature_name: str, source: str = "web_scrape") -> dict:
    return {
        "dimension_name": dimension,
        "feature_name": feature_name,
        "value": 82.0,
        "raw_value": repr({
            "evidence": [
                {
                    "quote": f"{dimension} {feature_name} supported.",
                    "source_url": "https://example.com",
                }
            ]
        }),
        "confidence": 0.9,
        "source": source,
    }


def _publishable_snapshot() -> dict:
    return _snapshot(
        features=[
            _supported_feature("coherencia", "visual_consistency"),
            _supported_feature("coherencia", "messaging_consistency", "llm"),
            _supported_feature("coherencia", "tone_consistency", "llm"),
            _supported_feature("coherencia", "cross_channel_coherence", "exa"),
            _supported_feature("presencia", "web_presence"),
            _supported_feature("presencia", "social_footprint", "social_media"),
            _supported_feature("presencia", "search_visibility", "exa"),
            _supported_feature("presencia", "directory_presence", "exa"),
            _supported_feature("diferenciacion", "positioning_clarity", "llm"),
            _supported_feature("diferenciacion", "uniqueness", "llm"),
            _supported_feature("diferenciacion", "competitor_distance", "exa"),
            _supported_feature("diferenciacion", "content_authenticity", "content_analysis"),
            _supported_feature("diferenciacion", "brand_personality", "content_analysis"),
        ],
        scores=_score_rows(82.0),
    )


def _processed_output_snapshot() -> dict:
    return {
        "brand": "Processed",
        "url": "https://processed.example",
        "composite_score": 81.0,
        "dimensions": {
            "coherencia": 82.0,
            "presencia": 79.0,
            "percepcion": 40.0,
            "diferenciacion": 84.0,
            "vitalidad": 35.0,
        },
        "evidence_summary": {
            "total": 9,
            "by_dimension": {
                "coherencia": 2,
                "presencia": 3,
                "percepcion": 0,
                "diferenciacion": 2,
                "vitalidad": 0,
            },
            "by_source": {"web_scrape": 4, "context": 3, "exa": 2},
            "by_quality": {"direct": 9},
            "entity_relevance_available": True,
        },
        "confidence_summary": {
            "coverage": 0.9,
            "confidence": 0.8,
            "status": "good",
        },
        "dimension_confidence": {
            "coherencia": {"status": "good", "confidence": 0.82, "missing_signals": []},
            "presencia": {"status": "good", "confidence": 0.78, "missing_signals": []},
            "percepcion": {
                "status": "insufficient_data",
                "confidence": 0.2,
                "missing_signals": ["review_quality"],
                "confidence_reason": ["no_evidence"],
            },
            "diferenciacion": {"status": "good", "confidence": 0.84, "missing_signals": []},
            "vitalidad": {
                "status": "insufficient_data",
                "confidence": 0.2,
                "missing_signals": ["momentum"],
                "confidence_reason": ["no_evidence"],
            },
        },
        "trust_summary": {},
        "context_readiness": {},
        "audit": {},
    }


def _legacy_score_only_snapshot() -> dict:
    return {
        "brand": "Legacy Brand",
        "url": "https://legacy.example",
        "composite_score": 73.0,
        "dimensions": {
            "coherencia": 80.0,
            "presencia": 75.0,
            "percepcion": 70.0,
            "diferenciacion": 78.0,
            "vitalidad": 62.0,
        },
        "partial_dimensions": [],
        "audit": {},
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

    def test_collects_persisted_evidence_items(self):
        snap = _snapshot(
            evidence_items=[
                {
                    "source": "context",
                    "url": "https://example.com/sitemap.xml",
                    "quote": "sitemap.xml found with 12 URLs",
                    "feature_name": "site_structure",
                    "dimension_name": "presencia",
                    "confidence": 0.8,
                    "freshness_days": 0,
                }
            ]
        )

        evidences = collect_evidences(snap)

        self.assertEqual(len(evidences), 1)
        self.assertEqual(evidences[0].dimension, "presencia")
        self.assertEqual(evidences[0].feature_name, "site_structure")
        self.assertEqual(evidences[0].quote, "sitemap.xml found with 12 URLs")
        self.assertEqual(evidences[0].extra["source"], "context")


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


class BuildReportReadinessContextTests(unittest.TestCase):
    def test_readiness_exists_without_removing_existing_context_keys(self):
        ctx = build_report_context(_publishable_snapshot(), theme="dark")

        for key in (
            "theme",
            "term_lines",
            "brand",
            "score",
            "summary",
            "legacy_summary",
            "synthesis_prose",
            "tensions_prose",
            "sources_grouped",
            "all_sources",
            "dimensions",
            "rules_applied",
            "footer",
            "evaluation",
            "context_readiness",
            "evidence_summary",
            "cost_policy",
            "trust_summary",
            "narrative",
            "sources",
            "audit",
            "ui",
        ):
            self.assertIn(key, ctx)

        self.assertIn("readiness", ctx)
        self.assertIn("readiness", ctx["evaluation"])
        self.assertEqual(ctx["readiness"], ctx["evaluation"]["readiness"])
        self.assertIn("editorial_policy", ctx)

    def test_readiness_does_not_change_scores(self):
        snapshot = _publishable_snapshot()
        ctx = build_report_context(snapshot, theme="dark")

        self.assertEqual(ctx["score"]["global"], snapshot["run"]["composite_score"])
        score_by_dim = {
            row["dimension_name"]: row["score"]
            for row in snapshot["scores"]
        }
        context_score_by_dim = {
            dimension["name"]: dimension["score"]
            for dimension in ctx["dimensions"]
        }
        self.assertEqual(context_score_by_dim, score_by_dim)

    def test_editorial_policy_contains_report_mode_label_and_tone(self):
        ctx = build_report_context(_publishable_snapshot(), theme="dark")
        policy = ctx["editorial_policy"]

        self.assertEqual(policy["report_mode"], ctx["readiness"]["report_mode"])
        self.assertEqual(policy["report_mode_label"], "Publishable brand report")
        self.assertEqual(policy["report_tone"]["tone"], "editorial")
        self.assertTrue(policy["report_tone"]["allows_strategic_implications"])

    def test_editorial_policy_contains_per_dimension_state_policy(self):
        ctx = build_report_context(_publishable_snapshot(), theme="dark")
        policy = ctx["editorial_policy"]

        self.assertEqual(
            set(policy["dimension_policies"]),
            set(ctx["readiness"]["dimension_states"]),
        )
        coherencia = policy["dimension_policies"]["coherencia"]
        self.assertEqual(coherencia["state"], "ready")
        self.assertEqual(coherencia["state_label"], "Ready")
        self.assertEqual(coherencia["tone"]["language_level"], "editorial")
        self.assertTrue(coherencia["allowed_language"]["may_state_findings"])

    def test_editorial_policy_contains_evidence_policy(self):
        ctx = build_report_context(_publishable_snapshot(), theme="dark")
        evidence_policy = ctx["editorial_policy"]["evidence_policy"]

        self.assertTrue(evidence_policy["direct"]["can_support_editorial_claims"])
        self.assertFalse(evidence_policy["weak"]["can_support_editorial_claims"])
        self.assertFalse(evidence_policy["off_entity"]["can_support_editorial_claims"])
        self.assertEqual(
            evidence_policy["fallback"]["language"],
            "not evidence, only technical explanation",
        )

    def test_editorial_policy_does_not_change_scores_or_dimensions(self):
        snapshot = _publishable_snapshot()
        ctx = build_report_context(snapshot, theme="dark")

        self.assertIn("editorial_policy", ctx)
        self.assertEqual(ctx["score"]["global"], snapshot["run"]["composite_score"])
        self.assertEqual(
            [dimension["name"] for dimension in ctx["dimensions"]],
            ["coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad"],
        )

    def test_weak_fallback_like_context_produces_non_publishable_readiness(self):
        snapshot = _publishable_snapshot()
        snapshot["features"] = list(snapshot["features"]) + [
            {
                "dimension_name": "presencia",
                "feature_name": "web_presence",
                "value": 50.0,
                "raw_value": repr({"fallback": True, "reason": "no data"}),
                "confidence": 0.2,
                "source": "fallback",
            }
        ]

        ctx = build_report_context(snapshot, theme="dark")

        self.assertEqual(ctx["readiness"]["report_mode"], REPORT_MODE_TECHNICAL)
        self.assertEqual(
            ctx["readiness"]["dimension_states"]["presencia"],
            "technical_only",
        )

    def test_strong_context_can_produce_publishable_readiness(self):
        ctx = build_report_context(_publishable_snapshot(), theme="dark")

        self.assertEqual(ctx["readiness"]["report_mode"], REPORT_MODE_PUBLISHABLE)
        self.assertEqual(ctx["readiness"]["dimension_states"]["coherencia"], "ready")
        self.assertEqual(ctx["readiness"]["dimension_states"]["presencia"], "ready")
        self.assertEqual(ctx["readiness"]["dimension_states"]["diferenciacion"], "ready")

    def test_processed_output_snapshot_produces_non_empty_readiness(self):
        ctx = build_report_context(_processed_output_snapshot(), theme="dark")

        self.assertIn("readiness", ctx)
        self.assertEqual(ctx["readiness"]["evidence_summary_used"]["total"], 9)
        self.assertEqual(
            ctx["readiness"]["confidence_summary_used"]["coherencia"]["status"],
            "good",
        )
        self.assertEqual(ctx["readiness"]["dimension_states"]["coherencia"], "ready")

    def test_processed_output_snapshot_without_raw_features_does_not_mark_every_dimension_not_evaluable(self):
        ctx = build_report_context(_processed_output_snapshot(), theme="dark")

        states = ctx["readiness"]["dimension_states"]
        self.assertNotEqual(set(states.values()), {"not_evaluable"})
        self.assertEqual(states["coherencia"], "ready")
        self.assertEqual(states["presencia"], "ready")
        self.assertEqual(states["diferenciacion"], "ready")
        self.assertEqual(ctx["readiness"]["missing_high_weight_features"], {})

    def test_db_like_snapshot_readiness_behavior_still_works(self):
        ctx = build_report_context(_publishable_snapshot(), theme="dark")

        self.assertEqual(ctx["readiness"]["report_mode"], REPORT_MODE_PUBLISHABLE)
        self.assertEqual(ctx["readiness"]["evidence_summary_used"]["total"], 13)

    def test_publishable_readiness_has_diagnostic_summary(self):
        ctx = build_report_context(_publishable_snapshot(), theme="dark")

        self.assertIn("diagnostic_summary", ctx["readiness"])
        self.assertIn("enough evidence and confidence", ctx["readiness"]["diagnostic_summary"])

    def test_technical_readiness_has_plain_language_diagnostic_summary(self):
        snapshot = _publishable_snapshot()
        snapshot["features"] = list(snapshot["features"]) + [
            {
                "dimension_name": "presencia",
                "feature_name": "web_presence",
                "value": 50.0,
                "raw_value": repr({"fallback": True, "reason": "no data"}),
                "confidence": 0.2,
                "source": "fallback",
            }
        ]

        ctx = build_report_context(snapshot, theme="dark")

        self.assertEqual(ctx["readiness"]["report_mode"], REPORT_MODE_TECHNICAL)
        self.assertIn("Technical diagnostic", ctx["readiness"]["diagnostic_summary"])
        self.assertIn("technical-only dimensions", ctx["readiness"]["diagnostic_summary"])

    def test_insufficient_readiness_has_diagnostic_summary(self):
        ctx = build_report_context(_legacy_score_only_snapshot(), theme="dark")

        self.assertEqual(ctx["readiness"]["report_mode"], REPORT_MODE_INSUFFICIENT)
        self.assertIn("diagnostic_summary", ctx["readiness"])
        self.assertIn("legacy score-only snapshot", ctx["readiness"]["diagnostic_summary"])
        self.assertIn("evidence and confidence metadata", ctx["readiness"]["diagnostic_summary"])
        self.assertIn(
            "readiness_requires_evidence_and_confidence_metadata",
            ctx["readiness"]["warnings"],
        )

    def test_newer_processed_snapshot_diagnostic_summary_keeps_current_behavior(self):
        ctx = build_report_context(_processed_output_snapshot(), theme="dark")

        self.assertEqual(ctx["readiness"]["report_mode"], REPORT_MODE_PUBLISHABLE)
        self.assertNotIn("legacy score-only snapshot", ctx["readiness"]["diagnostic_summary"])


if __name__ == "__main__":
    unittest.main()
