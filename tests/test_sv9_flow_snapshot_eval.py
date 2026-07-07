from scripts.sv9_flow_snapshot_eval import (
    SV9_FLOW_SNAPSHOT_EVAL_VERSION,
    build_snapshot_eval,
    snapshot_and_run_id_from_envelope,
)


def test_snapshot_eval_accepts_scanner_api_audit_snapshot_envelope() -> None:
    snapshot, run_id = snapshot_and_run_id_from_envelope(
        {
            "source_run_id": 335,
            "debug": {
                "run": {
                    "id": 335,
                    "brand_name": "vercel.com",
                    "url": "https://vercel.com",
                },
                "raw_inputs": [],
            },
        }
    )

    assert run_id == 335
    assert snapshot["run"]["brand_name"] == "vercel.com"


def test_snapshot_eval_accepts_selected_deploy_snapshot_envelope() -> None:
    snapshot, run_id = snapshot_and_run_id_from_envelope(
        {
            "source": "deploy",
            "source_run_id": 86,
            "snapshot": {
                "run": {
                    "id": 86,
                    "brand_name": "www.mafer.ai",
                    "url": "https://www.mafer.ai",
                },
                "raw_inputs": [],
            },
        }
    )

    assert run_id == 86
    assert snapshot["run"]["brand_name"] == "www.mafer.ai"


def test_snapshot_eval_runs_flow_llm_repeats_without_pass1() -> None:
    calls = []

    def shadow_builder(run_id: int, **kwargs):
        calls.append((run_id, kwargs["interpretation_source"], kwargs["db_path"]))
        assert kwargs["get_cached_detection_fn"](run_id, "unused") is None
        assert kwargs["visual_signature_fn"]({}) is None
        return _shadow_payload(run_id)

    payload = build_snapshot_eval(
        {
            "debug": {
                "run": {
                    "id": 335,
                    "brand_name": "vercel.com",
                    "url": "https://vercel.com",
                },
                "raw_inputs": [],
            }
        },
        repeat=2,
        shadow_builder=shadow_builder,
    )

    assert payload["schema_version"] == SV9_FLOW_SNAPSHOT_EVAL_VERSION
    assert payload["source_run_id"] == 335
    assert payload["brand_name"] == "vercel.com"
    assert payload["stability"]["same_tile_effects"] is True
    assert "candidate" not in payload["runs"][0]
    assert calls == [(335, "flow-llm", "snapshot_json"), (335, "flow-llm", "snapshot_json")]


def _shadow_payload(run_id: int) -> dict:
    return {
        "source_run_id": run_id,
        "detection_source": "flow_llm",
        "interpretation_source": "flow-llm",
        "visual_signature_present": False,
        "report": {
            "brand_name": "vercel.com",
            "url": "https://vercel.com",
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
                        "content": "Help teams ship.",
                        "confidence": "high",
                    }
                }
            }
        },
        "llm_payload": {
            "status": "ok",
            "detected_count": 1,
            "block_failures": [],
            "block_detection_decisions": [
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
