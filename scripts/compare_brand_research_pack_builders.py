from __future__ import annotations

import argparse
import json
from typing import Any

from src.config import BRAND3_DB_PATH
from src.research.pack_comparison import compare_pack_builders_from_snapshot
from src.research.research_pack_promotion import evaluate_research_pack_promotion
from src.storage.sqlite_store import SQLiteStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare legacy BrandResearchPack builder against EvidenceGraph-backed builder.",
    )
    parser.add_argument("run_ids", nargs="*", type=int, help="Brand Audit run IDs to compare.")
    parser.add_argument("--limit", type=int, default=8, help="Compare latest runs when run IDs are omitted.")
    parser.add_argument("--json", action="store_true", help="Emit full JSON instead of compact text.")
    args = parser.parse_args(argv)

    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        run_ids = args.run_ids or _latest_run_ids(store, args.limit)
        comparisons = []
        for run_id in run_ids:
            snapshot = store.get_run_snapshot(run_id)
            if snapshot is None:
                print(f"run {run_id}: not found")
                continue
            comparison = compare_pack_builders_from_snapshot(snapshot)
            promotion = evaluate_research_pack_promotion(snapshot)
            comparisons.append((comparison, promotion))
    finally:
        store.close()

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "comparison": comparison.to_dict(),
                        "promotion_report": promotion.to_dict(),
                    }
                    for comparison, promotion in comparisons
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    for comparison, promotion in comparisons:
        summary = comparison.summary()
        print(
            f"run={comparison.run_id} brand={comparison.brand_name} "
            f"sources={comparison.graph_summary.get('source_count')} "
            f"claims={comparison.graph_summary.get('claim_count')} "
            f"gained={summary['gained_count']} lost={summary['lost_count']} changed={summary['changed_count']} "
            f"promotion={promotion.decisions[0].status}"
        )
        if promotion.decisions:
            decision = promotion.decisions[0]
            print(f"  reasons: {', '.join(decision.reason_codes)}")
        if summary["gained_fields"]:
            print("  gained:", ", ".join(summary["gained_fields"]))
        if summary["lost_fields"]:
            print("  lost:", ", ".join(summary["lost_fields"]))
        for field in comparison.fields:
            if field.field in {"offer", "declared_mission", "future_direction", "values_signals"} and field.changed:
                print(f"  {field.field}:")
                print(f"    legacy: {field.legacy_preview or '-'}")
                print(f"    graph : {field.graph_preview or '-'}")
    return 0


def _latest_run_ids(store: SQLiteStore, limit: int) -> list[int]:
    rows = store.conn.execute(
        """
        SELECT id
        FROM runs
        WHERE completed_at IS NOT NULL
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [int(row["id"]) for row in rows]


if __name__ == "__main__":
    raise SystemExit(main())
