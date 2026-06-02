from __future__ import annotations

import json

from scripts.contextdev_candidates_from_benchmark import _case_files
from src.research.contextdev_candidates import build_contextdev_candidates, summarize_contextdev_candidates


def test_case_files_skips_benchmark_summary(tmp_path) -> None:
    case_path = tmp_path / "chatgpt.json"
    benchmark_path = tmp_path / "benchmark.json"
    case_path.write_text("{}", encoding="utf-8")
    benchmark_path.write_text("{}", encoding="utf-8")

    assert _case_files([tmp_path]) == [case_path]


def test_candidate_summary_from_artifact_payload(tmp_path) -> None:
    payload = {
        "case": {"brand": "Example", "url": "https://example.com", "domain": "example.com"},
        "outputs": {
            "retrieve_brand": {"brand": {"title": "Example", "description": "Example builds tools."}},
            "products": {"products": [{"name": "Example Product", "description": "A useful tool."}]},
        },
    }
    path = tmp_path / "example.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    candidates = []
    for case_file in _case_files([tmp_path]):
        candidates.extend(build_contextdev_candidates(json.loads(case_file.read_text(encoding="utf-8"))))
    summary = summarize_contextdev_candidates(candidates)

    assert summary["candidate_count"] == 2
    assert summary["by_channel"] == {"entity_resolution": 1, "product_extraction": 1}
