from scripts.visual_signature_scanner_validation_batch import evaluate_scan, markdown_report


def test_evaluate_scan_marks_missing_screenshot_and_weak_identity_for_review():
    quality = evaluate_scan(
        {
            "status": "partial",
            "score": 44.0,
            "capture": {"available": False, "obstruction": {"present": False}},
            "dimensions": {"identity_clarity": {"score": 40.0}},
        }
    )

    assert quality["verdict"] == "needs_review"
    assert "missing_screenshot" in quality["flags"]
    assert "weak_identity_detection" in quality["flags"]
    assert "status:partial" in quality["flags"]


def test_evaluate_scan_marks_batch_capture_failure_for_review():
    quality = evaluate_scan(
        {
            "status": "partial",
            "score": 57.0,
            "capture": {"available": False, "obstruction": {"present": False}},
            "dimensions": {"identity_clarity": {"score": 75.0}},
        },
        validation_capture={
            "attempted": True,
            "success": False,
            "status": "timeout",
            "error_type": "timeout",
        },
    )

    assert quality["verdict"] == "needs_review"
    assert "batch_capture_failed:timeout" in quality["flags"]
    assert quality["validation_capture_status"] == "timeout"


def test_markdown_report_lists_targets_and_flags():
    markdown = markdown_report(
        {
            "generated_at": "2026-06-20T00:00:00+00:00",
            "results": [
                {
                    "target": {"brand_name": "Pleo", "segment": "fintech_saas"},
                    "quality": {
                        "score": 57.3,
                        "status": "partial",
                        "validation_capture_status": "captured",
                        "verdict": "needs_review",
                        "flags": ["missing_screenshot"],
                    },
                }
            ],
        }
    )

    assert "# Visual Signature Scanner Validation Batch" in markdown
    assert "| Pleo | fintech_saas | 57.3 | partial | captured | needs_review | missing_screenshot |" in markdown
