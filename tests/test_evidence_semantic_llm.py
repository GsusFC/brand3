from __future__ import annotations

from src.research.evidence_semantic_llm import build_llm_semantic_assessment, llm_semantic_response_schema
from src.research.evidence_vnext import build_evidence_vnext_packet_from_snapshot, compare_legacy_current_and_vnext_from_snapshot
from src.research.evidence_vnext_report import build_batch_report, render_batch_report_markdown


class FakeSemanticLLM:
    def __init__(self, payload: dict, *, api_key: str = "test-key", model: str = "gemini-3.5-flash"):
        self.payload = payload
        self.api_key = api_key
        self.model = model
        self.calls: list[dict] = []
        self.call_failures: list[dict] = []

    def _call_json(self, system, user, max_tokens=8000, **kwargs):
        self.calls.append({"system": system, "user": user, "max_tokens": max_tokens, **kwargs})
        if isinstance(self.payload, list):
            index = min(len(self.calls) - 1, len(self.payload) - 1)
            return self.payload[index]
        return self.payload


class NativeFakeSemanticLLM(FakeSemanticLLM):
    def __init__(self, payload: dict, *, api_key: str = "test-key", model: str = "gemini-3.5-flash"):
        super().__init__(payload, api_key=api_key, model=model)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        self.native_calls: list[dict] = []

    def _call_json_gemini_native(self, system, user, max_tokens=8000, **kwargs):
        self.native_calls.append({"system": system, "user": user, "max_tokens": max_tokens, **kwargs})
        return self.payload

    def _call_json(self, system, user, max_tokens=8000, **kwargs):
        raise AssertionError("OpenAI-compatible JSON path should not be used for Gemini native structured output")


def _semantic_llm_snapshot() -> dict:
    return {
        "run": {
            "id": 5101,
            "brand_name": "Canva",
            "url": "https://www.canva.com",
        },
        "raw_inputs": [
            {
                "source": "exa",
                "payload": {
                    "mentions": [
                        {
                            "url": "https://www.enterpret.com/customers/canva",
                            "title": "Case Study: Canva",
                            "summary": "Case Study: How Canva leverages Enterpret to improve product feedback.",
                            "source_class": "external",
                            "relation": "external",
                            "classification_reason": "external_candidate",
                        },
                        {
                            "url": "https://www.guideflow.com/blog/ai-design-tools",
                            "title": "AI design tools compared",
                            "summary": "A list of Canva alternatives and AI design tools compared.",
                            "source_class": "external",
                            "relation": "external",
                            "classification_reason": "external_candidate",
                        },
                    ],
                    "competitors": [],
                    "ai_visibility_results": [],
                    "news": [],
                },
            }
        ],
        "features": [
            {
                "dimension_name": "percepcion",
                "feature_name": "search_visibility",
                "value": 0.7,
                "raw_value": repr(
                    {
                        "evidence": [
                            {
                                "quote": "Case Study: How Canva leverages Enterpret to improve product feedback.",
                                "source_url": "https://www.enterpret.com/customers/canva",
                            },
                            {
                                "quote": "A list of Canva alternatives and AI design tools compared.",
                                "source_url": "https://www.guideflow.com/blog/ai-design-tools",
                            },
                        ]
                    }
                ),
                "confidence": 0.7,
                "source": "exa",
            },
        ],
        "evidence_items": [],
    }


def test_llm_semantic_classifier_is_disabled_by_default() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_semantic_llm_snapshot())
    result = build_llm_semantic_assessment(packet, enabled=False)

    assert result["status"] == "disabled"
    assert result["model_effect"] is False
    assert result["summary"]["accepted_count"] == 2
    assert result["assessments"] == []


def test_llm_semantic_classifier_returns_schema_valid_shadow_assessment() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_semantic_llm_snapshot())
    ids = [item.observation_id for item in packet.accepted]
    llm = FakeSemanticLLM(
        {
            "assessments": [
                {
                    "observation_id": ids[0],
                    "semantic_class": "customer_case",
                    "entity_fit": "strong",
                    "materiality": "high",
                    "confidence": 0.91,
                    "reason_codes": ["customer_case_surface"],
                },
                {
                    "observation_id": ids[1],
                    "semantic_class": "tangential",
                    "entity_fit": "partial",
                    "materiality": "low",
                    "confidence": 0.73,
                    "reason_codes": ["alternatives_page"],
                },
            ]
        }
    )

    result = build_llm_semantic_assessment(packet, llm=llm, enabled=True)

    assert result["status"] == "ok"
    assert result["model"] == "gemini-3.5-flash"
    assert result["transport"] == "openai_compatible"
    assert result["model_effect"] is True
    assert result["summary"]["accepted_material_count"] == 1
    assert result["summary"]["accepted_weak_count"] == 1
    assert result["attempt_count"] == 1
    assert result["batch_count"] == 1
    assert result["retry_count"] == 0
    assert llm.calls[0]["schema_name"] == "brand3_evidence_semantic_classifier"
    assert llm.calls[0]["json_schema"] == llm_semantic_response_schema()


def test_llm_semantic_classifier_prefers_gemini_native_structured_output() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_semantic_llm_snapshot())
    ids = [item.observation_id for item in packet.accepted]
    llm = NativeFakeSemanticLLM(
        {
            "assessments": [
                {
                    "observation_id": ids[0],
                    "semantic_class": "customer_case",
                    "entity_fit": "strong",
                    "materiality": "high",
                    "confidence": 0.91,
                    "reason_codes": ["customer_case_surface"],
                },
                {
                    "observation_id": ids[1],
                    "semantic_class": "competitor_comparison",
                    "entity_fit": "partial",
                    "materiality": "medium",
                    "confidence": 0.73,
                    "reason_codes": ["comparison_surface"],
                },
            ]
        }
    )

    result = build_llm_semantic_assessment(packet, llm=llm, enabled=True)

    assert result["status"] == "ok"
    assert result["transport"] == "gemini_native"
    assert len(llm.native_calls) == 1
    assert llm.native_calls[0]["schema_name"] == "brand3_evidence_semantic_classifier"
    assert llm.native_calls[0]["json_schema"] == llm_semantic_response_schema()


def test_llm_semantic_classifier_rejects_invalid_or_partial_payload() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_semantic_llm_snapshot())
    llm = FakeSemanticLLM({"assessments": []})

    result = build_llm_semantic_assessment(packet, llm=llm, enabled=True)

    assert result["status"] == "error"
    assert result["model_effect"] is False
    assert result["reason"] == "schema_validation_error"
    assert result["assessments"] == []
    assert result["attempt_count"] == 2
    assert result["batch_count"] == 1
    assert result["retry_count"] == 1
    assert len(llm.calls) == 2


def test_llm_semantic_classifier_retries_schema_validation_failure() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_semantic_llm_snapshot())
    ids = [item.observation_id for item in packet.accepted]
    llm = FakeSemanticLLM(
        [
            {"assessments": []},
            {
                "assessments": [
                    {
                        "observation_id": ids[0],
                        "semantic_class": "customer_case",
                        "entity_fit": "strong",
                        "materiality": "high",
                        "confidence": 0.91,
                        "reason_codes": ["customer_case_surface"],
                    },
                    {
                        "observation_id": ids[1],
                        "semantic_class": "competitor_comparison",
                        "entity_fit": "partial",
                        "materiality": "medium",
                        "confidence": 0.7,
                        "reason_codes": ["comparison_surface"],
                    },
                ]
            },
        ]
    )

    result = build_llm_semantic_assessment(packet, llm=llm, enabled=True)

    assert result["status"] == "ok"
    assert result["summary"]["accepted_material_count"] == 2
    assert result["attempt_count"] == 2
    assert result["batch_count"] == 1
    assert result["retry_count"] == 1
    assert len(llm.calls) == 2


def test_batch_report_compares_llm_shadow_with_heuristic_shadow(monkeypatch) -> None:
    monkeypatch.setenv("BRAND3_EVIDENCE_LLM_CLASSIFIER_ENABLED", "1")
    result = compare_legacy_current_and_vnext_from_snapshot(_semantic_llm_snapshot())
    result["vnext_semantic_llm_assessment"] = {
        "status": "ok",
        "model": "gemini-3.5-flash",
        "assessments": [
            {
                "observation_id": result["vnext_semantic_assessment"]["assessments"][0]["observation_id"],
                "semantic_class": "customer_case",
                "entity_fit": "strong",
                "materiality": "high",
                "confidence": 0.9,
                "reason_codes": ["customer_case_surface"],
            },
            {
                "observation_id": result["vnext_semantic_assessment"]["assessments"][1]["observation_id"],
                "semantic_class": "tangential",
                "entity_fit": "partial",
                "materiality": "low",
                "confidence": 0.7,
                "reason_codes": ["alternatives_page"],
            },
        ],
    }

    report = build_batch_report([result])
    markdown = render_batch_report_markdown(report)

    assert report["semantic_llm"]["status_counts"]["ok"] == 1
    assert report["semantic_llm"]["models"]["gemini-3.5-flash"] == 1
    assert report["semantic_llm"]["semantic_class_disagreement_count"] >= 1
    assert "## Semantic LLM Shadow" in markdown
