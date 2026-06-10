import unittest

from src.sv9.aggregator import (
    aggregate,
    apply_magnetism_cap,
    base_average,
    immediate_margin,
    most_painful_gap,
    score_from_rung_profile,
)
from src.sv9.models import (
    ComponentResult,
    RungVerdict,
    STATUS_NOT_DETECTED,
    STATUS_NOT_EVALUATED,
    STATUS_SCORED,
)
from src.sv9.rubric import COMPONENTS


def scored(key: str, score: int) -> ComponentResult:
    profile = [
        RungVerdict(rung=i, passed=i <= score, evidence="quote" if i <= score else "")
        for i in range(1, COMPONENTS[key]["scale"] + 1)
    ]
    return ComponentResult(component=key, status=STATUS_SCORED, score=score, rung_profile=profile)


def full_components(**overrides: ComponentResult) -> dict[str, ComponentResult]:
    components = {key: scored(key, COMPONENTS[key]["scale"]) for key in COMPONENTS}
    components.update(overrides)
    return components


class ScoreFromRungProfileTests(unittest.TestCase):
    def test_all_passed_reaches_ceiling(self):
        profile = [RungVerdict(rung=i, passed=True, evidence="q") for i in range(1, 11)]
        self.assertEqual(score_from_rung_profile(profile), 10)

    def test_stops_at_first_failed_rung(self):
        profile = [RungVerdict(rung=i, passed=i != 3, evidence="q") for i in range(1, 11)]
        self.assertEqual(score_from_rung_profile(profile), 2)

    def test_non_monotonic_passes_above_failure_do_not_count(self):
        profile = [
            RungVerdict(rung=1, passed=True, evidence="q"),
            RungVerdict(rung=2, passed=False),
            RungVerdict(rung=3, passed=True, evidence="q"),
        ]
        self.assertEqual(score_from_rung_profile(profile), 1)

    def test_empty_profile_scores_zero(self):
        self.assertEqual(score_from_rung_profile([]), 0)

    def test_profile_must_start_at_rung_one(self):
        profile = [RungVerdict(rung=2, passed=True, evidence="q")]
        self.assertEqual(score_from_rung_profile(profile), 0)


class NonMonotonicDetectionTests(unittest.TestCase):
    def test_anomalous_rungs_are_reported(self):
        component = ComponentResult(
            component="personality",
            status=STATUS_SCORED,
            score=1,
            rung_profile=[
                RungVerdict(rung=1, passed=True, evidence="q"),
                RungVerdict(rung=2, passed=False),
                RungVerdict(rung=3, passed=False),
                RungVerdict(rung=4, passed=True, evidence="q"),
                RungVerdict(rung=5, passed=False),
                RungVerdict(rung=6, passed=False),
                RungVerdict(rung=7, passed=True, evidence="q"),
                RungVerdict(rung=8, passed=False),
                RungVerdict(rung=9, passed=False),
                RungVerdict(rung=10, passed=False),
            ],
        )
        self.assertEqual(component.non_monotonic_rungs, [4, 7])


class BaseAverageAndCapTests(unittest.TestCase):
    def test_base_average_normalizes_five_point_scales(self):
        components = full_components(
            mission=scored("mission", 5),  # 10 normalized
            vision=scored("vision", 0),  # 0
            values=scored("values", 5),  # 10
            attributes=scored("attributes", 0),  # 0
            value_proposition=scored("value_proposition", 10),
            personality=scored("personality", 0),
            brand_idea=scored("brand_idea", 10),
            core_purpose=scored("core_purpose", 0),
        )
        self.assertAlmostEqual(base_average(components), 5.0)

    def test_zero_status_components_count_as_zero_in_base(self):
        components = full_components(
            mission=ComponentResult(component="mission", status=STATUS_NOT_DETECTED),
            vision=ComponentResult(component="vision", status=STATUS_NOT_EVALUATED, error="boom"),
        )
        expected = (0 + 0 + 10 + 10 + 10 + 10 + 10 + 10) / 8
        self.assertAlmostEqual(base_average(components), expected)

    def test_magnetism_capped_on_broken_base(self):
        components = full_components(
            **{key: scored(key, 0) for key in COMPONENTS if key not in {"magnetism", "coherencia"}},
            magnetism=scored("magnetism", 9),
        )
        avg, capped = apply_magnetism_cap(components)
        self.assertTrue(capped)
        self.assertEqual(components["magnetism"].score, 5)
        self.assertLess(avg, 4.0)

    def test_magnetism_not_capped_on_solid_base(self):
        components = full_components(magnetism=scored("magnetism", 9))
        _avg, capped = apply_magnetism_cap(components)
        self.assertFalse(capped)
        self.assertEqual(components["magnetism"].score, 9)

    def test_low_magnetism_untouched_even_on_broken_base(self):
        components = full_components(
            **{key: scored(key, 0) for key in COMPONENTS if key not in {"magnetism", "coherencia"}},
            magnetism=scored("magnetism", 3),
        )
        _avg, capped = apply_magnetism_cap(components)
        self.assertFalse(capped)
        self.assertEqual(components["magnetism"].score, 3)


class AggregateTests(unittest.TestCase):
    def test_perfect_scan_totals_100(self):
        result = aggregate(full_components(), brand_name="Acme", url="https://acme.test")
        self.assertEqual(result.brand3_score, 100)
        self.assertTrue(result.is_complete)
        self.assertIsNone(result.most_painful_gap)
        self.assertEqual(result.immediate_margin, 0)
        self.assertFalse(result.needs_review)

    def test_pair_halves_score_alone_and_never_average(self):
        result = aggregate(
            full_components(
                mission=scored("mission", 4),
                vision=ComponentResult(component="vision", status=STATUS_NOT_DETECTED),
            ),
            brand_name="Acme",
            url="https://acme.test",
        )
        # mission 4 + vision 0: the pair contributes 4, never (4+0)/2 scaled.
        self.assertEqual(result.brand3_score, 100 - 5 - 1)

    def test_multipliers_double_magnetism_and_coherencia(self):
        result = aggregate(
            full_components(
                magnetism=scored("magnetism", 7),
                coherencia=scored("coherencia", 6),
            ),
            brand_name="Acme",
            url="https://acme.test",
        )
        self.assertEqual(result.components["magnetism"].points, 14)
        self.assertEqual(result.components["coherencia"].points, 12)
        self.assertEqual(result.brand3_score, 60 + 14 + 12)

    def test_not_evaluated_scores_zero_and_marks_partial(self):
        result = aggregate(
            full_components(
                personality=ComponentResult(
                    component="personality", status=STATUS_NOT_EVALUATED, error="llm_timeout"
                )
            ),
            brand_name="Acme",
            url="https://acme.test",
        )
        self.assertEqual(result.brand3_score, 90)
        self.assertFalse(result.is_complete)
        self.assertEqual(result.not_evaluated, ["personality"])

    def test_needs_review_on_low_coherencia(self):
        result = aggregate(
            full_components(coherencia=scored("coherencia", 3)),
            brand_name="Acme",
            url="https://acme.test",
        )
        self.assertTrue(result.needs_review)

    def test_aggregate_requires_every_component(self):
        components = full_components()
        components.pop("coherencia")
        with self.assertRaises(ValueError):
            aggregate(components, brand_name="Acme", url="https://acme.test")


class ImmediateMarginTests(unittest.TestCase):
    def test_margin_counts_one_rung_per_component_with_multiplier(self):
        components = full_components(
            mission=scored("mission", 3),  # +1
            coherencia=scored("coherencia", 8),  # +2
        )
        self.assertEqual(immediate_margin(components, magnetism_capped=False), 3)

    def test_not_detected_components_offer_their_first_rung(self):
        components = full_components(
            values=ComponentResult(component="values", status=STATUS_NOT_DETECTED),
        )
        self.assertEqual(immediate_margin(components, magnetism_capped=False), 1)

    def test_technical_failures_promise_nothing(self):
        components = full_components(
            values=ComponentResult(component="values", status=STATUS_NOT_EVALUATED, error="x"),
        )
        self.assertEqual(immediate_margin(components, magnetism_capped=False), 0)

    def test_capped_magnetism_gains_nothing_from_one_rung(self):
        components = full_components(magnetism=scored("magnetism", 5))
        self.assertEqual(immediate_margin(components, magnetism_capped=True), 0)
        self.assertEqual(immediate_margin(components, magnetism_capped=False), 2)


class MostPainfulGapTests(unittest.TestCase):
    def test_widest_gap_wins(self):
        components = full_components(
            mission=scored("mission", 4),  # gap 1
            core_purpose=scored("core_purpose", 2),  # gap 8
        )
        self.assertEqual(most_painful_gap(components), "core_purpose")

    def test_tie_breaks_toward_heavier_component(self):
        components = full_components(
            mission=scored("mission", 0),  # gap 5
            magnetism=scored("magnetism", 8),  # gap 4 in points... use coherencia below
            coherencia=scored("coherencia", 7),  # gap 6
        )
        # coherencia gap (6 points) > mission gap (5 points)
        self.assertEqual(most_painful_gap(components), "coherencia")

    def test_excludes_technical_failures(self):
        components = full_components(
            personality=ComponentResult(
                component="personality", status=STATUS_NOT_EVALUATED, error="x"
            ),
            mission=scored("mission", 4),
        )
        self.assertEqual(most_painful_gap(components), "mission")


if __name__ == "__main__":
    unittest.main()
