from __future__ import annotations

from typing import Any

from src.features.magnetism.analyst_tldr import (
    ANALYST_TLDR_PROMPT_VERSION,
    analyst_tldr_response_schema,
    build_analyst_tldr_prompt,
    maybe_build_analyst_tldr,
    normalize_analyst_response,
)
from src.reports.brand_research_pack import build_brand_research_pack_from_snapshot


class FakeAnalystLLM:
    def __init__(self, response: Any):
        self.api_key = "valid-key"
        self.response = response
        self.captured_system = ""
        self.captured_user = ""

    def _call_json(self, system: str, user: str, max_tokens: int = 8000, **kwargs: Any) -> Any:
        self.captured_system = system
        self.captured_user = user
        self.captured_kwargs = kwargs
        return self.response


class FakeFailingAnalystLLM(FakeAnalystLLM):
    def __init__(self, reason: str, error: str):
        super().__init__({})
        self.last_failure_reason = reason
        self.call_failures = [
            {
                "reason": reason,
                "error": error,
                "error_type": "timeout" if reason == "llm_timeout" else "provider_error",
                "model": "model-a",
            }
        ]


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
    assert llm.captured_kwargs["schema_name"] == "brand3_analyst_tldr"
    assert llm.captured_kwargs["json_schema"]["required"] == [
        "entity_reading",
        "verdict_vs_current",
        "main_gain",
        "main_risk",
        "scoring_context",
        "tldr_brand3",
    ]
    assert result["scoring_context"]["evidence_duty_status"] == "not_required"


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


def test_analyst_scoring_context_preserves_earned_magnetism_judgement() -> None:
    raw = {
        "entity_reading": "Nutripilot is an AI sports nutrition product.",
        "verdict_vs_current": "better",
        "main_gain": "Separates hook clarity from proof.",
        "main_risk": "Science proof is thin.",
        "scoring_context": {
            "expressive_magnetism_score": 82,
            "earned_magnetism_score": 64,
            "promise_requires_evidence": True,
            "evidence_duty_status": "weak",
            "coherence_evidence_duty_penalty": 12,
            "reasoning": "Sports nutrition and AI decision claims require scientific and authority evidence.",
            "evidence_gaps": ["methodology", "scientific validation", "verified integrations"],
        },
        "tldr_brand3": {},
    }

    result = normalize_analyst_response(raw, current_tldr={}, research_pack=_research_pack())

    scoring = result["scoring_context"]
    assert scoring["expressive_magnetism_score"] == 82
    assert scoring["earned_magnetism_score"] == 64
    assert scoring["promise_requires_evidence"] is True
    assert scoring["evidence_duty_status"] == "weak"
    assert scoring["coherence_evidence_duty_penalty"] == 12
    assert "scientific validation" in scoring["evidence_gaps"]


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


def test_timeout_failure_keeps_structured_analysis_error(monkeypatch) -> None:
    monkeypatch.setenv("BRAND3_ANALYST_TLDR_TIMEOUT_SECONDS", "91")
    llm = FakeFailingAnalystLLM("llm_timeout", "llm_call_timeout_after_91s")

    result = maybe_build_analyst_tldr(
        llm=llm,
        brand_name="Base44",
        url="https://base44.com",
        research_pack=_research_pack(),
        current_tldr={},
    )

    assert llm.captured_kwargs["timeout_seconds"] == 91
    assert result["analysis_error"]["reason"] == "llm_timeout"
    assert result["analysis_error"]["detail"] == "llm_call_timeout_after_91s"
    assert result["analysis_error"]["error_type"] == "timeout"


def test_single_item_array_response_is_accepted() -> None:
    llm = FakeAnalystLLM(
        [
            {
                "entity_reading": "Base44 reads as an AI app builder.",
                "tldr_brand3": {
                    "value_proposition": {
                        "answer": "AI app builder for non-technical founders.",
                        "claim_type": "declared",
                        "mode": "compressed",
                        "confidence": "high",
                        "reasoning": "The offer is literal and traceable.",
                        "evidence_used": ["Base44 is an AI app builder for non-technical founders."],
                        "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                        "counter_evidence": [],
                        "human_review_recommended": False,
                    }
                },
            }
        ]
    )

    result = maybe_build_analyst_tldr(
        llm=llm,
        brand_name="Base44",
        url="https://base44.com",
        research_pack=_research_pack(),
        current_tldr={},
    )

    assert "analysis_error" not in result
    assert result["entity_reading"] == "Base44 reads as an AI app builder."
    assert result["tldr_brand3"]["value_proposition"]["answer"] == "AI app builder for non-technical founders."


def test_wrapped_analyst_response_is_accepted() -> None:
    llm = FakeAnalystLLM(
        {
            "output": {
                "content": {
                    "entity_reading": "Base44 reads as an AI app builder.",
                    "tldr_brand3": {
                        "value_proposition": {
                            "answer": "AI app builder for non-technical founders.",
                            "claim_type": "declared",
                            "mode": "compressed",
                            "confidence": "high",
                            "reasoning": "The offer is literal and traceable.",
                            "evidence_used": ["Base44 is an AI app builder for non-technical founders."],
                            "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                            "counter_evidence": [],
                            "human_review_recommended": False,
                        }
                    },
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

    assert "analysis_error" not in result
    assert result["entity_reading"] == "Base44 reads as an AI app builder."
    assert result["tldr_brand3"]["value_proposition"]["answer"] == "AI app builder for non-technical founders."


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
    assert "negative_examples" in prompt
    assert "Book a demo" in prompt
    assert "absent/not_detected" in prompt
    assert '"brand": {' in prompt


def test_analyst_tldr_response_schema_requires_all_blocks() -> None:
    schema = analyst_tldr_response_schema()

    assert "scoring_context" in schema["required"]
    assert schema["properties"]["scoring_context"]["required"] == [
        "expressive_magnetism_score",
        "earned_magnetism_score",
        "promise_requires_evidence",
        "evidence_duty_status",
        "coherence_evidence_duty_penalty",
        "reasoning",
        "evidence_gaps",
    ]
    assert schema["properties"]["tldr_brand3"]["required"] == [
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
    assert schema["properties"]["tldr_brand3"]["additionalProperties"] is False
