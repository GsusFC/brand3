from __future__ import annotations

from src.research.evidence_material_diff_llm import (
    build_material_diff_llm_shadow,
    material_diff_response_schema,
)


class FakeMaterialDiffLLM:
    def __init__(self, payload, *, api_key: str = "test-key", model: str = "gemini-3.5-flash"):
        self.payload = payload
        self.api_key = api_key
        self.model = model
        self.base_url = "https://example.invalid/openai"
        self.calls: list[dict] = []
        self.call_failures: list[dict] = []

    def _call_json(self, system, user, max_tokens=8000, **kwargs):
        self.calls.append({"system": system, "user": user, "max_tokens": max_tokens, **kwargs})
        if isinstance(self.payload, list):
            index = min(len(self.calls) - 1, len(self.payload) - 1)
            return self.payload[index]
        return self.payload


class NativeFakeMaterialDiffLLM(FakeMaterialDiffLLM):
    def __init__(self, payload, *, api_key: str = "test-key", model: str = "gemini-3.5-flash"):
        super().__init__(payload, api_key=api_key, model=model)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        self.native_calls: list[dict] = []

    def _call_json_gemini_native(self, system, user, max_tokens=8000, **kwargs):
        self.native_calls.append({"system": system, "user": user, "max_tokens": max_tokens, **kwargs})
        return self.payload

    def _call_json(self, system, user, max_tokens=8000, **kwargs):
        raise AssertionError("Gemini native structured output should be used")


def _material_diff_report() -> dict:
    return {
        "work_orders": [
            {
                "work_order_id": "workorder:material_audit:273",
                "run_id": 273,
                "brand_name": "Causa Prima",
                "task": "Review changed material evidence after strict source contract",
                "next_action": "manual_audit_projected_material_changes",
                "context": {
                    "affected_material_fields": ["proof_points", "founder_or_press_context"],
                    "changed_material_field_names": ["proof_points", "founder_or_press_context"],
                    "remaining_review_examples": [
                        {
                            "feature_name": "positioning_clarity",
                            "provider": "llm",
                            "source_class": "external_third_party",
                            "classification_reason": "missing_evidence_url",
                            "url": "",
                            "text_preview": "Unlike existing finance tools, Causa Prima puts buyers and suppliers on the same network.",
                        }
                    ],
                    "changed_material_fields": [
                        {
                            "field": "proof_points",
                            "current_preview": "Old proof points.",
                            "vnext_preview": "New proof points.",
                        }
                    ],
                },
            }
        ]
    }


def test_material_diff_shadow_is_disabled_without_runtime_effect() -> None:
    result = build_material_diff_llm_shadow(_material_diff_report(), enabled=False)

    assert result["status"] == "disabled"
    assert result["runtime_effect"] is False
    assert result["persistence_effect"] is False
    assert result["candidate_count"] == 1
    assert result["assessments"] == []


def test_material_diff_shadow_returns_schema_valid_assessment() -> None:
    llm = FakeMaterialDiffLLM(
        {
            "items": [
                {
                    "id": "workorder:material_audit:273",
                    "v": "keep_manual_review",
                    "risk": "medium",
                    "entity": "strong",
                    "trust": "missing",
                    "conf": 0.82,
                    "approved": [],
                    "blocked": ["proof_points"],
                    "r": ["missing_source_url", "material_field_changed"],
                }
            ]
        }
    )

    result = build_material_diff_llm_shadow(_material_diff_report(), llm=llm)

    assert result["status"] == "ok"
    assert result["model_effect"] is True
    assert result["assessment_count"] == 1
    assert result["summary"]["verdict_counts"]["keep_manual_review"] == 1
    assert result["summary"]["source_trust_counts"]["missing"] == 1
    assert result["summary"]["repair_action_counts"]["backfill_source_url_or_remove_material"] == 1
    assert result["assessments"][0]["blocked_material_fields"] == ["proof_points"]
    assert result["repair_plan"][0]["action"] == "backfill_source_url_or_remove_material"
    assert result["repair_plan"][0]["lane"] == "provenance_repair"
    assert result["repair_plan"][0]["search_hints"]
    assert result["summary"]["decision_packet_count"] == 1
    assert result["summary"]["decision_packet_action_counts"]["source_url_attached_or_exclude_unsourced_quote"] == 1
    assert result["decision_packets"][0]["recommended_decision"] == "source_url_attached_or_exclude_unsourced_quote"
    assert "replace_with_sourced_equivalent" in result["decision_packets"][0]["allowed_decisions"]
    assert result["decision_packets"][0]["requires_recompute"] is True
    assert llm.calls[0]["schema_name"] == "brand3_material_diff_shadow"
    assert llm.calls[0]["json_schema"] == material_diff_response_schema()


def test_material_diff_shadow_prefers_gemini_native_structured_output() -> None:
    llm = NativeFakeMaterialDiffLLM(
        {
            "items": [
                {
                    "id": "workorder:material_audit:273",
                    "v": "approve_vnext_material",
                    "risk": "low",
                    "entity": "strong",
                    "trust": "acceptable",
                    "conf": 0.88,
                    "approved": ["proof_points"],
                    "blocked": [],
                    "r": ["source_supported"],
                }
            ]
        }
    )

    result = build_material_diff_llm_shadow(_material_diff_report(), llm=llm)

    assert result["status"] == "ok"
    assert result["transport"] == "gemini_native"
    assert result["summary"]["auto_clear_candidate_count"] == 1
    assert result["summary"]["repair_action_counts"]["manual_fast_approve_candidate"] == 1
    assert result["repair_plan"][0]["action"] == "manual_fast_approve_candidate"
    assert len(llm.native_calls) == 1
    assert llm.native_calls[0]["json_schema"] == material_diff_response_schema()


def test_material_diff_shadow_rejects_partial_payload() -> None:
    llm = FakeMaterialDiffLLM({"items": []})

    result = build_material_diff_llm_shadow(_material_diff_report(), llm=llm)

    assert result["status"] == "error"
    assert result["model_effect"] is False
    assert result["reason"] == "schema_validation_error"
    assert result["assessment_count"] == 0
    assert result["attempt_count"] == 2


def test_material_diff_shadow_is_ok_without_candidates() -> None:
    result = build_material_diff_llm_shadow({"work_orders": []})

    assert result["status"] == "ok"
    assert result["candidate_count"] == 0
    assert result["model_effect"] is False


def test_material_diff_shadow_routes_weak_source_to_quarantine_repair() -> None:
    llm = FakeMaterialDiffLLM(
        {
            "items": [
                {
                    "id": "workorder:material_audit:273",
                    "v": "keep_manual_review",
                    "risk": "medium",
                    "entity": "strong",
                    "trust": "weak",
                    "conf": 0.83,
                    "approved": [],
                    "blocked": ["proof_points"],
                    "r": ["security_source_review"],
                }
            ]
        }
    )

    result = build_material_diff_llm_shadow(_material_diff_report(), llm=llm)

    assert result["status"] == "ok"
    assert result["repair_plan"][0]["action"] == "quarantine_weak_source_from_material"
    assert result["repair_plan"][0]["lane"] == "source_trust_repair"
    assert result["decision_packets"][0]["recommended_decision"] == "quarantine_source_from_material"
    assert result["decision_packets"][0]["record"]["decision"] == "quarantine_source_from_material"
