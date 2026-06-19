from scripts.evidence_adjudication_apply import apply_adjudication_decisions, build_apply_manifest


def _vnext_payload() -> dict:
    return {
        "report": {
            "rows": [{"run_id": 288, "brand_name": "base44.com"}],
            "work_orders": [
                {
                    "work_order_id": "workorder:entity_alias_confirmation:288",
                    "packet_id": "intervention:entity_alias_confirmation",
                    "run_id": 288,
                    "brand_name": "base44.com",
                    "next_action": "confirm_entity_alias_before_promotion",
                    "requires_recompute": True,
                }
            ],
        }
    }


def _decisions() -> dict:
    return {
        "records": [
            {
                "record_id": "entity_alias_confirmation_288",
                "work_order_id": "workorder:entity_alias_confirmation:288",
                "run_id": 288,
                "decision": "external_profile_alias_confirmed",
                "reviewer": "codex",
                "rationale": "Official site links to profile.",
                "requires_recompute": True,
            }
        ]
    }


def test_apply_adjudication_decisions_closes_matching_work_order() -> None:
    applied = apply_adjudication_decisions(_vnext_payload(), _decisions(), source_file="vnext_288.json")
    manifest = build_apply_manifest([applied])

    assert applied["runtime_effect"] is False
    assert applied["persistence_effect"] is False
    assert applied["summary"]["closed_work_order_count"] == 1
    assert applied["summary"]["open_work_order_count"] == 0
    assert applied["summary"]["requires_recompute"] is True
    assert applied["post_adjudication"]["status"] == "recompute_required"
    assert applied["post_adjudication"]["note"] == "Promotion state is not recomputed by this dry-run applicator."
    assert applied["closed_work_orders"][0]["decision"] == "external_profile_alias_confirmed"
    assert manifest["summary"]["recompute_run_ids"] == [288]


def test_apply_adjudication_decisions_leaves_unmatched_work_order_open() -> None:
    applied = apply_adjudication_decisions(_vnext_payload(), {"records": []})

    assert applied["summary"]["closed_work_order_count"] == 0
    assert applied["summary"]["open_work_order_count"] == 1
    assert applied["summary"]["requires_recompute"] is False
    assert applied["post_adjudication"]["status"] == "pending_decisions"
