"""Benchmarking and reporting helpers for Brand3."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from statistics import mean

from src.config import BRAND3_DB_PATH
from src.niche import list_calibration_profiles
from src.services.output_files import _save_benchmark_comparison_result, _save_benchmark_result
from src.storage.sqlite_store import SQLiteStore


def benchmark_profiles(
    spec_path: str,
    *,
    profiles: list[str] | None = None,
    include_auto: bool = True,
    use_llm: bool = True,
    use_social: bool = True,
    use_competitors: bool = True,
    run_fn=None,
) -> dict:
    from src.services.brand_service import run as _run

    run_impl = run_fn or _run
    spec_file = Path(spec_path)
    spec = json.loads(spec_file.read_text(encoding="utf-8"))
    benchmark_name = spec.get("name") or spec_file.stem
    brands = spec.get("brands", [])
    if not brands:
        raise ValueError("Benchmark spec must include at least one brand")

    selected_profiles = profiles or ["base"]
    invalid_profiles = [
        profile_id
        for profile_id in selected_profiles
        if profile_id not in {item["profile_id"] for item in list_calibration_profiles()}
    ]
    if invalid_profiles:
        raise ValueError(f"Unknown calibration profiles: {', '.join(invalid_profiles)}")

    variants = []
    if include_auto:
        variants.append({"label": "auto", "profile": None, "source": "auto"})
    for profile_id in selected_profiles:
        variants.append({"label": profile_id, "profile": profile_id, "source": "manual"})

    results = []
    summary = {
        "variants": {variant["label"]: {"count": 0, "average_composite": None} for variant in variants},
        "niche_matches": {"matched": 0, "mismatched": 0, "unscored": 0},
    }
    variant_scores: dict[str, list[float]] = {variant["label"]: [] for variant in variants}

    for brand in brands:
        url = brand["url"]
        item_results = []
        for variant in variants:
            result = run_impl(
                url,
                brand_name=brand.get("brand_name"),
                use_llm=use_llm,
                use_social=use_social,
                use_competitors=use_competitors,
                calibration_profile_override=variant["profile"],
                skip_visual_analysis=True,
            )
            expected_niche = brand.get("expected_niche")
            expected_subtype = brand.get("expected_subtype")
            predicted_niche = result.get("niche_classification", {}).get("predicted_niche")
            predicted_subtype = result.get("niche_classification", {}).get("predicted_subtype")
            niche_match = None if not expected_niche else expected_niche == predicted_niche
            subtype_match = None if not expected_subtype else expected_subtype == predicted_subtype
            if expected_niche:
                if niche_match:
                    summary["niche_matches"]["matched"] += 1
                else:
                    summary["niche_matches"]["mismatched"] += 1
            else:
                summary["niche_matches"]["unscored"] += 1
            summary.setdefault("subtype_matches", {"matched": 0, "mismatched": 0, "unscored": 0})
            if expected_subtype:
                if subtype_match:
                    summary["subtype_matches"]["matched"] += 1
                else:
                    summary["subtype_matches"]["mismatched"] += 1
            else:
                summary["subtype_matches"]["unscored"] += 1

            variant_payload = {
                "variant": variant["label"],
                "profile_source": result.get("profile_source"),
                "calibration_profile": result.get("calibration_profile"),
                "run_id": result.get("run_id"),
                "composite_score": result.get("composite_score"),
                "dimensions": result.get("dimensions"),
                "predicted_niche": predicted_niche,
                "predicted_subtype": predicted_subtype,
                "niche_confidence": result.get("niche_classification", {}).get("confidence"),
                "expected_niche": expected_niche,
                "expected_subtype": expected_subtype,
                "niche_match": niche_match,
                "subtype_match": subtype_match,
            }
            item_results.append(variant_payload)
            if variant_payload["composite_score"] is not None:
                variant_scores[variant["label"]].append(float(variant_payload["composite_score"]))

        results.append(
            {
                "brand_name": brand.get("brand_name"),
                "url": url,
                "notes": brand.get("notes"),
                "results": item_results,
            }
        )

    for variant in variants:
        label = variant["label"]
        scores = variant_scores[label]
        summary["variants"][label]["count"] = len(scores)
        summary["variants"][label]["average_composite"] = round(mean(scores), 1) if scores else None

    payload = {
        "benchmark_name": benchmark_name,
        "spec_path": str(spec_file),
        "generated_at": datetime.now().isoformat(),
        "use_llm": use_llm,
        "use_social": use_social,
        "use_competitors": use_competitors,
        "variants": variants,
        "summary": summary,
        "brands": results,
    }
    output_path = _save_benchmark_result(payload)
    payload["output_path"] = str(output_path)
    print(json.dumps(payload, indent=2))
    return payload


def compare_benchmarks(before_path: str, after_path: str) -> dict:
    before_file = Path(before_path)
    after_file = Path(after_path)
    before_payload = json.loads(before_file.read_text(encoding="utf-8"))
    after_payload = json.loads(after_file.read_text(encoding="utf-8"))

    def _brand_key(item: dict) -> tuple[str, str]:
        return (item.get("brand_name") or "", item.get("url") or "")

    def _variant_map(item: dict) -> dict[str, dict]:
        return {result["variant"]: result for result in item.get("results", [])}

    before_brands = {_brand_key(item): item for item in before_payload.get("brands", [])}
    after_brands = {_brand_key(item): item for item in after_payload.get("brands", [])}

    shared_keys = sorted(set(before_brands) & set(after_brands))
    added_keys = sorted(set(after_brands) - set(before_brands))
    removed_keys = sorted(set(before_brands) - set(after_brands))

    variant_deltas: dict[str, list[float]] = {}
    variant_match_changes: dict[str, dict[str, int]] = {}
    brand_results = []

    for key in shared_keys:
        before_brand = before_brands[key]
        after_brand = after_brands[key]
        before_variants = _variant_map(before_brand)
        after_variants = _variant_map(after_brand)
        shared_variants = sorted(set(before_variants) & set(after_variants))
        comparisons = []

        for variant in shared_variants:
            before_variant = before_variants[variant]
            after_variant = after_variants[variant]
            before_composite = before_variant.get("composite_score")
            after_composite = after_variant.get("composite_score")
            delta = None
            if before_composite is not None and after_composite is not None:
                delta = round(float(after_composite) - float(before_composite), 1)
                variant_deltas.setdefault(variant, []).append(delta)

            dimension_names = sorted(
                set((before_variant.get("dimensions") or {}).keys())
                | set((after_variant.get("dimensions") or {}).keys())
            )
            dimension_deltas = {}
            for dimension_name in dimension_names:
                before_value = (before_variant.get("dimensions") or {}).get(dimension_name)
                after_value = (after_variant.get("dimensions") or {}).get(dimension_name)
                if before_value is None or after_value is None:
                    dimension_deltas[dimension_name] = {
                        "before": before_value,
                        "after": after_value,
                        "delta": None,
                    }
                else:
                    dimension_deltas[dimension_name] = {
                        "before": before_value,
                        "after": after_value,
                        "delta": round(float(after_value) - float(before_value), 1),
                    }

            match_stats = variant_match_changes.setdefault(
                variant,
                {
                    "niche_match_improved": 0,
                    "niche_match_worsened": 0,
                    "subtype_match_improved": 0,
                    "subtype_match_worsened": 0,
                },
            )
            before_niche_match = before_variant.get("niche_match")
            after_niche_match = after_variant.get("niche_match")
            if before_niche_match is False and after_niche_match is True:
                match_stats["niche_match_improved"] += 1
            elif before_niche_match is True and after_niche_match is False:
                match_stats["niche_match_worsened"] += 1

            before_subtype_match = before_variant.get("subtype_match")
            after_subtype_match = after_variant.get("subtype_match")
            if before_subtype_match is False and after_subtype_match is True:
                match_stats["subtype_match_improved"] += 1
            elif before_subtype_match is True and after_subtype_match is False:
                match_stats["subtype_match_worsened"] += 1

            comparisons.append(
                {
                    "variant": variant,
                    "before": {
                        "composite_score": before_composite,
                        "predicted_niche": before_variant.get("predicted_niche"),
                        "predicted_subtype": before_variant.get("predicted_subtype"),
                        "niche_match": before_niche_match,
                        "subtype_match": before_subtype_match,
                    },
                    "after": {
                        "composite_score": after_composite,
                        "predicted_niche": after_variant.get("predicted_niche"),
                        "predicted_subtype": after_variant.get("predicted_subtype"),
                        "niche_match": after_niche_match,
                        "subtype_match": after_subtype_match,
                    },
                    "composite_delta": delta,
                    "dimension_deltas": dimension_deltas,
                }
            )

        brand_results.append(
            {
                "brand_name": after_brand.get("brand_name"),
                "url": after_brand.get("url"),
                "variant_comparisons": comparisons,
            }
        )

    summary = {
        "shared_brands": len(shared_keys),
        "added_brands": len(added_keys),
        "removed_brands": len(removed_keys),
        "variant_deltas": {
            variant: {
                "count": len(deltas),
                "average_composite_delta": round(mean(deltas), 1) if deltas else None,
                **variant_match_changes.get(variant, {}),
            }
            for variant, deltas in variant_deltas.items()
        },
    }

    payload = {
        "before_benchmark": before_payload.get("benchmark_name") or before_file.stem,
        "after_benchmark": after_payload.get("benchmark_name") or after_file.stem,
        "before_path": str(before_file),
        "after_path": str(after_file),
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "brands": brand_results,
        "added_brand_keys": [{"brand_name": key[0], "url": key[1]} for key in added_keys],
        "removed_brand_keys": [{"brand_name": key[0], "url": key[1]} for key in removed_keys],
    }
    output_path = _save_benchmark_comparison_result(payload)
    payload["output_path"] = str(output_path)
    print(json.dumps(payload, indent=2))
    return payload


def brand_report(brand_name: str, limit: int = 10, *, db_path: str = BRAND3_DB_PATH) -> dict:
    store = SQLiteStore(db_path)
    try:
        report = store.get_brand_report(brand_name, limit=limit)
        runs = report["runs"]
        if not runs:
            print(json.dumps(report, indent=2))
            return report

        composites = [run["composite_score"] for run in runs if run["composite_score"] is not None]
        newest = composites[0] if composites else None
        oldest = composites[-1] if composites else None
        trend = None
        if newest is not None and oldest is not None and len(composites) >= 2:
            trend = round(newest - oldest, 1)

        dimensions_summary = {}
        for dimension_name, series in report["dimension_series"].items():
            values = [item["score"] for item in series]
            dimensions_summary[dimension_name] = {
                "latest": values[0],
                "average": round(mean(values), 1),
                "trend": round(values[0] - values[-1], 1) if len(values) >= 2 else 0.0,
                "samples": len(values),
            }

        feedback_summary = {
            "count": len(report["annotations"]),
            "dimensions": {},
        }
        for annotation in report["annotations"]:
            dim = annotation.get("dimension_name") or "general"
            feedback_summary["dimensions"][dim] = feedback_summary["dimensions"].get(dim, 0) + 1

        payload = {
            "brand_name": brand_name,
            "brand_profile": report.get("brand_profile"),
            "run_count": len(runs),
            "latest_composite": newest,
            "average_composite": round(mean(composites), 1) if composites else None,
            "composite_trend": trend,
            "latest_scoring_state_fingerprint": runs[0].get("scoring_state_fingerprint"),
            "latest_predicted_niche": runs[0].get("predicted_niche"),
            "latest_predicted_subtype": runs[0].get("predicted_subtype"),
            "latest_niche_confidence": runs[0].get("niche_confidence"),
            "latest_calibration_profile": runs[0].get("calibration_profile"),
            "scoring_states": {},
            "dimensions": dimensions_summary,
            "feedback": feedback_summary,
            "recent_runs": runs,
        }
        for run_item in runs:
            fingerprint = run_item.get("scoring_state_fingerprint")
            if fingerprint:
                payload["scoring_states"][fingerprint] = payload["scoring_states"].get(fingerprint, 0) + 1
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()
