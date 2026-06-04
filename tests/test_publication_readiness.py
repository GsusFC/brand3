from src.quality.publication_readiness import (
    PUBLICATION_DECISION_VERSION,
    publication_decision_from_report_readiness,
    publication_decision_from_scanner_readiness,
)


def test_report_publishable_readiness_becomes_publishable_decision() -> None:
    decision = publication_decision_from_report_readiness(
        {"report_mode": "publishable_brand_report"}
    )

    assert decision.publishable is True
    assert decision.status == "publishable"
    assert decision.surface == "brand_audit_report"
    payload = decision.to_payload()
    assert payload["version"] == PUBLICATION_DECISION_VERSION
    assert payload["listable"] is True
    assert payload["ui_readable"] is True
    assert payload["api_readable"] is True


def test_missing_report_readiness_is_non_public() -> None:
    decision = publication_decision_from_report_readiness(None)

    assert decision.publishable is False
    assert decision.status == "non_public"
    assert decision.reason_codes == ("missing_report_readiness",)
    assert decision.listable is False
    assert decision.ui_readable is True


def test_technical_report_readiness_is_non_public_with_blockers() -> None:
    decision = publication_decision_from_report_readiness(
        {
            "report_mode": "technical_diagnostic",
            "blockers": ["core_dimensions_not_evaluable"],
        }
    )

    assert decision.publishable is False
    assert decision.status == "non_public"
    assert decision.listable is False
    assert decision.ui_readable is True
    assert decision.reason_codes == (
        "report_mode:technical_diagnostic",
        "blocker:core_dimensions_not_evaluable",
    )


def test_scanner_publishable_readiness_becomes_publishable_decision() -> None:
    decision = publication_decision_from_scanner_readiness(
        {"status": "publishable", "publishable": True, "reason_codes": []}
    )

    assert decision.publishable is True
    assert decision.status == "publishable"
    assert decision.surface == "magnetism_scan"
    assert decision.listable is True
    assert decision.api_readable is True


def test_scanner_debug_readiness_remains_non_publishable_debug() -> None:
    decision = publication_decision_from_scanner_readiness(
        {
            "status": "debug_only",
            "publishable": False,
            "reason_codes": ["manual_input_debug_path"],
        }
    )

    assert decision.publishable is False
    assert decision.status == "debug_only"
    assert decision.listable is True
    assert decision.ui_readable is True
    assert decision.api_readable is True
    assert decision.reason_codes == ("manual_input_debug_path",)


def test_missing_scanner_readiness_is_non_public() -> None:
    decision = publication_decision_from_scanner_readiness(None)

    assert decision.publishable is False
    assert decision.status == "non_public"
    assert decision.listable is False
    assert decision.api_readable is False
    assert decision.reason_codes == ("missing_scanner_readiness",)
