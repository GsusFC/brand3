from __future__ import annotations

from src.visual_signature.perception import (
    PerceptualStateMachine,
    classify_mutation_result,
    classify_obstruction_state,
    evaluate_intervention_eligibility,
)


def _no_obstruction() -> dict[str, object]:
    return {
        "present": False,
        "type": "none",
        "severity": "none",
        "coverage_ratio": 0.0,
        "first_impression_valid": True,
        "confidence": 0.05,
        "signals": [],
        "limitations": [],
    }


def _cookie_modal() -> dict[str, object]:
    return {
        "present": True,
        "type": "cookie_modal",
        "severity": "major",
        "coverage_ratio": 0.42,
        "first_impression_valid": False,
        "confidence": 0.91,
        "signals": ["dom_keyword:cookie", "dom_overlay_term:dialog"],
        "page_level_signals": ["dom_keyword:cookie"],
        "overlay_level_signals": ["dom_overlay_term:dialog"],
        "visual_signals": ["viewport_centered_modal_with_backdrop"],
        "limitations": [],
    }


def _cookie_modal_without_safe_affordance() -> dict[str, object]:
    return {
        "present": True,
        "type": "cookie_modal",
        "severity": "major",
        "coverage_ratio": 0.44,
        "first_impression_valid": False,
        "confidence": 0.88,
        "signals": ["dom_keyword:cookie", "dom_overlay_term:dialog"],
        "page_level_signals": ["dom_keyword:cookie"],
        "overlay_level_signals": ["dom_overlay_term:dialog"],
        "visual_signals": ["viewport_centered_modal_with_backdrop"],
        "limitations": [],
    }


def _login_wall() -> dict[str, object]:
    return {
        "present": True,
        "type": "login_wall",
        "severity": "blocking",
        "coverage_ratio": 0.92,
        "first_impression_valid": False,
        "confidence": 0.97,
        "signals": ["dom_keyword:login", "dom_keyword:sign in"],
        "page_level_signals": ["dom_keyword:login"],
        "overlay_level_signals": ["dom_keyword:sign in"],
        "visual_signals": ["viewport_fullscreen_overlay_pattern"],
        "limitations": [],
    }


def _unknown_overlay() -> dict[str, object]:
    return {
        "present": True,
        "type": "unknown_overlay",
        "severity": "major",
        "coverage_ratio": 0.5,
        "first_impression_valid": False,
        "confidence": 0.22,
        "signals": ["viewport_centered_modal_with_backdrop"],
        "page_level_signals": [],
        "overlay_level_signals": [],
        "visual_signals": ["viewport_centered_modal_with_backdrop"],
        "limitations": [],
    }


def test_raw_with_no_obstruction_remains_raw_state():
    decision = classify_obstruction_state(_no_obstruction())

    assert decision.state == "RAW_STATE"
    assert decision.reason == "no_obstruction_detected"


def test_cookie_modal_with_exact_safe_affordance_becomes_eligible_for_safe_intervention():
    decision = evaluate_intervention_eligibility(
        _cookie_modal(),
        affordance_labels=["Accept all"],
    )

    assert decision.state == "ELIGIBLE_FOR_SAFE_INTERVENTION"
    assert decision.eligible_for_safe_intervention is True
    assert decision.reason == "exact_safe_affordance_detected"
    assert decision.safe_affordances == ["accept all"]


def test_cookie_modal_without_safe_affordance_remains_obstructed():
    decision = evaluate_intervention_eligibility(
        _cookie_modal_without_safe_affordance(),
        affordance_labels=[],
    )

    assert decision.state == "OBSTRUCTED_STATE"
    assert decision.eligible_for_safe_intervention is False
    assert decision.reason == "no_safe_affordance_detected"


def test_cookie_modal_manage_choices_goes_to_review_required():
    decision = evaluate_intervention_eligibility(
        _cookie_modal_without_safe_affordance(),
        affordance_labels=["Manage choices"],
    )

    assert decision.state == "REVIEW_REQUIRED_STATE"
    assert decision.eligible_for_safe_intervention is False
    assert decision.reason == "ambiguous_affordance_detected"


def test_login_wall_is_blocked():
    decision = evaluate_intervention_eligibility(_login_wall(), affordance_labels=["Close"])

    assert decision.state == "UNSAFE_MUTATION_BLOCKED"
    assert decision.reason == "protected_environment_detected"
    assert decision.eligible_for_safe_intervention is False


def test_unknown_overlay_goes_to_review_required():
    decision = classify_obstruction_state(_unknown_overlay())

    assert decision.state == "REVIEW_REQUIRED_STATE"
    assert decision.reason in {"low_confidence_obstruction", "human_review_required"}


def test_successful_minimal_mutation_preserves_raw_state_and_records_after_refs():
    classification = classify_mutation_result(
        before_state="ELIGIBLE_FOR_SAFE_INTERVENTION",
        attempted=True,
        successful=True,
        reversible=True,
        evidence_preserved=True,
        mutation_type="cookie_dismissal",
        trigger="safe_mutation_attempted",
        before_artifact_ref="raw://viewport-1",
        after_artifact_ref="clean://viewport-1",
        evidence_refs=["evidence://raw", "evidence://clean"],
        mutation_id="mutation-1",
    )

    assert classification.state == "MINIMALLY_MUTATED_STATE"
    assert classification.reason == "safe_mutation_succeeded"
    assert classification.transition.from_state == "ELIGIBLE_FOR_SAFE_INTERVENTION"
    assert classification.transition.to_state == "MINIMALLY_MUTATED_STATE"
    assert classification.mutation_audit.attempted is True
    assert classification.mutation_audit.successful is True
    assert classification.mutation_audit.before_artifact_ref == "raw://viewport-1"
    assert classification.mutation_audit.after_artifact_ref == "clean://viewport-1"
    assert "raw_state_preserved_as_primary_evidence" in classification.mutation_audit.integrity_notes


def test_failed_minimal_mutation_does_not_erase_raw_state():
    classification = classify_mutation_result(
        before_state="ELIGIBLE_FOR_SAFE_INTERVENTION",
        attempted=True,
        successful=False,
        reversible=True,
        evidence_preserved=True,
        mutation_type="newsletter_dismissal",
        trigger="safe_mutation_attempted",
        before_artifact_ref="raw://viewport-2",
        after_artifact_ref=None,
        evidence_refs=["evidence://raw"],
        mutation_id="mutation-2",
    )

    assert classification.state == "REVIEW_REQUIRED_STATE"
    assert classification.reason == "safe_mutation_failed"
    assert classification.mutation_audit.attempted is True
    assert classification.mutation_audit.successful is False
    assert classification.mutation_audit.before_artifact_ref == "raw://viewport-2"
    assert classification.mutation_audit.after_artifact_ref is None
    assert "raw_state_preserved_after_failed_attempt" in classification.mutation_audit.integrity_notes


def test_perceptual_state_machine_keeps_raw_snapshot_intact():
    machine = PerceptualStateMachine.from_raw_capture(
        evidence_refs=["raw://capture-1"],
        notes=["raw evidence stored"],
    )

    eligible = machine.evaluate_eligibility(
        _cookie_modal(),
        affordance_labels=["Close"],
        evidence_refs=["obstruction://cookie"],
    )
    mutation = machine.classify_mutation(
        before_state=eligible.state,
        attempted=True,
        successful=True,
        reversible=True,
        evidence_preserved=True,
        mutation_type="cookie_dismissal",
        trigger="safe_mutation_attempted",
        before_artifact_ref="raw://capture-1",
        after_artifact_ref="clean://capture-1",
        evidence_refs=["mutation://cookie"],
        mutation_id="mutation-3",
    )

    payload = machine.to_dict()

    assert payload["raw_snapshot"]["state"] == "RAW_STATE"
    assert payload["raw_snapshot"]["evidence_refs"] == ["raw://capture-1"]
    assert payload["current_state"] == "MINIMALLY_MUTATED_STATE"
    assert payload["transitions"][0]["reason"] == "raw_capture_created"
    assert payload["mutation_results"][0]["mutation_audit"]["before_artifact_ref"] == "raw://capture-1"
    assert mutation.state == "MINIMALLY_MUTATED_STATE"
