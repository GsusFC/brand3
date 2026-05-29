from __future__ import annotations

from typing import Any

from src.features.magnetism.analyst_tldr import (
    ANALYST_TLDR_PROMPT_VERSION,
    build_analyst_tldr_prompt,
    maybe_build_analyst_tldr,
    normalize_analyst_response,
)
from src.reports.brand_research_pack import build_brand_research_pack_from_snapshot


class FakeAnalystLLM:
    def __init__(self, response: dict[str, Any]):
        self.api_key = "valid-key"
        self.response = response
        self.captured_system = ""
        self.captured_user = ""

    def _call_json(self, system: str, user: str, max_tokens: int = 8000) -> dict[str, Any]:
        self.captured_system = system
        self.captured_user = user
        return self.response


def _research_pack(brand_name: str = "Base44", url: str = "https://base44.com") -> Any:
    snapshot = {
        "run": {"id": 1101, "brand_name": brand_name, "url": url},
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": url,
                    "title": brand_name,
                    "markdown_content": (
                        "Base44 is an AI app builder for non-technical founders. "
                        "Build and ship apps fast. "
                        "Our founder exited a previous startup and built Base44 to make app creation simple."
                    ),
                },
            },
            {
                "source": "entity_research_packet",
                "payload": {
                    "input_url": url,
                    "audited_surface_type": "parent_home",
                    "entity_name": brand_name,
                    "parent_brand": None,
                    "product_name": None,
                    "brand_architecture": "single_brand_surface",
                    "owned_surfaces": [
                        {"url": url, "role": "audited_surface", "entity_scope": "audited_surface", "reason": "input"}
                    ],
                    "limitations": [],
                },
            },
        ],
        "features": [],
        "evidence_items": [],
    }
    return build_brand_research_pack_from_snapshot(snapshot)


def test_analyst_pass_normalizes_base44_and_captures_prompt() -> None:
    llm = FakeAnalystLLM(
        {
            "entity_reading": "Base44 reads as a company-level AI app builder.",
            "verdict_vs_current": "better",
            "main_gain": "Reads the offer from the pack instead of from fragments.",
            "main_risk": "Founder context still needs review.",
            "tldr_brand3": {
                "core_purpose": {
                    "answer": "To make app creation simple for non-technical founders.",
                    "claim_type": "declared",
                    "mode": "compressed",
                    "confidence": "high",
                    "reasoning": "The owned homepage states the offer and audience directly.",
                    "evidence_used": ["Base44 is an AI app builder for non-technical founders."],
                    "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                    "counter_evidence": [],
                    "human_review_recommended": False,
                },
                "value_proposition": {
                    "answer": "An AI app builder for non-technical founders.",
                    "claim_type": "declared",
                    "mode": "compressed",
                    "confidence": "high",
                    "reasoning": "The offer is literal and traceable.",
                    "evidence_used": ["Base44 is an AI app builder for non-technical founders."],
                    "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                    "counter_evidence": [],
                    "human_review_recommended": False,
                },
            },
        }
    )

    pack = _research_pack()
    result = maybe_build_analyst_tldr(
        llm=llm,
        brand_name="Base44",
        url="https://base44.com",
        research_pack=pack,
        current_tldr={},
    )

    assert result is not None
    assert result["prompt_version"] == ANALYST_TLDR_PROMPT_VERSION
    assert "Brand3's Analyst Pass" in llm.captured_system
    assert "block_exercises" in llm.captured_user
    assert "Base44" in llm.captured_user
    assert result["tldr_brand3"]["core_purpose"]["answer"].startswith("To make app creation simple")
    assert result["tldr_brand3"]["core_purpose"]["evidence_sources"][0]["source_key"] == "https://base44.com"
    assert result["tldr_brand3"]["vision"]["claim_type"] == "absent"
    assert result["tldr_brand3"]["vision"]["mode"] == "not_detected"


def test_block_without_evidence_used_remains_visible_and_flagged() -> None:
    llm = FakeAnalystLLM(
        {
            "tldr_brand3": {
                "personality": {
                    "answer": "Ambitious and builder-oriented.",
                    "claim_type": "declared",
                    "mode": "literal",
                    "confidence": "high",
                    "reasoning": "The story suggests ambition.",
                    "evidence_sources": [{"source_key": "https://base44.com/about", "source_type": "press_or_founder"}],
                }
            }
        }
    )
    result = maybe_build_analyst_tldr(
        llm=llm,
        brand_name="Base44",
        url="https://base44.com",
        research_pack=_research_pack(),
        current_tldr={},
    )

    block = result["tldr_brand3"]["personality"]
    assert block["answer"] is None
    assert block["evidence_used"] == []
    assert block["claim_type"] == "absent"
    assert block["mode"] == "not_detected"
    assert block["human_review_recommended"] is False


def test_partial_response_fills_missing_blocks_as_not_detected() -> None:
    llm = FakeAnalystLLM(
        {
            "tldr_brand3": {
                "value_proposition": {
                    "answer": "AI app builder for non-technical founders.",
                    "claim_type": "declared",
                    "mode": "compressed",
                    "confidence": "high",
                    "reasoning": "Literal offer language.",
                    "evidence_used": ["Base44 is an AI app builder for non-technical founders."],
                    "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                    "counter_evidence": [],
                    "human_review_recommended": False,
                }
            }
        }
    )
    result = maybe_build_analyst_tldr(
        llm=llm,
        brand_name="Base44",
        url="https://base44.com",
        research_pack=_research_pack(),
        current_tldr={},
    )

    assert set(result["tldr_brand3"].keys()) == {
        "core_purpose",
        "magnetism",
        "value_proposition",
        "personality",
        "brand_idea",
        "attributes",
        "values",
        "mission",
        "vision",
    }
    assert result["tldr_brand3"]["vision"]["claim_type"] == "absent"
    assert result["tldr_brand3"]["vision"]["mode"] == "not_detected"
    assert result["tldr_brand3"]["mission"]["answer"] is None


def test_invalid_json_returns_controlled_fallback() -> None:
    llm = FakeAnalystLLM({})
    current_tldr = {
        "value_proposition": {
            "answer": "Keep me",
            "claim_type": "declared",
            "mode": "compressed",
            "confidence": "high",
        }
    }
    result = maybe_build_analyst_tldr(
        llm=llm,
        brand_name="Base44",
        url="https://base44.com",
        research_pack=_research_pack(),
        current_tldr=current_tldr,
    )

    assert result["analysis_error"]["reason"] == "llm_error"
    assert result["tldr_brand3"]["value_proposition"]["answer"] == "Keep me"
    assert result["tldr_brand3"]["value_proposition"]["claim_type"] == "declared"


def test_prompt_is_driven_by_pack_not_brand_rules() -> None:
    pack = _research_pack("Bokeroon", "https://bokeroon.com")
    prompt = build_analyst_tldr_prompt(
        brand_name="Bokeroon",
        url="https://bokeroon.com",
        research_pack=pack,
        current_tldr={},
    )

    assert "Bokeroon" in prompt
    assert "source_rules" in prompt
    assert '"brand": {' in prompt
