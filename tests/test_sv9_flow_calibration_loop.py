from __future__ import annotations

import json

from scripts.sv9_flow_calibration_loop import (
    build_calibration_packet,
    build_review_queue,
    render_loop_summary,
    write_calibration_packet,
)
from scripts.sv9_flow_sv9_batch_report import build_batch_report


def test_calibration_packet_builds_manifest_cost_and_review_queue() -> None:
    payloads = [
        _payload("Stable", delta=2),
        _payload(
            "Linear",
            delta=-1,
            components={
                "core_purpose": _component(delta=-4, flow="scored", legacy="scored"),
            },
        ),
        _payload(
            "Mistral",
            delta=16,
            components={
                "coherencia": _component(delta=4, flow="scored", legacy="scored"),
            },
        ),
    ]

    packet = build_calibration_packet(
        payloads,
        sources=["stable.json", "linear.json", "mistral.json"],
        cohort_name="unit",
        budget_usd=5.0,
    )

    assert packet["schema_version"] == "sv9-flow-calibration-loop-v1"
    assert packet["batch_report"]["summary"]["acceptable"] == 1
    assert packet["batch_report"]["summary"]["review"] == 2
    assert packet["cohort_manifest"]["run_count"] == 3
    assert packet["cohort_manifest"]["entries"][1]["risk_tags"] == [
        "assessment_kind:policy_review",
        "visual_acquisition_absent",
    ]
    assert packet["cost_observation"]["budget_usd"] == 5.0
    assert packet["cost_observation"]["usage_metadata_available"] is False
    assert packet["cost_observation"]["estimated_llm_calls"] == {
        "flow_interpretation_per_block": 27,
        "flow_sv9_evaluator_components": 30,
        "legacy_sv9_evaluator_components": 30,
        "total_upper_bound_without_cache": 87,
    }
    assert packet["review_queue"]["priority_counts"] == {"P1": 1, "P3": 1}


def test_calibration_packet_uses_observed_llm_usage_when_present() -> None:
    payload = _payload("Observed", delta=1)
    payload["llm_usage"] = {
        "roles": {
            "flow_interpretation": {
                "cache_hits": 2,
                "cache_misses": 3,
                "cache_writes": 1,
                "provider_calls": 3,
                "usage_metadata_available": True,
            },
            "sv9_evaluator": {
                "cache_hits": 4,
                "cache_misses": 5,
                "cache_writes": 2,
                "provider_calls": 5,
                "usage_metadata_available": False,
            },
        }
    }

    packet = build_calibration_packet([payload], sources=["observed.json"], cohort_name="unit")
    cost = packet["cost_observation"]

    assert cost["cost_observability"] == "observed_call_count"
    assert cost["cache_observability"]["available"] is True
    assert cost["usage_metadata_available"] is True
    assert cost["observed_llm_usage"]["provider_calls"] == 8
    assert cost["observed_llm_usage"]["cache_hits"] == 6
    assert cost["observed_llm_usage"]["roles"]["flow_interpretation"]["provider_calls"] == 3
    assert "observed call/cache accounting" in render_loop_summary(packet)


def test_review_queue_prioritizes_blockers_not_evaluated_and_core_deltas() -> None:
    report = build_batch_report(
        [
            _payload("Broken", delta=0, flow_not_evaluated=["core_purpose"]),
            _payload("Mafer", delta=-12, components={"magnetism": _component(delta=-4)}),
            _payload("Factorial", delta=6, components={"attributes": _component(delta=4)}),
        ]
    )

    queue = build_review_queue(report)

    assert [item["priority"] for item in queue["items"]] == ["P0", "P1", "P2"]
    assert queue["items"][0]["priority_reason"] == "flow_component_not_evaluated"
    assert queue["items"][1]["component_focus"] == ["magnetism"]
    assert queue["items"][2]["component_focus"] == ["attributes"]


def test_review_queue_keeps_material_gate_overrides_visible() -> None:
    report = build_batch_report(
        [
            _payload(
                "Pleo",
                delta=1,
                components={"magnetism": _component(delta=4)},
                gate_override_block="magnetism",
            )
        ]
    )

    queue = build_review_queue(report)

    assert queue["items"][0]["priority"] == "P2"
    assert "magnetism" in queue["items"][0]["component_focus"]
    assert queue["items"][0]["gate_overrides"][0]["block"] == "magnetism"


def test_review_queue_includes_gate_candidates_even_without_material_delta() -> None:
    payload = _payload(
        "Quiet Candidate",
        delta=1,
        gate_override_block="magnetism",
        gate_override_source="llm_rejected_gate_candidate",
    )
    packet = build_calibration_packet([payload], sources=["quiet.json"], cohort_name="unit")

    items = packet["review_queue"]["items"]
    assert len(items) == 1
    assert items[0]["priority"] == "P3"
    assert items[0]["priority_reason"] == "gate_positive_llm_negative_candidate"
    assert items[0]["component_focus"] == ["magnetism"]
    assert items[0]["recommended_next_step"] == (
        "confirm the LLM rejection of the gate candidate against source refs"
    )
    entry = packet["cohort_manifest"]["entries"][0]
    assert "gate_candidate:magnetism" in entry["risk_tags"]
    assert entry["gate_authority"] == "veto_only"


def test_write_calibration_packet_persists_expected_artifacts(tmp_path) -> None:
    packet = build_calibration_packet([_payload("Stable", delta=1)], sources=["stable.json"], cohort_name="unit")

    write_calibration_packet(packet, tmp_path)

    expected = {
        "cohort_manifest.json",
        "cost_observation.json",
        "batch_report.json",
        "batch_report.md",
        "review_queue.json",
        "review_queue.md",
        "loop_summary.md",
    }
    assert expected == {path.name for path in tmp_path.iterdir()}
    saved = json.loads((tmp_path / "cost_observation.json").read_text(encoding="utf-8"))
    assert saved["cost_observability"] == "call_count_estimate_only"


def _payload(
    brand: str,
    *,
    delta: int,
    components: dict | None = None,
    flow_not_detected: list[str] | None = None,
    flow_not_evaluated: list[str] | None = None,
    visual: bool = False,
    gate_override_block: str | None = None,
    gate_override_source: str = "gate_override",
) -> dict:
    component_payload = {
        "magnetism": _component(delta=0),
        **(components or {}),
    }
    flow_components = {
        "magnetism": {"score": 4, "status": "scored"},
        **{
            key: {"score": 0, "status": value["status"]["flow"]}
            for key, value in component_payload.items()
        },
    }
    return {
        "brand_name": brand,
        "url": f"https://{brand.lower()}.example",
        "source_run_id": 1,
        "visual_acquisition_present": visual,
        "sv9": {
            "brand3_score": 50 + delta,
            "not_detected": flow_not_detected or [],
            "not_evaluated": flow_not_evaluated or [],
            "reliability_status": "broken" if flow_not_evaluated else "shadow",
            "components": flow_components,
        },
        "legacy_sv9": {
            "brand3_score": 50,
            "not_detected": [],
            "not_evaluated": [],
            "reliability_status": "shadow",
            "components": {},
        },
        "comparison": {
            "brand3_score_delta": delta,
            "base_average_delta": 0,
            "not_detected_added": [],
            "not_detected_removed": [],
            "reliability_changed": False,
            "components": component_payload,
        },
        "flow": {
            "interpretation_debug": {
                "gate_authority": "veto_only",
                "block_detection_decisions": [
                    {
                        "block": gate_override_block or "magnetism",
                        "outcome": "supports_detection",
                        "limitation_code": "",
                        "support_terms": ["momentum"],
                        "weaken_terms": [],
                    }
                ],
                "detection_provenance": (
                    {
                        gate_override_block: {
                            "llm_detected": False,
                            "gate_detected": True,
                            "final_detected": gate_override_source == "gate_override",
                            "final_source": gate_override_source,
                            "gate_reason": "supports_detection",
                            **(
                                {"review_queue_reason": "gate_positive_llm_negative"}
                                if gate_override_source == "llm_rejected_gate_candidate"
                                else {}
                            ),
                        }
                    }
                    if gate_override_block
                    else {}
                ),
            }
        },
    }


def _component(delta: int, *, flow: str = "scored", legacy: str = "scored") -> dict:
    return {
        "score_delta": delta,
        "status": {"flow": flow, "legacy": legacy},
        "status_changed": flow != legacy,
        "tile_changes": {"changed": bool(delta)},
    }
