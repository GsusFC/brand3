import unittest

from src.reports.entity_narrative_state import build_entity_narrative_state


def _finding(
    observation,
    *,
    implication="This may indicate a measured surface pattern.",
    typical_decision="Teams may compare proof depth before choosing a direction.",
    evidence_urls=None,
):
    return {
        "title": "Evidence-bound finding",
        "observation": observation,
        "implication": implication,
        "typical_decision": typical_decision,
        "evidence_urls": ["https://example.com/evidence"] if evidence_urls is None else evidence_urls,
    }


def _payload(findings_by_dimension=None, *, tension=None):
    return {
        "version": 1,
        "source": "report_narrative",
        "run_id": 42,
        "synthesis_prose": "The evidence describes a stable developer workflow surface.",
        "tensions_prose": tension,
        "findings_by_dimension": findings_by_dimension or {},
    }


def _payload_diagnostic(
    *,
    findings_count=1,
    findings_without_evidence_urls=0,
    safe_attribution_total=0,
    safe_attribution_phrase_counts=None,
    sentence_opening_counts=None,
    generic_phrase_counts=None,
    observation_families=None,
):
    return {
        "version": 1,
        "status": "warning" if safe_attribution_total else "pass",
        "metrics": {
            "findings_count": findings_count,
            "findings_without_evidence_urls": findings_without_evidence_urls,
            "safe_attribution_total": safe_attribution_total,
            "safe_attribution_phrase_counts": safe_attribution_phrase_counts or {},
            "sentence_opening_counts": sentence_opening_counts or {},
            "generic_phrase_counts": generic_phrase_counts or {},
            "observation_repetition_family_counts": observation_families or {},
        },
        "input_metadata": {
            "brand": "Example",
            "run_id": 42,
        },
    }


def _render_diagnostic(
    *,
    visible_evidence_links=1,
    visible_decision_space_count=0,
    visible_openings=None,
    observation_families=None,
):
    return {
        "version": 1,
        "status": "warning",
        "visible_render_metrics": {
            "visible_evidence_chip_link_count": visible_evidence_links,
            "visible_decision_space_count": visible_decision_space_count,
            "repeated_sentence_opening_counts": visible_openings or {},
            "observation_repetition_family_counts": observation_families or {},
        },
    }


class EntityNarrativeStateTests(unittest.TestCase):
    def test_stable_output_shape(self):
        result = build_entity_narrative_state(
            _payload({"presencia": [_finding("External coverage repeats workflow language.")]}),
            payload_diagnostic=_payload_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            snapshot={"brand": {"name": "Example", "url": "https://example.com"}, "source": "test"},
        )

        self.assertEqual(result["version"], "entity_narrative_state.v0")
        self.assertIn("status", result)
        self.assertIn("metadata", result)
        self.assertIn("inputs", result)
        self.assertIn("state", result)
        self.assertIn("derivation", result)
        self.assertIn("limitations", result)
        self.assertTrue(result["status"]["offline_only"])
        self.assertFalse(result["status"]["runtime_enabled"])
        self.assertFalse(result["status"]["used_by_scoring"])
        self.assertFalse(result["status"]["used_by_prompts"])
        self.assertFalse(result["status"]["used_by_rendering"])

    def test_no_strategic_claims_are_invented(self):
        result = build_entity_narrative_state(
            _payload({"coherencia": [_finding("The evidence pool repeats category language.")]}),
            payload_diagnostic=_payload_diagnostic(
                observation_families={
                    "external_corroboration_caveat_repetition": {
                        "total": 4,
                        "phrases": {"no external corroboration": 4},
                    }
                }
            ),
            render_diagnostic=_render_diagnostic(),
        )

        state = result["state"]
        self.assertNotIn("brand_archetype", state)
        self.assertNotIn("market_position_intent", state)
        self.assertEqual(state["contradiction_candidates"], [])
        self.assertNotIn("primary_tension", state)

    def test_good_evidence_case_does_not_force_false_tension(self):
        result = build_entity_narrative_state(
            _payload({"presencia": [_finding("Third-party coverage repeats launch language.")]}),
            payload_diagnostic=_payload_diagnostic(
                findings_count=14,
                findings_without_evidence_urls=6,
                safe_attribution_total=8,
                safe_attribution_phrase_counts={"based only on self-description": 8},
                observation_families={
                    "external_corroboration_caveat_repetition": {
                        "total": 8,
                        "phrases": {"no external corroboration": 8},
                    }
                },
            ),
            render_diagnostic=_render_diagnostic(visible_evidence_links=13),
            snapshot={
                "brand_name": "LaunchDarkly",
                "url": "https://launchdarkly.com",
                "evidence_total": 28,
                "owned_evidence_total": 23,
                "third_party_evidence_total": 15,
            },
        )

        self.assertEqual(result["metadata"]["brand"], "LaunchDarkly")
        self.assertEqual(result["state"]["evidence_url_coverage"]["coverage_level"], "mixed")
        self.assertEqual(result["state"]["owned_claim_density"]["level"], "high")
        self.assertNotIn("primary_tension", result["state"])

    def test_explicit_observed_related_surfaces_are_copied_through(self):
        result = build_entity_narrative_state(
            _payload(
                {
                    "presencia": [
                        _finding(
                            "External surfaces repeat adjacent product language.",
                            evidence_urls=[
                                "https://watermelon.ai",
                                "https://developer.watermelon.ai/docs",
                                "https://producthunt.com/products/watermelon",
                            ],
                        )
                    ]
                }
            ),
            payload_diagnostic=_payload_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            snapshot={
                "brand_name": "Watermelon",
                "url": "https://watermelon.sh",
                "observed_related_surfaces": [
                    {
                        "surface": "watermelon.ai",
                        "relation_type": "adjacent_domain",
                        "evidence": ["manual review"],
                        "confidence": "medium",
                        "requires_human_review": True,
                        "source": "manual_review",
                    },
                    {
                        "surface": "developer.watermelon.ai",
                        "relation_type": "developer_surface",
                        "evidence": ["manual review"],
                        "confidence": "medium",
                        "requires_human_review": True,
                        "source": "manual_review",
                    },
                ],
            },
        )

        aliases = result["state"]["entity_aliases"]
        self.assertEqual(aliases["primary"], "watermelon.sh")
        surfaces = aliases["observed_related_surfaces"]
        self.assertEqual([item["surface"] for item in surfaces], ["watermelon.ai", "developer.watermelon.ai"])
        self.assertEqual(surfaces[0]["relation_type"], "adjacent_domain")
        self.assertEqual(surfaces[0]["confidence"], "medium")
        self.assertEqual(surfaces[0]["source"], "manual_review")
        self.assertTrue(surfaces[0]["requires_human_review"])
        self.assertTrue(aliases["needs_review"])

    def test_arbitrary_evidence_urls_are_ignored_as_related_surfaces(self):
        result = build_entity_narrative_state(
            _payload(
                {
                    "presencia": [
                        _finding(
                            "External evidence appears on adjacent URLs.",
                            evidence_urls=[
                                "https://watermelon.ai",
                                "https://developer.watermelon.ai/docs",
                                "https://producthunt.com/products/watermelon",
                            ],
                        )
                    ]
                }
            ),
            payload_diagnostic=_payload_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            snapshot={
                "brand_name": "Watermelon",
                "url": "https://watermelon.sh",
            },
        )

        aliases = result["state"]["entity_aliases"]
        self.assertEqual(aliases["observed_related_surfaces"], [])
        self.assertFalse(aliases["needs_review"])

    def test_name_similarity_alone_is_ignored(self):
        result = build_entity_narrative_state(
            _payload({"presencia": [_finding("The evidence mentions similar names.")]}),
            payload_diagnostic=_payload_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            snapshot={
                "brand_name": "Watermelon",
                "url": "https://watermelon.sh",
                "related_domains": ["watermelon.ai", "watermelon.co"],
                "discovered_domains": ["developer.watermelon.ai"],
            },
        )

        aliases = result["state"]["entity_aliases"]
        self.assertEqual(aliases["observed_related_surfaces"], [])
        self.assertFalse(aliases["needs_review"])

    def test_requires_human_review_surface_sets_needs_review_true(self):
        result = build_entity_narrative_state(
            _payload({"presencia": [_finding("Manual review identifies an adjacent surface.")]}),
            payload_diagnostic=_payload_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            snapshot={
                "brand_name": "Watermelon",
                "url": "https://watermelon.sh",
                "observed_related_surfaces": [
                    {
                        "surface": "developer.watermelon.ai",
                        "relation_type": "developer_surface",
                        "evidence": ["manual review"],
                        "confidence": "medium",
                        "requires_human_review": True,
                        "source": "manual_review",
                    }
                ],
            },
        )

        self.assertTrue(result["state"]["entity_aliases"]["needs_review"])

    def test_related_surfaces_do_not_create_contradiction_candidates(self):
        result = build_entity_narrative_state(
            _payload({"presencia": [_finding("Manual review identifies an adjacent surface.")]}),
            payload_diagnostic=_payload_diagnostic(),
            render_diagnostic=_render_diagnostic(),
            snapshot={
                "brand_name": "Watermelon",
                "url": "https://watermelon.sh",
                "observed_related_surfaces": [
                    {
                        "surface": "watermelon.ai",
                        "relation_type": "adjacent_domain",
                        "evidence": ["manual review"],
                        "confidence": "medium",
                        "requires_human_review": True,
                        "source": "manual_review",
                    }
                ],
            },
        )

        self.assertEqual(result["state"]["contradiction_candidates"], [])

    def test_missing_evidence_urls_are_coverage_metrics_not_failures(self):
        result = build_entity_narrative_state(
            _payload(
                {
                    "coherencia": [
                        _finding("Owned copy repeats a claim.", evidence_urls=[]),
                        _finding("External copy repeats a claim."),
                    ]
                }
            ),
            payload_diagnostic=_payload_diagnostic(
                findings_count=2,
                findings_without_evidence_urls=1,
            ),
            render_diagnostic=_render_diagnostic(visible_evidence_links=1),
        )

        coverage = result["state"]["evidence_url_coverage"]
        self.assertEqual(coverage["findings_without_evidence_urls"], 1)
        self.assertEqual(coverage["coverage_level"], "mixed")
        self.assertNotEqual(result["status"].get("runtime_enabled"), True)
        self.assertIn("evidence_url_coverage", [item["finding_id"] for item in result["state"]["compression_candidates"]])

    def test_inactive_budgets_remain_inactive_or_absent(self):
        result = build_entity_narrative_state(
            _payload({"presencia": [_finding("External coverage repeats workflow language.")]}),
            payload_diagnostic=_payload_diagnostic(),
            render_diagnostic=_render_diagnostic(),
        )

        self.assertEqual(result["state"]["owned_claim_density"]["level"], "inactive")
        self.assertEqual(result["state"]["fallback_language_budget"]["mode"], "inactive")
        self.assertNotIn("attribution_budget", result["state"])
        self.assertNotIn("corroboration_caveat_budget", result["state"])

    def test_review_gated_fields_are_not_promoted_to_facts(self):
        result = build_entity_narrative_state(
            _payload(
                {"presencia": [_finding("Owned copy and third-party coverage point in different directions.")]},
                tension="Owned copy emphasizes workflow clarity while external coverage emphasizes procurement risk.",
            ),
            payload_diagnostic=_payload_diagnostic(),
            render_diagnostic=_render_diagnostic(),
        )

        tension = result["state"]["primary_tension"]
        self.assertEqual(tension["source"], "payload_tension")
        self.assertEqual(tension["confidence"], "low")
        self.assertTrue(tension["requires_human_review"])
        self.assertEqual(result["state"]["contradiction_candidates"], [])

    def test_decision_space_suppression_remains_advisory(self):
        result = build_entity_narrative_state(
            _payload({"presencia": [_finding("Owned copy repeats workflow language.")]}),
            payload_diagnostic=_payload_diagnostic(
                generic_phrase_counts={"teams in this position typically": 9}
            ),
            render_diagnostic=_render_diagnostic(visible_decision_space_count=0),
        )

        mode = result["state"]["decision_space_mode"]
        self.assertEqual(mode["mode"], "hidden_generic")
        self.assertTrue(mode["render_suppression_observed"])
        self.assertTrue(mode["advisory_only"])
        self.assertFalse(result["status"]["used_by_rendering"])


if __name__ == "__main__":
    unittest.main()
