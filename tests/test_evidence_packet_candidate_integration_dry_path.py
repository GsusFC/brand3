from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    script_path = Path("scripts/evidence_packet_candidate_integration_dry_path.py")
    spec = importlib.util.spec_from_file_location("candidate_integration_dry_path", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_manifest_filters_blocked_and_empty_text(tmp_path):
    module = _load_module()

    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    ready_candidate = {
        "dimensions": {
            "diferenciacion": {
                "readiness_status": "ready",
                "prompt_constraints": ["Use bounded interpretation."],
                "evidence": [
                    {"text": " ", "url": "https://drop.example", "source_class": "external"},
                    {"text": "kept evidence", "url": "https://keep.example", "source_class": "external", "limits": "x"},
                ],
            }
        }
    }
    blocked_candidate = {
        "dimensions": {
            "coherencia": {
                "readiness_status": "blocked",
                "prompt_constraints": [],
                "evidence": [{"text": "blocked", "url": "https://blocked.example", "source_class": "external"}],
            }
        }
    }

    (input_dir / "linear.prompt_input_candidate.v0.json").write_text(json.dumps(ready_candidate))
    (input_dir / "builtwith_kit_com.prompt_input_candidate.v0.json").write_text(json.dumps(blocked_candidate))

    module.INPUT_DIR = input_dir
    module.TARGETS = [
        {"case_id": "linear", "dimension": "diferenciacion", "intent": "ready"},
        {"case_id": "builtwith_kit_com", "dimension": "coherencia", "intent": "blocked_control"},
    ]

    manifest = module._build_manifest()
    assert len(manifest["requests"]) == 1
    request = manifest["requests"][0]
    payload = json.loads(request["user"])
    assert request["included_evidence_count"] == 1
    assert len(payload["included_evidence"]) == 1
    assert payload["included_evidence"][0]["text"] == "kept evidence"
    assert payload["included_evidence"][0]["url"] == "https://keep.example"
    assert len(manifest["skipped"]) == 1
    assert manifest["skipped"][0]["status"] == "blocked"


def test_comparison_sets_pass_flags_and_parse_unrecovered_zero():
    module = _load_module()
    module._previous_summary = lambda case_id, dimension: {"available": False}

    manifest = {
        "skipped": [
            {"case_id": "builtwith_kit_com", "dimension": "coherencia"},
            {"case_id": "builtwith_kit_com", "dimension": "percepcion"},
            {"case_id": "launchdarkly", "dimension": "coherencia"},
        ]
    }
    raw_outputs = {
        "executed": True,
        "results": [
            {
                "case_id": "vercel",
                "dimension": "coherencia",
                "intent": "thin",
                "readiness_status": "thin",
                "included_evidence_count": 1,
                "json_repair_retry_attempted": False,
                "json_repair_retry_succeeded": False,
                "parse_failure_unrecovered": False,
                "summary": {
                    "finding_count": 1,
                    "has_typical_decision": False,
                    "limits_field_present": True,
                    "risky_terms_outside_limits": [],
                    "evidence_url_validity": True,
                },
            },
            {
                "case_id": "watermelon",
                "dimension": "percepcion",
                "intent": "thin",
                "readiness_status": "thin",
                "included_evidence_count": 1,
                "json_repair_retry_attempted": False,
                "json_repair_retry_succeeded": False,
                "parse_failure_unrecovered": False,
                "summary": {
                    "finding_count": 1,
                    "has_typical_decision": False,
                    "limits_field_present": True,
                    "risky_terms_outside_limits": [],
                    "evidence_url_validity": True,
                },
            },
        ],
    }

    comparison = module._comparison(manifest, raw_outputs)
    assert comparison["parse_failures_unrecovered"] == 0
    assert comparison["pass_flags"]["parse_failures_unrecovered_zero"] is True
    assert comparison["pass_flags"]["blocked_or_review_controls_skipped"] is True
    assert comparison["pass_flags"]["thin_cases_qualified"] is True
    assert comparison["trial_pass"] is True
