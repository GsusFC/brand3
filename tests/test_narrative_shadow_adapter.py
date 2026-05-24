from __future__ import annotations

import json

from src.reports.narrative_shadow_adapter import (
    build_shadow_narrative_request,
    parse_shadow_narrative_response,
)


def test_build_shadow_request_blocks_non_executable_status():
    request, skip = build_shadow_narrative_request(
        {
            "case_id": "builtwith_kit_com",
            "dimension": "coherencia",
            "intent": "blocked_control",
            "readiness_status": "blocked",
            "user": json.dumps({"included_evidence": [{"text": "x", "url": "https://x"}]}),
        },
        model="x-model",
    )
    assert request is None
    assert skip is not None
    assert skip["reason"] == "status_not_executable_for_shadow_call"


def test_build_shadow_request_filters_empty_text_and_builds_allowlist():
    request, skip = build_shadow_narrative_request(
        {
            "case_id": "linear",
            "dimension": "diferenciacion",
            "intent": "segmented_matrix_case",
            "readiness_status": "ready",
            "user": json.dumps(
                {
                    "task": "task",
                    "prompt_rules": ["keep this"],
                    "included_evidence": [
                        {"text": "  ", "url": "https://drop.example", "source_class": "external"},
                        {"text": "keep", "url": "https://keep.example", "source_class": "external", "limits": "x"},
                    ],
                }
            ),
        },
        model="x-model",
    )
    assert skip is None
    assert request is not None
    payload = json.loads(request["user"])
    assert request["included_evidence_count"] == 1
    assert payload["included_evidence"][0]["text"] == "keep"
    assert request["allowed_evidence_urls"] == ["https://keep.example"]
    assert "Do not include typical_decision." in payload["prompt_rules"]


def test_parse_shadow_response_enforces_url_allowlist_and_limits():
    summary = parse_shadow_narrative_response(
        {
            "findings": [
                {
                    "title": "Relative Positioning",
                    "evidence_anchor": "distance",
                    "observation": "obs",
                    "bounded_interpretation": "interp",
                    "limits": "Does not prove adoption.",
                    "evidence_urls": ["https://ok.example", "https://bad.example"],
                }
            ]
        },
        ["https://ok.example"],
        "diferenciacion",
    )
    assert summary["finding_count"] == 1
    assert summary["has_typical_decision"] is False
    assert summary["limits_field_present"] is True
    assert summary["evidence_url_validity"] is False
    assert summary["invalid_evidence_urls"] == ["https://bad.example"]
    assert summary["risky_terms_outside_limits"] == []
