import pytest

from scripts.evidence_adjudication_decisions import build_decision_manifest, build_decision_record


def _record() -> dict:
    return {
        "record_id": "entity_alias_confirmation_288",
        "status": "pending_decision",
        "allowed_decisions": ["external_profile_alias_confirmed", "quarantine_profile_material_claims"],
        "required_fields": ["decision", "reviewer", "rationale", "profile_url", "affected_material_fields"],
        "requires_recompute": True,
        "review_urls": ["https://www.linkedin.com/company/base44"],
        "affected_material_fields": ["competitive_context"],
        "card": {"run_id": 288},
    }


def test_decision_record_validates_and_builds_recompute_manifest() -> None:
    decision = build_decision_record(
        _record(),
        decision="external_profile_alias_confirmed",
        reviewer="codex",
        rationale="Official site links to the profile.",
    )
    manifest = build_decision_manifest([decision])

    assert decision["status"] == "completed"
    assert decision["profile_url"] == "https://www.linkedin.com/company/base44"
    assert decision["affected_material_fields"] == "competitive_context"
    assert decision["requires_recompute"] is True
    assert manifest["runtime_effect"] is False
    assert manifest["persistence_effect"] is False
    assert manifest["summary"]["recompute_run_ids"] == [288]
    assert manifest["summary"]["decision_counts"] == {"external_profile_alias_confirmed": 1}


def test_decision_record_rejects_unallowed_decision() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        build_decision_record(
            _record(),
            decision="approve_anyway",
            reviewer="codex",
            rationale="No.",
        )
