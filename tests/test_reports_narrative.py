"""Phase 2 of fix/report-narrative — LLM narrative generators."""

from __future__ import annotations

import json
import importlib
import threading
import time
import unittest
from unittest.mock import MagicMock

from src.config import LLM_PREMIUM_MODEL
from src.reports.derivation import DimensionEvidences, Evidence
from src.reports.experimental_perceptual_narrative import (
    build_perceptual_narrative_hints,
)
from src.reports.narrative import (
    Finding,
    SynthesisContext,
    _build_findings_user_prompt,
    clear_cache,
    generate_all_findings,
    generate_dimension_findings,
    generate_synthesis,
    generate_tensions,
)

_DISPLAY = {
    "coherencia": "Coherence",
    "presencia": "Presence",
    "percepcion": "Perception",
    "diferenciacion": "Differentiation",
    "vitalidad": "Vitality",
}


def _ev(dim: str, quote: str = "", url: str | None = None, sentiment: str | None = None) -> Evidence:
    return Evidence(
        dimension=dim,
        quote=quote or None,
        url=url,
        source_type="news" if url and "techcrunch" in url else "owned" if url and "netlify" in url else "other",
        source_domain=("techcrunch.com" if url and "techcrunch" in url else None),
        sentiment=sentiment,
        feature_name="test_feature",
    )


def _dim(name: str, score: float, evidences: list[Evidence] | None = None) -> DimensionEvidences:
    return DimensionEvidences(
        dimension=name,
        display_name=_DISPLAY.get(name, name),
        score=score,
        verdict="solid" if score >= 80 else "mixed",
        verdict_adjective="cohesive" if score >= 80 else "uneven",
        evidences=evidences or [],
    )


def _synthesis_ctx(evidences: list[Evidence] | None = None, score: float | None = 72.0) -> SynthesisContext:
    return SynthesisContext(
        brand="Netlify",
        url="https://www.netlify.com",
        composite_score=score,
        dimensions=[
            _dim("coherencia", 78.0),
            _dim("presencia", 82.0),
            _dim("percepcion", 66.0),
            _dim("diferenciacion", 54.0),
            _dim("vitalidad", 71.0),
        ],
        data_quality="good",
        top_evidences=evidences or [
            _ev("percepcion", "Netlify redefines modern web development.",
                "https://techcrunch.com/2025/netlify-x"),
        ],
    )


def test_default_narrative_analyzer_uses_premium_model(monkeypatch):
    from src.reports import narrative as narr_mod

    narr_mod = importlib.reload(narr_mod)
    created_models: list[str | None] = []

    class FakeLLMAnalyzer:
        api_key = "key"

        def __init__(self, *, model=None):
            self.model = model
            created_models.append(model)

    monkeypatch.setattr("src.features.llm_analyzer.LLMAnalyzer", FakeLLMAnalyzer)

    analyzer = narr_mod._default_analyzer()

    assert analyzer is not None
    assert created_models == [LLM_PREMIUM_MODEL]
    assert analyzer.model == LLM_PREMIUM_MODEL


class SynthesisTests(unittest.TestCase):
    def setUp(self):
        clear_cache()

    def test_llm_string_is_passed_through(self):
        mock = MagicMock()
        mock._call.return_value = (
            "Netlify se presenta como la plataforma moderna para builders web. "
            "La cobertura externa lo confirma. "
            "La presencia social es fuerte pero la percepción aún se fragmenta. "
            "La tensión principal: mensaje claro con poca diferenciación."
        )
        out = generate_synthesis(_synthesis_ctx(), analyzer=mock)
        self.assertIn("Netlify", out)
        mock._call.assert_called_once()

    def test_strips_markdown_fences(self):
        mock = MagicMock()
        mock._call.return_value = "```\nPárrafo limpio sobre Netlify.\n```"
        out = generate_synthesis(_synthesis_ctx(), analyzer=mock)
        self.assertEqual(out, "Párrafo limpio sobre Netlify.")

    def test_fallback_when_llm_empty(self):
        mock = MagicMock()
        mock._call.return_value = ""
        out = generate_synthesis(_synthesis_ctx(), analyzer=mock)
        self.assertIn("Cross-dimension snapshot for Netlify.", out)
        self.assertIn("Presence is the highest-scoring dimension at 82/100", out)
        self.assertIn("Differentiation the lowest at 54/100", out)
        self.assertNotIn("Netlify scores 72/100", out)

    def test_fallback_when_llm_raises(self):
        mock = MagicMock()
        mock._call.side_effect = RuntimeError("boom")
        out = generate_synthesis(_synthesis_ctx(), analyzer=mock)
        self.assertIn("Netlify", out)
        self.assertIn("Cross-dimension snapshot", out)

    def test_prompt_injects_analysis_date_anchor(self):
        from src.reports.narrative import _build_synthesis_user_prompt

        ctx = _synthesis_ctx()
        ctx.analysis_date = "2026-05-07 12:34:56"

        prompt = _build_synthesis_user_prompt(ctx)

        self.assertIn("Today's date is 2026-05-07", prompt)
        self.assertIn("NOT your training cutoff", prompt)
        self.assertIn("before 2026-05-07 is past or present", prompt)

    def test_prompt_includes_tension_text_when_available(self):
        from src.reports.narrative import _build_synthesis_user_prompt

        ctx = _synthesis_ctx()
        ctx.tension_text = (
            "The dimensions show self-description and external coverage diverging "
            "around audience clarity."
        )

        prompt = _build_synthesis_user_prompt(ctx)

        self.assertIn("Tension already identified by §5", prompt)
        self.assertIn(ctx.tension_text, prompt)
        self.assertIn("do not invent a different tension", prompt)


class DimensionFindingsTests(unittest.TestCase):
    def setUp(self):
        clear_cache()

    def test_parses_two_findings(self):
        mock = MagicMock()
        mock._call_json.return_value = {
            "findings": [
                {
                    "title": "Prensa consolida posicionamiento",
                    "prose": "Medios de referencia describen a la marca como estándar del sector.",
                    "evidence_urls": [
                        "https://techcrunch.com/2025/netlify-x",
                        "https://www.netlify.com/about",
                    ],
                },
                {
                    "title": "Autodescripción técnica",
                    "prose": "La propia web enfatiza el enfoque serverless sin rodeos.",
                    "evidence_urls": ["https://www.netlify.com/about"],
                },
            ]
        }
        dim = _dim("percepcion", 66.0, evidences=[
            _ev("percepcion", "Netlify redefines modern web development.",
                "https://techcrunch.com/2025/netlify-x"),
            _ev("percepcion", "Build the best web experiences.",
                "https://www.netlify.com/about"),
        ])
        findings = generate_dimension_findings(dim, "Netlify", analyzer=mock)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].title, "Prensa consolida posicionamiento")
        self.assertEqual(len(findings[0].evidence_urls), 2)
        self.assertEqual(findings[1].evidence_urls, ["https://www.netlify.com/about"])

    def test_empty_list_when_no_evidences(self):
        mock = MagicMock()
        dim = _dim("percepcion", 66.0, evidences=[])
        findings = generate_dimension_findings(dim, "Netlify", analyzer=mock)
        self.assertEqual(findings, [])
        mock._call_json.assert_not_called()

    def test_fallback_finding_when_llm_returns_empty_dict(self):
        mock = MagicMock()
        mock._call_json.return_value = {}
        dim = _dim("percepcion", 66.0, evidences=[
            _ev("percepcion", "Quote A", "https://techcrunch.com/a"),
            _ev("percepcion", "Quote B", "https://techcrunch.com/b"),
        ])
        findings = generate_dimension_findings(dim, "Netlify", analyzer=mock)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].title, "Available evidence")
        self.assertIn("Editorial synthesis unavailable", findings[0].prose)
        self.assertEqual(len(findings[0].evidence_urls), 2)

    def test_filters_urls_not_in_input_evidences(self):
        mock = MagicMock()
        mock._call_json.return_value = {
            "findings": [{
                "title": "Con URL fabricada",
                "prose": "Si el LLM inventa una URL, no debe colarse.",
                "evidence_urls": [
                    "https://techcrunch.com/real",
                    "https://hallucinated.example/fake",  # not in evidences
                ],
            }]
        }
        dim = _dim("percepcion", 66.0, evidences=[
            _ev("percepcion", "real", "https://techcrunch.com/real"),
        ])
        findings = generate_dimension_findings(dim, "Netlify", analyzer=mock)
        self.assertEqual(findings[0].evidence_urls, ["https://techcrunch.com/real"])

    def test_fallback_when_llm_raises(self):
        mock = MagicMock()
        mock._call_json.side_effect = TimeoutError("remote")
        dim = _dim("percepcion", 66.0, evidences=[
            _ev("percepcion", "q", "https://techcrunch.com/a"),
        ])
        findings = generate_dimension_findings(dim, "Netlify", analyzer=mock)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].title, "Available evidence")

    def test_findings_prompt_injects_analysis_date_anchor(self):
        dim = _dim("presencia", 66.0, evidences=[
            _ev("presencia", "Founded in 2025", "https://example.com/about"),
        ])

        prompt = _build_findings_user_prompt(
            dim,
            "Outcraft",
            analysis_date="2026-05-07T08:00:00Z",
        )

        self.assertIn("Today's date is 2026-05-07", prompt)
        self.assertIn("before 2026-05-07 is past or present", prompt)

    def test_findings_prompt_omits_perceptual_hints_by_default(self):
        dim = _dim("percepcion", 66.0, evidences=[
            _ev("percepcion", "Build the best web experiences.", "https://www.netlify.com/about"),
        ])

        prompt = _build_findings_user_prompt(dim, "Netlify")

        self.assertNotIn("EXPERIMENTAL PERCEPTUAL NARRATIVE HINTS", prompt)
        self.assertNotIn("Category-To-Surface Translation", prompt)

    def test_findings_prompt_injects_perceptual_hints_when_provided(self):
        dim = _dim("percepcion", 66.0, evidences=[
            _ev("percepcion", "Build the best web experiences.", "https://www.netlify.com/about"),
        ])
        hints = build_perceptual_narrative_hints("percepcion")

        prompt = _build_findings_user_prompt(
            dim,
            "Netlify",
            perceptual_hints=hints,
        )

        self.assertIn("EXPERIMENTAL PERCEPTUAL NARRATIVE HINTS", prompt)
        self.assertIn("Category-To-Surface Translation", prompt)
        self.assertIn("Claim / Signal Gap", prompt)
        self.assertIn("Use these as reading lenses only", prompt)
        self.assertIn("write it as a limitation or conditional implication", prompt)

    def test_perceptual_hints_can_augment_findings_without_presenting_low_confidence_as_fact(self):
        captured_prompts: list[str] = []

        def _call_json(system, user, max_tokens=2000):
            captured_prompts.append(user)
            return {"findings": [{
                "title": "Copy-Level Surface Claim",
                "observation": "The brand says \"Build the best web experiences\" on its own site.",
                "implication": "That copy could support a category-to-surface reading, but it remains self-description rather than observed product behavior.",
                "typical_decision": "Teams in this position typically choose between clarifying evidence on the surface, adding third-party corroboration, or narrowing the claim; the right move depends on intent, strategy, and resources not observable from outside.",
                "evidence_urls": ["https://www.netlify.com/about"],
            }]}

        mock = MagicMock()
        mock._call_json.side_effect = _call_json
        dim = _dim("percepcion", 66.0, evidences=[
            _ev("percepcion", "Build the best web experiences.", "https://www.netlify.com/about"),
        ])
        hints = build_perceptual_narrative_hints("percepcion")

        findings = generate_dimension_findings(
            dim,
            "Netlify",
            analyzer=mock,
            perceptual_hints=hints,
        )

        self.assertEqual(len(findings), 1)
        self.assertIn("category-to-surface", findings[0].implication)
        self.assertIn("self-description rather than observed product behavior", findings[0].implication)
        self.assertIn("low:", captured_prompts[0])
        self.assertIn("never as fact", captured_prompts[0])


class TensionsTests(unittest.TestCase):
    def setUp(self):
        clear_cache()

    def test_returns_prose_when_present(self):
        mock = MagicMock()
        mock._call_json.return_value = {
            "tension": (
                "Autodescripción técnica y abstracta contrasta con "
                "cobertura externa que enfatiza casos concretos."
            )
        }
        dims = [_dim(d, 70.0) for d in ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")]
        out = generate_tensions(dims, "Netlify", analyzer=mock)
        self.assertIsNotNone(out)
        self.assertIn("Autodescripción", out)

    def test_returns_none_when_null(self):
        mock = MagicMock()
        mock._call_json.return_value = {"tension": None}
        dims = [_dim(d, 70.0) for d in ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")]
        out = generate_tensions(dims, "Netlify", analyzer=mock)
        self.assertIsNone(out)

    def test_returns_none_when_llm_fails(self):
        mock = MagicMock()
        mock._call_json.return_value = {}  # empty dict = failure
        dims = [_dim(d, 70.0) for d in ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")]
        out = generate_tensions(dims, "Netlify", analyzer=mock)
        self.assertIsNone(out)

    def test_tensions_prompt_injects_analysis_date_anchor(self):
        from src.reports.narrative import _build_tensions_user_prompt

        dims = [_dim(d, 70.0) for d in ("coherencia", "presencia")]

        prompt = _build_tensions_user_prompt(
            dims,
            "Outcraft",
            analysis_date="2026-05-07",
        )

        self.assertIn("Today's date is 2026-05-07", prompt)
        self.assertIn("NOT your training cutoff", prompt)


class NoneCompositeScoreTests(unittest.TestCase):
    """Finding 2 — composite_score=None must not become 0/100 or band F."""

    def setUp(self):
        clear_cache()

    def _ctx(self, score: float | None) -> SynthesisContext:
        return SynthesisContext(
            brand="Acme",
            url="https://acme.example",
            composite_score=score,
            dimensions=[_dim("coherencia", 70.0), _dim("presencia", 55.0)],
            data_quality="insufficient",
            top_evidences=[],
        )

    def test_fallback_does_not_fabricate_zero_score(self):
        """Without LLM and without composite, fallback stays honest."""
        mock = MagicMock()
        mock._call.return_value = ""  # force fallback
        out = generate_synthesis(self._ctx(None), analyzer=mock)
        self.assertIn("Cross-dimension snapshot for Acme.", out)
        # The composite score slot must not read "scores 0/100" or similar;
        # per-dimension scores (e.g. "70/100") are fine.
        self.assertNotIn("scores 0/100", out)
        self.assertNotIn("(band F)", out)

    def test_fallback_keeps_numeric_score_when_present(self):
        mock = MagicMock()
        mock._call.return_value = ""
        out = generate_synthesis(self._ctx(72.0), analyzer=mock)
        self.assertIn("Coherence is the highest-scoring dimension at 70/100", out)
        self.assertNotIn("Acme scores 72/100", out)
        self.assertNotIn("global score unavailable", out)

    def test_prompt_does_not_lie_when_composite_is_none(self):
        """The LLM prompt must not state 'n/a/100' or a fabricated band."""
        from src.reports.narrative import _build_synthesis_user_prompt

        prompt = _build_synthesis_user_prompt(self._ctx(None))
        self.assertIn("Per-dimension scores (for context only", prompt)
        self.assertNotIn("n/a/100", prompt)
        self.assertNotIn("(band F)", prompt)
        self.assertNotIn("(band ?)", prompt)


class ParallelFindingsTests(unittest.TestCase):
    def setUp(self):
        clear_cache()

    def test_runs_concurrently_across_dimensions(self):
        """Instrument the mock to confirm 5 calls overlap in time."""
        start_times: list[float] = []
        lock = threading.Lock()
        barrier = threading.Barrier(5)

        def fake_call(system, user, max_tokens=2000):
            with lock:
                start_times.append(time.monotonic())
            barrier.wait(timeout=5)  # all 5 must arrive to unblock
            return {"findings": [{
                "title": "x",
                "prose": "y",
                "evidence_urls": ["https://example.com/a"],
            }]}

        mock = MagicMock()
        mock._call_json.side_effect = fake_call

        dims = [
            _dim(d, 70.0, evidences=[
                _ev(d, "q", "https://example.com/a"),
            ])
            for d in ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")
        ]
        result = generate_all_findings(dims, "Netlify", analyzer=mock, max_workers=5)

        self.assertEqual(set(result.keys()), {d.dimension for d in dims})
        self.assertEqual(mock._call_json.call_count, 5)
        # If calls were serial, the first 5 starts would span >1s given the barrier
        # timeout. Concurrent calls all arrive within a few ms.
        span = max(start_times) - min(start_times)
        self.assertLess(span, 1.0, f"calls not concurrent (span={span:.2f}s)")

    def test_timeout_does_not_block_other_dimensions(self):
        """Finding 1 — a hung dimension must not block the render.

        Patch `_FINDINGS_CALL_TIMEOUT_S` to a short window and have the
        `Perception` mock sleep past it. The other 4 must still return
        their LLM output; Perception must fall back.
        """
        from src.reports import narrative as narr_mod

        hung = threading.Event()

        def slow_or_fast(system, user, max_tokens=2000):
            if "Dimension: Perception" in user:
                hung.wait(timeout=10)  # blocks past the patched timeout
                return {"findings": [{
                    "title": "late", "prose": "too late", "evidence_urls": [],
                }]}
            return {"findings": [{
                "title": "ok",
                "prose": "ok",
                "evidence_urls": ["https://example.com/a"],
            }]}

        mock = MagicMock()
        mock._call_json.side_effect = slow_or_fast

        dims = [
            _dim(d, 70.0, evidences=[_ev(d, "q", "https://example.com/a")])
            for d in ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")
        ]

        started = time.monotonic()
        original_timeout = narr_mod._FINDINGS_CALL_TIMEOUT_S
        narr_mod._FINDINGS_CALL_TIMEOUT_S = 0.5
        try:
            result = generate_all_findings(
                dims, "Netlify", analyzer=mock, max_workers=5,
            )
        finally:
            narr_mod._FINDINGS_CALL_TIMEOUT_S = original_timeout
            hung.set()  # release the hung thread so test shuts down cleanly

        elapsed = time.monotonic() - started
        # Must not have waited for the 10s sleep inside the hung thread.
        self.assertLess(elapsed, 3.0, f"generate_all_findings blocked for {elapsed:.2f}s")
        self.assertEqual(result["percepcion"][0].title, "Available evidence")
        for name in ("coherencia", "presencia", "diferenciacion", "vitalidad"):
            self.assertEqual(result[name][0].title, "ok")

    def test_one_failing_dim_does_not_break_others(self):
        def side_effect(system, user, max_tokens=2000):
            if "perception" in user.lower():
                raise RuntimeError("upstream 500")
            return {"findings": [{
                "title": "ok",
                "prose": "ok",
                "evidence_urls": ["https://example.com/a"],
            }]}

        mock = MagicMock()
        mock._call_json.side_effect = side_effect

        dims = [
            _dim(d, 70.0, evidences=[_ev(d, "q", "https://example.com/a")])
            for d in ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")
        ]
        result = generate_all_findings(dims, "Netlify", analyzer=mock, max_workers=5)

        self.assertEqual(len(result["percepcion"]), 1)
        self.assertEqual(result["percepcion"][0].title, "Available evidence")
        for name in ("coherencia", "presencia", "diferenciacion", "vitalidad"):
            self.assertEqual(result[name][0].title, "ok")


class CacheTests(unittest.TestCase):
    def setUp(self):
        clear_cache()

    def test_synthesis_cache_reuses_result(self):
        mock = MagicMock()
        mock._call.return_value = "ok"
        generate_synthesis(_synthesis_ctx(), analyzer=mock, run_id=99)
        generate_synthesis(_synthesis_ctx(), analyzer=mock, run_id=99)
        self.assertEqual(mock._call.call_count, 1)

    def test_findings_cache_scoped_per_dimension(self):
        mock = MagicMock()
        mock._call_json.return_value = {"findings": [
            {"title": "t", "prose": "p", "evidence_urls": ["https://example.com/a"]}
        ]}
        dim_a = _dim("coherencia", 70.0, evidences=[_ev("coherencia", "q", "https://example.com/a")])
        dim_b = _dim("presencia", 70.0, evidences=[_ev("presencia", "q", "https://example.com/a")])
        generate_dimension_findings(dim_a, "Netlify", analyzer=mock, run_id=99)
        generate_dimension_findings(dim_b, "Netlify", analyzer=mock, run_id=99)
        generate_dimension_findings(dim_a, "Netlify", analyzer=mock, run_id=99)  # cache hit
        self.assertEqual(mock._call_json.call_count, 2)

    def test_findings_cache_separates_base_and_perceptual_experiment(self):
        mock = MagicMock()
        mock._call_json.return_value = {"findings": [
            {"title": "t", "prose": "p", "evidence_urls": ["https://example.com/a"]}
        ]}
        dim = _dim("percepcion", 70.0, evidences=[
            _ev("percepcion", "q", "https://example.com/a")
        ])
        hints = build_perceptual_narrative_hints("percepcion")

        generate_dimension_findings(dim, "Netlify", analyzer=mock, run_id=99)
        generate_dimension_findings(
            dim,
            "Netlify",
            analyzer=mock,
            run_id=99,
            perceptual_hints=hints,
        )
        generate_dimension_findings(dim, "Netlify", analyzer=mock, run_id=99)

        self.assertEqual(mock._call_json.call_count, 2)

    def test_findings_prompt_with_contradictions(self):
        dim = _dim("coherencia", 70.0, evidences=[
            Evidence(
                dimension="coherencia",
                quote="We are absolute leaders",
                url="https://netlify.com",
                source_type="owned",
                source_domain="netlify.com",
                sentiment=None,
                feature_name="messaging_consistency",
            )
        ])
        packet = {
            "contradiction_candidates": [
                {
                    "type": "owned_claim_vs_external_source_mismatch",
                    "feature_name": "messaging_consistency",
                    "dimension": "coherencia",
                }
            ]
        }
        prompt = _build_findings_user_prompt(dim, "Netlify", packet=packet)
        self.assertIn("ACTIVE CONTRADICTIONS / WARNINGS:", prompt)
        self.assertIn("Warning: Discrepancy detected between owned claims and external sources for feature 'messaging_consistency'", prompt)

        dim_other = _dim("presencia", 70.0, evidences=[])
        prompt_other = _build_findings_user_prompt(dim_other, "Netlify", packet=packet)
        self.assertNotIn("ACTIVE CONTRADICTIONS / WARNINGS:", prompt_other)


if __name__ == "__main__":
    unittest.main()
