from __future__ import annotations

from typing import Any

from src.features.magnetism.extractor import MagnetismExtractor
from src.features.magnetism.strategist_tldr import normalize_strategist_response


class FakeStrategistLLM:
    def __init__(self, response: dict[str, Any]):
        self.api_key = "valid-key"
        self.response = response
        self.captured_system = ""
        self.captured_user = ""

    def _call_json(self, system: str, user: str, max_tokens: int = 8000) -> dict[str, Any]:
        self.captured_system = system
        self.captured_user = user
        return self.response


def test_strategist_validator_downgrades_synthesized_declared_claim() -> None:
    normalized = normalize_strategist_response(
        {
            "tldr_brand3": {
                "core_purpose": {
                    "answer": "To eliminate infrastructure complexity so developers can focus on shipping code.",
                    "claim_type": "declared",
                    "mode": "compressed",
                    "confidence": "high",
                    "reasoning": "Synthesizes the platform promise and developer audience.",
                    "evidence_used": ["The platform for devs who just want to ship."],
                }
            }
        },
        current_tldr={},
    )

    block = normalized["tldr_brand3"]["core_purpose"]
    assert block["claim_type"] == "inferred"
    assert block["mode"] == "interpreted_from_discourse"
    assert block["confidence"] == "medium"
    assert block["human_review_recommended"] is True
    assert normalized["tldr_brand3"]["vision"]["mode"] == "not_detected"


def test_strategist_validator_rejects_answer_without_evidence() -> None:
    normalized = normalize_strategist_response(
        {
            "tldr_brand3": {
                "vision": {
                    "answer": "To reinvent how humans and AI live together.",
                    "claim_type": "inferred",
                    "mode": "interpreted_from_discourse",
                    "confidence": "high",
                    "reasoning": "Sounds future-facing.",
                    "evidence_used": [],
                }
            }
        },
        current_tldr={},
    )

    block = normalized["tldr_brand3"]["vision"]
    assert block["claim_type"] == "absent"
    assert block["mode"] == "not_detected"
    assert block["confidence"] == "low"
    assert block["answer"] is None


def test_extractor_keeps_code_tldr_when_strategist_flag_is_disabled(monkeypatch) -> None:
    fake_llm = FakeStrategistLLM(
        {
            "tldr_brand3": {
                "magnetism": {
                    "answer": "LLM-only line.",
                    "claim_type": "declared",
                    "mode": "literal",
                    "confidence": "high",
                    "reasoning": "Would only appear if the pass ran.",
                    "evidence_used": ["LLM-only line."],
                }
            }
        }
    )
    extractor = MagnetismExtractor(llm=fake_llm)  # type: ignore[arg-type]
    monkeypatch.setattr(extractor, "_extract_via_llm", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.features.magnetism.extractor.BRAND3_TLDR_STRATEGIST_PASS", False)

    result = extractor.extract_from_audit_snapshot(
        {
            "run": {"id": 202, "brand_name": "Flag Brand", "url": "https://flag.test"},
            "features": [],
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {"markdown_content": "Build fast. Flag Brand helps teams ship workflows."},
                }
            ],
            "evidence_items": [],
        }
    )

    assert "tldr_strategy" not in result
    assert "tldr_brand3_current" not in result
    assert fake_llm.captured_user == ""



def test_extractor_can_replace_tldr_with_validated_strategist_pass(monkeypatch) -> None:
    fake_llm = FakeStrategistLLM(
        {
            "entity_reading": "Natura Umana appears as a parent brand with tinyNature as the product surface.",
            "verdict_vs_current": "better",
            "main_gain": "Separates product surface from parent brand evidence.",
            "main_risk": "Parent/product architecture still needs confirmation.",
            "tldr_brand3": {
                "value_proposition": {
                    "answer": "A personal AI assistant command center that delegates complex requests to specialized internal sub-agents.",
                    "claim_type": "inferred",
                    "mode": "interpreted_from_discourse",
                    "confidence": "medium",
                    "reasoning": "Combines the assistant claim with the command-center and delegation evidence.",
                    "evidence_used": [
                        "Your personal AI assistant for life orchestration.",
                        "tinyNature is not just a chatbot; it is a command center.",
                    ],
                    "counter_evidence": ["The exact value proposition is synthesized from multiple public statements."],
                    "human_review_recommended": True,
                },
                "mission": {
                    "answer": "To build technology that enhances life without distraction.",
                    "claim_type": "declared",
                    "mode": "compressed",
                    "confidence": "high",
                    "reasoning": "The mission page directly states the operating mission.",
                    "evidence_used": ["Our mission is to build technology that enhances life without distraction."],
                    "counter_evidence": [],
                    "human_review_recommended": False,
                },
            },
        }
    )
    extractor = MagnetismExtractor(llm=fake_llm)  # type: ignore[arg-type]
    monkeypatch.setattr(extractor, "_extract_via_llm", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.features.magnetism.extractor.BRAND3_TLDR_STRATEGIST_PASS", True)

    snapshot = {
        "run": {"id": 201, "brand_name": "tinyNature", "url": "https://lab.naturaumana.ai"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://lab.naturaumana.ai",
                    "markdown_content": (
                        "Life orchestration, perfected by nature. "
                        "Your personal AI assistant for life orchestration. "
                        "tinyNature is not just a chatbot; it is a command center. "
                        "Our mission is to build technology that enhances life without distraction."
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    result = extractor.extract_from_audit_snapshot(snapshot)

    assert "tldr_brand3_current" in result
    assert result["tldr_strategy"]["mode"] == "llm_strategist_pass"
    assert result["tldr_brand3"]["value_proposition"]["answer"].startswith("A personal AI assistant")
    assert result["tldr_brand3"]["value_proposition"]["claim_type"] == "inferred"
    assert result["tldr_brand3"]["mission"]["answer"] == "To build technology that enhances life without distraction."
    assert result["tldr_brand3"]["vision"]["mode"] == "not_detected"
    assert "block_exercises" in fake_llm.captured_user
