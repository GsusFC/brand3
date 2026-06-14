import unittest
from copy import deepcopy
from unittest.mock import MagicMock

from src.reports.dossier import (
    REPORT_NARRATIVE_SOURCE,
    build_brand_dossier,
    build_report_narrative_payload,
)
from tests.test_reports_renderer import _sample_snapshot


class BrandDossierTests(unittest.TestCase):
    def test_build_brand_dossier_applies_narrative_overlays(self):
        analyzer = MagicMock()
        synthesis_prompts: list[str] = []

        def _call(system: str, user: str, max_tokens: int = 1200):
            synthesis_prompts.append(user)
            return "Narrative synthesis for the report."

        analyzer._call.side_effect = _call

        def _call_json(system: str, user: str, max_tokens: int = 2000):
            if '"tension"' in user:
                return {"tension": "One meaningful tension."}
            return {"findings": [{"title": "f", "prose": "p", "evidence_urls": []}]}

        analyzer._call_json.side_effect = _call_json

        dossier = build_brand_dossier(_sample_snapshot(), analyzer=analyzer)

        self.assertEqual(dossier["synthesis_prose"], "Narrative synthesis for the report.")
        self.assertEqual(dossier["summary"], "Narrative synthesis for the report.")
        self.assertEqual(dossier["tensions_prose"], "One meaningful tension.")
        self.assertEqual(len(synthesis_prompts), 1)
        self.assertIn("One meaningful tension.", synthesis_prompts[0])
        self.assertIn("evaluation", dossier)
        self.assertIn("narrative", dossier)
        self.assertIn("sources", dossier)
        self.assertIn("audit", dossier)
        self.assertIn("ui", dossier)
        self.assertEqual(dossier["evaluation"]["composite_display"], "74")
        self.assertEqual(dossier["narrative"]["summary"], "Narrative synthesis for the report.")
        self.assertEqual(len(dossier["dimensions"]), 5)
        self.assertTrue(all("findings" in dim for dim in dossier["dimensions"]))

    def test_perceptual_narrative_experiment_preserves_scores_and_structure(self):
        snapshot = _sample_snapshot()

        def _analyzer() -> MagicMock:
            analyzer = MagicMock()
            analyzer._call.return_value = "Narrative synthesis for the report."
            analyzer._call_json.side_effect = lambda system, user, max_tokens=2000: (
                {"tension": "One meaningful tension."}
                if '"tension"' in user
                else {"findings": [{"title": "f", "prose": "p", "evidence_urls": []}]}
            )
            return analyzer

        base = build_brand_dossier(snapshot, analyzer=_analyzer())
        experimental = build_brand_dossier(
            snapshot,
            analyzer=_analyzer(),
            enable_perceptual_narrative=True,
        )

        self.assertEqual(experimental["evaluation"], base["evaluation"])
        self.assertEqual(experimental["score"], base["score"])
        self.assertEqual(
            experimental["evaluation"]["band_letter"],
            base["evaluation"]["band_letter"],
        )
        self.assertEqual(set(experimental.keys()), set(base.keys()))
        self.assertEqual(len(experimental["dimensions"]), len(base["dimensions"]))

    def test_perceptual_narrative_experiment_is_off_by_default(self):
        prompts: list[str] = []
        analyzer = MagicMock()
        analyzer._call.return_value = "Narrative synthesis for the report."

        def _call_json(system: str, user: str, max_tokens: int = 2000):
            prompts.append(user)
            if '"tension"' in user:
                return {"tension": "One meaningful tension."}
            return {"findings": [{"title": "f", "prose": "p", "evidence_urls": []}]}

        analyzer._call_json.side_effect = _call_json

        build_brand_dossier(_sample_snapshot(), analyzer=analyzer)

        self.assertTrue(prompts)
        self.assertFalse(
            any("EXPERIMENTAL PERCEPTUAL NARRATIVE HINTS" in prompt for prompt in prompts)
        )

    def test_build_report_narrative_payload_serializes_rich_narrative(self):
        analyzer = MagicMock()
        analyzer._call.return_value = "Persisted synthesis."
        analyzer._call_json.side_effect = lambda system, user, max_tokens=2000: (
            {"tension": "Persisted tension."}
            if '"tension"' in user
            else {
                "findings": [
                    {
                        "title": "Persisted finding",
                        "observation": "Observed surface signal.",
                        "implication": "May indicate a pattern.",
                        "evidence_urls": [],
                    }
                ]
            }
        )

        payload = build_report_narrative_payload(_sample_snapshot(), analyzer=analyzer)

        self.assertEqual(payload["source"], REPORT_NARRATIVE_SOURCE)
        self.assertEqual(payload["synthesis_prose"], "Persisted synthesis.")
        self.assertEqual(payload["tensions_prose"], "Persisted tension.")
        self.assertIn("coherencia", payload["findings_by_dimension"])
        self.assertEqual(
            payload["findings_by_dimension"]["coherencia"][0]["title"],
            "Persisted finding",
        )
        self.assertEqual(
            payload["findings_by_dimension"]["coherencia"][0]["typical_decision"],
            "",
        )

    def test_build_report_narrative_payload_reuses_analyst_pass_without_llm(self):
        analyzer = MagicMock()
        analyzer._call.side_effect = AssertionError("analyst payload should avoid synthesis LLM")
        analyzer._call_json.side_effect = AssertionError("analyst payload should avoid findings LLM")
        analyst_pass = {
            "executive_summary": "Analyst executive summary.",
            "primary_risk": "Evidence is concentrated in owned surfaces.",
            "primary_opportunity": "External proof could clarify differentiation.",
            "dimensions": {
                "coherencia": {
                    "diagnosis": "Coherence diagnosis.",
                    "findings": ["Owned messaging repeats one claim."],
                    "evidence": ["Homepage repeats the positioning line."],
                    "recommendation": "Connect the claim to proof.",
                    "limitations": ["Limited third-party evidence."],
                }
            },
        }

        payload = build_report_narrative_payload(
            _sample_snapshot(),
            analyzer=analyzer,
            analyst_pass=analyst_pass,
        )

        self.assertEqual(payload["source"], REPORT_NARRATIVE_SOURCE)
        self.assertEqual(payload["synthesis_prose"], "Analyst executive summary.")
        self.assertIn("Primary risk:", payload["tensions_prose"])
        self.assertIn("coherencia", payload["findings_by_dimension"])
        finding = payload["findings_by_dimension"]["coherencia"][0]
        self.assertEqual(finding["title"], "Coherence diagnosis.")
        self.assertEqual(finding["observation"], "Owned messaging repeats one claim.")
        self.assertIn("Connect the claim to proof.", finding["implication"])

    def test_build_report_narrative_payload_falls_back_when_analyst_pass_has_error(self):
        analyzer = MagicMock()
        analyzer._call.return_value = "Fallback synthesis."
        analyzer._call_json.side_effect = lambda system, user, max_tokens=2000: (
            {"tension": "Fallback tension."}
            if '"tension"' in user
            else {
                "findings": [
                    {
                        "title": "Fallback finding",
                        "observation": "Fallback observation.",
                        "implication": "Fallback implication.",
                        "evidence_urls": [],
                    }
                ]
            }
        )

        payload = build_report_narrative_payload(
            _sample_snapshot(),
            analyzer=analyzer,
            analyst_pass={"analysis_error": {"reason": "llm_error"}},
        )

        self.assertEqual(payload["synthesis_prose"], "Fallback synthesis.")
        self.assertEqual(payload["tensions_prose"], "Fallback tension.")
        self.assertIn("coherencia", payload["findings_by_dimension"])
        self.assertTrue(analyzer._call.called)
        self.assertTrue(analyzer._call_json.called)

    def test_build_brand_dossier_prefers_persisted_narrative_without_llm(self):
        snapshot = deepcopy(_sample_snapshot())
        snapshot.setdefault("raw_inputs", []).append(
            {
                "source": REPORT_NARRATIVE_SOURCE,
                "created_at": "2026-05-15T00:00:00",
                "payload": {
                    "version": 1,
                    "source": REPORT_NARRATIVE_SOURCE,
                    "synthesis_prose": "Stored narrative synthesis.",
                    "tensions_prose": "Stored narrative tension.",
                    "findings_by_dimension": {
                        "presencia": [
                            {
                                "title": "Stored finding",
                                "observation": "Stored observation.",
                                "implication": "Stored implication.",
                                "typical_decision": "Stored decision space.",
                                "evidence_urls": [],
                            }
                        ]
                    },
                },
            }
        )
        analyzer = MagicMock()
        analyzer._call.side_effect = AssertionError("persisted narrative should avoid LLM")
        analyzer._call_json.side_effect = AssertionError("persisted narrative should avoid LLM")

        dossier = build_brand_dossier(snapshot, analyzer=analyzer)

        self.assertEqual(dossier["synthesis_prose"], "Stored narrative synthesis.")
        self.assertEqual(dossier["tensions_prose"], "Stored narrative tension.")
        presencia = next(dim for dim in dossier["dimensions"] if dim["name"] == "presencia")
        self.assertEqual(presencia["findings"][0].title, "Stored finding")
        self.assertEqual(presencia["findings"][0].typical_decision, "Stored decision space.")
        self.assertEqual(presencia["findings"][0].prose, "Stored observation. Stored implication.")

    def test_build_brand_dossier_with_real_packet_does_not_crash(self):
        snapshot = _sample_snapshot()
        analyzer = MagicMock()
        analyzer._call.return_value = "synthesis prose"
        analyzer._call_json.side_effect = lambda system, user, max_tokens=2000: (
            {"tension": "One meaningful tension."}
            if '"tension"' in user
            else {"findings": [{"title": "f", "observation": "o", "implication": "i", "typical_decision": "d", "evidence_urls": []}]}
        )
        dossier = build_brand_dossier(snapshot, analyzer=analyzer)
        self.assertIsNotNone(dossier)
        self.assertEqual(len(dossier["dimensions"]), 5)


if __name__ == "__main__":
    unittest.main()
