from __future__ import annotations

from src.features.magnetism.block_interpreters import (
    TLDR_BLOCK_INTERPRETER_SPECS,
    get_tldr_block_interpreter_spec,
)


REQUIRED_SPEC_KEYS = {
    "block",
    "task",
    "primary_question",
    "source_layers",
    "look_for",
    "reject",
    "minimum_evidence_rule",
    "claim_type_rules",
    "mode_rules",
    "confidence_rules",
    "human_review_triggers",
    "output_style",
}


def test_migrated_tldr_block_specs_have_executable_contract() -> None:
    assert set(TLDR_BLOCK_INTERPRETER_SPECS) == {
        "mission",
        "vision",
        "value_proposition",
    }
    for block, spec in TLDR_BLOCK_INTERPRETER_SPECS.items():
        assert REQUIRED_SPEC_KEYS.issubset(spec), block
        assert spec["block"] == block
        assert spec["task"]
        assert spec["primary_question"].endswith("?")
        assert spec["source_layers"]
        assert spec["look_for"]
        assert isinstance(spec["reject"], list)
        assert spec["minimum_evidence_rule"]
        assert spec["claim_type_rules"]
        assert spec["mode_rules"]
        assert spec["confidence_rules"]
        assert isinstance(spec["human_review_triggers"], list)
        assert spec["output_style"]


def test_get_tldr_block_interpreter_spec_returns_copy() -> None:
    spec = get_tldr_block_interpreter_spec("mission")
    assert spec is not None
    spec["task"] = "mutated"

    fresh = get_tldr_block_interpreter_spec("mission")
    assert fresh is not None
    assert fresh["task"] != "mutated"


def test_unmigrated_block_has_no_interpreter_spec() -> None:
    assert get_tldr_block_interpreter_spec("personality") is None
