#!/usr/bin/env python3
"""Measure Research Pack rollout readiness across local Brand3 runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.config import BRAND3_DB_PATH
from src.research.pack_comparison import compare_pack_builders_from_snapshot
from src.research.research_pack_promotion import evaluate_research_pack_promotion
from src.storage.sqlite_store import SQLiteStore


CRITICAL_FIELDS = ("company_summary", "product_summary", "offer")
READY_PROMOTION_RATE = 0.95


def main() -> int:
    args = _parse_args()
    store = SQLiteStore(str(args.db))
    try:
        run_ids = args.run_ids or _latest_run_ids(store, args.limit)
        reports = [build_run_rollout_report(store, run_id) for run_id in run_ids]
    finally:
        store.close()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for report in reports:
        run_id = report.get("run_id") or "unknown"
        (args.output_dir / f"run-{run_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = summarize_rollout_reports(reports, db_path=str(args.db))
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "summary.md").write_text(render_rollout_summary_markdown(summary), encoding="utf-8")
    print(f"Wrote {args.output_dir}")
    print(
        "Summary: runs={run_count} promotable={promotable_count} blocked={blocked_count} review={review_required_count}".format(
            run_count=summary["run_count"],
            promotable_count=summary["promotion_status_counts"].get("promotable", 0),
            blocked_count=summary["promotion_status_counts"].get("blocked", 0),
            review_required_count=summary["promotion_status_counts"].get("review_required", 0),
        )
    )
    return 0


def build_run_rollout_report(store: SQLiteStore, run_id: int) -> dict[str, Any]:
    snapshot = store.get_run_snapshot(run_id)
    if snapshot is None:
        return {"run_id": run_id, "status": "not_found"}

    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    try:
        comparison = compare_pack_builders_from_snapshot(snapshot)
        promotion = evaluate_research_pack_promotion(snapshot)
    except Exception as exc:  # pragma: no cover - defensive for ad hoc local runs.
        return {
            "run_id": run_id,
            "status": "error",
            "brand_name": str(run.get("brand_name") or ""),
            "url": str(run.get("url") or ""),
            "error": str(exc),
        }

    summary = comparison.summary()
    return {
        "run_id": run_id,
        "status": "ok",
        "brand_name": str(run.get("brand_name") or ""),
        "url": str(run.get("url") or ""),
        "base_cohort": _rollout_base_cohort(comparison),
        "segment": _rollout_segment(summary),
        "cohort": f"{_rollout_base_cohort(comparison)}:{_rollout_segment(summary)}",
        "graph_summary": comparison.graph_summary,
        "comparison": comparison.to_dict(),
        "promotion_report": promotion.to_dict(),
        "promotion_status": promotion.decisions[0].status if promotion.decisions else "unknown",
        "gained_count": summary["gained_count"],
        "lost_count": summary["lost_count"],
        "changed_count": summary["changed_count"],
        "critical_losses": _critical_losses(summary),
    }


def summarize_rollout_reports(reports: list[dict[str, Any]], *, db_path: str) -> dict[str, Any]:
    promotion_status_counts: dict[str, int] = {}
    critical_loss_counts: dict[str, int] = {}
    cohort_rows: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    for report in reports:
        if report.get("status") != "ok":
            rows.append({"run_id": report.get("run_id"), "status": report.get("status")})
            continue

        status = str(report.get("promotion_status") or "unknown")
        promotion_status_counts[status] = promotion_status_counts.get(status, 0) + 1
        critical_losses = list(report.get("critical_losses") or [])
        for field in critical_losses:
            critical_loss_counts[field] = critical_loss_counts.get(field, 0) + 1

        cohort = str(report.get("cohort") or "unknown")
        base_cohort = str(report.get("base_cohort") or "unknown")
        segment = str(report.get("segment") or "unknown")
        cohort_row = cohort_rows.setdefault(
            cohort,
            {
                "cohort": cohort,
                "base_cohort": base_cohort,
                "segment": segment,
                "run_count": 0,
                "promotable_count": 0,
                "blocked_count": 0,
                "review_required_count": 0,
                "gained_total": 0,
                "lost_total": 0,
                "changed_total": 0,
                "critical_loss_total": 0,
            },
        )
        cohort_row["run_count"] += 1
        cohort_row["gained_total"] += int(report.get("gained_count") or 0)
        cohort_row["lost_total"] += int(report.get("lost_count") or 0)
        cohort_row["changed_total"] += int(report.get("changed_count") or 0)
        cohort_row["critical_loss_total"] += len(critical_losses)
        if status == "promotable":
            cohort_row["promotable_count"] += 1
        elif status == "blocked":
            cohort_row["blocked_count"] += 1
        elif status == "review_required":
            cohort_row["review_required_count"] += 1

        rows.append(
            {
                "run_id": report.get("run_id"),
                "brand_name": report.get("brand_name"),
                "url": report.get("url"),
                "cohort": cohort,
                "promotion_status": status,
                "gained_count": report.get("gained_count"),
                "lost_count": report.get("lost_count"),
                "changed_count": report.get("changed_count"),
                "critical_losses": critical_losses,
                "base_cohort": base_cohort,
                "segment": segment,
            }
        )

    cohort_metrics = []
    for cohort, row in sorted(cohort_rows.items()):
        run_count = int(row["run_count"]) or 1
        cohort_metrics.append(
            {
                **row,
                "promotion_rate": round(row["promotable_count"] / run_count, 4),
                "blocked_rate": round(row["blocked_count"] / run_count, 4),
                "review_required_rate": round(row["review_required_count"] / run_count, 4),
                "avg_gained": round(row["gained_total"] / run_count, 2),
                "avg_lost": round(row["lost_total"] / run_count, 2),
                "avg_changed": round(row["changed_total"] / run_count, 2),
                "avg_critical_losses": round(row["critical_loss_total"] / run_count, 2),
            }
        )

    return {
        "version": "research_pack_rollout_batch_v0_1",
        "db_path": db_path,
        "run_count": len(reports),
        "ok_count": sum(1 for report in reports if report.get("status") == "ok"),
        "promotion_status_counts": dict(sorted(promotion_status_counts.items())),
        "critical_loss_counts": dict(sorted(critical_loss_counts.items(), key=lambda item: (-item[1], item[0]))),
        "cohort_metrics": cohort_metrics,
        "cohort_rollout_policy": _cohort_rollout_policy(cohort_metrics),
        "rollout_readiness": _rollout_readiness(cohort_metrics, critical_loss_counts),
        "runs": rows,
    }


def render_rollout_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Research Pack Rollout",
        "",
        f"- Runs: `{summary['run_count']}`",
        f"- OK: `{summary['ok_count']}`",
        f"- Promotion statuses: `{summary['promotion_status_counts']}`",
        f"- Rollout readiness: `{(summary.get('rollout_readiness') or {}).get('status')}`",
        "",
    ]
    lines.extend(
        [
            "## Cohorts",
            "",
            "| Cohort | Runs | Promotable | Blocked | Review | Promotion rate | Critical losses | Avg gained | Avg lost | Avg changed |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary.get("cohort_metrics") or []:
        lines.append(
            "| {cohort} | {run_count} | {promotable} | {blocked} | {review} | {promotion_rate:.2%} | {critical} | {gained:.2f} | {lost:.2f} | {changed:.2f} |".format(
                cohort=_md_cell(row.get("cohort")),
                run_count=row.get("run_count") or 0,
                promotable=row.get("promotable_count") or 0,
                blocked=row.get("blocked_count") or 0,
                review=row.get("review_required_count") or 0,
                promotion_rate=float(row.get("promotion_rate") or 0.0),
                critical=row.get("critical_loss_total") or 0,
                gained=float(row.get("avg_gained") or 0.0),
                lost=float(row.get("avg_lost") or 0.0),
                changed=float(row.get("avg_changed") or 0.0),
            )
        )

    rollout_policy = summary.get("cohort_rollout_policy") or []
    if rollout_policy:
        lines.extend(
            [
                "",
                "## Cohort Policy",
                "",
                "| Cohort | Status | Reasons |",
                "| --- | --- | --- |",
            ]
        )
        for row in rollout_policy:
            lines.append(
                "| {cohort} | {status} | {reasons} |".format(
                    cohort=_md_cell(row.get("cohort")),
                    status=row.get("status") or "",
                    reasons=_md_cell(", ".join(row.get("reason_codes") or [])),
                )
            )

    critical_loss_counts = summary.get("critical_loss_counts") or {}
    if critical_loss_counts:
        lines.extend(
            [
                "",
                "## Critical Losses",
                "",
                "| Field | Count |",
                "| --- | ---: |",
            ]
        )
        for field, count in critical_loss_counts.items():
            lines.append(f"| {field} | {count} |")
    lines.extend(
        [
            "",
            "## Runs",
            "",
            "| Run | Brand | Cohort | Status | Gained | Lost | Changed | Critical losses |",
            "| ---: | --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in summary.get("runs") or []:
        losses = ", ".join(str(item) for item in row.get("critical_losses") or []) or "-"
        lines.append(
            "| {run_id} | {brand} | {cohort} | {status} | {gained} | {lost} | {changed} | {losses} |".format(
                run_id=row.get("run_id"),
                brand=_md_cell(row.get("brand_name")),
                cohort=_md_cell(row.get("cohort")),
                status=row.get("promotion_status") or row.get("status"),
                gained=row.get("gained_count") or 0,
                lost=row.get("lost_count") or 0,
                changed=row.get("changed_count") or 0,
                losses=_md_cell(losses),
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def _cohort_rollout_policy(cohort_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in cohort_metrics:
        reasons: list[str] = []
        promotion_rate = float(row.get("promotion_rate") or 0.0)
        blocked_rate = float(row.get("blocked_rate") or 0.0)
        review_rate = float(row.get("review_required_rate") or 0.0)
        critical_losses = int(row.get("critical_loss_total") or 0)
        if promotion_rate < READY_PROMOTION_RATE:
            reasons.append("promotion_rate_below_threshold")
        if blocked_rate > 0.0:
            reasons.append("blocked_runs_present")
        if review_rate > 0.0:
            reasons.append("review_required_runs_present")
        if critical_losses > 0:
            reasons.append("critical_losses_present")
        rows.append(
            {
                "cohort": row.get("cohort"),
                "status": "ready" if not reasons else "not_ready",
                "reason_codes": reasons or ["meets_rollout_thresholds"],
                "promotion_rate": promotion_rate,
                "blocked_rate": blocked_rate,
                "review_rate": review_rate,
                "critical_loss_total": critical_losses,
            }
        )
    return rows


def _rollout_readiness(cohort_metrics: list[dict[str, Any]], critical_loss_counts: dict[str, int]) -> dict[str, Any]:
    if not cohort_metrics:
        return {
            "status": "not_ready",
            "reason_codes": ["no_cohort_data"],
            "notes": ["No runs were available to evaluate rollout readiness."],
        }

    promotion_rate = max(float(row.get("promotion_rate") or 0.0) for row in cohort_metrics)
    blocked_rate = max(float(row.get("blocked_rate") or 0.0) for row in cohort_metrics)
    review_rate = max(float(row.get("review_required_rate") or 0.0) for row in cohort_metrics)
    critical_loss_total = sum(int(value) for value in critical_loss_counts.values())

    reason_codes = []
    if promotion_rate < READY_PROMOTION_RATE:
        reason_codes.append("promotion_rate_below_threshold")
    if blocked_rate > 0.0:
        reason_codes.append("blocked_runs_present")
    if review_rate > 0.0:
        reason_codes.append("review_required_runs_present")
    if critical_loss_total > 0:
        reason_codes.append("critical_losses_present")

    if not reason_codes:
        return {
            "status": "ready",
            "reason_codes": ["meets_rollout_thresholds"],
            "thresholds": {
                "promotion_rate_min": READY_PROMOTION_RATE,
                "blocked_rate_max": 0.0,
                "review_rate_max": 0.0,
                "critical_loss_total_max": 0,
            },
        }

    return {
        "status": "not_ready",
        "reason_codes": reason_codes,
        "thresholds": {
            "promotion_rate_min": READY_PROMOTION_RATE,
            "blocked_rate_max": 0.0,
            "review_rate_max": 0.0,
            "critical_loss_total_max": 0,
        },
        "notes": [
            f"Best promotion rate observed: {promotion_rate:.2%}",
            f"Blocked rate observed: {blocked_rate:.2%}",
            f"Review-required rate observed: {review_rate:.2%}",
            f"Critical losses observed: {critical_loss_total}",
        ],
    }


def _critical_losses(summary: dict[str, Any]) -> list[str]:
    losses = [field for field in summary.get("lost_fields") or [] if field in CRITICAL_FIELDS]
    if summary.get("entity_type_changed"):
        losses.append("entity_type")
    if summary.get("parent_brand_changed"):
        losses.append("parent_brand")
    return losses


def _rollout_base_cohort(comparison) -> str:
    graph_summary = comparison.graph_summary or {}
    source_count = int(graph_summary.get("source_count") or 0)
    if source_count >= 25:
        source_band = "25+"
    elif source_count >= 10:
        source_band = "10-24"
    else:
        source_band = "0-9"
    entity_type = comparison.legacy_entity_type or comparison.graph_entity_type or "unknown"
    return f"{entity_type}:{source_band}"


def _rollout_segment(summary: dict[str, Any]) -> str:
    if _critical_losses(summary):
        return "critical-loss"
    if int(summary.get("lost_count") or 0) > 0:
        return "lossy"
    if int(summary.get("changed_count") or 0) > 0:
        return "clean-changed"
    return "clean"


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


def _md_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_ids", nargs="*", type=int, help="Run IDs to evaluate. Defaults to latest completed runs.")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--db", type=Path, default=Path(BRAND3_DB_PATH))
    parser.add_argument("--output-dir", type=Path, default=Path("out/research_pack_rollout"))
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
