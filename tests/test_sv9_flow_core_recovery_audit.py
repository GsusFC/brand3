from scripts.sv9_flow_core_recovery_audit import build_core_recovery_audit


def test_core_recovery_audit_extracts_recovered_core_component() -> None:
    report = build_core_recovery_audit(
        [
            {
                "brand_name": "Acme",
                "url": "https://acme.example",
                "source_run_id": 123,
                "comparison": {
                    "components": {
                        "core_purpose": {
                            "score_delta": 6,
                            "status": {"flow": "scored", "legacy": "not_detected"},
                        },
                        "coherencia": {
                            "score_delta": 8,
                            "status": {"flow": "scored", "legacy": "not_detected"},
                        },
                    }
                },
                "flow": {
                    "candidate": {
                        "interpretation": {
                            "blocks": {
                                "core_purpose": {
                                    "content": "Acme provides a software platform for teams.",
                                    "confidence": "high",
                                    "rationale": "The homepage describes the platform.",
                                }
                            },
                            "evidence_refs": {"core_purpose": ["raw_inputs.0", "raw_inputs.1"]},
                        },
                        "evidence_pack": {
                            "evidence": [
                                {
                                    "ref": "raw_inputs.0",
                                    "source": "web",
                                    "evidence_type": "raw_input",
                                    "content": "Acme platform homepage.",
                                    "metadata": {"source_class": "owned_copy"},
                                },
                                {
                                    "ref": "raw_inputs.1",
                                    "source": "exa",
                                    "evidence_type": "raw_input",
                                    "content": "External summary.",
                                    "metadata": {"source_class": "other"},
                                },
                            ]
                        },
                    }
                },
                "sv9": {
                    "components": {
                        "core_purpose": {
                            "lit_tiles": ["PR1", "PR2"],
                            "blind_spot_tiles": ["PR10"],
                            "off_tiles": ["PR3"],
                        }
                    }
                },
            }
        ]
    )

    assert report["item_count"] == 1
    item = report["items"][0]
    assert item["component"] == "core_purpose"
    assert item["score_delta"] == 6
    assert item["lit_tiles"] == ["PR1", "PR2"]
    assert "product_or_offer_bound_language" in item["risk_flags"]
    assert "uses_non_owned_refs" in item["risk_flags"]


def test_core_recovery_audit_ignores_non_recovery_core_component() -> None:
    report = build_core_recovery_audit(
        [
            {
                "brand_name": "Acme",
                "comparison": {
                    "components": {
                        "core_purpose": {
                            "score_delta": 6,
                            "status": {"flow": "scored", "legacy": "scored"},
                        }
                    }
                },
            }
        ]
    )

    assert report["item_count"] == 0


def test_core_recovery_audit_treats_legacy_zero_score_as_recovery() -> None:
    report = build_core_recovery_audit(
        [
            {
                "brand_name": "Acme",
                "comparison": {
                    "components": {
                        "core_purpose": {
                            "score_delta": 6,
                            "status": {"flow": "scored", "legacy": "scored"},
                        }
                    }
                },
                "legacy_sv9": {
                    "components": {
                        "core_purpose": {
                            "status": "scored",
                            "score": 0,
                            "lit_tiles": [],
                            "off_tiles": ["PR1"],
                        }
                    }
                },
                "flow": {
                    "candidate": {
                        "interpretation": {
                            "blocks": {"core_purpose": {"content": "Acme provides software."}},
                            "evidence_refs": {"core_purpose": []},
                        }
                    }
                },
            }
        ]
    )

    assert report["item_count"] == 1
