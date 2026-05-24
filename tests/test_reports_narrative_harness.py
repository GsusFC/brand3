import unittest

from src.reports.narrative_harness import (
    audit_report_narrative_payload,
    audit_report_narrative_render,
)


def _payload(findings_by_dimension=None, *, synthesis=None, tension=None):
    return {
        "version": 1,
        "source": "report_narrative",
        "run_id": 42,
        "synthesis_prose": synthesis or "Owned documentation and external coverage share developer workflow language.",
        "tensions_prose": tension,
        "findings_by_dimension": findings_by_dimension or {},
    }


def _finding(
    observation,
    *,
    title="Evidence-bound finding",
    implication="This may indicate a surface pattern.",
    typical_decision="Teams may compare proof depth and message focus before choosing a direction.",
    evidence_urls=None,
):
    return {
        "title": title,
        "observation": observation,
        "implication": implication,
        "typical_decision": typical_decision,
        "evidence_urls": ["https://example.com/evidence"] if evidence_urls is None else evidence_urls,
    }


def _check(result, check_id):
    return next(check for check in result["checks"] if check["check_id"] == check_id)


class NarrativeHarnessTests(unittest.TestCase):
    def test_stable_output_shape(self):
        result = audit_report_narrative_payload(
            _payload(),
            base_dossier={"brand": {"name": "Example Brand"}},
        )

        self.assertEqual(result["version"], 1)
        self.assertIn(result["status"], {"pass", "warning", "error"})
        self.assertIn("summary", result)
        self.assertIn("checks", result)
        self.assertIn("metrics", result)
        self.assertIn("input_metadata", result)
        self.assertEqual(result["input_metadata"]["brand"], "Example Brand")
        self.assertEqual(result["input_metadata"]["payload_source"], "report_narrative")

    def test_repeated_openings_are_flagged(self):
        payload = _payload(
            {
                "presencia": [
                    _finding("The brand says \"Build faster\" on its homepage."),
                    _finding("The brand says \"Deploy faster\" in product copy."),
                    _finding("The brand says \"Ship faster\" in the developer page."),
                ]
            }
        )

        result = audit_report_narrative_payload(payload)

        check = _check(result, "repeated_sentence_openings")
        self.assertEqual(check["status"], "warning")
        self.assertGreaterEqual(len(check["evidence"]), 3)
        openings = {item["opening"] for item in check["evidence"]}
        self.assertTrue(any("the brand says" in opening for opening in openings))

    def test_generic_filler_is_counted(self):
        payload = _payload(
            {
                "coherencia": [
                    _finding(
                        "The source copy is coherent.",
                        implication="This suggests strong positioning and a compelling story.",
                    )
                ]
            }
        )

        result = audit_report_narrative_payload(payload)

        check = _check(result, "generic_strategic_filler")
        self.assertEqual(check["status"], "warning")
        self.assertEqual(result["metrics"]["generic_phrase_counts"]["strong positioning"], 1)
        self.assertEqual(result["metrics"]["generic_phrase_counts"]["compelling"], 1)

    def test_unsupported_prescriptions_are_flagged(self):
        payload = _payload(
            {
                "percepcion": [
                    _finding(
                        "A third-party listing repeats the category claim.",
                        typical_decision="The brand should prioritize external proof and must clarify the offer.",
                    )
                ]
            }
        )

        result = audit_report_narrative_payload(payload)

        check = _check(result, "unsupported_prescription_language")
        self.assertEqual(check["status"], "warning")
        phrases = {item["phrase"] for item in check["evidence"]}
        self.assertIn("the brand should", phrases)
        self.assertIn("must", phrases)

    def test_missing_evidence_urls_warns_without_error(self):
        payload = _payload(
            {
                "diferenciacion": [
                    _finding(
                        "The owned surface repeats the same category claim.",
                        evidence_urls=[],
                    )
                ]
            }
        )

        result = audit_report_narrative_payload(payload)

        check = _check(result, "missing_evidence_urls")
        self.assertEqual(check["status"], "warning")
        self.assertEqual(check["severity"], "warning")
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(result["metrics"]["findings_without_evidence_urls"], 1)

    def test_self_description_as_validation_is_flagged(self):
        payload = _payload(
            {
                "coherencia": [
                    _finding("The brand is the leading platform for modern teams.")
                ]
            }
        )

        result = audit_report_narrative_payload(payload)

        check = _check(result, "self_description_as_validation")
        self.assertEqual(check["status"], "warning")
        self.assertIn("the brand is", check["evidence"][0]["excerpt"].lower())

    def test_safe_attribution_overuse_warns_without_validation_error(self):
        payload = _payload(
            {
                "coherencia": [
                    _finding(
                        "The brand describes itself as an email-first operating system. "
                        "This is based only on self-description."
                    ),
                    _finding("The brand says \"Make email your most valuable channel\" on its homepage."),
                    _finding("The brand claims creators can grow their audience through email."),
                ]
            }
        )

        result = audit_report_narrative_payload(payload)

        check = _check(result, "safe_attribution_overuse")
        self.assertEqual(check["status"], "warning")
        self.assertEqual(check["severity"], "warning")
        self.assertEqual(result["metrics"]["safe_attribution_total"], 4)
        self.assertEqual(
            result["metrics"]["safe_attribution_phrase_counts"]["the brand describes itself"],
            1,
        )
        self.assertEqual(
            result["metrics"]["safe_attribution_phrase_counts"]["based only on self-description"],
            1,
        )
        validation_check = _check(result, "self_description_as_validation")
        self.assertEqual(validation_check["status"], "pass")

    def test_observation_family_flags_safe_attribution_repetition(self):
        payload = _payload(
            {
                "coherencia": [
                    _finding("The brand describes itself as a platform."),
                    _finding("The brand claims it improves workflows."),
                    _finding("This is based only on self-description."),
                ]
            }
        )

        result = audit_report_narrative_payload(payload)

        check = _check(result, "observation_repetition_families")
        self.assertEqual(check["status"], "warning")
        families = {item["family"] for item in check["evidence"]}
        self.assertIn("safe_attribution_repetition", families)
        self.assertEqual(
            result["metrics"]["observation_repetition_family_counts"][
                "safe_attribution_repetition"
            ]["total"],
            3,
        )

    def test_observation_family_flags_fallback_evidence_opening_repetition(self):
        payload = _payload(
            {
                "presencia": [
                    _finding("The available sources point in the same direction."),
                    _finding("Available evidence is limited but consistent."),
                    _finding("The evidence pool repeats the same surface signal."),
                ]
            }
        )

        result = audit_report_narrative_payload(payload)

        check = _check(result, "observation_repetition_families")
        self.assertEqual(check["status"], "warning")
        families = {item["family"] for item in check["evidence"]}
        self.assertIn("fallback_evidence_opening_repetition", families)

    def test_observation_family_flags_external_corroboration_caveat_repetition(self):
        payload = _payload(
            {
                "percepcion": [
                    _finding("The claim appears with no external corroboration."),
                    _finding("The surface repeats the claim without external corroboration."),
                    _finding("This is based only on self-description."),
                ]
            }
        )

        result = audit_report_narrative_payload(payload)

        check = _check(result, "observation_repetition_families")
        self.assertEqual(check["status"], "warning")
        families = {item["family"] for item in check["evidence"]}
        self.assertIn("external_corroboration_caveat_repetition", families)

    def test_synthesis_tension_mismatch_warns_when_both_exist(self):
        payload = _payload(
            synthesis="Homepage copy concentrates on developer workflow and deployment clarity.",
            tension="Pricing pages and support documentation introduce enterprise procurement uncertainty.",
        )

        result = audit_report_narrative_payload(payload)

        check = _check(result, "synthesis_tension_lexical_mismatch")
        self.assertEqual(check["status"], "warning")
        self.assertIn("overlap_ratio", check["evidence"][0]["excerpt"])

    def test_clean_payload_produces_no_errors(self):
        payload = _payload(
            {
                "presencia": [
                    _finding(
                        "The homepage copy quotes \"Ship faster\" beside developer workflow language.",
                        implication="That pattern may indicate a surface built around workflow clarity.",
                        typical_decision="Teams may compare proof depth, category focus, or audience specificity before choosing a direction.",
                    )
                ],
                "percepcion": [
                    _finding(
                        "External coverage describes developer workflow adoption using the same deployment language.",
                        implication="That repetition could support a cautious read of message continuity.",
                        typical_decision="Teams may compare owned proof, third-party proof, or narrower category language before choosing a direction.",
                    )
                ],
            },
            synthesis=(
                "Owned documentation and external coverage both concentrate on developer workflow clarity. "
                "The repeated deployment language may support a cautious read of message continuity."
            ),
            tension=(
                "Owned documentation and external coverage share developer workflow language, while proof depth "
                "remains the main trade-off."
            ),
        )

        result = audit_report_narrative_payload(payload)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(result["summary"]["warnings"], 0)
        self.assertEqual(result["metrics"]["safe_attribution_total"], 0)
        self.assertEqual(result["metrics"]["safe_attribution_phrase_counts"], {})

    def test_render_aware_diagnostic_distinguishes_payload_and_visible_risk(self):
        decision = (
            "Teams in this position typically choose between broadening the platform, "
            "doubling down on the niche, or waiting for more market feedback."
        )
        payload = _payload(
            {
                "coherencia": [
                    _finding(
                        "The brand describes itself as an email-first operating system. "
                        "This is based only on self-description.",
                        typical_decision=decision,
                    )
                ]
            }
        )
        rendered_html = """
        <html><body>
          <section class="dimension">
            <h4>Email-first OS</h4>
            <p class="finding-primary">
              The brand describes itself as an email-first operating system.
              This is based only on self-description.
            </p>
            <ul class="chips"><li><a href="https://example.com/evidence">example.com/evidence</a></li></ul>
          </section>
        </body></html>
        """

        result = audit_report_narrative_render(payload, rendered_html)

        self.assertEqual(result["version"], 1)
        self.assertIn("payload_metrics", result)
        self.assertIn("visible_render_metrics", result)
        self.assertEqual(
            result["payload_metrics"]["generic_phrase_counts"]["teams in this position typically"],
            1,
        )
        self.assertEqual(
            result["visible_render_metrics"]["visible_teams_in_this_position_typically_count"],
            0,
        )
        suppressed = result["suppressed_by_rendering"]
        self.assertTrue(
            any(
                item.get("phrase") == "teams in this position typically"
                and item.get("suppressed_count") == 1
                for item in suppressed
            )
        )
        self.assertEqual(result["visible_render_metrics"]["visible_link_count"], 1)
        self.assertEqual(result["visible_render_metrics"]["visible_evidence_chip_link_count"], 1)

    def test_render_aware_diagnostic_flags_still_visible_safe_attribution(self):
        payload = _payload(
            {
                "coherencia": [
                    _finding("The brand describes itself as a platform."),
                    _finding("This is based only on self-description."),
                    _finding("The brand claims faster workflows."),
                ]
            }
        )
        rendered_text = (
            "The brand describes itself as a platform. "
            "This is based only on self-description. "
            "The brand claims faster workflows."
        )

        result = audit_report_narrative_render(
            payload,
            rendered_text,
            rendered_as_html=False,
        )

        risks = result["still_visible_risks"]
        self.assertTrue(
            any(item["risk"] == "visible_safe_attribution_overuse" for item in risks)
        )
        self.assertEqual(result["visible_render_metrics"]["safe_attribution_total"], 3)
        self.assertEqual(
            result["visible_render_metrics"]["observation_repetition_family_counts"][
                "safe_attribution_repetition"
            ]["total"],
            3,
        )


if __name__ == "__main__":
    unittest.main()
