from src.sv9_flow.contracts import BrandEvidencePack, EvidenceRecord
from src.sv9_flow.interpretation_llm_worker import (
    FLOW_INTERPRETATION_PROMPT_VERSION,
    block_interpretation_response_schema,
    brand_interpretation_response_schema,
    build_brand_interpretation_with_llm,
    normalize_llm_interpretation_response,
    _block_user_prompt,
    _user_prompt,
)


def test_normalize_llm_interpretation_requires_valid_evidence_refs() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="raw_inputs.0",
                source="homepage",
                evidence_type="raw_input",
                content="Acme helps finance teams close faster.",
            )
        ],
    )
    raw = {
        "prompt_version": FLOW_INTERPRETATION_PROMPT_VERSION,
        "blocks": {
            "mission": {
                "detected": True,
                "content": "Help finance teams close faster.",
                "confidence": "high",
                "evidence_refs": ["raw_inputs.0"],
                "rationale": "The homepage states this directly.",
            },
            "vision": {
                "detected": True,
                "content": "Own the finance category.",
                "confidence": "medium",
                "evidence_refs": ["missing.ref"],
                "rationale": "Invalid ref should prevent detection.",
            },
        },
        "limitations": ["limited_sample"],
    }

    interpretation = normalize_llm_interpretation_response(raw, pack)

    assert interpretation.blocks["mission"]["detected"] is True
    assert interpretation.evidence_refs["mission"] == ["raw_inputs.0"]
    assert interpretation.blocks["vision"]["detected"] is False
    assert "vision_dropped_missing_evidence_refs" in interpretation.limitations
    assert "limited_sample" in interpretation.limitations


def test_normalize_llm_interpretation_rejects_refs_outside_block_shortlist() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(ref="raw_inputs.0", source="homepage", evidence_type="raw_input", content="Mission text."),
            EvidenceRecord(ref="features.0", source="feature", evidence_type="tone", content="Personality text."),
        ],
    )
    raw = {
        "blocks": {
            "mission": {
                "detected": True,
                "content": "Mission text.",
                "confidence": "high",
                "evidence_refs": ["features.0"],
                "rationale": "Existing ref, wrong shortlist.",
            }
        },
        "limitations": [],
    }

    interpretation = normalize_llm_interpretation_response(
        raw,
        pack,
        block_evidence_shortlists={"mission": ["raw_inputs.0"]},
    )

    assert interpretation.blocks["mission"]["detected"] is False
    assert "mission_dropped_missing_evidence_refs" in interpretation.limitations


def test_normalize_llm_interpretation_fills_missing_blocks_as_not_detected() -> None:
    pack = BrandEvidencePack(brand_name="Acme", url="https://acme.example")

    interpretation = normalize_llm_interpretation_response({"blocks": {}}, pack)

    assert interpretation.blocks["mission"]["detected"] is False
    assert interpretation.blocks["magnetism"]["detected"] is False
    assert interpretation.evidence_refs == {}


def test_llm_worker_marks_empty_provider_payload_as_empty() -> None:
    class EmptyLLM:
        api_key = "test"
        last_failure_reason = "llm_error"
        call_failures = [{"reason": "llm_error", "error_type": "empty_response", "response_empty": True}]

        def _call_json(self, *args, **kwargs):
            return {}

    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="raw_inputs.0",
                source="homepage",
                evidence_type="raw_input",
                content="Acme helps teams ship.",
            )
        ],
    )

    interpretation, debug = build_brand_interpretation_with_llm(pack, llm=EmptyLLM())

    assert debug["status"] == "empty"
    assert debug["detected_count"] == 0
    assert len(debug["failed_blocks"]) == 9
    assert len(debug["block_failures"]) == 9
    assert debug["block_failures"][0]["reason"] == "empty_or_parse_failed"
    assert debug["failure_reason"] == "llm_error"
    assert debug["failure"] == {
        "reason": "llm_error",
        "error_type": "empty_response",
        "provider_status": None,
        "response_empty": True,
    }
    assert debug["block_call_debug"][0] == {
        "json_mode_empty": True,
        "text_fallback_attempted": False,
        "text_fallback_empty": None,
        "last_failure": {
            "reason": "llm_error",
            "error_type": "empty_response",
            "response_empty": True,
            "json_parse_error": None,
        },
        "block": "mission",
    }
    assert interpretation.blocks["mission"]["detected"] is False


def test_llm_worker_can_build_interpretation_per_block() -> None:
    class PerBlockLLM:
        api_key = "test"
        last_failure_reason = None
        call_failures = []

        def __init__(self):
            self.calls = []

        def _call_json(self, system, user, **kwargs):
            self.calls.append((system, user, kwargs))
            if '"block": "mission"' in user:
                return {
                    "detected": True,
                    "content": "Help teams ship.",
                    "confidence": "high",
                    "evidence_refs": ["raw_inputs.0"],
                    "rationale": "Homepage states it.",
                    "limitations": [],
                }
            return {
                "detected": False,
                "content": "",
                "confidence": "low",
                "evidence_refs": [],
                "rationale": "Not enough evidence.",
                "limitations": [],
            }

    llm = PerBlockLLM()
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(ref="raw_inputs.0", source="homepage", evidence_type="raw_input", content="Help teams ship.")
        ],
    )

    interpretation, debug = build_brand_interpretation_with_llm(
        pack,
        llm=llm,
        block_evidence_shortlists={"mission": ["raw_inputs.0"]},
    )

    assert len(llm.calls) == 9
    assert all(call[2]["json_schema"] is None for call in llm.calls)
    assert debug["mode"] == "per_block"
    assert debug["status"] == "ok"
    assert debug["detected_count"] == 1
    assert debug["block_call_debug"][0]["json_mode_empty"] is False
    assert debug["block_call_debug"][0]["text_fallback_attempted"] is False
    assert "mission" not in debug["failed_blocks"]
    assert "vision" not in debug["failed_blocks"]
    assert any(item["block"] == "vision" and item["reason"] == "insufficient_evidence" for item in debug["block_failures"])
    assert interpretation.blocks["mission"]["detected"] is True
    assert interpretation.evidence_refs["mission"] == ["raw_inputs.0"]


def test_llm_worker_falls_back_to_text_call_when_json_mode_is_empty() -> None:
    class TextFallbackLLM:
        api_key = "test"
        last_failure_reason = None
        call_failures = []

        def __init__(self):
            self.json_calls = 0
            self.text_calls = 0

        def _call_json(self, system, user, **kwargs):
            self.json_calls += 1
            return {}

        def _call(self, system, user, max_tokens=900):
            self.text_calls += 1
            if '"block": "mission"' in user:
                return """{
                  "detected": true,
                  "content": "Help teams ship.",
                  "confidence": "high",
                  "evidence_refs": ["raw_inputs.0"],
                  "rationale": "Homepage states it.",
                  "limitations": []
                }"""
            return """{
              "detected": false,
              "content": "",
              "confidence": "low",
              "evidence_refs": [],
              "rationale": "Not enough evidence.",
              "limitations": []
            }"""

    llm = TextFallbackLLM()
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(ref="raw_inputs.0", source="homepage", evidence_type="raw_input", content="Help teams ship.")
        ],
    )

    interpretation, debug = build_brand_interpretation_with_llm(
        pack,
        llm=llm,
        block_evidence_shortlists={"mission": ["raw_inputs.0"]},
    )

    assert llm.json_calls == 9
    assert llm.text_calls == 9
    assert debug["detected_count"] == 1
    assert debug["block_call_debug"][0]["json_mode_empty"] is True
    assert debug["block_call_debug"][0]["text_fallback_attempted"] is True
    assert debug["block_call_debug"][0]["text_fallback_empty"] is False
    assert interpretation.blocks["mission"]["detected"] is True


def test_llm_worker_text_fallback_accepts_fenced_json() -> None:
    class FencedTextLLM:
        api_key = "test"
        last_failure_reason = None
        call_failures = []

        def _call_json(self, system, user, **kwargs):
            return {}

        def _call(self, system, user, max_tokens=900):
            if '"block": "mission"' in user:
                return """```json
                {
                  "detected": true,
                  "content": "Help teams ship.",
                  "confidence": "high",
                  "evidence_refs": ["raw_inputs.0"],
                  "rationale": "Homepage states it.",
                  "limitations": []
                }
                ```"""
            return """No clear evidence.
            {
              "detected": false,
              "content": "",
              "confidence": "low",
              "evidence_refs": [],
              "rationale": "Not enough evidence.",
              "limitations": []
            }"""

    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(ref="raw_inputs.0", source="homepage", evidence_type="raw_input", content="Help teams ship.")
        ],
    )

    interpretation, debug = build_brand_interpretation_with_llm(
        pack,
        llm=FencedTextLLM(),
        block_evidence_shortlists={"mission": ["raw_inputs.0"]},
    )

    assert debug["detected_count"] == 1
    assert interpretation.blocks["mission"]["detected"] is True


def test_user_prompt_contains_complete_output_contract() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(ref="raw_inputs.0", source="homepage", evidence_type="raw_input", content="Mission text.")
        ],
    )

    prompt = _user_prompt(pack, block_evidence_shortlists={"mission": ["raw_inputs.0"]})

    assert '"output_contract"' in prompt
    assert "top-level keys: prompt_version, blocks, limitations" in prompt
    assert '"mission"' in prompt
    assert '"vision"' in prompt
    assert '"magnetism"' in prompt


def test_block_interpretation_schema_requires_single_block_shape() -> None:
    schema = block_interpretation_response_schema()

    assert schema["required"] == ["detected", "content", "confidence", "evidence_refs", "rationale", "limitations"]


def test_brand_interpretation_schema_requires_all_blocks_shape() -> None:
    schema = brand_interpretation_response_schema()

    assert schema["required"] == ["prompt_version", "blocks", "limitations"]
    assert "mission" in schema["properties"]["blocks"]["required"]
    assert "brand_idea" in schema["properties"]["blocks"]["required"]


def test_block_prompt_adds_guidance_for_brand_idea_and_value_proposition() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="features.0",
                source="legacy_feature",
                evidence_type="diferenciacion.uniqueness",
                content="Unique methodology and vocabulary.",
            )
        ],
    )

    brand_idea_prompt = _block_user_prompt(pack, block="brand_idea", evidence_refs=["features.0"])
    value_prompt = _block_user_prompt(pack, block="value_proposition", evidence_refs=["features.0"])

    assert "ownable language" in brand_idea_prompt
    assert "Do not infer brand_idea from visual style alone" in brand_idea_prompt
    assert "positive" in brand_idea_prompt
    assert "negative" in brand_idea_prompt
    assert "Visual polish alone is not a brand idea" in brand_idea_prompt
    assert "concrete value" in value_prompt
    assert "Prefer a concrete offer statement" in value_prompt
    assert "The evidence states who receives what concrete benefit" in value_prompt
    assert "A broad mission claim is not enough" in value_prompt


def test_block_prompt_uses_small_required_json_contract() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(ref="raw_inputs.0", source="homepage", evidence_type="raw_input", content="Mission text.")
        ],
    )

    prompt = _block_user_prompt(pack, block="mission", evidence_refs=["raw_inputs.0"])

    assert '"required_json"' in prompt
    assert '"output_contract"' not in prompt
    assert "Return only one valid JSON object with the required_json keys." in prompt
