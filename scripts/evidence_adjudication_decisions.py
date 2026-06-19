#!/usr/bin/env python3
"""Validate and emit local adjudication decisions for evidence work records.

The script consumes pending decision records produced by evidence boards and
writes completed decision artifacts. It does not mutate scanner runs, vNext
reports, or production data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    records = _load_records(args)
    if not records:
        raise SystemExit("No record JSON files found.")

    field_values = _field_values(args.field)
    output_dir = Path(args.output_dir)
    record_dir = output_dir / "records"
    record_dir.mkdir(parents=True, exist_ok=True)

    decisions = [
        build_decision_record(
            record,
            decision=args.decision,
            reviewer=args.reviewer,
            rationale=args.rationale,
            field_values=field_values,
        )
        for record in records
    ]
    payload = build_decision_manifest(decisions)
    for decision in decisions:
        (record_dir / f"{decision['record_id']}.json").write_text(
            json.dumps(decision, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    (output_dir / "adjudication_decisions.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "adjudication_decisions.md").write_text(render_decision_markdown(payload), encoding="utf-8")
    (output_dir / "recompute_run_ids.txt").write_text(
        "\n".join(str(item) for item in payload["summary"]["recompute_run_ids"]) + "\n",
        encoding="utf-8",
    )
    print(
        "adjudication_decisions records={records} decision={decision} recompute={recompute}".format(
            records=len(decisions),
            decision=args.decision,
            recompute=len(payload["summary"]["recompute_run_ids"]),
        )
    )
    return 0


def build_decision_record(
    record: dict[str, Any],
    *,
    decision: str,
    reviewer: str,
    rationale: str,
    field_values: dict[str, str] | None = None,
) -> dict[str, Any]:
    field_values = dict(field_values or {})
    allowed = [str(item) for item in record.get("allowed_decisions") or []]
    if decision not in allowed:
        raise ValueError(f"decision {decision!r} is not allowed for {record.get('record_id')!r}: {allowed}")
    completed = {
        "record_id": record.get("record_id") or "",
        "status": "completed",
        "decision": decision,
        "reviewer": reviewer,
        "rationale": rationale,
        "requires_recompute": bool(record.get("requires_recompute")),
        "run_id": _run_id(record),
        "work_order_id": record.get("work_order_id") or "",
        "source_record": record,
    }
    for field in record.get("required_fields") or []:
        field = str(field)
        if field in {"decision", "reviewer", "rationale"}:
            continue
        completed[field] = _default_field_value(field, record, field_values)
    missing = [field for field in record.get("required_fields") or [] if not str(completed.get(str(field)) or "").strip()]
    if missing:
        raise ValueError(f"missing required fields for {record.get('record_id')!r}: {missing}")
    return completed


def build_decision_manifest(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    recompute_run_ids = sorted(
        {int(item["run_id"]) for item in decisions if item.get("requires_recompute") and item.get("run_id") is not None}
    )
    decision_counts: dict[str, int] = {}
    for item in decisions:
        decision = str(item.get("decision") or "")
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
    return {
        "version": "evidence_adjudication_decisions_v0_1",
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "summary": {
            "record_count": len(decisions),
            "decision_counts": dict(sorted(decision_counts.items())),
            "recompute_run_ids": recompute_run_ids,
        },
        "records": decisions,
    }


def render_decision_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Evidence Adjudication Decisions",
        "",
        f"- Runtime effect: `{str(bool(payload.get('runtime_effect'))).lower()}`",
        f"- Persistence effect: `{str(bool(payload.get('persistence_effect'))).lower()}`",
        "",
        "## Summary",
        "",
        f"- `record_count`: `{summary.get('record_count', 0)}`",
        f"- `decision_counts`: `{summary.get('decision_counts', {})}`",
        f"- `recompute_run_ids`: `{summary.get('recompute_run_ids', [])}`",
        "",
        "## Records",
        "",
        "| Run | Record | Decision | Recompute |",
        "| --- | --- | --- | --- |",
    ]
    for record in payload.get("records") or []:
        lines.append(
            "| {run_id} | {record_id} | {decision} | {recompute} |".format(
                run_id=record.get("run_id") or "",
                record_id=_md_cell(record.get("record_id") or ""),
                decision=_md_cell(record.get("decision") or ""),
                recompute=str(bool(record.get("requires_recompute"))).lower(),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-dir", type=Path, help="Directory containing pending record JSON files.")
    parser.add_argument(
        "--record-json",
        action="append",
        type=Path,
        default=[],
        help="Specific pending record JSON file. May be passed multiple times.",
    )
    parser.add_argument("--decision", required=True, help="Decision value to apply to all provided records.")
    parser.add_argument("--reviewer", required=True, help="Reviewer identifier.")
    parser.add_argument("--rationale", required=True, help="Decision rationale.")
    parser.add_argument(
        "--field",
        action="append",
        default=[],
        help="Additional field in KEY=VALUE form. May be passed multiple times.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("out/evidence_vnext/adjudication_decisions"),
        help="Directory for completed decision artifacts.",
    )
    return parser.parse_args(argv)


def _load_records(args: argparse.Namespace) -> list[dict[str, Any]]:
    paths = list(args.record_json or [])
    if args.records_dir:
        paths.extend(sorted(Path(args.records_dir).glob("*.json")))
    records: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for path in paths:
        path = Path(path)
        if path in seen:
            continue
        seen.add(path)
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def _field_values(values: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in values:
        key, sep, value = str(item).partition("=")
        if not sep or not key.strip():
            raise ValueError(f"invalid --field value {item!r}; expected KEY=VALUE")
        fields[key.strip()] = value.strip()
    return fields


def _default_field_value(field: str, record: dict[str, Any], field_values: dict[str, str]) -> str:
    if field in field_values:
        return field_values[field]
    if field == "profile_url":
        return ", ".join(_unique(str(item) for item in record.get("review_urls") or [] if str(item).strip()))
    if field == "affected_material_fields":
        return ", ".join(_unique(str(item) for item in record.get("affected_material_fields") or [] if str(item).strip()))
    source_record = record.get("record") if isinstance(record.get("record"), dict) else {}
    return str(source_record.get(field) or record.get(field) or "")


def _run_id(record: dict[str, Any]) -> Any:
    card = record.get("card") if isinstance(record.get("card"), dict) else {}
    if card.get("run_id") is not None:
        return card.get("run_id")
    source = record.get("record") if isinstance(record.get("record"), dict) else {}
    return source.get("run_id")


def _unique(values: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _md_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
