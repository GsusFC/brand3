#!/usr/bin/env python3
"""Build an operator repair board from material-diff shadow outputs.

Inputs are ``material_diff_shadow_*.json`` files emitted by
``scripts/evidence_material_diff_shadow.py``. The board is local-only: it
creates review records and helper manifests, but it does not mutate Brand3 data.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    input_files = _input_files(args)
    if not input_files:
        raise SystemExit("No material_diff_shadow JSON files found.")

    output_dir = Path(args.output_dir)
    records_dir = output_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)

    packets = _load_packets(input_files)
    board = build_repair_board(packets, input_files=[str(path) for path in input_files])

    for item in board["records"]:
        record_path = records_dir / f"{item['record_id']}.json"
        record_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")

    (output_dir / "repair_board.json").write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "repair_board.md").write_text(render_repair_board_markdown(board), encoding="utf-8")
    (output_dir / "recompute_run_ids.txt").write_text(
        "\n".join(str(item) for item in board["summary"]["recompute_run_ids"]) + "\n",
        encoding="utf-8",
    )
    (output_dir / "source_backfill_queries.txt").write_text(
        "\n".join(board["summary"]["source_backfill_queries"]) + "\n",
        encoding="utf-8",
    )
    print(
        "repair_board packets={packets} records={records} recompute={recompute} backfill_queries={queries}".format(
            packets=board["summary"]["packet_count"],
            records=len(board["records"]),
            recompute=len(board["summary"]["recompute_run_ids"]),
            queries=len(board["summary"]["source_backfill_queries"]),
        )
    )
    return 0


def build_repair_board(packets: list[dict[str, Any]], *, input_files: list[str] | None = None) -> dict[str, Any]:
    cards = [_card(packet) for packet in packets]
    records = [_record(card) for card in cards]
    return {
        "version": "evidence_repair_board_v0_1",
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "input_files": list(input_files or []),
        "cards": cards,
        "records": records,
        "summary": _summary(cards),
    }


def render_repair_board_markdown(board: dict[str, Any]) -> str:
    summary = board.get("summary") or {}
    lines = [
        "# Evidence Repair Board",
        "",
        f"- Runtime effect: `{str(bool(board.get('runtime_effect'))).lower()}`",
        f"- Persistence effect: `{str(bool(board.get('persistence_effect'))).lower()}`",
        "",
        "## Summary",
        "",
        f"- `packet_count`: `{summary.get('packet_count', 0)}`",
        f"- `recompute_run_ids`: `{summary.get('recompute_run_ids', [])}`",
        f"- `action_counts`: `{summary.get('action_counts', {})}`",
        f"- `decision_counts`: `{summary.get('decision_counts', {})}`",
        f"- `lane_counts`: `{summary.get('lane_counts', {})}`",
        "",
        "## Cards",
        "",
        "| Run | Brand | Action | Decision | Recompute | Record |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for card in board.get("cards") or []:
        lines.append(
            "| {run_id} | {brand} | {action} | {decision} | {recompute} | {record_id} |".format(
                run_id=card.get("run_id") or "",
                brand=_md_cell(card.get("brand_name") or ""),
                action=_md_cell(card.get("action") or ""),
                decision=_md_cell(card.get("recommended_decision") or ""),
                recompute=str(bool(card.get("requires_recompute"))).lower(),
                record_id=_md_cell(card.get("record_id") or ""),
            )
        )
    if summary.get("source_backfill_queries"):
        lines.extend(["", "## Source Backfill Queries", ""])
        for query in summary.get("source_backfill_queries") or []:
            lines.append(f"- `{query}`")
    lines.append("")
    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shadow-dir", type=Path, help="Directory containing material_diff_shadow_*.json files.")
    parser.add_argument(
        "--input-json",
        action="append",
        type=Path,
        default=[],
        help="Specific material_diff_shadow JSON file. May be passed multiple times.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("out/evidence_vnext/repair_board"),
        help="Directory for repair board artifacts.",
    )
    return parser.parse_args(argv)


def _input_files(args: argparse.Namespace) -> list[Path]:
    paths = list(args.input_json or [])
    if args.shadow_dir:
        paths.extend(sorted(Path(args.shadow_dir).glob("material_diff_shadow_*.json")))
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        path = Path(path)
        if path.name.endswith("summary.json"):
            continue
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def _load_packets(input_files: list[Path]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for path in input_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for packet in payload.get("decision_packets") or []:
            if isinstance(packet, dict):
                packets.append(packet)
    return packets


def _card(packet: dict[str, Any]) -> dict[str, Any]:
    record = packet.get("record") if isinstance(packet.get("record"), dict) else {}
    run_id = packet.get("run_id")
    action = str(packet.get("action") or "repair")
    record_id = f"decision_{run_id}_{action}".replace(":", "_").replace("/", "_")
    source_hints = record.get("search_hints") if isinstance(record.get("search_hints"), list) else []
    return {
        "record_id": record_id,
        "packet_id": packet.get("packet_id") or "",
        "work_order_id": packet.get("work_order_id") or "",
        "run_id": run_id,
        "brand_name": packet.get("brand_name") or "",
        "action": action,
        "recommended_decision": packet.get("recommended_decision") or "",
        "allowed_decisions": list(packet.get("allowed_decisions") or []),
        "required_fields": list(packet.get("required_fields") or []),
        "instructions": list(packet.get("instructions") or []),
        "requires_recompute": bool(packet.get("requires_recompute")),
        "source_backfill_queries": [str(item) for item in source_hints if str(item).strip()],
        "record": dict(record),
    }


def _record(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": card.get("record_id") or "",
        "status": "pending_decision",
        "recommended_decision": card.get("recommended_decision") or "",
        "allowed_decisions": list(card.get("allowed_decisions") or []),
        "required_fields": list(card.get("required_fields") or []),
        "requires_recompute": bool(card.get("requires_recompute")),
        "instructions": list(card.get("instructions") or []),
        "record": dict(card.get("record") or {}),
    }


def _summary(cards: list[dict[str, Any]]) -> dict[str, Any]:
    action_counts = Counter(str(card.get("action") or "") for card in cards)
    decision_counts = Counter(str(card.get("recommended_decision") or "") for card in cards)
    lane_counts = Counter(_lane_for_action(str(card.get("action") or "")) for card in cards)
    recompute_run_ids = sorted(
        {
            int(card["run_id"])
            for card in cards
            if card.get("requires_recompute") and card.get("run_id") is not None
        }
    )
    source_backfill_queries: list[str] = []
    for card in cards:
        source_backfill_queries.extend(str(item) for item in card.get("source_backfill_queries") or [] if str(item))
    return {
        "packet_count": len(cards),
        "action_counts": _count_dict(action_counts),
        "decision_counts": _count_dict(decision_counts),
        "lane_counts": _count_dict(lane_counts),
        "recompute_run_ids": recompute_run_ids,
        "source_backfill_queries": source_backfill_queries,
    }


def _lane_for_action(action: str) -> str:
    if action == "backfill_source_url_or_remove_material":
        return "provenance_repair"
    if action == "quarantine_weak_source_from_material":
        return "source_trust_repair"
    if action == "prepare_trust_review_packet":
        return "human_review_packet"
    return "manual_review"


def _count_dict(counter: Counter[str]) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0]))}


def _md_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
