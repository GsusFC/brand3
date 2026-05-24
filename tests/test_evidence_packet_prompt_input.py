from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from src.reports.evidence_packet_prompt_input import build_prompt_input_candidate_v0


def _packet(name: str) -> dict:
    path = Path("examples/reports/evidence_packet") / f"{name}.local_evidence_packet.v0.json"
    return json.loads(path.read_text())


def _packet_with_review_gated_finding() -> dict:
    packet = deepcopy(_packet("linear"))
    packet["finding_eligible_evidence"].append(
        {
            "text": "Ambiguous same-name profile evidence",
            "url": "https://ambiguous.example.com/brand",
            "dimension": "percepcion",
            "feature_name": "brand_sentiment",
            "feature_source": "exa",
            "source_class": "related_unresolved",
            "eligibility": "eligible_for_narrative_finding",
            "classification_reason": "exa_related_surface_unresolved",
            "limits": "",
        }
    )
    return packet


def test_prompt_input_candidate_has_stable_shape_and_flags():
    candidate = build_prompt_input_candidate_v0(_packet("linear"))

    assert list(candidate.keys()) == [
        "version",
        "case_id",
        "audit_url",
        "source",
        "runtime_effect",
        "prompt_effect",
        "dimensions",
        "global_constraints",
        "excluded_dimensions",
        "review_required_dimensions",
        "metadata",
    ]
    assert candidate["version"] == 0
    assert candidate["source"] == "evidence_packet_v0"
    assert candidate["runtime_effect"] is False
    assert candidate["prompt_effect"] is False
    assert candidate["metadata"]["runtime_effect"] is False
    assert candidate["metadata"]["prompt_effect"] is False


def test_ready_dimensions_are_included_and_blocked_dimensions_excluded():
    linear = build_prompt_input_candidate_v0(_packet("linear"))
    builtwith = build_prompt_input_candidate_v0(_packet("builtwith_kit_com"))

    assert linear["dimensions"]["percepcion"]["include_in_prompt"] is True
    assert linear["dimensions"]["vitalidad"]["include_in_prompt"] is True
    assert linear["dimensions"]["diferenciacion"]["include_in_prompt"] is True
    assert all(not data["include_in_prompt"] for data in builtwith["dimensions"].values())
    assert {item["dimension"] for item in builtwith["excluded_dimensions"]} == {
        "coherencia",
        "presencia",
        "percepcion",
        "diferenciacion",
        "vitalidad",
    }


def test_thin_dimensions_are_included_with_qualification_constraints():
    candidate = build_prompt_input_candidate_v0(_packet("linear"))

    presencia = candidate["dimensions"]["presencia"]
    assert presencia["readiness_status"] == "thin"
    assert presencia["include_in_prompt"] is True
    assert any("thin" in constraint.lower() for constraint in presencia["prompt_constraints"])


def test_review_required_dimensions_are_excluded():
    candidate = build_prompt_input_candidate_v0(_packet("launchdarkly"))

    coherencia = candidate["dimensions"]["coherencia"]
    assert coherencia["readiness_status"] == "review_required"
    assert coherencia["include_in_prompt"] is False
    assert candidate["review_required_dimensions"]


def test_disallowed_evidence_types_are_excluded_from_prompt():
    candidate = build_prompt_input_candidate_v0(_packet("linear"))
    disallowed = {
        "technical_internal",
        "visual_internal_metric",
        "trust_security",
        "noise",
        "related_unresolved",
        "marketplace_listing",
    }

    for dimension in candidate["dimensions"].values():
        assert not any(item["source_class"] in disallowed for item in dimension["evidence"])
        assert not any(not item["text"] for item in dimension["evidence"])


def test_review_gated_finding_evidence_is_moved_to_review_required():
    candidate = build_prompt_input_candidate_v0(_packet_with_review_gated_finding())
    percepcion = candidate["dimensions"]["percepcion"]

    assert not any("ambiguous.example.com" in item.get("url", "") for item in percepcion["evidence"])
    assert any("ambiguous.example.com" in item.get("url", "") for item in percepcion["review_required_evidence"])


def test_competitor_comparison_evidence_carries_no_leadership_or_strategy_constraints():
    candidate = build_prompt_input_candidate_v0(_packet("linear"))

    diferenciacion = candidate["dimensions"]["diferenciacion"]
    assert diferenciacion["include_in_prompt"] is True
    assert any(item["source_class"] == "competitor_comparison" for item in diferenciacion["evidence"])
    constraints = " ".join(diferenciacion["prompt_constraints"]).lower()
    assert "relative positioning" in constraints
    assert "not leadership" in constraints
    assert "strategy" in constraints


def test_linear_includes_diferenciacion_with_bounded_comparison_evidence():
    candidate = build_prompt_input_candidate_v0(_packet("linear"))
    evidence = candidate["dimensions"]["diferenciacion"]["evidence"]

    assert len([item for item in evidence if item["source_class"] == "competitor_comparison"]) == 2
    assert all("snapshot://feature/competitor_web_comparison" == item["url"] for item in evidence)
    assert all("relative positioning distance only" in item["limits"] for item in evidence)


def test_watermelon_is_handled_conservatively():
    candidate = build_prompt_input_candidate_v0(_packet("watermelon"))

    assert candidate["dimensions"]["diferenciacion"]["include_in_prompt"] is False
    assert candidate["dimensions"]["vitalidad"]["include_in_prompt"] is False
    assert candidate["excluded_dimensions"]


def test_candidate_reduces_current_dimension_inputs():
    candidate = build_prompt_input_candidate_v0(_packet("linear"))
    reduction = candidate["metadata"]["noise_reduction_by_dimension"]

    assert reduction["diferenciacion"]["candidate_inputs"] < reduction["diferenciacion"]["current_inputs"]
    assert candidate["metadata"]["included_evidence_count"] < sum(
        item["current_inputs"] for item in reduction.values()
    )


def test_prompt_input_candidate_is_json_serializable():
    json.dumps(build_prompt_input_candidate_v0(_packet("linear")))


def test_contradiction_constraints_injected():
    packet = _packet("celestial_ai")
    candidate = build_prompt_input_candidate_v0(packet)
    
    coherencia = candidate["dimensions"]["coherencia"]
    prompt_constraints = coherencia["prompt_constraints"]
    
    warning_present = any(
        "Warning: Discrepancy detected between owned claims and external sources" in c
        for c in prompt_constraints
    )
    assert warning_present is True
    
    feature_warning = [c for c in prompt_constraints if "Warning:" in c][0]
    assert "messaging_consistency" in feature_warning

