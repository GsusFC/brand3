from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIBRARY_ROOT = ROOT / "examples" / "perceptual_library"
SCHEMA_PATH = LIBRARY_ROOT / "schema" / "perceptual_case_record_schema.json"
PILOT_SELECTION_PATH = LIBRARY_ROOT / "pilots" / "floc_perceptual_pilot_selection.json"
CHARMS_RECORD_PATH = LIBRARY_ROOT / "cases" / "charms" / "perceptual_case_record.json"
D4DATA_RECORD_PATH = LIBRARY_ROOT / "cases" / "d4data" / "perceptual_case_record.json"
GRANDVALIRA_RECORD_PATH = LIBRARY_ROOT / "cases" / "grandvalira" / "perceptual_case_record.json"
CASE_RECORD_PATHS = [CHARMS_RECORD_PATH, D4DATA_RECORD_PATH, GRANDVALIRA_RECORD_PATH]


REQUIRED_LAYERS = {
    "extracted_facts",
    "visual_observations",
    "strategic_interpretations",
    "unsupported_or_low_confidence_inferences",
}

REQUIRED_EVIDENCE_FIELDS = {"source_type", "source_id", "support_level"}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _evidenced_items(record: dict):
    for layer in REQUIRED_LAYERS:
        for item in record[layer]:
            yield layer, item
    for item in record["contradictions"]:
        yield "contradictions", item


def _case_records() -> list[dict]:
    return [_load_json(path) for path in CASE_RECORD_PATHS]


def test_perceptual_case_schema_declares_operational_layers_and_boundaries():
    schema = _load_json(SCHEMA_PATH)

    assert REQUIRED_LAYERS.issubset(schema["required_top_level_fields"])
    assert "contradictions" in schema["required_top_level_fields"]
    assert schema["layer_contract"]["extracted_facts"]["requires_evidence"] is True
    assert schema["layer_contract"]["unsupported_or_low_confidence_inferences"]["requires_human_review"] is True
    assert schema["evidence_contract"]["required_fields"] == ["source_type", "source_id", "support_level"]
    assert "scoring" in schema["non_goals"]
    assert "runtime_ingestion" in schema["non_goals"]


def test_pilot_selection_uses_three_contrasting_cases_without_scaling_records():
    selection = _load_json(PILOT_SELECTION_PATH)

    pilots = selection["selected_pilots"]
    assert [pilot["case_id"] for pilot in pilots] == ["charms", "d4data", "grandvalira_resorts"]
    assert {pilot["role"] for pilot in pilots} == {
        "editorial_minimal_atmospheric",
        "experimental_motion_heavy",
        "corporate_system",
    }
    assert CHARMS_RECORD_PATH.exists()
    assert D4DATA_RECORD_PATH.exists()
    assert GRANDVALIRA_RECORD_PATH.exists()
    assert selection["guardrails"]["scoring_changes"] is False
    assert selection["guardrails"]["runtime_changes"] is False


def test_charms_d4data_and_grandvalira_records_validate_against_schema_contract():
    schema = _load_json(SCHEMA_PATH)
    required_fields = set(schema["required_top_level_fields"])

    records = _case_records()

    assert {record["case"]["case_id"] for record in records} == {"charms", "d4data", "grandvalira"}
    for record in records:
        assert required_fields.issubset(record), record["record_id"]
        assert record["schema_version"] == schema["schema_version"]
        assert REQUIRED_LAYERS.issubset(record)
        assert record["method_boundaries"]["no_scoring"] is True
        assert record["method_boundaries"]["no_runtime_changes"] is True
        assert record["method_boundaries"]["no_visual_signature_runtime_changes"] is True
        assert record["validation"]["ready_for_scoring"] is False
        assert record["validation"]["ready_for_runtime"] is False
        assert all(item["confidence"] == "high" for item in record["extracted_facts"])
        assert all(item["confidence"] == "low" for item in record["unsupported_or_low_confidence_inferences"])
        assert all(
            item["requires_human_review"] is True
            for item in record["unsupported_or_low_confidence_inferences"]
        )


def test_every_record_item_has_evidence_anchor():
    for record in _case_records():
        for layer, item in _evidenced_items(record):
            assert item["evidence"], {record["record_id"]: {layer: item["id"]}}
            for evidence in item["evidence"]:
                assert REQUIRED_EVIDENCE_FIELDS.issubset(evidence), {
                    record["record_id"]: {layer: item["id"], "evidence": evidence}
                }
                assert evidence["source_type"] in {
                    "public_case_page",
                    "public_case_copy",
                    "public_case_metadata",
                    "local_prior_case_artifact",
                    "capture",
                    "human_review_note",
                }
                assert evidence["support_level"] in {
                    "direct",
                    "corroborating",
                    "copy_based",
                    "weak_inference",
                    "negative_evidence",
                }


def test_confidence_semantics_are_enforced_by_fixture_shape():
    for record in _case_records():
        for layer, item in _evidenced_items(record):
            support_levels = {evidence["support_level"] for evidence in item["evidence"]}
            if item["confidence"] == "high":
                assert "direct" in support_levels, {record["record_id"]: {layer: item["id"]}}
            if item["confidence"] == "low":
                assert item.get("requires_human_review") is True, {
                    record["record_id"]: {layer: item["id"]}
                }
                assert "weak_inference" in support_levels, {record["record_id"]: {layer: item["id"]}}


def test_contradictions_are_explicit_claim_signal_pairs():
    for record in _case_records():
        contradictions = record["contradictions"]
        assert contradictions
        for item in contradictions:
            assert item["stated_claim"]
            assert item["observed_signal"]
            assert item["contradiction_level"] in {"none", "soft", "moderate", "strong", "unverified"}
            assert item["confidence"] in {"high", "medium", "low"}
            assert item["requires_human_review"] is True
            assert item["evidence"]
