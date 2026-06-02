#!/usr/bin/env python3
"""Run BrandResearchPack quality checks against local Brand3 runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.config import BRAND3_DB_PATH
from src.reports.brand_research_pack import build_brand_research_pack_from_snapshot
from src.research.evidence_graph import build_evidence_graph_from_snapshot
from src.research.research_pack_builder import build_brand_research_pack_from_graph
from src.research.research_pack_quality import evaluate_research_pack_quality, evaluate_research_pack_quality_gate
from src.storage.sqlite_store import SQLiteStore


def main() -> int:
    args = _parse_args()
    store = SQLiteStore(str(args.db))
    try:
        run_ids = args.run_ids or _latest_run_ids(store, args.limit)
        reports = [
            build_run_quality_report(
                store,
                run_id,
                builder=args.builder,
                min_total=args.min_total,
                min_dimension=args.min_dimension,
            )
            for run_id in run_ids
        ]
    finally:
        store.close()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for report in reports:
        run_id = report.get("run_id") or "unknown"
        (args.output_dir / f"run-{run_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = summarize_quality_reports(
        reports,
        builder=args.builder,
        db_path=str(args.db),
        min_total=args.min_total,
        min_dimension=args.min_dimension,
    )
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "summary.md").write_text(render_quality_summary_markdown(summary), encoding="utf-8")
    print(f"Wrote {args.output_dir}")
    print(f"Summary: runs={summary['run_count']} passed={summary['passed_count']} statuses={summary['quality_status_counts']}")
    return 0


def build_run_quality_report(
    store: SQLiteStore,
    run_id: int,
    *,
    builder: str,
    min_total: float,
    min_dimension: float,
) -> dict[str, Any]:
    snapshot = store.get_run_snapshot(run_id)
    if snapshot is None:
        return {"run_id": run_id, "status": "not_found"}

    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    try:
        pack = _build_pack(snapshot, builder=builder)
        quality = evaluate_research_pack_quality(pack)
        gate = evaluate_research_pack_quality_gate(quality, min_total=min_total, min_dimension=min_dimension)
    except Exception as exc:  # pragma: no cover - defensive for ad hoc local runs.
        return {
            "run_id": run_id,
            "status": "error",
            "brand_name": str(run.get("brand_name") or ""),
            "url": str(run.get("url") or ""),
            "error": str(exc),
        }

    quality_payload = quality.to_dict()
    return {
        "run_id": run_id,
        "status": "ok",
        "builder": builder,
        "brand_name": str(run.get("brand_name") or ""),
        "url": str(run.get("url") or ""),
        "quality_status": quality_payload["status"],
        "total_score": quality_payload["total_score"],
        "gate": gate,
        "dimensions": quality_payload["dimensions"],
        "warnings": quality_payload["warnings"],
        "pack_summary": quality_payload["pack_summary"],
    }


def summarize_quality_reports(
    reports: list[dict[str, Any]],
    *,
    builder: str,
    db_path: str,
    min_total: float,
    min_dimension: float,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    dimension_scores: dict[str, list[float]] = {}
    dimension_failures: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    for report in reports:
        if report.get("status") != "ok":
            rows.append({"run_id": report.get("run_id"), "status": report.get("status")})
            continue
        quality_status = str(report.get("quality_status") or "unknown")
        status_counts[quality_status] = status_counts.get(quality_status, 0) + 1
        weak_dimensions = []
        for name, dimension in (report.get("dimensions") or {}).items():
            score = float((dimension or {}).get("score") or 0.0)
            dimension_scores.setdefault(name, []).append(score)
            if str((dimension or {}).get("status") or "") != "pass":
                dimension_failures[name] = dimension_failures.get(name, 0) + 1
                weak_dimensions.append(name)
        rows.append(
            {
                "run_id": report.get("run_id"),
                "status": report.get("status"),
                "brand_name": report.get("brand_name"),
                "url": report.get("url"),
                "quality_status": report.get("quality_status"),
                "total_score": report.get("total_score"),
                "gate_passed": bool((report.get("gate") or {}).get("passed")),
                "weak_dimensions": weak_dimensions,
                "warnings": report.get("warnings") or [],
            }
        )

    average_dimension_scores = {
        name: round(sum(values) / len(values), 2)
        for name, values in sorted(dimension_scores.items())
        if values
    }
    return {
        "version": "brand_research_pack_quality_batch_v0_1",
        "builder": builder,
        "db_path": db_path,
        "min_total": min_total,
        "min_dimension": min_dimension,
        "run_count": len(reports),
        "ok_count": sum(1 for report in reports if report.get("status") == "ok"),
        "passed_count": sum(1 for report in reports if report.get("status") == "ok" and (report.get("gate") or {}).get("passed")),
        "quality_status_counts": dict(sorted(status_counts.items())),
        "average_dimension_scores": average_dimension_scores,
        "dimension_failure_counts": dict(sorted(dimension_failures.items(), key=lambda item: (-item[1], item[0]))),
        "runs": rows,
    }


def render_quality_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# BrandResearchPack Quality Batch",
        "",
        f"- Builder: `{summary['builder']}`",
        f"- Runs: `{summary['run_count']}`",
        f"- OK: `{summary['ok_count']}`",
        f"- Gate passed: `{summary['passed_count']}`",
        f"- Statuses: `{summary['quality_status_counts']}`",
        "",
        "## Dimension Averages",
        "",
        "| Dimension | Average score | Fail/warn count |",
        "| --- | ---: | ---: |",
    ]
    failures = summary.get("dimension_failure_counts") or {}
    for name, score in (summary.get("average_dimension_scores") or {}).items():
        lines.append(f"| {name} | {float(score):.1f} | {failures.get(name, 0)} |")

    lines.extend(
        [
            "",
            "## Runs",
            "",
            "| Run | Brand | Status | Score | Gate | Weak dimensions | Top warnings |",
            "| ---: | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for row in summary.get("runs") or []:
        warnings = ", ".join(str(item) for item in (row.get("warnings") or [])[:3]) or "-"
        weak = ", ".join(str(item) for item in row.get("weak_dimensions") or []) or "-"
        score = row.get("total_score")
        score_text = f"{float(score):.1f}" if score is not None else "-"
        lines.append(
            "| {run_id} | {brand} | {status} | {score} | {gate} | {weak} | {warnings} |".format(
                run_id=row.get("run_id"),
                brand=_md_cell(row.get("brand_name")),
                status=row.get("quality_status") or row.get("status"),
                score=score_text,
                gate="pass" if row.get("gate_passed") else "fail",
                weak=_md_cell(weak),
                warnings=_md_cell(warnings),
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def _build_pack(snapshot: dict[str, Any], *, builder: str):
    if builder == "legacy":
        return build_brand_research_pack_from_snapshot(snapshot)
    graph = build_evidence_graph_from_snapshot(snapshot)
    return build_brand_research_pack_from_graph(graph)


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
    parser.add_argument("--builder", choices=("graph", "legacy"), default="graph")
    parser.add_argument("--min-total", type=float, default=75.0)
    parser.add_argument("--min-dimension", type=float, default=60.0)
    parser.add_argument("--output-dir", type=Path, default=Path("out/research_pack_quality"))
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
