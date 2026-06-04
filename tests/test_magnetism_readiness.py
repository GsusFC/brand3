from src.features.magnetism.readiness import assess_scanner_readiness


def test_canonical_analyst_pass_payload_is_publishable() -> None:
    readiness = assess_scanner_readiness(
        "url",
        {
            "source": "brand_audit_snapshot",
            "tldr_generation_mode": "analyst_pass_validated",
        },
    )

    assert readiness.status == "publishable"
    assert readiness.publishable is True
    assert readiness.reason_codes == ()


def test_canonical_no_llm_fallback_is_failed() -> None:
    readiness = assess_scanner_readiness(
        "audit_run",
        {
            "source": "brand_audit_snapshot",
            "tldr_generation_mode": "legacy_fallback_no_llm",
        },
    )

    assert readiness.status == "failed"
    assert readiness.publishable is False
    assert readiness.reason_codes == ("canonical_tldr_degraded:no_llm",)
    assert readiness.error_message == "failed:canonical_tldr_degraded:no_llm"


def test_manual_payload_is_debug_only() -> None:
    readiness = assess_scanner_readiness(
        "manual",
        {
            "source": "legacy_direct",
            "tldr_generation_mode": "legacy_code",
        },
    )

    assert readiness.status == "debug_only"
    assert readiness.publishable is False
    assert readiness.reason_codes == (
        "manual_input_debug_path",
        "tldr_mode:legacy_code",
        "source:legacy_direct",
    )
