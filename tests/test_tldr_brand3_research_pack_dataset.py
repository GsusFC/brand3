from __future__ import annotations

import json
from pathlib import Path


DATASET_PATH = Path("examples/benchmarks/tldr_brand3_research_pack/dataset.json")
README_PATH = Path("examples/benchmarks/tldr_brand3_research_pack/README.md")
NOTES_DIR = Path("examples/benchmarks/tldr_brand3_research_pack/notes")
TLDR_KEYS = [
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


def _load_dataset() -> dict:
    return json.loads(DATASET_PATH.read_text())


def _assert_tldr_contract(payload: dict) -> None:
    blocks = payload["tldr_brand3"]
    assert set(blocks.keys()) == set(TLDR_KEYS)
    for key in TLDR_KEYS:
        block = blocks[key]
        assert block["block"] == key
        assert block["question"]
        if block["claim_type"] != "absent":
            assert block["evidence_used"], key
        else:
            assert block["mode"] == "not_detected"


def test_dataset_json_is_valid_and_has_expected_cases() -> None:
    dataset = _load_dataset()
    assert dataset["version"] == "tldr_brand3_research_pack_dataset_v0_1"
    assert len(dataset["cases"]) == 7
    assert {case["source_url"] for case in dataset["cases"]} == {
        "https://base44.com",
        "https://bokeroon.com",
        "https://fly.io",
        "https://every.to/about",
        "https://lab.naturaumana.ai",
        "https://creatify.ai/es/",
        "https://www.heygen.com",
    }
    assert dataset["missing_cases"][0]["source_url"] == "https://pinata.cloud"


def test_each_case_has_research_pack_and_tldr_contract() -> None:
    dataset = _load_dataset()
    for case in dataset["cases"]:
        assert case["source_url"]
        assert case["research_pack"]["version"] == "brand_research_pack_v0_1"
        assert case["research_pack"]["input_url"]
        _assert_tldr_contract(case["analyst_tldr"])
        if case["scanner_current_tldr"] is not None:
            _assert_tldr_contract(case["scanner_current_tldr"])


def test_differences_include_taxonomy_when_applicable() -> None:
    dataset = _load_dataset()
    by_url = {case["source_url"]: case for case in dataset["cases"]}
    assert "structural_noise_selected" in by_url["https://base44.com"]["differences"]["error_taxonomy"]
    assert "rhetorical_question_as_purpose" in by_url["https://bokeroon.com"]["differences"]["error_taxonomy"]
    assert "audited_surface_too_narrow" in by_url["https://lab.naturaumana.ai"]["differences"]["error_taxonomy"]


def test_notes_and_index_exist() -> None:
    assert README_PATH.exists()
    assert NOTES_DIR.exists()
    assert (NOTES_DIR / "base44.md").exists()
    assert (NOTES_DIR / "bokeroon.md").exists()
    assert (NOTES_DIR / "heygen.md").exists()
