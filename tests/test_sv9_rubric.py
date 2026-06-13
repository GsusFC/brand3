import unittest

from src.sv9.rubric import (
    BASE_COMPONENTS,
    COMPONENTS,
    PRESENTATION_ORDER,
    RUBRIC_VERSION,
    component_max_points,
    component_points,
)


class Sv9RubricTests(unittest.TestCase):
    def test_brand3_score_totals_100(self):
        self.assertEqual(sum(component_max_points(k) for k in COMPONENTS), 100)

    def test_nine_components_plus_coherencia(self):
        self.assertEqual(len(COMPONENTS), 10)
        self.assertIn("coherencia", COMPONENTS)
        self.assertEqual(len(BASE_COMPONENTS), 8)
        self.assertNotIn("magnetism", BASE_COMPONENTS)
        self.assertNotIn("coherencia", BASE_COMPONENTS)

    def test_presentation_order_covers_everything_and_closes_with_coherencia(self):
        self.assertEqual(set(PRESENTATION_ORDER), set(COMPONENTS))
        self.assertEqual(PRESENTATION_ORDER[-1], "coherencia")
        self.assertEqual(PRESENTATION_ORDER[-2], "magnetism")

    def test_ladders_match_scales_and_are_consecutive(self):
        for key, spec in COMPONENTS.items():
            self.assertEqual(len(spec["ladder"]), spec["scale"], key)
            self.assertEqual(
                [r["rung"] for r in spec["ladder"]],
                list(range(1, spec["scale"] + 1)),
                key,
            )

    def test_pairs_are_five_point_scales(self):
        pairs = {}
        for key, spec in COMPONENTS.items():
            if spec["pair"]:
                pairs.setdefault(spec["pair"], []).append(key)
        self.assertEqual(set(pairs), {"mission_vision", "values_attributes"})
        for members in pairs.values():
            self.assertEqual(len(members), 2)
            for member in members:
                self.assertEqual(COMPONENTS[member]["scale"], 5)

    def test_multipliers_only_on_magnetism_and_coherencia(self):
        for key, spec in COMPONENTS.items():
            expected = 2 if key in {"magnetism", "coherencia"} else 1
            self.assertEqual(spec["multiplier"], expected, key)

    def test_component_points_applies_multiplier(self):
        self.assertEqual(component_points("magnetism", 7), 14)
        self.assertEqual(component_points("coherencia", 10), 20)
        self.assertEqual(component_points("mission", 5), 5)

    def test_relational_context_needs_reference_real_components(self):
        for key, spec in COMPONENTS.items():
            for rung in spec["ladder"]:
                for dep in rung.get("context_needs", []):
                    self.assertIn(dep, COMPONENTS, f"{key} rung {rung['rung']}")

    def test_coherencia_has_no_detection_and_tagged_axes(self):
        spec = COMPONENTS["coherencia"]
        self.assertIsNone(spec["tldr_key"])
        axes = {r.get("axis") for r in spec["ladder"]}
        self.assertTrue({"internal", "external"} <= axes)

    def test_rubric_version_is_pinned(self):
        # v2 = tile scoring (suma de baldosas), product decision 2026-06-11.
        self.assertEqual(RUBRIC_VERSION, "sv9-rubric-v2")


if __name__ == "__main__":
    unittest.main()
