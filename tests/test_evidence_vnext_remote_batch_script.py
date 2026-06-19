from scripts.evidence_vnext_remote_batch import _markdown, _run_row, _summary


def test_remote_vnext_run_row_extracts_operator_fields() -> None:
    payload = {
        "brand_name": "AuditCo",
        "url": "https://audit.example",
        "report": {
            "rows": [
                {
                    "status": "review_required",
                    "promotion_status": "audit_required",
                    "accepted": 3,
                    "review_required": 2,
                    "rejected": 1,
                    "changed_fields": 1,
                    "lost_fields": 0,
                    "material_lost_fields": 0,
                }
            ],
            "readiness_matrix": {
                "rows": [
                    {
                        "readiness_status": "needs_manual_audit",
                        "next_action": "manual_audit_projected_material_changes",
                        "automation_lane": "contract_then_human_review",
                        "human_required": True,
                        "remaining_reason_codes": ["limited_review_pressure_present"],
                    }
                ]
            },
            "decision_queue": [
                {"action": "implement_provider_acquisition_contract"},
                {"action": "manual_audit_projected_material_changes"},
            ],
            "work_orders": [
                {
                    "task": "Review changed material evidence after strict source contract",
                    "next_action": "manual_audit_projected_material_changes",
                    "context": {
                        "changed_material_fields": [{"field": "proof_points"}],
                        "remaining_review_examples": [
                            {
                                "classification_reason": "trust_or_security_source_requires_review",
                                "url": "https://example.com/security",
                            }
                        ],
                    },
                }
            ],
            "adjudication_intake": {"pending_count": 1},
            "top_review_reasons": {"same_name_external_profile_not_alias": 2},
            "top_rejected_reasons": {"empty_text_evidence_blocked": 1},
        },
    }

    row = _run_row(4207, payload=payload)

    assert row["run_id"] == 4207
    assert row["brand_name"] == "AuditCo"
    assert row["promotion_status"] == "audit_required"
    assert row["readiness_status"] == "needs_manual_audit"
    assert row["human_required"] is True
    assert row["decision_count"] == 2
    assert row["work_order_count"] == 1
    assert row["work_order_triage_lanes"] == ["llm_structured_candidate"]
    assert row["work_order_triage_recommendations"] == ["structured_material_diff_review"]
    assert row["work_order_triage"][0]["model_role"] == "classify_materiality_entity_fit_and_source_trust"
    assert row["pending_adjudications"] == 1
    assert row["review_reasons"] == {"same_name_external_profile_not_alias": 2}


def test_remote_vnext_summary_counts_decision_patterns() -> None:
    rows = [
        {
            "accepted": 3,
            "review_required": 2,
            "rejected": 1,
            "status": "review_required",
            "promotion_status": "audit_required",
            "readiness_status": "needs_manual_audit",
            "next_action": "manual_audit_projected_material_changes",
            "human_required": True,
            "pending_adjudications": 1,
            "work_order_count": 1,
            "decision_actions": [
                "implement_provider_acquisition_contract",
                "manual_audit_projected_material_changes",
            ],
            "work_order_tasks": ["Review changed material evidence after strict source contract"],
            "work_order_triage_lanes": ["llm_structured_candidate"],
            "work_order_triage_recommendations": ["structured_material_diff_review"],
            "review_reasons": {"same_name_external_profile_not_alias": 2},
            "rejected_reasons": {"empty_text_evidence_blocked": 1},
            "remaining_reason_codes": ["limited_review_pressure_present"],
        },
        {
            "accepted": 0,
            "review_required": 0,
            "rejected": 4,
            "status": "candidate",
            "promotion_status": "candidate",
            "readiness_status": "ready",
            "next_action": "none",
            "human_required": False,
            "pending_adjudications": 0,
            "work_order_count": 0,
            "decision_actions": ["implement_provider_acquisition_contract"],
            "work_order_tasks": [],
            "work_order_triage_lanes": [],
            "work_order_triage_recommendations": [],
            "review_reasons": {},
            "rejected_reasons": {"empty_text_evidence_blocked": 4},
            "remaining_reason_codes": [],
        },
    ]

    summary = _summary(rows)

    assert summary["run_count"] == 2
    assert summary["accepted_total"] == 3
    assert summary["human_required_count"] == 1
    assert summary["pending_adjudication_total"] == 1
    assert summary["decision_action_counts"]["implement_provider_acquisition_contract"] == 2
    assert summary["work_order_triage_lane_counts"]["llm_structured_candidate"] == 1
    assert summary["work_order_triage_recommendation_counts"]["structured_material_diff_review"] == 1
    assert summary["top_rejected_reasons"]["empty_text_evidence_blocked"] == 5


def test_remote_vnext_markdown_renders_rows() -> None:
    batch = {
        "summary": {
            "run_count": 1,
            "accepted_total": 3,
            "review_required_total": 2,
            "rejected_total": 1,
            "human_required_count": 1,
            "pending_adjudication_total": 1,
            "work_order_total": 1,
            "status_counts": {"review_required": 1},
            "promotion_counts": {"audit_required": 1},
            "readiness_counts": {"needs_manual_audit": 1},
            "decision_action_counts": {"manual_audit_projected_material_changes": 1},
            "work_order_task_counts": {"Review changed material evidence after strict source contract": 1},
            "work_order_triage_lane_counts": {"llm_structured_candidate": 1},
            "work_order_triage_recommendation_counts": {"structured_material_diff_review": 1},
            "top_review_reasons": {"same_name_external_profile_not_alias": 1},
            "top_rejected_reasons": {"empty_text_evidence_blocked": 1},
        },
        "rows": [
            {
                "run_id": 4207,
                "brand_name": "AuditCo",
                "promotion_status": "audit_required",
                "readiness_status": "needs_manual_audit",
                "accepted": 3,
                "review_required": 2,
                "rejected": 1,
                "next_action": "manual_audit_projected_material_changes",
                "work_order_count": 1,
                "work_order_triage": [
                    {
                        "task": "Review changed material evidence after strict source contract",
                        "lane": "llm_structured_candidate",
                        "recommendation": "structured_material_diff_review",
                        "model_role": "classify_materiality_entity_fit_and_source_trust",
                    }
                ],
            }
        ],
    }

    markdown = _markdown(batch)

    assert "# Evidence vNext Remote Batch" in markdown
    assert "`manual_audit_projected_material_changes`: `1`" in markdown
    assert "`llm_structured_candidate`: `1`" in markdown
    assert "structured_material_diff_review" in markdown
    assert "| 4207 | AuditCo | audit_required | needs_manual_audit | 3 | 2 | 1 |" in markdown


def test_remote_vnext_run_row_routes_source_contract_without_model() -> None:
    payload = {
        "brand_name": "SourceCo",
        "url": "https://source.example",
        "report": {
            "rows": [{"promotion_status": "blocked"}],
            "readiness_matrix": {
                "rows": [
                    {
                        "readiness_status": "blocked_after_shadow_policy",
                        "next_action": "add_source_url_or_remove_material_quote",
                        "human_required": True,
                    }
                ]
            },
            "work_orders": [
                {
                    "task": "Attach source URL or remove material quote",
                    "next_action": "add_source_url_or_remove_material_quote",
                    "context": {
                        "projected_material_overlaps": [
                            {
                                "field": "proof_points",
                                "classification_reason": "missing_evidence_url",
                            }
                        ]
                    },
                }
            ],
        },
    }

    row = _run_row(99, payload=payload)

    assert row["work_order_triage_lanes"] == ["deterministic_source_contract"]
    assert row["work_order_triage_recommendations"] == ["fix_provenance_or_exclude_unsourced_material"]
    assert row["work_order_triage"][0]["model_role"] == "none"


def test_remote_vnext_run_row_routes_alias_as_llm_assisted_adjudication() -> None:
    payload = {
        "brand_name": "AliasCo",
        "url": "https://alias.example",
        "report": {
            "rows": [{"promotion_status": "blocked"}],
            "readiness_matrix": {
                "rows": [
                    {
                        "readiness_status": "blocked_after_shadow_policy",
                        "next_action": "confirm_entity_alias_before_promotion",
                        "human_required": True,
                    }
                ]
            },
            "work_orders": [
                {
                    "task": "Confirm unresolved external profile alias in material evidence",
                    "next_action": "confirm_entity_alias_before_promotion",
                    "context": {
                        "remaining_review_examples": [
                            {
                                "classification_reason": "same_name_external_profile_not_alias",
                                "url": "https://linkedin.com/company/aliasco",
                            }
                        ]
                    },
                }
            ],
        },
    }

    row = _run_row(100, payload=payload)

    assert row["work_order_triage_lanes"] == ["llm_assisted_adjudication"]
    assert row["work_order_triage_recommendations"] == ["structured_entity_alias_shadow"]
    assert row["work_order_triage"][0]["model_role"] == "suggest_alias_confidence_only"
