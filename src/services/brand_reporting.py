"""Brand-level reporting helpers."""

from __future__ import annotations

from statistics import mean

from src.storage.sqlite_store import SQLiteStore


def brand_report(brand_name: str, limit: int = 10, *, db_path: str) -> dict:
    store = SQLiteStore(db_path)
    try:
        report = store.get_brand_report(brand_name, limit=limit)
        runs = report["runs"]
        if not runs:
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
        return payload
    finally:
        store.close()
