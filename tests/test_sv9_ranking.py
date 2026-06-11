import tempfile
import unittest
from pathlib import Path

from src.sv9.aggregator import aggregate
from src.sv9.categories import MIN_COHORT_FOR_PERCENTILE, suggest_category
from src.sv9.models import ComponentResult, RungVerdict, STATUS_NOT_EVALUATED, STATUS_SCORED
from src.sv9.ranking import build_ranking, domain_from_url
from src.sv9.rubric import COMPONENTS
from src.sv9.store import Sv9Store


def scored(key: str, score: int) -> ComponentResult:
    profile = [
        RungVerdict(rung=i, passed=i <= score, evidence="q" if i <= score else "")
        for i in range(1, COMPONENTS[key]["scale"] + 1)
    ]
    return ComponentResult(component=key, status=STATUS_SCORED, score=score, rung_profile=profile)


def make_scan(store: Sv9Store, *, brand: str, url: str, score_level: int, complete: bool = True) -> int:
    components = {key: scored(key, score_level) for key in COMPONENTS}
    if not complete:
        components["values"] = ComponentResult(
            component="values", status=STATUS_NOT_EVALUATED, error="x"
        )
    result = aggregate(components, brand_name=brand, url=url)
    return store.save_scan(result)


class DomainExtractionTests(unittest.TestCase):
    def test_strips_scheme_www_and_port(self):
        self.assertEqual(domain_from_url("https://www.netlify.com/pricing"), "netlify.com")
        self.assertEqual(domain_from_url("criptan.com"), "criptan.com")
        self.assertEqual(domain_from_url("http://example.com:8080"), "example.com")
        self.assertIsNone(domain_from_url(""))


class CategorySuggestionTests(unittest.TestCase):
    def test_known_niches_map_and_unknown_stay_unsuggested(self):
        self.assertEqual(suggest_category("frontier_ai"), "ia")
        self.assertEqual(suggest_category("llm_framework"), "devtools_infra")
        self.assertIsNone(suggest_category("base"))
        self.assertIsNone(suggest_category(None))


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Sv9Store(str(Path(self.tmp.name) / "r.sqlite3"))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_orders_by_score_and_dedupes_latest_per_domain(self):
        make_scan(self.store, brand="Acme", url="https://acme.test", score_level=2)
        make_scan(self.store, brand="Acme", url="https://www.acme.test", score_level=4)  # latest wins
        make_scan(self.store, brand="Beta", url="https://beta.test", score_level=5)

        ranking = build_ranking(self.store)
        self.assertEqual([e["domain"] for e in ranking["entries"]], ["beta.test", "acme.test"])
        self.assertEqual(ranking["entries"][0]["position"], 1)
        # Acme shows its latest scan's score, not the older one.
        acme = ranking["entries"][1]
        self.assertGreater(acme["brand3_score"], 40)

    def test_incomplete_scans_and_other_rubric_versions_stay_out(self):
        make_scan(self.store, brand="Par", url="https://par.test", score_level=3, complete=False)
        complete_id = make_scan(self.store, brand="Ok", url="https://ok.test", score_level=3)
        self.store.conn.execute(
            "UPDATE sv9_scans SET rubric_version='sv9-rubric-v0' WHERE id != ?", (complete_id,)
        )
        self.store.conn.commit()

        ranking = build_ranking(self.store)
        self.assertEqual([e["domain"] for e in ranking["entries"]], ["ok.test"])

    def test_excluded_domains_disappear(self):
        make_scan(self.store, brand="Test", url="https://example.com", score_level=3)
        self.store.upsert_brand_category(
            "example.com", primary_category=None, exclude_from_ranking=True
        )
        ranking = build_ranking(self.store)
        self.assertEqual(ranking["entries"], [])

    def test_confirmed_category_beats_suggestion_and_filters_work(self):
        make_scan(self.store, brand="Acme", url="https://acme.test", score_level=3)
        make_scan(self.store, brand="Beta", url="https://beta.test", score_level=4)
        self.store.upsert_brand_category(
            "acme.test", primary_category="fintech", evaluador="sergio"
        )

        ranking = build_ranking(self.store)
        acme = next(e for e in ranking["entries"] if e["domain"] == "acme.test")
        self.assertEqual(acme["category"], "fintech")
        self.assertEqual(acme["category_source"], "confirmada")

        filtered = build_ranking(self.store, category="fintech")
        self.assertEqual([e["domain"] for e in filtered["entries"]], ["acme.test"])
        # Position is global, kept even under filter.
        self.assertEqual(filtered["entries"][0]["position"], 2)

    def test_percentile_omitted_below_min_cohort_and_present_above(self):
        for i in range(MIN_COHORT_FOR_PERCENTILE):
            make_scan(
                self.store,
                brand=f"B{i}",
                url=f"https://b{i}.test",
                score_level=(i % 5) + 1,
            )
            self.store.upsert_brand_category(f"b{i}.test", primary_category="saas_b2b")
        make_scan(self.store, brand="Solo", url="https://solo.test", score_level=5)
        self.store.upsert_brand_category("solo.test", primary_category="fintech")

        ranking = build_ranking(self.store)
        solo = next(e for e in ranking["entries"] if e["domain"] == "solo.test")
        self.assertIsNone(solo["percentile"])  # cohort of 1
        cohort_entries = [e for e in ranking["entries"] if e["category"] == "saas_b2b"]
        self.assertTrue(all(e["percentile"] is not None for e in cohort_entries))
        best = max(cohort_entries, key=lambda e: e["brand3_score"])
        self.assertGreater(best["percentile"], 50)


if __name__ == "__main__":
    unittest.main()
