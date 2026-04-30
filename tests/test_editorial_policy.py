import unittest

from src.reports.editorial_policy import (
    allowed_language_for_dimension_state,
    evidence_language_hint,
    label_dimension_state,
    label_report_mode,
    tone_for_dimension_state,
    tone_for_report_mode,
)


class EditorialPolicyTests(unittest.TestCase):
    def test_known_report_modes_return_stable_labels_and_tone_hints(self):
        publishable = tone_for_report_mode("publishable_brand_report")
        self.assertEqual(label_report_mode("publishable_brand_report"), "Publishable brand report")
        self.assertEqual(publishable["tone"], "editorial")
        self.assertTrue(publishable["allows_strategic_implications"])
        self.assertTrue(publishable["allows_recommendations"])

        diagnostic = tone_for_report_mode("technical_diagnostic")
        self.assertEqual(diagnostic["tone"], "cautious")
        self.assertEqual(diagnostic["allows_strategic_implications"], "limited")

        insufficient = tone_for_report_mode("insufficient_evidence")
        self.assertEqual(insufficient["tone"], "diagnostic")
        self.assertFalse(insufficient["allows_strategic_implications"])
        self.assertEqual(insufficient["allows_recommendations"], "only_data_requests")

    def test_unknown_report_mode_returns_safe_fallback(self):
        unknown = tone_for_report_mode("future_mode")

        self.assertEqual(label_report_mode("future_mode"), "Unknown readiness mode")
        self.assertEqual(unknown["tone"], "cautious")
        self.assertFalse(unknown["allows_strategic_implications"])
        self.assertEqual(unknown["allows_recommendations"], "diagnostic_only")

    def test_known_dimension_states_return_correct_permissions(self):
        ready = allowed_language_for_dimension_state("ready")
        self.assertEqual(label_dimension_state("ready"), "Ready")
        self.assertEqual(ready["language_level"], "editorial")
        self.assertTrue(ready["may_state_findings"])
        self.assertTrue(ready["may_infer_implications"])
        self.assertTrue(ready["may_recommend"])

        observation = allowed_language_for_dimension_state("observation_only")
        self.assertEqual(observation["language_level"], "observational")
        self.assertTrue(observation["may_state_findings"])
        self.assertEqual(observation["may_infer_implications"], "limited")
        self.assertEqual(observation["may_recommend"], "cautious")

        technical = allowed_language_for_dimension_state("technical_only")
        self.assertEqual(technical["language_level"], "technical")
        self.assertEqual(technical["may_state_findings"], "limited")
        self.assertFalse(technical["may_infer_implications"])
        self.assertEqual(technical["may_recommend"], "diagnostic_only")

        unavailable = allowed_language_for_dimension_state("not_evaluable")
        self.assertEqual(unavailable["language_level"], "unavailable")
        self.assertFalse(unavailable["may_state_findings"])
        self.assertFalse(unavailable["may_infer_implications"])
        self.assertEqual(unavailable["may_recommend"], "data_needed_only")

    def test_unknown_dimension_state_defaults_to_restrictive_permissions(self):
        unknown = tone_for_dimension_state("future_state")

        self.assertEqual(label_dimension_state("future_state"), "Unknown state")
        self.assertEqual(unknown["language_level"], "technical")
        self.assertFalse(unknown["may_state_findings"])
        self.assertFalse(unknown["may_infer_implications"])
        self.assertEqual(unknown["may_recommend"], "diagnostic_only")

    def test_weak_off_entity_and_fallback_cannot_support_editorial_claims(self):
        for evidence_type in ("weak", "off_entity", "fallback"):
            hint = evidence_language_hint(evidence_type)
            self.assertFalse(hint["can_support_editorial_claims"])
            self.assertFalse(hint["can_support_cautious_observations"])
            self.assertTrue(hint["can_support_diagnostic_notes"])

        self.assertEqual(
            evidence_language_hint("off_entity")["language"],
            "must not support claims",
        )
        self.assertEqual(
            evidence_language_hint("fallback")["language"],
            "not evidence, only technical explanation",
        )

    def test_direct_and_indirect_evidence_permissions_are_distinct(self):
        direct = evidence_language_hint("direct")
        indirect = evidence_language_hint("indirect")

        self.assertTrue(direct["can_support_editorial_claims"])
        self.assertTrue(indirect["can_support_cautious_observations"])
        self.assertFalse(indirect["can_support_editorial_claims"])


if __name__ == "__main__":
    unittest.main()
