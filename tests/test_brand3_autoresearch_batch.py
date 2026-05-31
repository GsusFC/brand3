from __future__ import annotations

from pathlib import Path

import experiments.brand3_autoresearch.run_batch as run_batch


def _fake_result(strategic: float, delta: float, retain: bool = True) -> dict:
    return {
        "report": {
            "block_summaries": [
                {"block": "core_purpose", "analyst_average": {"strategic_usefulness": strategic}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "value_proposition", "analyst_average": {"strategic_usefulness": strategic}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "brand_idea", "analyst_average": {"strategic_usefulness": strategic}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "mission", "analyst_average": {"strategic_usefulness": strategic}, "delta_average": {"strategic_usefulness": delta}},
            ]
        },
        "decision": {
            "decision": "retain" if retain else "revert",
            "retain": retain,
            "scanner_average": {"strategic_usefulness": strategic - 5.0},
            "analyst_average": {"strategic_usefulness": strategic},
            "structural_noise_delta": 1,
            "case_count": 1,
        },
        "case_delta_summary": {"improvements": [], "regressions": []},
    }


def test_execute_spec_and_persist_history(tmp_path: Path, monkeypatch) -> None:
    def fake_evaluate_candidate_variant(*, candidate_dir=None, candidate_file=None, candidate_slug=None, dataset=None, gold=None):
        label = ""
        if candidate_dir is not None:
            label = Path(candidate_dir).name
        elif candidate_file is not None:
            label = Path(candidate_file).stem
        if label.endswith("b"):
            return _fake_result(82.0, 0.0)
        return _fake_result(78.0, -8.0)

    monkeypatch.setattr(run_batch, "evaluate_candidate_variant", fake_evaluate_candidate_variant)

    spec = {
        "name": "base44",
        "candidate_dir": "candidate_a",
        "candidate_dir_b": "candidate_b",
    }
    record = run_batch.execute_spec(spec, dataset={}, gold={}, base_dir=tmp_path)

    assert record["mode"] == "compare"
    assert record["comparison"]["winner"] == "b"
    assert record["comparison"]["score_b"][1] > record["comparison"]["score_a"][1]
    assert record["candidate_a"]["slug"] == "candidate_a"
    assert record["candidate_b"]["slug"] == "candidate_b"

    history_path = tmp_path / "history" / "batch_history.jsonl"
    run_batch.append_history(history_path, [record])

    loaded = run_batch.load_history(history_path)
    assert loaded[0]["comparison"]["winner"] == "b"


def test_summarize_history_waits_for_enough_data() -> None:
    records = []
    for _ in range(5):
        records.append(
            {
                "mode": "compare",
                "comparison": {
                    "winner": "b",
                    "score_a": [1.0, 78.0, -0.0],
                    "score_b": [1.0, 80.0, -0.0],
                    "margin": 2.0,
                    "retain_a": True,
                    "retain_b": True,
                    "critical_regression_a": 0.0,
                    "critical_regression_b": 0.0,
                },
            }
        )

    summary = run_batch.summarize_history(records, min_runs_for_recommendation=5)

    assert summary["sufficient_data"] is True
    assert summary["recommendation"]["status"] == "prefer_b"
    assert summary["wins"]["b"] == 5
    assert summary["average_margin"] == 2.0
