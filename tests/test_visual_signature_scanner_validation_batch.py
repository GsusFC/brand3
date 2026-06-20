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
                        "verdict": "needs_review",
                        "flags": ["missing_screenshot"],
                    },
                }
            ],
        }
    )

    assert "# Visual Signature Scanner Validation Batch" in markdown
    assert "| Pleo | fintech_saas | 57.3 | partial | needs_review | missing_screenshot |" in markdown
