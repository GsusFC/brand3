import json
from pathlib import Path

from scripts.evidence_intervention_board import build_intervention_board, main, render_intervention_board_markdown


def _packet() -> dict:
    return {
        "packet_id": "intervention:entity_alias_confirmation",
        "title": "Confirm unresolved external profile alias in material evidence",
        "priority": "high",
        "intervention_type": "entity_alias_confirmation",
        "allowed_decisions": ["external_profile_alias_confirmed", "quarantine_profile_material_claims"],
        "decision_required_fields": ["decision", "reviewer", "rationale", "profile_url"],
        "promotion_after_closure": "recompute_required",
        "checklist": ["Verify external profile ownership."],
        "runs": [
            {
                "run_id": 288,
                "brand_name": "base44.com",
                "automation_lane": "contract_then_human_review",
                "next_action": "confirm_entity_alias_before_promotion",
                "remaining_review_examples": [
                    {
                        "url": "https://www.linkedin.com/company/base44",
                        "provider": "llm",
                        "classification_reason": "same_name_external_profile_not_alias",
                    }
                ],
                "projected_material_overlaps": [
                    {
                        "field": "competitive_context",
                        "url": "https://linkedin.com/company/base44/",
                        "classification_reason": "same_name_external_profile_material_source",
                    }
                ],
                "changed_material_fields": [{"field": "proof_points"}],
            }
        ],
    }


def test_intervention_board_builds_entity_alias_records() -> None:
    board = build_intervention_board([_packet()], input_files=["vnext_288.json"])
    markdown = render_intervention_board_markdown(board)

    assert board["runtime_effect"] is False
    assert board["persistence_effect"] is False
    assert board["summary"]["packet_count"] == 1
    assert board["summary"]["record_count"] == 1
    assert board["summary"]["recompute_run_ids"] == [288]
    assert board["summary"]["review_urls"] == ["https://www.linkedin.com/company/base44"]
    assert board["cards"][0]["affected_material_fields"] == ["competitive_context"]
    assert board["records"][0]["status"] == "pending_decision"
    assert board["records"][0]["requires_recompute"] is True
    assert "entity_alias_confirmation" in markdown
    assert "https://www.linkedin.com/company/base44" in markdown


def test_intervention_board_cli_filters_by_intervention_type(tmp_path: Path) -> None:
    input_path = tmp_path / "vnext_288.json"
    output_dir = tmp_path / "board"
    payload = {
        "report": {
            "intervention_packets": [
                _packet(),
                {
                    "packet_id": "intervention:none",
                    "intervention_type": "none",
                    "promotion_after_closure": "candidate",
                    "runs": [{"run_id": 287, "brand_name": "ramp.com"}],
                },
            ]
        }
    }
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    assert (
        main(
            [
                "--input-json",
                str(input_path),
                "--intervention-type",
                "entity_alias_confirmation",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    board = json.loads((output_dir / "intervention_board.json").read_text(encoding="utf-8"))

    assert board["summary"]["record_count"] == 1
    assert board["summary"]["recompute_run_ids"] == [288]
    assert (output_dir / "records" / "entity_alias_confirmation_288.json").exists()
