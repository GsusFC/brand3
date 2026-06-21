"""Read-side reporting helpers for Brand3."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from statistics import mean

from src.config import BRAND3_DB_PATH
from src.niche import list_calibration_profiles
from src.quality.dimension_confidence import dimension_confidence_from_snapshot
from src.quality.evidence_summary import summarize_evidence_records
from src.quality.trust import quality_label
from src.services.analysis_reporting import brand_report as _brand_report_impl
from src.services.output_files import _save_benchmark_comparison_result, _save_benchmark_result
from src.services.report_summaries import _trust_summary_payload
from src.storage.sqlite_store import SQLiteStore


def learn(
    run_id: int | None = None,
    brand_name: str | None = None,
    url: str | None = None,
    *,
    db_path: str = BRAND3_DB_PATH,
) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        target_run_id = run_id or store.get_latest_run_id(brand_name=brand_name, url=url)
        if not target_run_id:
            raise ValueError("No matching run found for learning analysis")

        snapshot = store.get_run_snapshot(target_run_id)
        from src.learning.calibration import CalibrationAnalyzer

        analyzer = CalibrationAnalyzer()
        recommendations = analyzer.analyze_snapshot(snapshot)
        recommendations.extend(analyzer.analyze_annotations(store.list_annotations(brand_name=brand_name)))

        payload = [
            {
                "scope": rec.scope,
                "target": rec.target,
                "severity": rec.severity,
                "message": rec.message,
                "evidence": rec.evidence,
            }
            for rec in recommendations
        ]
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def list_runs(
    brand_name: str | None = None,
    url: str | None = None,
    limit: int = 20,
    *,
    db_path: str = BRAND3_DB_PATH,
) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        runs = store.list_runs(brand_name=brand_name, url=url, limit=limit)
        print(json.dumps(runs, indent=2))
        return runs
    finally:
        store.close()


def list_brands(limit: int = 50, *, db_path: str = BRAND3_DB_PATH) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        brands = store.list_brands(limit=limit)
        print(json.dumps(brands, indent=2))
        return brands
    finally:
        store.close()


def list_profiles() -> list[dict]:
    profiles = list_calibration_profiles()
    print(json.dumps(profiles, indent=2))
    return profiles


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
                    "delta": delta,
                    "dimension_deltas": dimension_deltas,
                }
            )

        brand_results.append(
            {
                "brand_name": before_brand.get("brand_name") or after_brand.get("brand_name"),
                "url": before_brand.get("url") or after_brand.get("url"),
                "comparisons": comparisons,
            }
        )

    payload = {
        "before_path": str(before_file),
        "after_path": str(after_file),
        "shared_brands": len(shared_keys),
        "added_brands": len(added_keys),
        "removed_brands": len(removed_keys),
        "variant_deltas": {
            variant: {
                "average_delta": round(mean(deltas), 1) if deltas else None,
                "count": len(deltas),
            }
            for variant, deltas in variant_deltas.items()
        },
        "variant_match_changes": variant_match_changes,
        "brands": brand_results,
    }
    payload["summary"] = {
        "shared_brands": payload["shared_brands"],
        "added_brands": payload["added_brands"],
        "removed_brands": payload["removed_brands"],
        "variant_deltas": {
            variant: {
                "average_composite_delta": stats.get("average_delta"),
                "count": stats.get("count"),
                "niche_match_improved": payload["variant_match_changes"].get(variant, {}).get("niche_match_improved", 0),
                "niche_match_worsened": payload["variant_match_changes"].get(variant, {}).get("niche_match_worsened", 0),
                "subtype_match_improved": payload["variant_match_changes"].get(variant, {}).get("subtype_match_improved", 0),
                "subtype_match_worsened": payload["variant_match_changes"].get(variant, {}).get("subtype_match_worsened", 0),
            }
            for variant, stats in payload["variant_deltas"].items()
        },
        "variant_match_changes": payload["variant_match_changes"],
    }
    output_path = _save_benchmark_comparison_result(payload)
    payload["output_path"] = str(output_path)
    print(json.dumps(payload, indent=2))
    return payload


def list_feedback(brand_name: str | None = None, *, db_path: str = BRAND3_DB_PATH) -> list[dict]:
    store = SQLiteStore(db_path)
    try:
        feedback = store.list_feedback(brand_name=brand_name)
        print(json.dumps(feedback, indent=2))
        return feedback
    finally:
        store.close()


def _context_readiness_from_snapshot(snapshot: dict) -> dict:
    for item in reversed(snapshot.get("raw_inputs") or []):
        if item.get("source") != "context" or not isinstance(item.get("payload"), dict):
            continue
        payload = item["payload"]
        coverage = float(payload.get("coverage") or 0.0)
        confidence = float(payload.get("confidence") or 0.0)
        if coverage < 0.3:
            status = "insufficient_data"
        elif confidence < 0.6:
            status = "degraded"
        else:
            status = "good"
        return {
            "available": True,
            "coverage": coverage,
            "confidence": confidence,
            "coverage_label": quality_label(coverage),
            "confidence_label": quality_label(confidence),
            "status": status,
            "confidence_reason": payload.get("confidence_reason") or [],
            "context_score": payload.get("context_score"),
        }
    return {
        "available": False,
        "coverage": 0.0,
        "confidence": 0.0,
        "coverage_label": "baja",
        "confidence_label": "baja",
        "status": "insufficient_data",
        "confidence_reason": ["context_scan_unavailable"],
    }


def show_run(run_id: int, *, db_path: str = BRAND3_DB_PATH) -> dict:
    store = SQLiteStore(db_path)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        context_summary = _context_readiness_from_snapshot(snapshot)
        trust_summary = snapshot["audit"].get("trust_summary") if snapshot.get("audit") else None
        if not trust_summary:
            trust_summary = {
                "data_quality": snapshot["run"].get("data_quality"),
                "context_summary": context_summary,
                "evidence_summary": snapshot["audit"].get("evidence_summary") if snapshot.get("audit") else None,
                "dimension_confidence": snapshot["audit"].get("dimension_confidence") if snapshot.get("audit") else None,
            }
        payload = {
            "run_id": run_id,
            **snapshot["run"],
            "audit": snapshot["audit"],
            "brand_profile": snapshot["brand_profile"],
            "context_readiness": context_summary,
            "trust_summary": trust_summary,
        }
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def run_evidence_summary(run_id: int, *, db_path: str = BRAND3_DB_PATH) -> dict:
    store = SQLiteStore(db_path)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        audit = snapshot.get("run", {}).get("audit") or {}
        summary = summarize_evidence_records(
            snapshot.get("features") or [],
            evidence_items=snapshot.get("evidence_items") or [],
        )
        summary = audit.get("evidence_summary") or summary
        print(json.dumps(summary, indent=2))
        return summary
    finally:
        store.close()


def run_dimension_confidence(run_id: int, *, db_path: str = BRAND3_DB_PATH) -> dict:
    store = SQLiteStore(db_path)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        audit = snapshot.get("run", {}).get("audit") or {}
        summary = audit.get("dimension_confidence") or dimension_confidence_from_snapshot(snapshot)
        print(json.dumps(summary, indent=2))
        return summary
    finally:
        store.close()


def run_trust_summary(run_id: int, *, db_path: str = BRAND3_DB_PATH) -> dict:
    store = SQLiteStore(db_path)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        run_payload = snapshot.get("run") or {}
        context_summary = _context_readiness_from_snapshot(snapshot)
        evidence_summary = summarize_evidence_records(
            snapshot.get("features") or [],
            evidence_items=snapshot.get("evidence_items") or [],
        )
        dimension_confidence = dimension_confidence_from_snapshot(snapshot)
        trust_summary = _trust_summary_payload(
            data_quality=run_payload.get("data_quality") or "unknown",
            context_summary=context_summary,
            evidence_summary=evidence_summary,
            dimension_confidence=dimension_confidence,
        )
        summary = {
            "run_id": run_id,
            **trust_summary,
            "trust_summary": trust_summary,
            "context_readiness": context_summary,
            "evidence_summary": evidence_summary,
            "dimension_confidence": dimension_confidence,
        }
        print(json.dumps(summary, indent=2))
        return summary
    finally:
        store.close()


def brand_report(brand_name: str, limit: int = 10) -> dict:
    return _brand_report_impl(brand_name, limit=limit, db_path=BRAND3_DB_PATH)
