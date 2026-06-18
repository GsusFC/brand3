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
            "work_orders": [{"task": "Review changed material evidence after strict source contract"}],
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
            }
        ],
    }

    markdown = _markdown(batch)

    assert "# Evidence vNext Remote Batch" in markdown
    assert "`manual_audit_projected_material_changes`: `1`" in markdown
    assert "| 4207 | AuditCo | audit_required | needs_manual_audit | 3 | 2 | 1 |" in markdown
