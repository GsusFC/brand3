import copy
import json
import unittest
from pathlib import Path

from src.reports.state_first_prose_generator import (
    NO_PROSE_CANDIDATE,
    generate_state_first_prose_candidate,
)


ROOT = Path(__file__).resolve().parents[1]


def _load(relative_path: str) -> dict:
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def _planning(case_id: str) -> dict:
    return _load(
        f"examples/reports/narrative_harness/state_first_generation_v0/{case_id}.state_first_generator_v0.json"
    )


class StateFirstProseGeneratorTests(unittest.TestCase):
    def test_stable_output_shape_and_lab_flags(self):
        result = generate_state_first_prose_candidate(_planning("iris"))

        self.assertEqual(result["version"], "state_first_prose_candidate.v0")
        for key in (
            "status",
            "source_artifacts",
            "generation_frame",
            "baseline_problem_summary",
            "shared_evidence_map",
            "state_first_findings_by_dimension",
            "comparison",
            "verdict",
        ):
            self.assertIn(key, result)
        self.assertTrue(result["status"]["lab_only"])
        self.assertTrue(result["status"]["deterministic_generation"])
        self.assertFalse(result["status"]["runtime_integration"])
        self.assertFalse(result["status"]["prompt_rollout"])
        self.assertFalse(result["status"]["scoring_change"])
        self.assertFalse(result["status"]["renderer_change"])
        self.assertFalse(result["status"]["report_mutation"])
        self.assertFalse(result["status"]["visual_signature_change"])
        self.assertFalse(result["status"]["production_ready"])

    def test_iris_generates_name_collision_candidate(self):
        result = generate_state_first_prose_candidate(_planning("iris"))

        self.assertEqual(result["generation_frame"]["pressure_subtype"], "name_collision")
        self.assertIn("irisdesign.dev", result["generation_frame"]["global_caveat"])
        self.assertIn("not aliases", result["generation_frame"]["global_caveat"])
        self.assertTrue(result["status"]["requires_human_review"])
        self.assertIn("ambiguous_name_collision_surfaces", result["shared_evidence_map"])
        self.assertIn(
            "Does not infer ownership from name similarity.",
            result["state_first_findings_by_dimension"]["presencia"]["overreach_avoided"],
        )
        self.assertIn(
            "speed/value proposition",
            result["state_first_findings_by_dimension"]["diferenciacion"]["state_first_candidate"],
        )
        self.assertIn(
            "visibility and interpretation risk",
            result["state_first_findings_by_dimension"]["percepcion"]["state_first_candidate"],
        )
        self.assertIn(
            "should not import activity",
            result["state_first_findings_by_dimension"]["vitalidad"]["state_first_candidate"],
        )

    def test_watermelon_generates_ecosystem_candidate(self):
        result = generate_state_first_prose_candidate(_planning("watermelon"))

        self.assertEqual(result["generation_frame"]["pressure_subtype"], "ecosystem_surface_pressure")
        self.assertIn("ecosystem pressure only", result["generation_frame"]["global_caveat"])
        self.assertIn("ecosystem_context_surfaces", result["shared_evidence_map"])
        self.assertTrue(result["status"]["requires_human_review"])
        self.assertIn(
            "Does not infer roadmap, traction, or community strength from adjacent surfaces.",
            result["state_first_findings_by_dimension"]["vitalidad"]["overreach_avoided"],
        )
        self.assertIn(
            "repository or marketplace context cannot verify category advantage",
            result["state_first_findings_by_dimension"]["diferenciacion"]["state_first_candidate"],
        )
        self.assertIn(
            "separate surface noise from brand signal",
            result["state_first_findings_by_dimension"]["percepcion"]["state_first_candidate"],
        )
        self.assertIn(
            "map surfaces by relation type",
            result["state_first_findings_by_dimension"]["presencia"]["state_first_candidate"],
        )

    def test_launchdarkly_generates_light_stable_entity_candidate(self):
        result = generate_state_first_prose_candidate(_planning("launchdarkly"))

        self.assertEqual(result["generation_frame"]["mode"], "light")
        self.assertEqual(result["generation_frame"]["pressure_subtype"], "stable_entity_evidence_binding")
        self.assertIn("should not invent ambiguity", result["generation_frame"]["global_caveat"])
        self.assertFalse(result["status"]["requires_human_review"])
        self.assertIn("owned_surfaces", result["shared_evidence_map"])
        self.assertEqual(
            result["state_first_findings_by_dimension"]["vitalidad"]["requires_human_review"],
            False,
        )

    def test_unsupported_subtype_abstains(self):
        artifact = copy.deepcopy(_planning("iris"))
        artifact["state_first_finding_plan"]["pressure_subtype"] = "unsupported_pressure"

        result = generate_state_first_prose_candidate(artifact)

        self.assertFalse(result["generation_decision"]["candidate_available"])
        self.assertEqual(result["generation_decision"]["reason"], NO_PROSE_CANDIDATE)
        self.assertIsNone(result["generated_state_first_prose"])

    def test_every_dimension_includes_boundaries_uncertainty_and_overreach(self):
        for case_id in ("iris", "watermelon", "launchdarkly"):
            with self.subTest(case_id=case_id):
                result = generate_state_first_prose_candidate(_planning(case_id))
                for dimension, finding in result["state_first_findings_by_dimension"].items():
                    self.assertTrue(finding["state_first_candidate"], dimension)
                    self.assertTrue(finding["evidence_boundary"], dimension)
                    self.assertIsInstance(finding["uncertainty_retained"], list)
                    self.assertTrue(finding["uncertainty_retained"], dimension)
                    self.assertIsInstance(finding["overreach_avoided"], list)
                    self.assertTrue(finding["overreach_avoided"], dimension)
                    self.assertIn("evidence_used", finding)

    def test_strong_modes_require_human_review(self):
        for case_id in ("iris", "watermelon"):
            with self.subTest(case_id=case_id):
                result = generate_state_first_prose_candidate(_planning(case_id))
                self.assertTrue(result["status"]["requires_human_review"])
                self.assertTrue(
                    all(
                        item["requires_human_review"]
                        for item in result["state_first_findings_by_dimension"].values()
                    )
                )

    def test_light_mode_only_requires_review_for_missing_evidence_dimensions(self):
        result = generate_state_first_prose_candidate(_planning("launchdarkly"))

        self.assertFalse(result["status"]["requires_human_review"])
        self.assertTrue(result["state_first_findings_by_dimension"]["coherencia"]["requires_human_review"])
        self.assertFalse(result["state_first_findings_by_dimension"]["vitalidad"]["requires_human_review"])


if __name__ == "__main__":
    unittest.main()
