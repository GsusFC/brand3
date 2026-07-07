from src.services.scanner_api_stability import compare_probe_summaries, extract_probe_summary


def test_extract_probe_summary_reads_persisted_fields():
    bundle = {
        "status": {
            "id": 255,
            "status": "ready",
            "phase": "ready",
            "scan_mode": {"mode": "from_audit_run"},
        },
        "result": {
            "id": 255,
            "audit": {"source_run_id": 315},
            "scores": {
                "magnetism": 66,
                "coherence": 80,
                "quadrant": "Bien pensada sin alma comercial",
            },
            "tldr_brand3": {"magnetism": {"answer": "x"}},
            "debug": {
                "normalized_payload": {
                    "research_pack": {"summary": "same"},
                    "analyst_tldr_validated": {"foo": "bar"},
                    "metrics": {
                        "magnetism_scoring_context": {
                            "earned_magnetism_score": 66,
                            "expressive_magnetism_score": 79,
                            "evidence_duty_status": "partial",
                            "reasoning": {
                                "_truncated": True,
                                "preview": "Derived from research-pack proof structure",
                            },
                        }
                    },
                }
            },
        },
        "audit_snapshot": {
            "source_run_id": 315,
            "run": {"composite_score": 66.8},
            "debug": {
                "raw_inputs": {"homepage_text": "hello"},
                "run": {
                    "audit": {
                        "acquisition": {
                            "provenance": {
                                "quality": {"label": "degraded", "score": 58}
                            }
                        }
                    }
                },
            },
        },
    }

    summary = extract_probe_summary(bundle)

    assert summary["scan_id"] == 255
    assert summary["source_run_id"] == 315
    assert summary["magnetism_score"] == 66
    assert summary["coherence_score"] == 80
    assert summary["earned_magnetism_score"] == 66
    assert summary["expressive_magnetism_score"] == 79
    assert summary["evidence_duty_status"] == "partial"
    assert summary["reasoning_preview"] == "Derived from research-pack proof structure"
    assert summary["quality_label"] == "degraded"
    assert summary["quality_score"] == 58
    assert summary["research_pack_hash"]
    assert summary["raw_inputs_hash"]


def test_compare_probe_summaries_flags_critical_changes():
    summaries = [
        {
            "scan_id": 255,
            "source_run_id": 315,
            "magnetism_score": 66,
            "coherence_score": 80,
            "quadrant": "Bien pensada sin alma comercial",
            "earned_magnetism_score": 66,
            "expressive_magnetism_score": 79,
            "evidence_duty_status": "partial",
            "research_pack_hash": "aaaa",
            "raw_inputs_hash": "same",
        },
        {
            "scan_id": 256,
            "source_run_id": 316,
            "magnetism_score": 66,
            "coherence_score": 80,
            "quadrant": "Bien pensada sin alma comercial",
            "earned_magnetism_score": 66,
            "expressive_magnetism_score": 79,
            "evidence_duty_status": "partial",
            "research_pack_hash": "bbbb",
            "raw_inputs_hash": "same",
        },
    ]

    comparison = compare_probe_summaries(summaries)

    assert comparison["stable"] is False
    assert comparison["critical_stable"] is False
    assert [item["field"] for item in comparison["critical_changes"]] == ["research_pack_hash"]
