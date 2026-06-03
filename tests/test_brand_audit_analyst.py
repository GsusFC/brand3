from __future__ import annotations

from typing import Any

from src.reports.brand_audit_analyst import (
    AUDIT_DIMENSIONS,
    BRAND_AUDIT_ANALYST_PROMPT_VERSION,
    brand_audit_analyst_response_schema,
    build_brand_audit_analyst_prompt,
    run_brand_audit_analyst_pass,
)


class FakeAuditLLM:
    def __init__(self, response: Any, *, api_key: str | None = "valid-key"):
        self.api_key = api_key
        self.response = response
        self.captured_system = ""
        self.captured_user = ""
        self.captured_kwargs: dict[str, Any] = {}

    def _call_json(self, system: str, user: str, max_tokens: int = 8000, **kwargs: Any) -> Any:
        self.captured_system = system
        self.captured_user = user
        self.captured_kwargs = kwargs
        return self.response


def _dimensions() -> dict[str, float]:
    return {
        "coherencia": 72.0,
        "diferenciacion": 48.0,
        "presencia": 61.0,
        "percepcion": 35.0,
        "vitalidad": 42.0,
    }


def _features() -> dict[str, dict[str, Any]]:
    return {
        "coherencia": {
            "messaging_consistency": {
                "value": 0.7,
                "confidence": 0.8,
                "source": "web",
                "raw_value": {
                    "evidence": [
                        {
                            "quote": "Base44 is an AI app builder for non-technical founders.",
                            "source_url": "https://base44.com",
                        }
                    ]
                },
            }
        }
    }


def _research_pack() -> dict[str, Any]:
    return {
        "version": "brand_research_pack_v0_1",
        "entity": {"name": "Base44", "url": "https://base44.com"},
        "promotable_signals": [
            {
                "claim": "Base44 is an AI app builder for non-technical founders.",
                "source_key": "https://base44.com",
            }
        ],
        "source_map": {
            "https://base44.com": {
                "url": "https://base44.com",
                "source_type": "owned_official",
            }
        },
    }


def test_brand_audit_analyst_prompt_and_schema_are_dimension_based() -> None:
    prompt = build_brand_audit_analyst_prompt(
        brand_name="Base44",
        url="https://base44.com",
        research_pack=_research_pack(),
        dimensions=_dimensions(),
        features_by_dim=_features(),
    )
    schema = brand_audit_analyst_response_schema()

    assert BRAND_AUDIT_ANALYST_PROMPT_VERSION in prompt
    assert "executive Brand Audit by dimension" in prompt
    assert "Base44 is an AI app builder" in prompt
    assert schema["properties"]["dimensions"]["required"] == AUDIT_DIMENSIONS


def test_brand_audit_analyst_normalizes_partial_response() -> None:
    llm = FakeAuditLLM(
        {
            "executive_summary": "Base44 has a clear product-level offer, but weaker external proof.",
            "primary_risk": "The evidence is stronger on owned claim than market validation.",
            "primary_opportunity": "Use the clear offer as the anchor for proof and presence.",
            "dimensions": {
                "coherencia": {
                    "dimension": "coherencia",
                    "question": "Does the brand say one clear thing across owned evidence?",
                    "diagnosis": "The owned offer is clear and repeated.",
                    "findings": ["The audience and product category are stated directly."],
                    "evidence": ["Base44 is an AI app builder for non-technical founders."],
                    "recommendation": "Keep the offer language stable across proof pages.",
                    "confidence": "high",
                    "limitations": [],
                },
                "diferenciacion": {
                    "diagnosis": "The category contrast is still under-supported.",
                    "findings": ["The evidence states the offer but not a distinctive mechanism."],
                    "evidence": [],
                    "recommendation": "Add proof of why the builder is materially different.",
                    "confidence": "medium",
                    "limitations": [],
                },
            },
        }
    )

    result = run_brand_audit_analyst_pass(
        llm=llm,
        brand_name="Base44",
        url="https://base44.com",
        research_pack=_research_pack(),
        dimensions=_dimensions(),
        features_by_dim=_features(),
    )

    assert result["prompt_version"] == BRAND_AUDIT_ANALYST_PROMPT_VERSION
    assert result["dimensions"]["coherencia"]["confidence"] == "high"
    assert result["dimensions"]["coherencia"]["score"] == 72.0
    assert result["dimensions"]["diferenciacion"]["confidence"] == "low"
    assert "diagnosis present without evidence" in result["validation_notes"][0]
    assert result["dimensions"]["vitalidad"]["confidence"] == "low"
    assert llm.captured_kwargs["schema_name"] == "brand_audit_executive_v2"


def test_brand_audit_analyst_fallback_when_llm_unavailable() -> None:
    result = run_brand_audit_analyst_pass(
        llm=FakeAuditLLM({}, api_key=None),
        brand_name="Base44",
        url="https://base44.com",
        research_pack=_research_pack(),
        dimensions=_dimensions(),
        features_by_dim=_features(),
    )

    assert result["analysis_error"]["reason"] == "llm_unavailable"
    assert result["dimensions"]["coherencia"]["score"] == 72.0
    assert result["dimensions"]["coherencia"]["confidence"] == "low"


def test_brand_audit_analyst_fallback_when_llm_has_no_json_call() -> None:
    class FeatureOnlyLLM:
        api_key = "valid-key"

    result = run_brand_audit_analyst_pass(
        llm=FeatureOnlyLLM(),
        brand_name="Base44",
        url="https://base44.com",
        research_pack=_research_pack(),
        dimensions=_dimensions(),
        features_by_dim=_features(),
    )

    assert result["analysis_error"]["reason"] == "llm_json_unavailable"
    assert result["dimensions"]["diferenciacion"]["score"] == 48.0


def test_brand_audit_analyst_fallback_when_json_call_fails() -> None:
    class FailingLLM:
        api_key = "valid-key"

        def _call_json(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("provider unavailable")

    result = run_brand_audit_analyst_pass(
        llm=FailingLLM(),
        brand_name="Base44",
        url="https://base44.com",
        research_pack=_research_pack(),
        dimensions=_dimensions(),
        features_by_dim=_features(),
    )

    assert result["analysis_error"]["reason"] == "llm_error"
    assert "provider unavailable" in result["analysis_error"]["detail"]
