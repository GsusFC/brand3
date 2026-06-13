import unittest

from src.sv9.evaluator import (
    evaluate_component,
    evaluate_coherencia,
    evaluate_snapshot_components,
)
from src.sv9.models import (
    STATUS_NOT_DETECTED,
    STATUS_NOT_EVALUATED,
    STATUS_SCORED,
)
from src.sv9.rubric import COMPONENTS


def tldr_block(content: str, *, detected: bool = True, evidence: list[str] | None = None) -> dict:
    return {
        "content": content if detected else None,
        "detected": detected,
        "mode": "literal" if detected else "not_detected",
        "confidence": "high" if detected else "insufficient",
        "evidence": evidence if detected else [],
        "rationale": "test block",
    }


def full_tldr() -> dict:
    return {
        key: tldr_block(f"{key} detected text", evidence=[f"{key} quote"])
        for key in [
            "core_purpose",
            "magnetism",
            "value_proposition",
            "personality",
            "brand_idea",
            "attributes",
            "values",
            "mission",
            "vision",
        ]
    }


class FakeLLM:
    """Returns canned per-rung verdicts; records prompts for assertions."""

    def __init__(self, pass_up_to: int = 3, *, omit_rungs: bool = False, fail_call: bool = False):
        self.api_key = "test-key"
        self.pass_up_to = pass_up_to
        self.omit_rungs = omit_rungs
        self.fail_call = fail_call
        self.calls: list[dict] = []
        self.last_failure_reason = "llm_error"

    def _call_json(self, system, user, max_tokens=8000, *, json_schema=None, schema_name=None, timeout_seconds=None, strict_schema=True):
        self.calls.append({"system": system, "user": user, "schema_name": schema_name})
        if self.fail_call:
            return {}
        scale = 5 if any(f"sv9_ladder_{k}" == schema_name for k in ("mission", "vision", "values", "attributes")) else 10
        last_rung = scale - 1 if self.omit_rungs else scale
        return {
            "verdicts": [
                {
                    "rung": rung,
                    "passed": rung <= self.pass_up_to,
                    "evidence": f"quote {rung}" if rung <= self.pass_up_to else "",
                    "reasoning": "test",
                }
                for rung in range(1, last_rung + 1)
            ]
        }


class EvaluateComponentTests(unittest.TestCase):
    def test_not_detected_scores_zero_without_llm_call(self):
        llm = FakeLLM()
        tldr = full_tldr()
        tldr["mission"] = tldr_block("", detected=False)
        result = evaluate_component("mission", tldr=tldr, signals=[], brand_name="Acme", url="u", llm=llm)
        self.assertEqual(result.status, STATUS_NOT_DETECTED)
        self.assertEqual(result.score, 0)
        self.assertEqual(llm.calls, [])

    def test_detected_component_scores_consecutive_rungs(self):
        llm = FakeLLM(pass_up_to=4)
        result = evaluate_component(
            "personality", tldr=full_tldr(), signals=[], brand_name="Acme", url="u", llm=llm
        )
        self.assertEqual(result.status, STATUS_SCORED)
        self.assertEqual(result.score, 4)
        self.assertEqual(len(result.rung_profile), 10)

    def test_missing_llm_marks_not_evaluated(self):
        result = evaluate_component(
            "mission", tldr=full_tldr(), signals=[], brand_name="Acme", url="u", llm=None
        )
        self.assertEqual(result.status, STATUS_NOT_EVALUATED)
        self.assertEqual(result.error, "llm_unavailable")

    def test_failed_llm_call_marks_not_evaluated_and_keeps_detection(self):
        llm = FakeLLM(fail_call=True)
        result = evaluate_component(
            "mission", tldr=full_tldr(), signals=[], brand_name="Acme", url="u", llm=llm
        )
        self.assertEqual(result.status, STATUS_NOT_EVALUATED)
        self.assertEqual(result.detected_content, "mission detected text")
        self.assertTrue(result.error)

    def test_incomplete_rung_coverage_marks_not_evaluated(self):
        llm = FakeLLM(omit_rungs=True)
        result = evaluate_component(
            "mission", tldr=full_tldr(), signals=[], brand_name="Acme", url="u", llm=llm
        )
        self.assertEqual(result.status, STATUS_NOT_EVALUATED)

    def test_not_evaluable_rungs_are_recorded_but_score_unchanged(self):
        class ChannelGapLLM(FakeLLM):
            def _call_json(self, system, user, max_tokens=8000, **kwargs):
                self.calls.append({"user": user})
                # Rung 1 fails for lack of an evidence channel; 2-3 pass.
                return {
                    "verdicts": [
                        {"rung": 1, "passed": False, "evaluable": False, "evidence": "", "reasoning": "no visual channel"},
                        {"rung": 2, "passed": True, "evaluable": True, "evidence": "q", "reasoning": ""},
                        {"rung": 3, "passed": True, "evaluable": True, "evidence": "q", "reasoning": ""},
                        {"rung": 4, "passed": False, "evaluable": True, "evidence": "", "reasoning": "evidence against"},
                        {"rung": 5, "passed": False, "evaluable": True, "evidence": "", "reasoning": ""},
                    ]
                }

        result = evaluate_component(
            "mission", tldr=full_tldr(), signals=[], brand_name="Acme", url="u", llm=ChannelGapLLM()
        )
        self.assertEqual(result.status, STATUS_SCORED)
        # Tile scoring: the unjudgeable tile 1 neither scores nor truncates
        # the two tiles genuinely earned above it.
        self.assertEqual(result.score, 2)
        self.assertEqual(result.not_evaluable_rungs, [1])
        self.assertEqual(result.non_monotonic_rungs, [2, 3])

    def test_passed_rung_is_evaluable_by_definition(self):
        class ContradictoryLLM(FakeLLM):
            def _call_json(self, system, user, max_tokens=8000, **kwargs):
                self.calls.append({"user": user})
                return {
                    "verdicts": [
                        {"rung": r, "passed": True, "evaluable": False, "evidence": "q", "reasoning": ""}
                        for r in range(1, 6)
                    ]
                }

        result = evaluate_component(
            "mission", tldr=full_tldr(), signals=[], brand_name="Acme", url="u", llm=ContradictoryLLM()
        )
        self.assertEqual(result.score, 5)
        self.assertEqual(result.not_evaluable_rungs, [])

    def test_pass_without_evidence_is_demoted(self):
        class NoQuoteLLM(FakeLLM):
            def _call_json(self, system, user, max_tokens=8000, **kwargs):
                self.calls.append({"user": user})
                return {
                    "verdicts": [
                        {"rung": r, "passed": True, "evidence": "", "reasoning": "confident"}
                        for r in range(1, 6)
                    ]
                }

        result = evaluate_component(
            "mission", tldr=full_tldr(), signals=[], brand_name="Acme", url="u", llm=NoQuoteLLM()
        )
        self.assertEqual(result.status, STATUS_SCORED)
        self.assertEqual(result.score, 0)
        self.assertTrue(all(not v.passed for v in result.rung_profile))

    def test_relational_context_carries_facts_not_judgments(self):
        llm = FakeLLM()
        tldr = full_tldr()
        evaluate_component("vision", tldr=tldr, signals=[], brand_name="Acme", url="u", llm=llm)
        prompt = llm.calls[0]["user"]
        self.assertIn("mission detected text", prompt)
        self.assertNotIn("score", prompt.split("LADDER")[0].lower())

    def test_missing_upstream_component_shows_as_not_detected_in_context(self):
        llm = FakeLLM()
        tldr = full_tldr()
        tldr["mission"] = tldr_block("", detected=False)
        evaluate_component("vision", tldr=tldr, signals=[], brand_name="Acme", url="u", llm=llm)
        self.assertIn("(no detectado)", llm.calls[0]["user"])


class BrandIdeaSignalEvaluationTests(unittest.TestCase):
    def test_brand_idea_evaluates_from_visual_signals_without_detection(self):
        llm = FakeLLM(pass_up_to=3)
        tldr = full_tldr()
        tldr["brand_idea"] = tldr_block("", detected=False)
        signals = [
            {
                "feature": "vision_observations",
                "legacy_dimension": "sv9_vision_pass",
                "value": "professional-generic",
                "confidence": "high",
                "source": "vision_llm",
                "detail": '{"logo_detected": true, "dominant_colors": ["#101010"]}',
            }
        ]
        result = evaluate_component(
            "brand_idea", tldr=tldr, signals=signals, brand_name="Acme", url="u", llm=llm
        )
        self.assertEqual(result.status, STATUS_SCORED)
        self.assertEqual(result.score, 3)
        prompt = llm.calls[0]["user"]
        self.assertIn("(no detectado)", prompt)
        self.assertIn("logo_detected", prompt)

    def test_brand_idea_without_detection_or_signals_stays_not_detected(self):
        llm = FakeLLM()
        tldr = full_tldr()
        tldr["brand_idea"] = tldr_block("", detected=False)
        result = evaluate_component(
            "brand_idea", tldr=tldr, signals=[], brand_name="Acme", url="u", llm=llm
        )
        self.assertEqual(result.status, STATUS_NOT_DETECTED)
        self.assertEqual(llm.calls, [])

    def test_other_components_do_not_evaluate_on_signals_alone(self):
        llm = FakeLLM()
        tldr = full_tldr()
        tldr["mission"] = tldr_block("", detected=False)
        result = evaluate_component(
            "mission",
            tldr=tldr,
            signals=[{"feature": "x", "legacy_dimension": "y", "value": 1, "confidence": 1, "source": "s"}],
            brand_name="Acme",
            url="u",
            llm=llm,
        )
        self.assertEqual(result.status, STATUS_NOT_DETECTED)


class EvaluateCoherenciaTests(unittest.TestCase):
    def test_coherencia_runs_with_holes_and_sees_both_axes(self):
        llm = FakeLLM(pass_up_to=2)
        tldr = full_tldr()
        tldr["values"] = tldr_block("", detected=False)
        components = {
            key: evaluate_component(key, tldr=tldr, signals=[], brand_name="Acme", url="u", llm=llm)
            for key in COMPONENTS
            if key != "coherencia"
        }
        signals = [
            {"feature": "messaging_consistency", "legacy_dimension": "coherencia", "value": 62.0, "confidence": 0.8, "source": "llm_analysis"}
        ]
        result = evaluate_coherencia(
            components=components, tldr=tldr, signals=signals, brand_name="Acme", url="u", llm=llm
        )
        self.assertEqual(result.status, STATUS_SCORED)
        self.assertEqual(result.score, 2)
        prompt = llm.calls[-1]["user"]
        self.assertIn("(no detectado)", prompt)  # holes are coherence information
        self.assertIn("messaging_consistency", prompt)  # external axis present

    def test_coherencia_without_llm_is_not_evaluated(self):
        result = evaluate_coherencia(
            components={}, tldr=full_tldr(), signals=[], brand_name="Acme", url="u", llm=None
        )
        self.assertEqual(result.status, STATUS_NOT_EVALUATED)


class EvaluateSnapshotComponentsTests(unittest.TestCase):
    def test_full_pass_yields_ten_components(self):
        llm = FakeLLM(pass_up_to=3)
        results = evaluate_snapshot_components(
            tldr=full_tldr(), signals={}, brand_name="Acme", url="u", llm=llm
        )
        self.assertEqual(set(results), set(COMPONENTS))
        for key, component in results.items():
            self.assertEqual(component.status, STATUS_SCORED, key)
        self.assertEqual(results["mission"].score, 3)
        self.assertEqual(results["coherencia"].score, 3)

    def test_one_component_failure_does_not_compromise_the_rest(self):
        class FlakyLLM(FakeLLM):
            def _call_json(self, system, user, max_tokens=8000, *, schema_name=None, **kwargs):
                if schema_name == "sv9_ladder_personality":
                    self.calls.append({"schema_name": schema_name})
                    return {}
                return super()._call_json(system, user, max_tokens, schema_name=schema_name, **kwargs)

        results = evaluate_snapshot_components(
            tldr=full_tldr(), signals={}, brand_name="Acme", url="u", llm=FlakyLLM(pass_up_to=5)
        )
        self.assertEqual(results["personality"].status, STATUS_NOT_EVALUATED)
        others = [k for k in COMPONENTS if k != "personality"]
        for key in others:
            self.assertEqual(results[key].status, STATUS_SCORED, key)


if __name__ == "__main__":
    unittest.main()
