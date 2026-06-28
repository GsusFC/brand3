from scripts.sv9_flow_local_eval import (
    SV9_FLOW_LOCAL_EVAL_VERSION,
    build_local_eval,
    compare_flow_repeats,
)


def test_compare_flow_repeats_detects_stable_structure_but_textual_drift() -> None:
    first = _shadow_payload(content="Help teams ship.")
    second = _shadow_payload(content="Help teams ship faster.")

    stability = compare_flow_repeats([first, second])

    assert stability["repeat_count"] == 2
    assert stability["same_detected_blocks"] is True
    assert stability["same_tile_effects"] is True
    assert stability["same_block_detection_decisions"] is True
    assert stability["same_block_content_hashes"] is False
    assert stability["changed_block_detection_decisions"] == []
    assert stability["changed_content_blocks"] == ["mission"]


def test_compare_flow_repeats_detects_block_detection_drift() -> None:
    first = _shadow_payload(
        block_detection_decisions=[
            {
                "block": "magnetism",
                "outcome": "insufficient_evidence",
                "evidence_refs": [],
                "support_terms": [],
                "weaken_terms": [],
                "limitation_code": "magnetism_insufficient_evidence_refs",
            }
        ]
    )
    second = _shadow_payload(
        block_detection_decisions=[
            {
                "block": "magnetism",
                "outcome": "weakens_detection",
                "evidence_refs": ["raw_inputs.0"],
                "support_terms": [],
                "weaken_terms": ["stagnation"],
                "limitation_code": "magnetism_structural_negative_evidence",
            }
        ]
    )

    stability = compare_flow_repeats([first, second])

    assert stability["same_detected_blocks"] is True
    assert stability["same_tile_effects"] is True
    assert stability["same_block_detection_decisions"] is False
    assert stability["changed_block_detection_decisions"] == ["magnetism"]


def test_build_local_eval_runs_cached_and_flow_repeats() -> None:
    calls = []

    report_only_by_source = {}

    def shadow_builder(run_id: int, **kwargs):
        calls.append((run_id, kwargs["interpretation_source"]))
        report_only_by_source.setdefault(kwargs["interpretation_source"], []).append(kwargs["report_only"])
        if kwargs["interpretation_source"] == "flow-llm":
            return _shadow_payload(run_id=run_id, source="flow_llm", interpretation_source="flow-llm")
        return _shadow_payload(run_id=run_id, source="sv9_detection_cache", interpretation_source="cached-pass1")

    payload = build_local_eval(
        [123],
        db_path="/tmp/local.sqlite",
        include_flow_llm=True,
        flow_repeat=2,
        shadow_builder=shadow_builder,
    )

    assert payload["schema_version"] == SV9_FLOW_LOCAL_EVAL_VERSION
    assert payload["db_path"] == "/tmp/local.sqlite"
    assert payload["summary"]["run_count"] == 1
    assert payload["summary"]["flow_llm_run_count"] == 1
    assert payload["summary"]["flow_llm_unstable_detected_run_ids"] == []
    assert payload["summary"]["flow_llm_unstable_block_detection_run_ids"] == []
    assert calls == [(123, "cached-pass1"), (123, "flow-llm"), (123, "flow-llm")]
    assert report_only_by_source == {"cached-pass1": [True], "flow-llm": [False, False]}


def _shadow_payload(
    *,
    run_id: int = 123,
    source: str = "flow_llm",
    interpretation_source: str = "flow-llm",
    content: str = "Help teams ship.",
    block_detection_decisions: list[dict] | None = None,
) -> dict:
    return {
        "source_run_id": run_id,
        "detection_source": source,
        "interpretation_source": interpretation_source,
        "visual_signature_present": True,
        "report": {
            "brand_name": "Acme",
            "url": "https://acme.example",
            "counts": {
                "evidence_records": 1,
                "interpretation_blocks": 1,
                "tile_signals": 1,
                "limitations": 0,
            },
            "tile_signal_effects": {"supports": 1},
            "tile_signal_effects_by_component": {"mission": {"supports": 1}},
            "limitations": [],
        },
        "candidate": {
            "interpretation": {
                "blocks": {
                    "mission": {
                        "detected": True,
                        "content": content,
                        "confidence": "high",
                    }
                }
            }
        },
        "llm_payload": {
            "status": "ok",
            "detected_count": 1,
            "block_failures": [],
            "block_detection_decisions": block_detection_decisions or [
                {
                    "block": "magnetism",
                    "outcome": "insufficient_evidence",
                    "evidence_refs": [],
                    "support_terms": [],
                    "weaken_terms": [],
                    "limitation_code": "magnetism_insufficient_evidence_refs",
                }
            ],
        },
    }
