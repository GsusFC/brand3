from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    script_path = Path("scripts/evidence_packet_candidate_integration_dry_path_v2_1.py")
    spec = importlib.util.spec_from_file_location("candidate_integration_dry_path_v2_1", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_manifest_filters_non_executable_rows(tmp_path):
    module = _load_module()
    manifest_path = tmp_path / "request_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "created_at": "x",
                "requests": [
                    {"case_id": "a", "dimension": "d", "readiness_status": "ready"},
                    {"case_id": "b", "dimension": "d", "readiness_status": "thin"},
                    {"case_id": "c", "dimension": "d", "readiness_status": "blocked"},
                ],
                "skipped": [{"case_id": "k", "dimension": "d", "status": "blocked"}],
            }
        )
    )
    loaded = module._load_manifest(manifest_path)
    assert len(loaded["requests"]) == 2
    assert {row["case_id"] for row in loaded["requests"]} == {"a", "b"}
    assert len(loaded["skipped"]) == 1


def test_comparison_sets_pass_flags_with_thin_rows_and_controls():
    module = _load_module()
    manifest = {
        "requests": [],
        "skipped": [
            {"case_id": "builtwith_kit_com", "dimension": "coherencia", "status": "blocked"},
            {"case_id": "builtwith_kit_com", "dimension": "percepcion", "status": "blocked"},
        ],
    }
    raw_outputs = {
        "executed": True,
        "results": [
            {
                "case_id": "vercel",
                "dimension": "coherencia",
                "intent": "segmented_matrix_case",
                "readiness_status": "thin",
                "included_evidence_count": 1,
                "summary": {
                    "finding_count": 1,
                    "has_typical_decision": False,
                    "limits_field_present": True,
                    "risky_terms_outside_limits": [],
                    "evidence_url_validity": True,
                },
                "json_repair_retry_attempted": False,
                "json_repair_retry_succeeded": False,
                "parse_failure_unrecovered": False,
            }
        ],
    }
    comparison = module._comparison(manifest, raw_outputs)
    assert comparison["pass_flags"]["no_typical_decision"] is True
    assert comparison["pass_flags"]["limits_present"] is True
    assert comparison["pass_flags"]["risky_terms_outside_limits_empty"] is True
    assert comparison["pass_flags"]["evidence_urls_valid"] is True
    assert comparison["pass_flags"]["blocked_or_review_controls_skipped"] is True
    assert comparison["pass_flags"]["thin_cases_qualified"] is True
    assert comparison["pass_flags"]["parse_failures_unrecovered_zero"] is True
    assert comparison["trial_pass"] is True
