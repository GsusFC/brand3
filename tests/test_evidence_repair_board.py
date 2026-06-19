from scripts.evidence_repair_board import build_repair_board, render_repair_board_markdown


def test_repair_board_builds_records_and_operator_manifests() -> None:
    packets = [
        {
            "packet_id": "repair:backfill_source_url_or_remove_material:273",
            "work_order_id": "workorder:material_audit:273",
            "run_id": 273,
            "brand_name": "causaprima.ai",
            "action": "backfill_source_url_or_remove_material",
            "recommended_decision": "source_url_attached_or_exclude_unsourced_quote",
            "allowed_decisions": ["source_url_attached", "replace_with_sourced_equivalent", "exclude_unsourced_quote"],
            "required_fields": ["decision", "reviewer", "rationale", "quote_text", "source_url"],
            "instructions": ["Search the provided exact quote hints."],
            "record": {
                "work_order_id": "workorder:material_audit:273",
                "run_id": 273,
                "decision": "",
                "search_hints": ['"two-sided network" causaprima.ai'],
            },
            "requires_recompute": True,
        },
        {
            "packet_id": "repair:prepare_trust_review_packet:276",
            "work_order_id": "workorder:material_audit:276",
            "run_id": 276,
            "brand_name": "ent.ai",
            "action": "prepare_trust_review_packet",
            "recommended_decision": "manual_trust_review",
            "allowed_decisions": ["approve_vnext_material", "send_back_for_evidence_correction"],
            "required_fields": ["decision", "reviewer", "rationale", "reviewed_source_urls"],
            "instructions": ["Review source URLs."],
            "record": {"work_order_id": "workorder:material_audit:276", "run_id": 276},
            "requires_recompute": False,
        },
    ]

    board = build_repair_board(packets, input_files=["material_diff_shadow_273.json"])
    markdown = render_repair_board_markdown(board)

    assert board["runtime_effect"] is False
    assert board["persistence_effect"] is False
    assert board["summary"]["packet_count"] == 2
    assert board["summary"]["recompute_run_ids"] == [273]
    assert board["summary"]["source_backfill_queries"] == ['"two-sided network" causaprima.ai']
    assert board["summary"]["lane_counts"]["provenance_repair"] == 1
    assert board["summary"]["lane_counts"]["human_review_packet"] == 1
    assert board["records"][0]["status"] == "pending_decision"
    assert board["records"][0]["requires_recompute"] is True
    assert "source_url_attached_or_exclude_unsourced_quote" in markdown
    assert '"two-sided network" causaprima.ai' in markdown


def test_repair_board_deduplicates_backfill_queries() -> None:
    packets = [
        {
            "run_id": 283,
            "brand_name": "causaprima.ai",
            "action": "backfill_source_url_or_remove_material",
            "recommended_decision": "source_url_attached_or_exclude_unsourced_quote",
            "record": {"search_hints": ['"same quote" causaprima.ai']},
            "requires_recompute": True,
        },
        {
            "run_id": 286,
            "brand_name": "causaprima.ai",
            "action": "backfill_source_url_or_remove_material",
            "recommended_decision": "source_url_attached_or_exclude_unsourced_quote",
            "record": {"search_hints": ['"same quote" causaprima.ai']},
            "requires_recompute": True,
        },
    ]

    board = build_repair_board(packets)

    assert board["summary"]["recompute_run_ids"] == [283, 286]
    assert board["summary"]["source_backfill_queries"] == ['"same quote" causaprima.ai']
