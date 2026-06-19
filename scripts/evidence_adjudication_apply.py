#!/usr/bin/env python3
"""Apply completed adjudication decisions to local vNext artifacts.

This is a dry-run applicator. It closes matching work orders and produces a
recompute plan, but it does not mutate scanner runs, persisted evidence, or
production data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    vnext_files = _vnext_files(args)
    if not vnext_files:
        raise SystemExit("No vnext JSON files found.")
    decisions = _load_decisions(Path(args.decisions_json))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for path in vnext_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        applied = apply_adjudication_decisions(payload, decisions, source_file=str(path))
        rows.append(applied)
        run_id = applied.get("run_id") or path.stem.removeprefix("vnext_")
        (output_dir / f"adjudication_apply_{run_id}.json").write_text(
            json.dumps(applied, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            "file={file} run={run} closed={closed} open={open} recompute={recompute}".format(
                file=path.name,
                run=run_id,
                closed=applied["summary"]["closed_work_order_count"],
                open=applied["summary"]["open_work_order_count"],
                recompute=str(applied["summary"]["requires_recompute"]).lower(),
            )
        )

    manifest = build_apply_manifest(rows)
    (output_dir / "adjudication_apply_summary.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "adjudication_apply_summary.md").write_text(render_apply_markdown(manifest), encoding="utf-8")
    (output_dir / "recompute_run_ids.txt").write_text(
        "\n".join(str(item) for item in manifest["summary"]["recompute_run_ids"]) + "\n",
        encoding="utf-8",
    )
    return 0


def apply_adjudication_decisions(
    vnext_payload: dict[str, Any],
    decisions_manifest: dict[str, Any],
    *,
    source_file: str = "",
) -> dict[str, Any]:
    report = vnext_payload.get("report") if isinstance(vnext_payload.get("report"), dict) else {}
    work_orders = [item for item in report.get("work_orders") or [] if isinstance(item, dict)]
    decisions = [item for item in decisions_manifest.get("records") or [] if isinstance(item, dict)]
    decisions_by_work_order = {str(item.get("work_order_id") or ""): item for item in decisions}
    decisions_by_record = {str(item.get("record_id") or ""): item for item in decisions}

    closed = []
    open_orders = []
    for order in work_orders:
        work_order_id = str(order.get("work_order_id") or "")
        record_id = _record_id_for_order(order)
        decision = decisions_by_work_order.get(work_order_id) or decisions_by_record.get(record_id)
        if decision:
            closed.append(_closed_order(order, decision))
        else:
            open_orders.append(order)

    run_id = _run_id(vnext_payload, work_orders)
    requires_recompute = any(bool(item.get("requires_recompute")) for item in closed)
    return {
        "version": "evidence_adjudication_apply_v0_1",
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "source_file": source_file,
        "run_id": run_id,
        "brand_name": _brand_name(vnext_payload, work_orders),
        "summary": {
            "work_order_count": len(work_orders),
            "closed_work_order_count": len(closed),
            "open_work_order_count": len(open_orders),
            "requires_recompute": requires_recompute,
            "recompute_run_ids": [run_id] if requires_recompute and run_id is not None else [],
            "decision_counts": _decision_counts(closed),
        },
        "closed_work_orders": closed,
        "open_work_orders": open_orders,
        "post_adjudication": {
            "status": "recompute_required" if requires_recompute else ("pending_decisions" if open_orders else "closed"),
            "note": "Promotion state is not recomputed by this dry-run applicator.",
        },
    }


def build_apply_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    recompute_run_ids = sorted(
        {
            int(run_id)
            for row in rows
            for run_id in row.get("summary", {}).get("recompute_run_ids", [])
            if run_id is not None
        }
    )
    decision_counts: dict[str, int] = {}
    for row in rows:
        for decision, count in row.get("summary", {}).get("decision_counts", {}).items():
            decision_counts[str(decision)] = decision_counts.get(str(decision), 0) + int(count)
    return {
        "version": "evidence_adjudication_apply_batch_v0_1",
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "rows": rows,
        "summary": {
            "file_count": len(rows),
            "closed_work_order_count": sum(int(row.get("summary", {}).get("closed_work_order_count") or 0) for row in rows),
            "open_work_order_count": sum(int(row.get("summary", {}).get("open_work_order_count") or 0) for row in rows),
            "recompute_run_ids": recompute_run_ids,
            "decision_counts": dict(sorted(decision_counts.items())),
        },
    }


def render_apply_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest.get("summary") or {}
    lines = [
        "# Evidence Adjudication Apply",
        "",
        f"- Runtime effect: `{str(bool(manifest.get('runtime_effect'))).lower()}`",
        f"- Persistence effect: `{str(bool(manifest.get('persistence_effect'))).lower()}`",
        "",
        "## Summary",
        "",
        f"- `file_count`: `{summary.get('file_count', 0)}`",
        f"- `closed_work_order_count`: `{summary.get('closed_work_order_count', 0)}`",
        f"- `open_work_order_count`: `{summary.get('open_work_order_count', 0)}`",
        f"- `recompute_run_ids`: `{summary.get('recompute_run_ids', [])}`",
        f"- `decision_counts`: `{summary.get('decision_counts', {})}`",
        "",
        "## Rows",
        "",
        "| Run | Brand | Closed | Open | Status |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in manifest.get("rows") or []:
        row_summary = row.get("summary") or {}
        lines.append(
            "| {run} | {brand} | {closed} | {open} | {status} |".format(
                run=row.get("run_id") or "",
                brand=_md_cell(row.get("brand_name") or ""),
                closed=row_summary.get("closed_work_order_count") or 0,
                open=row_summary.get("open_work_order_count") or 0,
                status=_md_cell((row.get("post_adjudication") or {}).get("status") or ""),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, help="Directory containing vnext_*.json files.")
    parser.add_argument(
        "--input-json",
        action="append",
        type=Path,
        default=[],
        help="Specific vnext JSON file. May be passed multiple times.",
    )
    parser.add_argument("--decisions-json", required=True, help="adjudication_decisions.json path.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("out/evidence_vnext/adjudication_apply"),
        help="Directory for apply artifacts.",
    )
    return parser.parse_args(argv)


def _vnext_files(args: argparse.Namespace) -> list[Path]:
    paths = list(args.input_json or [])
    if args.batch_dir:
        paths.extend(sorted(Path(args.batch_dir).glob("vnext_*.json")))
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        path = Path(path)
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def _load_decisions(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("decisions JSON must be an object")
    return payload


def _closed_order(order: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "work_order_id": order.get("work_order_id") or "",
        "packet_id": order.get("packet_id") or "",
        "run_id": order.get("run_id"),
        "brand_name": order.get("brand_name") or "",
        "decision": decision.get("decision") or "",
        "reviewer": decision.get("reviewer") or "",
        "rationale": decision.get("rationale") or "",
        "requires_recompute": bool(order.get("requires_recompute") or decision.get("requires_recompute")),
        "decision_record_id": decision.get("record_id") or "",
    }


def _record_id_for_order(order: dict[str, Any]) -> str:
    next_action = str(order.get("next_action") or "")
    run_id = order.get("run_id")
    if next_action == "confirm_entity_alias_before_promotion":
        return f"entity_alias_confirmation_{run_id}"
    packet_id = str(order.get("packet_id") or "")
    return f"{packet_id.removeprefix('intervention:')}_{run_id}"


def _decision_counts(closed: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in closed:
        decision = str(item.get("decision") or "")
        counts[decision] = counts.get(decision, 0) + 1
    return dict(sorted(counts.items()))


def _run_id(payload: dict[str, Any], work_orders: list[dict[str, Any]]) -> Any:
    if work_orders and work_orders[0].get("run_id") is not None:
        return work_orders[0].get("run_id")
    report = payload.get("report") if isinstance(payload.get("report"), dict) else {}
    rows = report.get("rows") if isinstance(report.get("rows"), list) else []
    if rows and isinstance(rows[0], dict):
        return rows[0].get("run_id")
    return None


def _brand_name(payload: dict[str, Any], work_orders: list[dict[str, Any]]) -> str:
    if work_orders:
        return str(work_orders[0].get("brand_name") or "")
    report = payload.get("report") if isinstance(payload.get("report"), dict) else {}
    rows = report.get("rows") if isinstance(report.get("rows"), list) else []
    if rows and isinstance(rows[0], dict):
        return str(rows[0].get("brand_name") or "")
    return ""


def _md_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
