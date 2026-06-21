"""Console diagnostics for service runs."""

from __future__ import annotations

from time import perf_counter


def _print_feature_details(brand_score) -> None:
    print("\n--- Feature Details ---")
    for dim_name, dim_score in brand_score.dimensions.items():
        print(f"\n[{dim_name}]")
        if dim_score.score is None:
            print("  score unavailable  reason=insufficient_data")
            continue
        for feat_name, feat in dim_score.features.items():
            conf = f"(conf: {feat.confidence:.0%})" if feat.confidence < 1 else ""
            src = f"src={feat.source}"
            print(f"  {feat_name:30s} {feat.value:6.1f}  {conf}  {src}")
            if feat.raw_value:
                raw_str = str(feat.raw_value)
                raw = raw_str[:120] + "..." if len(raw_str) > 120 else raw_str
                print(f"    raw: {raw}")


def _log_timing(label: str, started: float) -> float:
    now = perf_counter()
    print(f"[timing] {label}: {(now - started):.2f}s")
    return now
