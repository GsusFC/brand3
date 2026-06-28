from scripts.sv9_flow_decision_report import (
    SV9_FLOW_DECISION_REPORT_VERSION,
    build_decision_report,
    render_markdown_report,
)


def test_build_decision_report_summarizes_stability_and_decisions() -> None:
    payload = {
        "schema_version": "sv9-flow-local-eval-v1",
        "db_path": "data/brand3.sqlite3",
        "runs": [
            _eval_run(run_id=343, same_decisions=True),
            _eval_run(run_id=346, same_decisions=False, changed_blocks=["magnetism"]),
        ],
    }

    report = build_decision_report(payload)

    assert report["schema_version"] == SV9_FLOW_DECISION_REPORT_VERSION
    assert report["summary"] == {
        "run_count": 2,
        "stable_block_decision_runs": 1,
        "stable_detected_runs": 2,
        "stable_tile_effect_runs": 2,
        "textual_drift_runs": [343, 346],
        "changed_block_detection_runs": [{"run_id": 346, "blocks": ["magnetism"]}],
    }
    assert report["runs"][0]["flow_decisions"][0]["outcomes"] == {
        "magnetism": "weakens_detection",
        "values": "insufficient_evidence",
        "vision": "insufficient_evidence",
    }
    assert report["runs"][0]["flow_decisions"][0]["negative_terms"] == {
        "magnetism": ["stagnation"],
    }


def test_render_markdown_report_includes_human_readable_decisions() -> None:
    report = build_decision_report(
        {
            "schema_version": "sv9-flow-local-eval-v1",
            "db_path": "data/brand3.sqlite3",
            "runs": [_eval_run(run_id=343, same_decisions=True)],
        }
    )

    markdown = render_markdown_report(report)

    assert "# SV9 Flow Decision Report" in markdown
    assert "stable block decisions: `1/1`" in markdown
    assert "## Run 343 - COFI" in markdown
    assert "repeat 1 decisions: `magnetism: weakens_detection" in markdown
    assert "repeat 1 negative terms: `magnetism: stagnation`" in markdown


def _eval_run(*, run_id: int, same_decisions: bool, changed_blocks: list[str] | None = None) -> dict:
    return {
        "run_id": run_id,
        "cached_pass1": {
            "brand_name": "COFI",
            "url": "https://cofi.example",
            "tile_signal_effects": {"supports": 13, "insufficient_evidence": 7},
        },
        "flow_llm": [
            {
                "brand_name": "COFI",
                "url": "https://cofi.example",
                "detected_blocks": ["mission", "value_proposition"],
                "tile_signal_effects": {"supports": 12, "insufficient_evidence": 8},
                "block_detection_decisions": [
                    {
                        "block": "magnetism",
                        "outcome": "weakens_detection",
                        "evidence_refs": ["raw_inputs.8"],
                        "support_terms": [],
                        "weaken_terms": ["stagnation"],
                        "limitation_code": "magnetism_structural_negative_evidence",
                    },
                    {
                        "block": "values",
                        "outcome": "insufficient_evidence",
                        "evidence_refs": [],
                        "support_terms": [],
                        "weaken_terms": [],
                        "limitation_code": "values_insufficient_evidence_refs",
                    },
                    {
                        "block": "vision",
                        "outcome": "insufficient_evidence",
                        "evidence_refs": ["features.14"],
                        "support_terms": [],
                        "weaken_terms": [],
                        "limitation_code": "vision_structural_gate_rejected",
                    },
                ],
            }
        ],
        "flow_llm_stability": {
            "repeat_count": 2,
            "same_block_detection_decisions": same_decisions,
            "same_detected_blocks": True,
            "same_tile_effects": True,
            "same_block_content_hashes": False,
            "changed_block_detection_decisions": changed_blocks or [],
            "changed_content_blocks": ["mission"],
        },
    }
