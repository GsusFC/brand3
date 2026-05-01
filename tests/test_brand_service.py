import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData, ExaResult
from src.collectors.social_collector import PlatformMetrics, SocialData
from src.collectors.web_collector import WebData
from src.services import brand_service
from src.services.brand_service import (
    _aggregate_exa_content,
    _build_content_web,
    _compute_data_quality,
    _context_confidence_summary,
    _context_evidence_items,
    _cost_policy_summary,
    _dimension_confidence_summary,
    _llm_cache_summary,
    _recover_owned_web_content,
    _should_skip_llm_for_low_context,
    _trust_summary_payload,
)
from src.models.brand import FeatureValue
from src.quality.evidence_summary import summarize_evidence_from_features
from src.storage.sqlite_store import SQLiteStore


class BrandServiceContentFallbackTests(unittest.TestCase):
    def test_owned_fallback_recovers_same_domain_pages_before_exa_fallback(self):
        initial = WebData(url="https://example.com", title="Example", markdown_content="", error="blocked")
        about = WebData(
            url="https://example.com/about",
            title="About Example",
            markdown_content="About Example builds reliable brand intelligence. " * 8,
        )
        pricing = WebData(
            url="https://example.com/pricing",
            title="Pricing",
            markdown_content="Pricing information for teams and enterprise customers. " * 8,
        )
        exa = ExaData(
            brand_name="Example",
            mentions=[
                ExaResult(url=f"https://external{i}.com", title=f"Mention {i}", text="External mention. " * 30)
                for i in range(4)
            ],
        )

        class FakeCollector:
            def __init__(self):
                self.urls = []

            def scrape_multiple(self, urls):
                self.urls = urls
                return [about, WebData(url="https://example.com/docs", error="404"), pricing]

        collector = FakeCollector()
        recovered = _recover_owned_web_content("https://example.com", initial, collector)
        content_web, content_source, data_sources = _build_content_web(
            "https://example.com",
            "Example",
            recovered or initial,
            exa,
        )

        self.assertEqual(
            collector.urls,
            [
                "https://example.com/about",
                "https://example.com/pricing",
                "https://example.com/docs",
                "https://example.com/blog",
                "https://example.com/news",
                "https://example.com/help",
                "https://example.com/support",
                "https://example.com/trust",
                "https://example.com/security",
            ],
        )
        self.assertIsNotNone(content_web)
        self.assertEqual(content_source, "owned_fallback")
        self.assertEqual(data_sources["web_scrape"], "owned_fallback")
        self.assertEqual(data_sources["content_source"], "owned_fallback")
        self.assertEqual(data_sources["exa_fallback_mentions_used"], 0)
        self.assertEqual(
            data_sources["owned_fallback_urls"],
            ["https://example.com/about", "https://example.com/pricing"],
        )
        self.assertIn("About Example builds reliable brand intelligence", content_web.markdown_content)
        self.assertIn("Pricing information for teams", content_web.markdown_content)

    def test_owned_fallback_failure_keeps_exa_fallback_behavior(self):
        initial = WebData(url="https://uber.com", title="", markdown_content="", error="")
        exa = ExaData(
            brand_name="Uber",
            mentions=[
                ExaResult(url=f"https://example{i}.com", title=f"Mention {i}", text="Uber is a mobility platform. " * 30)
                for i in range(4)
            ],
        )

        class FakeCollector:
            def scrape_multiple(self, urls):
                return [WebData(url=url, markdown_content="", error="404") for url in urls]

        recovered = _recover_owned_web_content("https://uber.com", initial, FakeCollector())
        content_web, content_source, data_sources = _build_content_web(
            "https://uber.com",
            "Uber",
            recovered or initial,
            exa,
        )

        self.assertIsNone(recovered)
        self.assertIsNotNone(content_web)
        self.assertEqual(content_source, "exa_fallback")
        self.assertEqual(data_sources["content_source"], "exa_fallback")
        self.assertEqual(data_sources["exa_fallback_mentions_used"], 4)

    def test_owned_fallback_is_not_attempted_when_initial_web_data_is_usable(self):
        initial = WebData(
            url="https://example.com",
            title="Example",
            markdown_content="Usable homepage content. " * 12,
        )

        class FakeCollector:
            def scrape_multiple(self, urls):
                raise AssertionError("fallback URLs should not be scraped")

        recovered = _recover_owned_web_content("https://example.com", initial, FakeCollector())

        self.assertIsNone(recovered)

    def test_owned_fallback_uses_same_scheme_and_host_only(self):
        initial = WebData(url="https://www.example.com/start", markdown_content="", error="blocked")

        class FakeCollector:
            def __init__(self):
                self.urls = []

            def scrape_multiple(self, urls):
                self.urls = urls
                return []

        collector = FakeCollector()
        recovered = _recover_owned_web_content("https://www.example.com/start?x=1", initial, collector)

        self.assertIsNone(recovered)
        self.assertTrue(all(url.startswith("https://www.example.com/") for url in collector.urls))
        self.assertNotIn("https://example.com/about", collector.urls)

    def test_owned_fallback_data_quality_follows_owned_content_path(self):
        exa = ExaData(
            brand_name="Example",
            mentions=[ExaResult(url=f"https://e{i}.com", title="x") for i in range(5)],
        )

        self.assertEqual(_compute_data_quality(exa, "owned_fallback"), "good")

    def test_build_content_web_reports_browser_fallback_as_owned_content_source(self):
        web = WebData(
            url="https://claude.ai",
            title="Claude",
            markdown_content="Claude browser-rendered product and pricing content. " * 8,
            content_source="browser_fallback",
            browser_status=200,
        )
        exa = ExaData(
            brand_name="Claude",
            mentions=[ExaResult(url=f"https://e{i}.com", title="x") for i in range(5)],
        )

        content_web, content_source, data_sources = _build_content_web(
            "https://claude.ai",
            "Claude",
            web,
            exa,
        )

        self.assertIs(content_web, web)
        self.assertEqual(content_source, "browser_fallback")
        self.assertEqual(data_sources["web_scrape"], "browser_fallback")
        self.assertEqual(data_sources["content_source"], "browser_fallback")
        self.assertEqual(data_sources["exa_fallback_mentions_used"], 0)
        self.assertEqual(_compute_data_quality(exa, content_source), "good")

    def test_low_context_does_not_skip_llm_when_browser_fallback_has_usable_owned_content(self):
        context = ContextData(url="https://claude.ai", coverage=0.0)
        content_web = WebData(
            url="https://claude.ai",
            markdown_content="Claude browser-rendered product content. " * 8,
            content_source="browser_fallback",
        )

        self.assertFalse(
            _should_skip_llm_for_low_context(context, content_web, "browser_fallback")
        )

    def test_low_context_still_skips_llm_when_only_exa_fallback_exists(self):
        context = ContextData(url="https://claude.ai", coverage=0.0)
        content_web = WebData(
            url="https://claude.ai",
            markdown_content="External Exa aggregate content. " * 12,
        )

        self.assertTrue(
            _should_skip_llm_for_low_context(context, content_web, "exa_fallback")
        )

    def test_good_context_keeps_llm_allowed_without_owned_content(self):
        context = ContextData(url="https://example.com", coverage=0.8)

        self.assertFalse(
            _should_skip_llm_for_low_context(context, None, "none")
        )

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

    def test_cost_policy_summary_exposes_skips_and_cache_savings(self):
        summary = _cost_policy_summary(
            raw_input_cache={"context": "hit", "web": "miss", "social": "skipped"},
            llm_cache={"cache_hits": 2, "cache_misses": 1, "skipped_reason": "missing_api_key"},
            use_llm=True,
            use_social=False,
            use_competitors=False,
            skip_visual_analysis=True,
            context_data=ContextData(url="https://example.com", coverage=0.2, confidence=0.4),
            data_quality="insufficient",
        )

        self.assertEqual(summary["cache_hits"], 1)
        self.assertEqual(summary["cache_misses"], 1)
        self.assertEqual(summary["llm_cache_hits"], 2)
        self.assertEqual(summary["skipped"]["llm"], "missing_api_key")
        self.assertEqual(summary["skipped"]["social"], "disabled_by_request")
        self.assertEqual(summary["skipped"]["deep_llm_narrative"], "insufficient_context_coverage")
        self.assertGreaterEqual(summary["estimated_saved_operations"], 3)

    def test_dimension_confidence_marks_sparse_dimension_insufficient(self):
        summary = _dimension_confidence_summary(
            {
                "presencia": {
                    "web_presence": FeatureValue(
                        "web_presence",
                        80.0,
                        raw_value={"evidence_snippet": "homepage reachable"},
                        confidence=0.9,
                        source="web_scrape",
                    )
                }
            },
            data_quality="good",
            context_data=ContextData(url="https://example.com", coverage=0.8, confidence=0.8),
        )

        self.assertEqual(summary["presencia"]["status"], "insufficient_data")
        self.assertIn("social_footprint", summary["presencia"]["missing_signals"])
        self.assertIn("Conectar senales sociales relevantes", " ".join(summary["presencia"]["recommended_next_steps"]))
        self.assertLess(summary["presencia"]["coverage"], 0.3)

    def test_evidence_summary_counts_feature_and_persisted_evidence(self):
        summary = summarize_evidence_from_features(
            {
                "presencia": {
                    "web_presence": FeatureValue(
                        "web_presence",
                        80.0,
                        raw_value={"evidence_snippet": "homepage reachable"},
                        confidence=0.9,
                        source="web_scrape",
                    )
                }
            },
            evidence_items=[
                {
                    "source": "context",
                    "quote": "robots.txt found",
                    "dimension_name": "presencia",
                }
            ],
        )

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["by_dimension"]["presencia"], 2)
        self.assertEqual(summary["by_quality"]["indirect"], 1)
        self.assertEqual(summary["by_quality"]["weak"], 1)
        self.assertIn("coherencia", summary["dimensions_without_evidence"])

    def test_trust_summary_payload_includes_aggregate_status_and_labels(self):
        summary = _trust_summary_payload(
            data_quality="good",
            context_summary={"status": "good", "coverage": 0.8},
            evidence_summary={"total": 2},
            dimension_confidence={
                "presencia": {"status": "insufficient_data", "missing_signals": ["schema"]},
                "coherencia": {"status": "insufficient_data"},
                "percepcion": {"status": "insufficient_data"},
            },
        )

        self.assertEqual(summary["overall_status"], "insufficient_data")
        self.assertEqual(summary["overall_status_label"], "datos insuficientes")
        self.assertEqual(summary["overall_reason"], "multiple_dimensions_insufficient")
        self.assertEqual(summary["evidence"]["total"], 2)
        self.assertEqual(summary["limited_dimensions"][0]["name"], "presencia")
        self.assertEqual(summary["limited_dimensions"][0]["missing_signals"], ["schema"])

    def test_run_reuses_raw_input_cache_and_copies_payloads_to_current_run(self):
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            context = ContextData(
                url="https://example.com",
                robots_found=True,
                sitemap_found=True,
                sitemap_url_count=3,
                coverage=0.8,
                confidence=0.8,
            )
            web = WebData(
                url="https://example.com",
                title="Example",
                markdown_content="Example brand builds reliable software. " * 12,
            )
            exa = ExaData(
                brand_name="Example",
                mentions=[
                    ExaResult(url=f"https://source{i}.com", title="Example mention", text="Example brand mention.")
                    for i in range(5)
                ],
            )

            with patch.object(brand_service, "BRAND3_DB_PATH", str(db_path)):
                with patch("src.services.brand_service.ContextCollector.scan", return_value=context) as context_scan:
                    with patch("src.services.brand_service.WebCollector.scrape", return_value=web) as web_scrape:
                        with patch("src.services.brand_service.ExaCollector.collect_brand_data", return_value=exa) as exa_collect:
                            brand_service.run(
                                "https://example.com",
                                "Example",
                                use_llm=False,
                                use_social=False,
                                use_competitors=False,
                                skip_visual_analysis=True,
                            )
                            second = brand_service.run(
                                "https://example.com",
                                "Example",
                                use_llm=False,
                                use_social=False,
                                use_competitors=False,
                                skip_visual_analysis=True,
                            )

            self.assertEqual(context_scan.call_count, 1)
            self.assertEqual(web_scrape.call_count, 1)
            self.assertEqual(exa_collect.call_count, 1)
            self.assertEqual(second["data_sources"]["raw_input_cache"]["context"], "hit")
            self.assertEqual(second["data_sources"]["raw_input_cache"]["web"], "hit")
            self.assertEqual(second["data_sources"]["raw_input_cache"]["exa"], "hit")
            self.assertEqual(second["data_sources"]["raw_input_cache"]["social"], "skipped")
            self.assertEqual(second["data_sources"]["cost_policy"]["cache_hits"], 3)
            self.assertEqual(second["data_sources"]["cost_policy"]["skipped"]["llm"], "disabled_by_request")
            self.assertEqual(second["data_sources"]["cost_policy"]["skipped"]["social"], "disabled_by_request")

            store = SQLiteStore(str(db_path))
            try:
                snapshot = store.get_run_snapshot(second["run_id"])
            finally:
                store.close()
            raw_sources = {item["source"] for item in snapshot["raw_inputs"]}
            self.assertTrue({"context", "web", "exa"}.issubset(raw_sources))

    def test_run_refresh_bypasses_raw_input_cache_reads_but_writes_fresh_inputs(self):
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            context = ContextData(
                url="https://example.com",
                robots_found=True,
                sitemap_found=True,
                sitemap_url_count=3,
                coverage=0.8,
                confidence=0.8,
            )
            web = WebData(
                url="https://example.com",
                title="Example",
                markdown_content="Example brand builds reliable software. " * 12,
            )
            exa = ExaData(
                brand_name="Example",
                mentions=[
                    ExaResult(url=f"https://source{i}.com", title="Example mention", text="Example brand mention.")
                    for i in range(5)
                ],
            )

            with patch.object(brand_service, "BRAND3_DB_PATH", str(db_path)):
                with patch("src.services.brand_service.ContextCollector.scan", return_value=context) as context_scan:
                    with patch("src.services.brand_service.WebCollector.scrape", return_value=web) as web_scrape:
                        with patch("src.services.brand_service.ExaCollector.collect_brand_data", return_value=exa) as exa_collect:
                            brand_service.run(
                                "https://example.com",
                                "Example",
                                use_llm=False,
                                use_social=False,
                                use_competitors=False,
                                skip_visual_analysis=True,
                            )
                            refreshed = brand_service.run(
                                "https://example.com",
                                "Example",
                                use_llm=False,
                                use_social=False,
                                use_competitors=False,
                                skip_visual_analysis=True,
                                refresh=True,
                            )

            self.assertEqual(context_scan.call_count, 2)
            self.assertEqual(web_scrape.call_count, 2)
            self.assertEqual(exa_collect.call_count, 2)
            self.assertEqual(refreshed["data_sources"]["raw_input_cache"]["context"], "miss")
            self.assertEqual(refreshed["data_sources"]["raw_input_cache"]["web"], "miss")
            self.assertEqual(refreshed["data_sources"]["raw_input_cache"]["exa"], "miss")
            self.assertEqual(refreshed["data_sources"]["raw_input_cache"]["social"], "skipped")

            store = SQLiteStore(str(db_path))
            try:
                snapshot = store.get_run_snapshot(refreshed["run_id"])
            finally:
                store.close()
            raw_sources = {item["source"] for item in snapshot["raw_inputs"]}
            self.assertTrue({"context", "web", "exa"}.issubset(raw_sources))

    def test_run_social_timeout_continues_and_records_limitation(self):
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            context = ContextData(
                url="https://example.com",
                robots_found=True,
                sitemap_found=True,
                sitemap_url_count=3,
                coverage=0.8,
                confidence=0.8,
            )
            web = WebData(
                url="https://example.com",
                title="Example",
                markdown_content="Example brand builds reliable software. " * 12,
            )
            exa = ExaData(
                brand_name="Example",
                mentions=[
                    ExaResult(url=f"https://source{i}.com", title="Example mention", text="Example brand mention.")
                    for i in range(5)
                ],
            )
            social = SocialData(brand_name="Example", error="social_collection_timeout_after_1s")

            with patch.object(brand_service, "BRAND3_DB_PATH", str(db_path)):
                with patch("src.services.brand_service.ContextCollector.scan", return_value=context):
                    with patch("src.services.brand_service.WebCollector.scrape", return_value=web):
                        with patch("src.services.brand_service.ExaCollector.collect_brand_data", return_value=exa):
                            with patch(
                                "src.services.brand_service._collect_social_with_budget",
                                return_value=(social, "timeout"),
                            ):
                                result = brand_service.run(
                                    "https://example.com",
                                    "Example",
                                    use_llm=False,
                                    use_social=True,
                                    use_competitors=False,
                                    skip_visual_analysis=True,
                                    refresh=True,
                                )

            self.assertEqual(result["brand"], "Example")
            self.assertFalse(result["social_scraped"])
            self.assertEqual(result["data_sources"]["social_limitation"], "timeout")
            self.assertEqual(result["data_sources"]["raw_input_cache"]["social"], "timeout")
            self.assertEqual(result["data_sources"]["cost_policy"]["skipped"]["social"], "collection_timeout")

            store = SQLiteStore(str(db_path))
            try:
                snapshot = store.get_run_snapshot(result["run_id"])
            finally:
                store.close()
            social_inputs = [item for item in snapshot["raw_inputs"] if item["source"] == "social"]
            self.assertEqual(len(social_inputs), 1)
            self.assertEqual(social_inputs[0]["payload"]["error"], "social_collection_timeout_after_1s")

    def test_run_social_error_continues_and_records_limitation(self):
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            context = ContextData(url="https://example.com", coverage=0.8, confidence=0.8)
            web = WebData(
                url="https://example.com",
                title="Example",
                markdown_content="Example brand builds reliable software. " * 12,
            )
            exa = ExaData(
                brand_name="Example",
                mentions=[
                    ExaResult(url=f"https://source{i}.com", title="Example mention", text="Example brand mention.")
                    for i in range(5)
                ],
            )

            with patch.object(brand_service, "BRAND3_DB_PATH", str(db_path)):
                with patch("src.services.brand_service.ContextCollector.scan", return_value=context):
                    with patch("src.services.brand_service.WebCollector.scrape", return_value=web):
                        with patch("src.services.brand_service.ExaCollector.collect_brand_data", return_value=exa):
                            with patch(
                                "src.services.brand_service._collect_social_with_budget",
                                side_effect=RuntimeError("firebase/firecrawl unavailable"),
                            ):
                                result = brand_service.run(
                                    "https://example.com",
                                    "Example",
                                    use_llm=False,
                                    use_social=True,
                                    use_competitors=False,
                                    skip_visual_analysis=True,
                                    refresh=True,
                                )

            self.assertEqual(result["brand"], "Example")
            self.assertFalse(result["social_scraped"])
            self.assertEqual(result["data_sources"]["social_limitation"], "error")
            self.assertEqual(result["data_sources"]["raw_input_cache"]["social"], "error")
            self.assertEqual(result["data_sources"]["cost_policy"]["skipped"]["social"], "collection_error")

    def test_run_social_success_preserves_normal_behavior(self):
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            context = ContextData(url="https://example.com", coverage=0.8, confidence=0.8)
            web = WebData(
                url="https://example.com",
                title="Example",
                markdown_content="Example brand builds reliable software. " * 12,
            )
            exa = ExaData(
                brand_name="Example",
                mentions=[
                    ExaResult(url=f"https://source{i}.com", title="Example mention", text="Example brand mention.")
                    for i in range(5)
                ],
            )
            social = SocialData(
                brand_name="Example",
                platforms={
                    "linkedin": PlatformMetrics(
                        platform="linkedin",
                        profile_url="https://linkedin.com/company/example",
                        followers_count=1200,
                    )
                },
                profiles_found=["https://linkedin.com/company/example"],
                total_followers=1200,
                most_active_platform="linkedin",
            )

            with patch.object(brand_service, "BRAND3_DB_PATH", str(db_path)):
                with patch("src.services.brand_service.ContextCollector.scan", return_value=context):
                    with patch("src.services.brand_service.WebCollector.scrape", return_value=web):
                        with patch("src.services.brand_service.ExaCollector.collect_brand_data", return_value=exa):
                            with patch(
                                "src.services.brand_service._collect_social_with_budget",
                                return_value=(social, None),
                            ):
                                result = brand_service.run(
                                    "https://example.com",
                                    "Example",
                                    use_llm=False,
                                    use_social=True,
                                    use_competitors=False,
                                    skip_visual_analysis=True,
                                    refresh=True,
                                )

            self.assertTrue(result["social_scraped"])
            self.assertIsNone(result["data_sources"]["social_limitation"])
            self.assertEqual(result["data_sources"]["raw_input_cache"]["social"], "miss")
            self.assertNotIn("social", result["data_sources"]["cost_policy"]["skipped"])

    def test_run_llm_feature_timeout_continues_and_records_limitation(self):
        class FakeLLM:
            api_key = "key"
            model = "fake-model"
            cache_hits = 0
            cache_misses = 1
            cache_writes = 0

            def __init__(self):
                self.last_failure_reason = None
                self.call_failures = []

            def analyze_momentum(self, mentions, brand_name):
                return {"momentum_score": 60, "verdict": "maintaining", "signals": [], "evidence": []}

            def analyze_messaging_consistency(self, web_content, mentions, brand_name):
                self.last_failure_reason = None
                return {
                    "consistency_score": 80,
                    "verdict": "aligned",
                    "self_category": "software",
                    "third_party_category": "software",
                    "aligned_themes": ["software"],
                    "gaps": [],
                }

            def analyze_tone_consistency(self, web_content, snippets, brand_name):
                self.last_failure_reason = None
                return {
                    "tone_consistency_score": 75,
                    "gap_signal": "none",
                    "self_tone": "clear",
                    "external_tone": "clear",
                    "examples": [],
                }

            def analyze_positioning_clarity(self, content, brand_name, competitor_snippets):
                self.last_failure_reason = None
                return {
                    "clarity_score": 82,
                    "verdict": "clear",
                    "stated_position": "Reliable software for teams.",
                    "target_audience": "Teams",
                    "differentiator_claimed": "Reliability",
                    "evidence": [{"quote": "Reliable software for teams.", "signal": "clear"}],
                }

            def analyze_uniqueness(self, content, brand_name, competitor_snippets):
                self.last_failure_reason = "llm_timeout"
                self.call_failures.append({"reason": "llm_timeout", "error": "llm_call_timeout_after_1s"})
                return {}

            def analyze_brand_sentiment(self, mentions, brand_name):
                self.last_failure_reason = None
                return {
                    "sentiment_score": 72,
                    "verdict": "positive",
                    "controversy": False,
                    "signals": [],
                    "evidence": [],
                }

        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "brand3.sqlite3"
            context = ContextData(url="https://example.com", coverage=0.8, confidence=0.8)
            web = WebData(
                url="https://example.com",
                title="Example",
                markdown_content="Reliable software for teams. " * 40,
            )
            exa = ExaData(
                brand_name="Example",
                mentions=[
                    ExaResult(url=f"https://source{i}.com", title="Positive Example mention", text="Example is reliable.")
                    for i in range(5)
                ],
            )

            with patch.object(brand_service, "BRAND3_DB_PATH", str(db_path)):
                with patch("src.services.brand_service.ContextCollector.scan", return_value=context):
                    with patch("src.services.brand_service.WebCollector.scrape", return_value=web):
                        with patch("src.services.brand_service.ExaCollector.collect_brand_data", return_value=exa):
                            with patch("src.services.brand_service.LLMAnalyzer", FakeLLM):
                                with patch("src.services.brand_service._take_screenshot_with_budget", return_value=({}, "timeout")):
                                    result = brand_service.run(
                                        "https://example.com",
                                        "Example",
                                        use_llm=True,
                                        use_social=False,
                                        use_competitors=False,
                                        skip_visual_analysis=False,
                                        refresh=True,
                                    )

        self.assertEqual(result["brand"], "Example")
        self.assertIn("diferenciacion", result["dimensions"])
        self.assertIn("percepcion", result["dimensions"])
        self.assertEqual(
            result["data_sources"]["llm_cache"]["call_failures"][0]["reason"],
            "llm_timeout",
        )
        self.assertEqual(
            result["data_sources"]["cost_policy"]["skipped"]["llm_feature_calls"],
            "partial_timeout_or_error",
        )


if __name__ == "__main__":
    unittest.main()
