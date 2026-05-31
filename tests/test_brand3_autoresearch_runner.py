from __future__ import annotations

import json
from pathlib import Path

from experiments.brand3_autoresearch.run_benchmark import (
    apply_candidate_overrides,
    apply_single_candidate_override,
    candidate_variant_score,
    case_delta_summary,
    decision_from_report,
    evaluate_candidate_variant,
    export_scan_candidate,
    resolve_candidate_slug,
)
from experiments.brand3_autoresearch.materialize_variants import deep_merge, materialize_variant, load_candidate_map, load_overlay_map
from src.reports.tldr_brand3_research_pack_evaluation import build_evaluation_report


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_benchmark_runner_decides_with_existing_report() -> None:
    dataset = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/dataset.json"))
    gold = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/gold.json"))

    report = build_evaluation_report(dataset, gold)
    decision = decision_from_report(report)

    assert decision["decision"] in {"retain", "revert"}
    assert "scanner_average" in decision
    assert "analyst_average" in decision
    assert decision["case_count"] == len(report["case_evaluations"])


def test_apply_candidate_overrides_replaces_matching_case(tmp_path: Path) -> None:
    dataset = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/dataset.json"))
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    (candidate_dir / "base44.json").write_text(
        json.dumps({"payload": {"tldr_brand3": {"value_proposition": {"detected": True}}}}, ensure_ascii=False),
        encoding="utf-8",
    )

    updated = apply_candidate_overrides(dataset, candidate_dir)
    base44 = next(case for case in updated["cases"] if case["slug"] == "base44")

    assert base44["analyst_tldr"]["tldr_brand3"]["value_proposition"]["detected"] is True
    assert base44["candidate_source"]["path"].endswith("base44.json")


def test_apply_single_candidate_override_targets_one_case(tmp_path: Path) -> None:
    dataset = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/dataset.json"))
    candidate_file = tmp_path / "base44.json"
    candidate_file.write_text(
        json.dumps({"payload": {"tldr_brand3": {"mission": {"detected": True, "content": "Ship faster"}}}}, ensure_ascii=False),
        encoding="utf-8",
    )

    updated = apply_single_candidate_override(dataset, candidate_file=candidate_file, candidate_slug="base44")
    base44 = next(case for case in updated["cases"] if case["slug"] == "base44")
    bokeroon = next(case for case in updated["cases"] if case["slug"] == "bokeroon")

    assert base44["analyst_tldr"]["tldr_brand3"]["mission"]["detected"] is True
    assert base44["candidate_source"]["path"].endswith("base44.json")
    assert "candidate_source" not in bokeroon


def test_export_scan_candidate_writes_output(tmp_path: Path) -> None:
    scan_file = tmp_path / "scan.json"
    scan_file.write_text(
        json.dumps(
            {
                "id": 99,
                "brand_name": "Nike",
                "url": "https://nike.com",
                "raw_payload": json.dumps(
                    {
                        "tldr_brand3": {
                            "magnetism": {"content": "Just Do It"},
                        }
                    },
                    ensure_ascii=False,
                ),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "candidate" / "nike.json"

    exported = export_scan_candidate(scan_id=None, scan_file=scan_file, output=output)

    assert exported == output
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["metadata"]["source"] == "magnetism_scan"
    assert written["payload"]["tldr_brand3"]["magnetism"]["content"] == "Just Do It"


def test_case_delta_summary_separates_gains_and_regressions() -> None:
    report = {
        "case_evaluations": [
            {"source_url": "https://a.test", "delta_average": {"strategic_usefulness": 4.2}, "scanner_available": True},
            {"source_url": "https://b.test", "delta_average": {"strategic_usefulness": -2.7}, "scanner_available": True},
            {"source_url": "https://c.test", "delta_average": {"strategic_usefulness": 0.0}, "scanner_available": True},
        ]
    }

    summary = case_delta_summary(report)

    assert summary["improvements"] == [{"source_url": "https://a.test", "delta": 4.2, "scanner_available": True}]
    assert summary["regressions"] == [{"source_url": "https://b.test", "delta": -2.7, "scanner_available": True}]


def test_compare_scores_prefer_retained_better_variant(tmp_path: Path) -> None:
    dataset = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/dataset.json"))
    gold = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/gold.json"))
    stronger = tmp_path / "stronger.json"
    weaker = tmp_path / "weaker.json"
    stronger.write_text(
        json.dumps(
            {
                "payload": {
                    "tldr_brand3": {
                        "mission": {"detected": True, "content": "Ship focused improvements"},
                        "offer": {"detected": True, "content": "Tooling for evidence-based brand analysis"},
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    weaker.write_text(
        json.dumps({"payload": {"tldr_brand3": {"mission": {"detected": True, "content": "Ship faster"}}}}, ensure_ascii=False),
        encoding="utf-8",
    )

    variant_a = evaluate_candidate_variant(dataset=dataset, gold=gold, candidate_file=weaker, candidate_slug="base44")
    variant_b = evaluate_candidate_variant(dataset=dataset, gold=gold, candidate_file=stronger, candidate_slug="base44")

    assert candidate_variant_score(variant_b) >= candidate_variant_score(variant_a)
    assert variant_b["decision"]["case_count"] == len(variant_b["report"]["case_evaluations"])


def test_resolve_candidate_slug_falls_back_to_primary_slug() -> None:
    assert resolve_candidate_slug(Path("candidate_a.json"), None, "base44") == "base44"
    assert resolve_candidate_slug(Path("candidate_a.json"), None, None) == "candidate_a"


def test_compare_candidate_dirs_uses_distinct_variants(tmp_path: Path) -> None:
    dataset = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/dataset.json"))
    gold = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/gold.json"))
    dir_a = tmp_path / "candidate_a"
    dir_b = tmp_path / "candidate_b"
    dir_a.mkdir()
    dir_b.mkdir()

    (dir_a / "base44.json").write_text(
        json.dumps({"payload": {"tldr_brand3": {"mission": {"detected": True, "content": "Ship faster"}}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (dir_b / "base44.json").write_text(
        json.dumps(
            {
                "payload": {
                    "tldr_brand3": {
                        "mission": {"detected": True, "content": "Ship focused improvements"},
                        "offer": {"detected": True, "content": "Evidence-based brand analysis"},
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    variant_a = evaluate_candidate_variant(dataset=dataset, gold=gold, candidate_dir=dir_a)
    variant_b = evaluate_candidate_variant(dataset=dataset, gold=gold, candidate_dir=dir_b)

    assert candidate_variant_score(variant_a) <= candidate_variant_score(variant_b)
    assert variant_a["decision"]["case_count"] == len(variant_a["report"]["case_evaluations"])


def test_compare_payload_keeps_file_metadata_null_for_dir_only_runs(tmp_path: Path) -> None:
    dataset = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/dataset.json"))
    gold = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/gold.json"))
    dir_a = tmp_path / "candidate_a"
    dir_b = tmp_path / "candidate_b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "base44.json").write_text(
        json.dumps({"payload": {"tldr_brand3": {"mission": {"detected": True, "content": "Ship faster"}}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (dir_b / "base44.json").write_text(
        json.dumps({"payload": {"tldr_brand3": {"mission": {"detected": True, "content": "Ship focused improvements"}}}}, ensure_ascii=False),
        encoding="utf-8",
    )

    variant_a = evaluate_candidate_variant(dataset=dataset, gold=gold, candidate_dir=dir_a)
    variant_b = evaluate_candidate_variant(dataset=dataset, gold=gold, candidate_dir=dir_b)

    assert variant_a["decision"]["retain"] is True
    assert variant_b["decision"]["retain"] is True


def test_candidate_variant_score_penalizes_critical_regressions() -> None:
    payload_a = {
        "decision": {"retain": True, "structural_noise_delta": 0},
        "report": {
            "block_summaries": [
                {"block": "mission", "analyst_average": {"strategic_usefulness": 90.0}, "delta_average": {"strategic_usefulness": -10.0}},
                {"block": "value_proposition", "analyst_average": {"strategic_usefulness": 80.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "brand_idea", "analyst_average": {"strategic_usefulness": 80.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "personality", "analyst_average": {"strategic_usefulness": 95.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "attributes", "analyst_average": {"strategic_usefulness": 95.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "values", "analyst_average": {"strategic_usefulness": 95.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "magnetism", "analyst_average": {"strategic_usefulness": 95.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "vision", "analyst_average": {"strategic_usefulness": 95.0}, "delta_average": {"strategic_usefulness": 0.0}},
            ]
        },
    }
    payload_b = {
        "decision": {"retain": True, "structural_noise_delta": 0},
        "report": {
            "block_summaries": [
                {"block": "mission", "analyst_average": {"strategic_usefulness": 85.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "value_proposition", "analyst_average": {"strategic_usefulness": 83.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "brand_idea", "analyst_average": {"strategic_usefulness": 83.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "personality", "analyst_average": {"strategic_usefulness": 83.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "attributes", "analyst_average": {"strategic_usefulness": 83.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "values", "analyst_average": {"strategic_usefulness": 83.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "magnetism", "analyst_average": {"strategic_usefulness": 83.0}, "delta_average": {"strategic_usefulness": 0.0}},
                {"block": "vision", "analyst_average": {"strategic_usefulness": 83.0}, "delta_average": {"strategic_usefulness": 0.0}},
            ]
        },
    }

    assert candidate_variant_score(payload_b) > candidate_variant_score(payload_a)


def test_deep_merge_merges_nested_objects() -> None:
    base = {"payload": {"tldr_brand3": {"mission": {"detected": True, "content": "Ship faster"}, "values": {"detected": False}}}}
    overlay = {"payload": {"tldr_brand3": {"mission": {"content": "Ship focused improvements"}, "offer": {"detected": True}}}}

    merged = deep_merge(base, overlay)

    assert merged["payload"]["tldr_brand3"]["mission"]["detected"] is True
    assert merged["payload"]["tldr_brand3"]["mission"]["content"] == "Ship focused improvements"
    assert merged["payload"]["tldr_brand3"]["offer"]["detected"] is True


def test_materialize_variants_applies_overlays(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    overlay_a = tmp_path / "overlay_a"
    overlay_b = tmp_path / "overlay_b"
    output_a = tmp_path / "out_a"
    output_b = tmp_path / "out_b"
    source_dir.mkdir()
    overlay_a.mkdir()
    overlay_b.mkdir()
    (source_dir / "base44.json").write_text(
        json.dumps({"payload": {"tldr_brand3": {"mission": {"detected": True, "content": "Ship faster"}}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (overlay_b / "base44.json").write_text(
        json.dumps({"payload": {"tldr_brand3": {"offer": {"detected": True, "content": "Evidence-based brand analysis"}}}}, ensure_ascii=False),
        encoding="utf-8",
    )

    source_map = load_candidate_map(None, source_dir, None)
    overlays_a = load_overlay_map(overlay_a)
    overlays_b = load_overlay_map(overlay_b)

    written_a = materialize_variant(source_map=source_map, overlay_map=overlays_a, output_dir=output_a)
    written_b = materialize_variant(source_map=source_map, overlay_map=overlays_b, output_dir=output_b)

    assert written_a[0].exists()
    assert written_b[0].exists()
    assert json.loads((output_b / "base44.json").read_text(encoding="utf-8"))["payload"]["tldr_brand3"]["offer"]["detected"] is True
