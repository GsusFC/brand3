import json
import unittest
from pathlib import Path

from src.reports.state_first_findings_generator import (
    NO_CANDIDATE,
    generate_state_first_findings_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "reports" / "narrative_harness"


def _load(relative_path: str) -> dict:
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def _finding(evidence_urls=None):
    return {
        "title": "Stable signal",
        "observation": "The available evidence supports a limited observation.",
        "implication": "This should stay bounded.",
        "typical_decision": "",
        "evidence_urls": ["https://example.com"] if evidence_urls is None else evidence_urls,
    }


def _payload(findings_by_dimension=None):
    return {
        "summary": "A compact baseline summary.",
        "synthesis_prose": "A compact synthesis.",
        "tensions_prose": "",
        "findings_by_dimension": findings_by_dimension if findings_by_dimension is not None else {"presencia": [_finding()]},
    }


def _diagnostic(
    *,
    safe_attribution_total=0,
    caveat_total=0,
    fallback_total=0,
    findings_without_evidence_urls=0,
):
    return {
        "status": "warning" if safe_attribution_total or caveat_total or fallback_total else "pass",
        "metrics": {
            "findings_count": 1,
            "findings_without_evidence_urls": findings_without_evidence_urls,
            "safe_attribution_total": safe_attribution_total,
            "safe_attribution_phrase_counts": (
                {"based only on self-description": safe_attribution_total}
                if safe_attribution_total
                else {}
            ),
            "generic_phrase_counts": {},
            "observation_repetition_family_counts": {
                "external_corroboration_caveat_repetition": {
                    "total": caveat_total,
                    "phrases": {"no external corroboration": caveat_total},
                },
                "fallback_evidence_opening_repetition": {
                    "total": fallback_total,
                    "phrases": {"the available sources": fallback_total},
                },
            },
        },
    }


def _render_diagnostic(caveat_total=0, fallback_total=0):
    return {
        "status": "warning",
        "visible_render_metrics": {
            "visible_evidence_chip_link_count": 1,
            "visible_decision_space_count": 0,
            "repeated_sentence_opening_counts": {},
            "observation_repetition_family_counts": {
                "external_corroboration_caveat_repetition": {
                    "total": caveat_total,
                    "phrases": {"no external corroboration": caveat_total},
                },
                "fallback_evidence_opening_repetition": {
                    "total": fallback_total,
                    "phrases": {"the available sources": fallback_total},
                },
            },
        },
    }


def _entity_state(*, related=False, packet_related=False):
    related_surfaces = [
        {
            "surface": "docs.example.com",
            "relation_type": "developer_surface",
            "relationship": "explicitly_related",
            "confidence": "medium",
            "evidence": ["manual review"],
            "requires_human_review": True,
            "source": "manual_review",
        }
    ] if related else []
    packet_related_surfaces = [
        {
            "surface": "watermelon.ai",
            "relation_type": "ambiguous_name_match",
            "relationship": "unresolved",
            "confidence": "unresolved",
            "evidence": [
                {
                    "text": "entity resolution packet",
                    "url": "https://example.com/packet",
                }
            ],
            "requires_human_review": True,
        }
    ] if packet_related else []
    return {
        "version": "entity_narrative_state.v0",
        "status": {
            "experimental": True,
            "offline_only": True,
            "runtime_enabled": False,
            "used_by_scoring": False,
            "used_by_prompts": False,
            "used_by_rendering": False,
            "persisted_report_narrative": False,
            "llm_generated": False,
        },
        "state": {
            "primary_entity_signal": {
                "label": "Example",
                "confidence": "medium",
                "supporting_sources": ["https://example.com"],
            },
            "entity_aliases": {
                "primary": "example.com",
                "observed_related_surfaces": related_surfaces,
                "needs_review": related or packet_related,
            },
            "entity_resolution": {
                "related_surfaces": packet_related_surfaces,
            },
            "owned_claim_density": {"level": "inactive", "safe_attribution_total": 0},
            "evidence_url_coverage": {
                "finding_count": 1,
                "findings_without_evidence_urls": 0,
                "coverage_level": "strong",
            },
            "decision_space_mode": {"mode": "not_applicable_empty"},
            "contradiction_candidates": [],
        },
    }


class StateFirstFindingsGeneratorTests(unittest.TestCase):
    def test_stable_output_shape_and_lab_flags(self):
        result = generate_state_first_findings_candidate(
            _payload(),
            payload_diagnostic=_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            entity_state=_entity_state(),
        )

        self.assertEqual(result["version"], "state_first_findings_generator.v0")
        for key in (
            "status",
            "input_artifacts",
            "generation_decision",
            "baseline",
            "shared_entity_state",
            "shared_evidence_map",
            "global_uncertainty_model",
            "state_first_finding_plan",
            "generated_state_first_findings",
            "comparison",
            "verdict",
        ):
            self.assertIn(key, result)
        self.assertTrue(result["status"]["lab_only"])
        self.assertFalse(result["status"]["runtime_integration"])
        self.assertFalse(result["status"]["prompt_rollout"])
        self.assertFalse(result["status"]["scoring_change"])
        self.assertFalse(result["status"]["renderer_change"])
        self.assertFalse(result["status"]["visual_signature_change"])
        self.assertIn("intervention_reasons", result["generation_decision"])
        self.assertIn("pressure_profile", result["generation_decision"])
        self.assertIn("pressure_subtype", result["state_first_finding_plan"])
        self.assertIn("planning_focus", result["state_first_finding_plan"])
        self.assertEqual(
            set(result["generation_decision"]["pressure_profile"]),
            {
                "entity_boundary",
                "related_surface_pressure",
                "evidence_binding",
                "caveat_inflation",
                "fallback_repetition",
                "owned_claim_repetition",
                "generic_decision_space",
                "visual_or_perceptual_overreach",
                "healthy_case_restraint",
            },
        )

    def test_missing_payload_returns_no_candidate(self):
        result = generate_state_first_findings_candidate(
            {},
            payload_diagnostic=_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            entity_state=_entity_state(),
        )

        self.assertEqual(result["generation_decision"]["mode"], "none")
        self.assertFalse(result["generation_decision"]["candidate_available"])
        self.assertEqual(result["generation_decision"]["reason"], NO_CANDIDATE)
        self.assertIsNone(result["generated_state_first_findings"])

    def test_non_offline_state_returns_no_candidate(self):
        state = _entity_state()
        state["status"]["offline_only"] = False
        state["status"]["runtime_enabled"] = True

        result = generate_state_first_findings_candidate(
            _payload(),
            payload_diagnostic=_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            entity_state=state,
        )

        self.assertEqual(result["generation_decision"]["mode"], "none")
        self.assertIn(
            "entity_narrative_state_status_is_offline_lab_only",
            result["generation_decision"]["preconditions_failed"],
        )

    def test_related_surfaces_select_strong_mode(self):
        result = generate_state_first_findings_candidate(
            _payload(),
            payload_diagnostic=_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            entity_state=_entity_state(related=True),
        )

        self.assertEqual(result["generation_decision"]["mode"], "strong")
        self.assertTrue(result["generation_decision"]["candidate_available"])
        self.assertIn("review-gated", result["generated_state_first_findings"]["global_caveat"])
        self.assertIn("related_surface_review_required", result["generation_decision"]["intervention_reasons"])
        self.assertEqual(result["generation_decision"]["pressure_profile"]["related_surface_pressure"], "low")

    def test_entity_resolution_related_surfaces_select_strong_mode(self):
        result = generate_state_first_findings_candidate(
            _payload(),
            payload_diagnostic=_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            entity_state=_entity_state(packet_related=True),
        )

        self.assertEqual(result["generation_decision"]["mode"], "strong")
        self.assertTrue(result["generation_decision"]["candidate_available"])
        self.assertIn("related_surface_review_required", result["generation_decision"]["intervention_reasons"])
        self.assertEqual(result["shared_entity_state"]["related_surfaces"][0]["surface"], "watermelon.ai")
        self.assertEqual(result["shared_entity_state"]["observed_related_surfaces"][0]["surface"], "watermelon.ai")

    def test_fallback_repetition_selects_light_mode(self):
        result = generate_state_first_findings_candidate(
            _payload({"coherencia": [_finding(evidence_urls=[])]}),
            payload_diagnostic=_diagnostic(fallback_total=5, findings_without_evidence_urls=1),
            render_diagnostic=_render_diagnostic(fallback_total=5),
            entity_state=_entity_state(),
        )

        self.assertEqual(result["generation_decision"]["mode"], "light")
        self.assertTrue(result["generation_decision"]["candidate_available"])
        self.assertIn("fallback_repetition", result["generation_decision"]["intervention_reasons"])
        generated = result["generated_state_first_findings"]["findings_by_dimension"]["coherencia"][0]
        self.assertEqual(generated["missing_evidence_note"], "No finding-level evidence URL is attached in the baseline payload.")
        self.assertTrue(generated["requires_human_review"])

    def test_thin_payload_without_meaningful_pressure_selects_none(self):
        result = generate_state_first_findings_candidate(
            _payload({"coherencia": [_finding()]}),
            payload_diagnostic=_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            entity_state=_entity_state(),
        )

        self.assertEqual(result["generation_decision"]["mode"], "none")
        self.assertFalse(result["generation_decision"]["candidate_available"])
        self.assertIn(
            "thin_payload_restraint",
            result["generation_decision"]["intervention_reasons"],
        )

    def test_case_fixtures_select_expected_modes(self):
        cases = {
            "builtwith_kit_com": (
                _load("examples/reports/narrative_harness/builtwith_kit_com.payload.json"),
                _load("examples/reports/narrative_harness/builtwith_kit_com.diagnostic.json"),
                _load("examples/reports/narrative_harness/builtwith_kit_com.render_aware.diagnostic.json"),
                _load("examples/reports/narrative_harness/entity_state/builtwith_kit_com.entity_narrative_state.json"),
                "strong",
            ),
            "iris": (
                _load("examples/reports/narrative_harness/iris.payload.json"),
                _load("examples/reports/narrative_harness/iris.diagnostic.json"),
                _load("examples/reports/narrative_harness/iris.render_aware.diagnostic.json"),
                _load("examples/reports/narrative_harness/entity_state/iris.entity_narrative_state.v0.json"),
                "strong",
            ),
            "watermelon": (
                _load("examples/reports/narrative_harness/watermelon.payload.json"),
                _load("examples/reports/narrative_harness/watermelon.diagnostic.json"),
                _load("examples/reports/narrative_harness/watermelon.render_aware.diagnostic.json"),
                _load("examples/reports/narrative_harness/entity_state/watermelon.entity_narrative_state.v0.json"),
                "strong",
            ),
            "launchdarkly": (
                _load("examples/reports/narrative_harness/launchdarkly.payload.json"),
                _load("examples/reports/narrative_harness/launchdarkly.diagnostic.json"),
                _load("examples/reports/narrative_harness/launchdarkly.render_aware.diagnostic.json"),
                _load("examples/reports/narrative_harness/entity_state/launchdarkly.entity_narrative_state.v0.json"),
                "light",
            ),
            "netlify_snapshot_mock": (
                _load("examples/reports/narrative_harness/netlify_snapshot_mock.payload.json"),
                _load("examples/reports/narrative_harness/netlify_snapshot_mock.diagnostic.json"),
                _load("examples/reports/narrative_harness/netlify_snapshot_mock.render_aware.diagnostic.json"),
                _load("examples/reports/narrative_harness/entity_state/netlify_snapshot_mock.entity_narrative_state.v0.json"),
                "light",
            ),
        }

        for case_id, (payload, payload_diag, render_diag, state, expected_mode) in cases.items():
            with self.subTest(case_id=case_id):
                result = generate_state_first_findings_candidate(
                    payload,
                    payload_diagnostic=payload_diag,
                    render_diagnostic=render_diag,
                    entity_state=state,
                )
                self.assertEqual(result["generation_decision"]["mode"], expected_mode)
                self.assertTrue(result["status"]["lab_only"])
                self.assertFalse(result["status"]["runtime_integration"])

    def test_case_fixtures_expose_distinct_pressure_reasons(self):
        builtwith = generate_state_first_findings_candidate(
            _load("examples/reports/narrative_harness/builtwith_kit_com.payload.json"),
            payload_diagnostic=_load("examples/reports/narrative_harness/builtwith_kit_com.diagnostic.json"),
            render_diagnostic=_load("examples/reports/narrative_harness/builtwith_kit_com.render_aware.diagnostic.json"),
            entity_state=_load("examples/reports/narrative_harness/entity_state/builtwith_kit_com.entity_narrative_state.json"),
        )
        iris = generate_state_first_findings_candidate(
            _load("examples/reports/narrative_harness/iris.payload.json"),
            payload_diagnostic=_load("examples/reports/narrative_harness/iris.diagnostic.json"),
            render_diagnostic=_load("examples/reports/narrative_harness/iris.render_aware.diagnostic.json"),
            entity_state=_load("examples/reports/narrative_harness/entity_state/iris.entity_narrative_state.v0.json"),
        )
        watermelon = generate_state_first_findings_candidate(
            _load("examples/reports/narrative_harness/watermelon.payload.json"),
            payload_diagnostic=_load("examples/reports/narrative_harness/watermelon.diagnostic.json"),
            render_diagnostic=_load("examples/reports/narrative_harness/watermelon.render_aware.diagnostic.json"),
            entity_state=_load("examples/reports/narrative_harness/entity_state/watermelon.entity_narrative_state.v0.json"),
        )
        launchdarkly = generate_state_first_findings_candidate(
            _load("examples/reports/narrative_harness/launchdarkly.payload.json"),
            payload_diagnostic=_load("examples/reports/narrative_harness/launchdarkly.diagnostic.json"),
            render_diagnostic=_load("examples/reports/narrative_harness/launchdarkly.render_aware.diagnostic.json"),
            entity_state=_load("examples/reports/narrative_harness/entity_state/launchdarkly.entity_narrative_state.v0.json"),
        )
        netlify = generate_state_first_findings_candidate(
            _load("examples/reports/narrative_harness/netlify_snapshot_mock.payload.json"),
            payload_diagnostic=_load("examples/reports/narrative_harness/netlify_snapshot_mock.diagnostic.json"),
            render_diagnostic=_load("examples/reports/narrative_harness/netlify_snapshot_mock.render_aware.diagnostic.json"),
            entity_state=_load("examples/reports/narrative_harness/entity_state/netlify_snapshot_mock.entity_narrative_state.v0.json"),
        )

        builtwith_decision = builtwith["generation_decision"]
        builtwith_plan = builtwith["state_first_finding_plan"]
        self.assertEqual(builtwith_decision["mode"], "strong")
        self.assertIn("entity_boundary_risk", builtwith_decision["intervention_reasons"])
        self.assertIn("owned_claim_repetition", builtwith_decision["intervention_reasons"])
        self.assertIn("external_corroboration_caveat_inflation", builtwith_decision["intervention_reasons"])
        self.assertEqual(builtwith_decision["pressure_profile"]["entity_boundary"], "high")
        self.assertEqual(builtwith_plan["pressure_subtype"], "entity_boundary_collision")
        self.assertIn("mixed entity", builtwith["generated_state_first_findings"]["global_caveat"])
        self.assertIn("no false entity merge", builtwith_plan["overreach_suppression_rules"])

        iris_decision = iris["generation_decision"]
        iris_plan = iris["state_first_finding_plan"]
        self.assertEqual(iris_decision["mode"], "strong")
        self.assertIn("related_surface_review_required", iris_decision["intervention_reasons"])
        self.assertEqual(iris_decision["pressure_profile"]["related_surface_pressure"], "high")
        self.assertIn("visual_or_perceptual_overreach", iris_decision["intervention_reasons"])
        self.assertEqual(iris_plan["pressure_subtype"], "name_collision")
        self.assertIn("name-collision", iris["generated_state_first_findings"]["global_caveat"])
        self.assertIn("no name-collision inflation", iris_plan["overreach_suppression_rules"])

        watermelon_decision = watermelon["generation_decision"]
        watermelon_plan = watermelon["state_first_finding_plan"]
        self.assertEqual(watermelon_decision["mode"], "strong")
        self.assertIn("related_surface_review_required", watermelon_decision["intervention_reasons"])
        self.assertEqual(watermelon_decision["pressure_profile"]["related_surface_pressure"], "high")
        self.assertEqual(watermelon_plan["pressure_subtype"], "ecosystem_surface_pressure")
        self.assertIn("ecosystem surfaces", watermelon["generated_state_first_findings"]["global_caveat"])
        self.assertIn("no ecosystem ownership inference", watermelon_plan["overreach_suppression_rules"])

        launchdarkly_decision = launchdarkly["generation_decision"]
        launchdarkly_plan = launchdarkly["state_first_finding_plan"]
        self.assertEqual(launchdarkly_decision["mode"], "light")
        self.assertIn("stable_entity_restraint", launchdarkly_decision["intervention_reasons"])
        self.assertEqual(launchdarkly_decision["pressure_profile"]["healthy_case_restraint"], "high")
        self.assertEqual(launchdarkly_plan["pressure_subtype"], "stable_entity_evidence_binding")
        self.assertIn("proof distribution", launchdarkly["generated_state_first_findings"]["global_caveat"])

        netlify_decision = netlify["generation_decision"]
        netlify_plan = netlify["state_first_finding_plan"]
        self.assertEqual(netlify_decision["mode"], "light")
        self.assertIn("fallback_repetition", netlify_decision["intervention_reasons"])
        self.assertIn("missing_finding_level_evidence", netlify_decision["intervention_reasons"])
        self.assertEqual(netlify_plan["pressure_subtype"], "fallback_compression")
        self.assertIn("fallback evidence", netlify["generated_state_first_findings"]["global_caveat"])


if __name__ == "__main__":
    unittest.main()
