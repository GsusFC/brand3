from src.features.magnetism.scan_mode import (
    magnetism_input_type_from_payload,
    scan_mode_from_payload,
    scan_mode_from_row,
)


def test_scan_mode_identifies_manual_legacy_payload_as_not_comparable() -> None:
    policy = scan_mode_from_payload(
        {
            "source": "direct_magnetism_legacy",
            "extraction_mode": "legacy_direct",
            "direct_source_provider": "manual_evidence",
            "url": "manual",
        }
    )

    assert policy.mode == "legacy_manual"
    assert policy.comparable is False
    assert "manual_input_debug_path" in policy.reason_codes
    assert "bypasses_brand_audit_acquisition" in policy.reason_codes


def test_scan_mode_identifies_canonical_url_and_audit_run_as_comparable() -> None:
    url_policy = scan_mode_from_payload({"url": "https://example.com"}, input_type="url")
    audit_policy = scan_mode_from_payload(
        {"source": "brand_audit_snapshot", "source_run_id": 7},
        input_type="audit_run",
        source_run_id=7,
    )

    assert url_policy.to_payload() == {
        "mode": "canonical_url",
        "comparable": True,
        "reason_codes": [],
    }
    assert audit_policy.to_payload() == {
        "mode": "from_audit_run",
        "comparable": True,
        "reason_codes": [],
    }


def test_scan_mode_from_row_reuses_persisted_policy() -> None:
    policy = scan_mode_from_row(
        {
            "input_type": "manual",
            "raw_payload": (
                '{"scan_mode":{"mode":"legacy_manual","comparable":false,'
                '"reason_codes":["manual_input_debug_path"]}}'
            ),
        }
    )

    assert policy.mode == "legacy_manual"
    assert policy.comparable is False
    assert policy.reason_codes == ("manual_input_debug_path",)


def test_magnetism_input_type_resolver_reuses_manual_and_audit_rules() -> None:
    assert (
        magnetism_input_type_from_payload(
            {
                "source": "direct_magnetism_legacy",
                "direct_source_provider": "manual_evidence",
            }
        )
        == "manual"
    )
    assert (
        magnetism_input_type_from_payload(
            {"source": "brand_audit_snapshot"},
            source_run_id=7,
        )
        == "audit_run"
    )
    assert magnetism_input_type_from_payload({"url": "https://example.com"}) == "url"
