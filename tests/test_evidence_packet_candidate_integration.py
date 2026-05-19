from __future__ import annotations

from src.reports.evidence_packet_candidate_integration import build_lab_request, summarize_lab_response


def test_build_lab_request_blocks_non_ready_status():
    request, skip = build_lab_request(
        case_id="builtwith_kit_com",
        dimension="coherencia",
        intent="blocked_control",
        model="x-model",
        task_label="task",
        readiness_status="blocked",
        prompt_constraints=[],
        evidence=[{"text": "x", "url": "https://x", "source_class": "external"}],
    )
    assert request is None
    assert skip is not None
    assert skip["status"] == "blocked"
    assert skip["reason"] == "status_not_executable_for_lab_call"


def test_summarize_lab_response_validates_urls_and_limits():
    data = {
        "findings": [
            {
                "title": "Relative Positioning Signal",
                "evidence_anchor": "Competitor distance",
                "observation": "Signal shows relative distance between products.",
                "bounded_interpretation": "This may indicate category contrast only.",
                "limits": "Does not prove leadership or adoption.",
                "evidence_urls": ["https://allowed.example"],
            }
        ]
    }
    summary = summarize_lab_response(data, ["https://allowed.example"], "diferenciacion")
    assert summary["finding_count"] == 1
    assert summary["has_typical_decision"] is False
    assert summary["limits_field_present"] is True
    assert summary["evidence_url_validity"] is True
    assert summary["risky_terms_outside_limits"] == []
