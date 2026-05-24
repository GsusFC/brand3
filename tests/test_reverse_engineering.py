from __future__ import annotations

import json
from typing import Any

from src.features.reverse_engineering.extractor import ReverseEngineeringExtractor
from src.features.llm_analyzer import LLMAnalyzer


class FakeLLMAnalyzer:
    """Mock for LLMAnalyzer."""

    def __init__(self, api_key: str | None = "fake-key"):
        self.api_key = api_key
        self.captured_system = None
        self.captured_user = None
        self.mock_response: dict[str, Any] = {}

    def _call_json(self, system: str, user: str, max_tokens: int = 8000) -> dict[str, Any]:
        self.captured_system = system
        self.captured_user = user
        return self.mock_response


def test_reverse_engineering_extractor_heuristic_fallback_no_llm():
    extractor = ReverseEngineeringExtractor(llm=None)
    
    web_markdown = """
    Welcome to Brand3.
    We are on a moral mission to change how brands are built. Our values drive us.
    Checkout our pricing plan to subscribe today. Get started now!
    We also have an API and full developer documentation.
    """
    
    result = extractor.extract(
        web_markdown=web_markdown,
        mentions=[],
        visual_signature={},
        brand_name="Heuristic Brand"
    )

    assert result["brand_name"] == "Heuristic Brand"
    assert result["fallback_used"] is True
    assert set(result["layers"].keys()) == {
        "mindspace", "aetherspace", "gamespace", "envispace", "netspace", "tactispace", "ambientspace"
    }

    # "mission" should match aetherspace
    assert result["layers"]["aetherspace"]["status"] == "detected"
    assert len(result["layers"]["aetherspace"]["evidence"]) > 0

    # "api" should match netspace
    assert result["layers"]["netspace"]["status"] == "detected"

    # "pricing" should match tactispace
    assert result["layers"]["tactispace"]["status"] == "detected"

    # gamespace has no keywords in text
    assert result["layers"]["gamespace"]["status"] == "not_detected"


def test_reverse_engineering_extractor_heuristic_fallback_with_visual_signature():
    extractor = ReverseEngineeringExtractor(llm=None)
    
    visual_sig = {
        "semantics": {
            "status": "detected",
            "data": {
                "aesthetic_style": "minimalist brutalism",
                "visual_mood": "rebellious high-tech",
                "visual_polish_score": 9,
                "visual_polish_rationale": "Extremely polished typography",
                "visual_coherence": "perfect coherence"
            }
        }
    }
    
    result = extractor.extract(
        web_markdown="brand3 brand new framework",
        mentions=[],
        visual_signature=visual_sig,
        brand_name="Visual Brand"
    )

    assert result["layers"]["envispace"]["status"] == "detected"
    evidence = result["layers"]["envispace"]["evidence"]
    assert any("minimalist brutalism" in ev for ev in evidence)
    assert any("9/10" in ev for ev in evidence)


def test_reverse_engineering_extractor_llm_success():
    fake_llm = FakeLLMAnalyzer(api_key="valid-key")
    extractor = ReverseEngineeringExtractor(llm=fake_llm)  # type: ignore

    fake_llm.mock_response = {
        "mindspace": {
            "status": "detected",
            "findings": "Deep cognitive model around anti-gravity marketing.",
            "evidence": ["literal quote 1"]
        },
        "aetherspace": {
            "status": "not_detected",
            "findings": "No founder mythology found.",
            "evidence": []
        },
        "gamespace": {
            "status": "detected",
            "findings": "Uses quests and onboarding levels.",
            "evidence": ["literal quote 2"]
        }
        # missing other layers to test normalization
    }

    result = extractor.extract(
        web_markdown="moral mission anti-gravity marketing",
        mentions=["Brand3 is a paradigm shift"],
        visual_signature={},
        brand_name="Gemini Brand"
    )

    assert result["brand_name"] == "Gemini Brand"
    assert result["fallback_used"] is False
    assert result["layers_detected_count"] == 2
    
    # Check normalized defaults for missing layers
    assert result["layers"]["netspace"]["status"] == "not_detected"
    assert result["layers"]["netspace"]["findings"] == "No clear signal detected in the provided sources."
    assert result["layers"]["netspace"]["evidence"] == []

    # Check parsed layers
    assert result["layers"]["mindspace"]["status"] == "detected"
    assert result["layers"]["mindspace"]["findings"] == "Deep cognitive model around anti-gravity marketing."
    assert result["layers"]["mindspace"]["evidence"] == ["literal quote 1"]


def test_reverse_engineering_extractor_llm_exception_falls_back_to_heuristic():
    class ExceptionLLM(FakeLLMAnalyzer):
        def _call_json(self, system: str, user: str, max_tokens: int = 8000) -> dict[str, Any]:
            raise RuntimeError("Gemini rate limit exceeded")

    extractor = ReverseEngineeringExtractor(llm=ExceptionLLM())  # type: ignore
    
    result = extractor.extract(
        web_markdown="moral mission anti-gravity",
        mentions=[],
        visual_signature={},
        brand_name="Fallback Brand"
    )

    assert result["fallback_used"] is True
    assert result["layers"]["aetherspace"]["status"] == "detected"


def test_reverse_engineering_from_audit_snapshot_uses_canonical_evidence_bundle():
    extractor = ReverseEngineeringExtractor(llm=None)
    snapshot = {
        "run": {"id": 501, "brand_name": "Shared Brand", "url": "https://shared.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": (
                        "Shared Brand is a workflow platform for finance teams that helps "
                        "reduce reconciliation time. We provide API integrations and "
                        "developer documentation."
                    ),
                },
            },
            {
                "source": "visual_signature",
                "payload": {
                    "semantics": {
                        "aesthetic_style": "minimalist brutalism",
                        "visual_mood": "precise",
                        "visual_polish_score": 8,
                    }
                },
            },
        ],
        "evidence_items": [],
    }

    result = extractor.extract_from_audit_snapshot(snapshot)

    assert result["source"] == "brand_audit_snapshot"
    assert result["source_run_id"] == 501
    assert result["canonical_evidence_summary"]["source"] == "brand_audit_snapshot"
    assert result["canonical_evidence_summary"]["source_label"] == "Canonical Brand Audit evidence"
    assert result["layers"]["netspace"]["status"] == "detected"
    assert result["layers"]["envispace"]["status"] == "detected"
    assert any(
        "minimalist brutalism" in ev
        for ev in result["layers"]["envispace"]["evidence"]
    )
