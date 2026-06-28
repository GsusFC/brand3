from src.features.magnetism.extractor_tail_text_support_summary import visual_semantics_from_snapshot


def test_visual_semantics_from_snapshot_returns_unreliable_for_blocked_capture():
    snapshot = {
        "raw_inputs": [
            {
                "source": "visual_signature",
                "payload": {
                    "run_metadata": {"visual_signature_scan_status": "review_required"},
                    "raw_visual_signature_payload": {
                        "semantics": {
                            "data": {
                                "aesthetic_style": "modern minimalist",
                                "visual_mood": "professional",
                            }
                        }
                    },
                    "vision_payload": {
                        "viewport_obstruction": {
                            "present": True,
                            "severity": "blocking",
                            "first_impression_valid": False,
                        }
                    },
                },
            }
        ]
    }

    result = visual_semantics_from_snapshot(snapshot)

    assert result["status"] == "unreliable"
    assert result["data"] == {}
    assert sorted(result["reason_codes"]) == [
        "blocking_viewport_obstruction",
        "first_impression_invalid",
        "visual_signature_review_required",
    ]
