"""Phase 2 of fix/report-narrative — LLM narrative generators."""

from __future__ import annotations

import json
import threading
import time
import unittest
from unittest.mock import MagicMock

from src.reports.derivation import DimensionEvidences, Evidence
from src.reports.narrative import (
    Finding,
    SynthesisContext,
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
        self.assertIn("Netlify scores 72/100", out)
        self.assertIn("Strongest dimension: Presence", out)
        self.assertIn("Weakest dimension: Differentiation", out)

    def test_fallback_when_llm_raises(self):
        mock = MagicMock()
        mock._call.side_effect = RuntimeError("boom")
        out = generate_synthesis(_synthesis_ctx(), analyzer=mock)
        self.assertIn("Netlify", out)
        self.assertIn("72/100", out)


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
        self.assertIn("automatic synthesis unavailable", findings[0].prose)
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
        self.assertIn("global score unavailable", out)
        # The composite score slot must not read "scores 0/100" or similar;
        # per-dimension scores (e.g. "70/100") are fine.
        self.assertNotIn("scores 0/100", out)
        self.assertNotIn("(band F)", out)

    def test_fallback_keeps_numeric_score_when_present(self):
        mock = MagicMock()
        mock._call.return_value = ""
        out = generate_synthesis(self._ctx(72.0), analyzer=mock)
        self.assertIn("72/100", out)
        self.assertNotIn("global score unavailable", out)

    def test_prompt_does_not_lie_when_composite_is_none(self):
        """The LLM prompt must not state 'n/a/100' or a fabricated band."""
        from src.reports.narrative import _build_synthesis_user_prompt

        prompt = _build_synthesis_user_prompt(self._ctx(None))
        self.assertIn("n/a", prompt)
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


if __name__ == "__main__":
    unittest.main()
