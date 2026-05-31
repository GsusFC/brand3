from __future__ import annotations

import json
from pathlib import Path

from experiments.brand3_autoresearch.eval import evaluate_case, render_report


def test_autoresearch_eval_scores_candidate_payload():
    case = {
        "id": "owned_clear",
        "language": "en",
        "required_blocks": ["value_proposition", "mission"],
        "expected_absent_blocks": ["vision"],
        "forbid_terms": ["cookie", "login"],
        "min_evidence_blocks": 1,
    }
    candidate = {
        "lang": "en",
        "tldr_brand3": {
            "value_proposition": {
                "detected": True,
                "answer": "Helps finance teams close faster.",
                "evidence_used": ["docs"],
            },
            "mission": {
                "detected": True,
                "answer": "Build reliable workflows.",
                "evidence_used": ["mission page"],
            },
        },
        "diagnosis": {"headline": "Good"},
        "magenta_circle": {},
    }

    result = evaluate_case(case, candidate, {"coverage": 0.4, "evidence": 0.3, "noise": 0.2, "structure": 0.1})

    assert result.coverage_score == 1.0
    assert result.evidence_score == 1.0
    assert result.noise_score == 1.0
    assert result.structure_score == 1.0
    assert result.score > 0.9


def test_autoresearch_report_mentions_case_ids():
    from experiments.brand3_autoresearch.eval import CaseResult

    report = render_report(
        [CaseResult("owned_clear", 0.91, 1.0, 1.0, 1.0, 1.0, ["value_proposition"], [], [], [])],
        {"version": 1},
    )

    assert "Brand3 AutoResearch Report" in report
    assert "owned_clear" in report
