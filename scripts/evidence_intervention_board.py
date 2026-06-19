#!/usr/bin/env python3
"""Build local operator boards from vNext intervention packets.

Inputs are ``vnext_*.json`` files emitted by the remote batch scripts. The
board is local-only: it creates review records and helper manifests, but it
does not mutate Brand3 data or promotion state.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    input_files = _input_files(args)
    if not input_files:
        raise SystemExit("No vnext JSON files found.")

    output_dir = Path(args.output_dir)
    records_dir = output_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)

    packets = _load_packets(input_files, intervention_type=args.intervention_type)
    board = build_intervention_board(packets, input_files=[str(path) for path in input_files])

    for record in board["records"]:
        record_path = records_dir / f"{record['record_id']}.json"
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    (output_dir / "intervention_board.json").write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "intervention_board.md").write_text(render_intervention_board_markdown(board), encoding="utf-8")
    (output_dir / "recompute_run_ids.txt").write_text(
        "\n".join(str(item) for item in board["summary"]["recompute_run_ids"]) + "\n",
        encoding="utf-8",
    )
    (output_dir / "review_urls.txt").write_text(
        "\n".join(board["summary"]["review_urls"]) + "\n",
        encoding="utf-8",
    )
    print(
        "intervention_board packets={packets} records={records} recompute={recompute} review_urls={urls}".format(
            packets=board["summary"]["packet_count"],
            records=len(board["records"]),
            recompute=len(board["summary"]["recompute_run_ids"]),
            urls=len(board["summary"]["review_urls"]),
        )
    )
    return 0


def build_intervention_board(packets: list[dict[str, Any]], *, input_files: list[str] | None = None) -> dict[str, Any]:
    cards = [_card(packet, run) for packet in packets for run in packet.get("runs") or [] if isinstance(run, dict)]
    records = [_record(card) for card in cards]
    return {
        "version": "evidence_intervention_board_v0_1",
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "input_files": list(input_files or []),
        "cards": cards,
        "records": records,
        "summary": _summary(packets, cards),
    }


def render_intervention_board_markdown(board: dict[str, Any]) -> str:
    summary = board.get("summary") or {}
    lines = [
        "# Evidence Intervention Board",
        "",
        f"- Runtime effect: `{str(bool(board.get('runtime_effect'))).lower()}`",
        f"- Persistence effect: `{str(bool(board.get('persistence_effect'))).lower()}`",
        "",
        "## Summary",
        "",
        f"- `packet_count`: `{summary.get('packet_count', 0)}`",
        f"- `record_count`: `{summary.get('record_count', 0)}`",
        f"- `recompute_run_ids`: `{summary.get('recompute_run_ids', [])}`",
        f"- `intervention_type_counts`: `{summary.get('intervention_type_counts', {})}`",
        f"- `decision_counts`: `{summary.get('decision_counts', {})}`",
        f"- `review_url_count`: `{len(summary.get('review_urls') or [])}`",
        "",
        "## Cards",
        "",
        "| Run | Brand | Intervention | Decision | Recompute | Record |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for card in board.get("cards") or []:
        lines.append(
            "| {run_id} | {brand} | {intervention} | {decision} | {recompute} | {record_id} |".format(
                run_id=card.get("run_id") or "",
                brand=_md_cell(card.get("brand_name") or ""),
                intervention=_md_cell(card.get("intervention_type") or ""),
                decision=_md_cell(", ".join(card.get("allowed_decisions") or [])),
                recompute=str(card.get("promotion_after_closure") == "recompute_required").lower(),
                record_id=_md_cell(card.get("record_id") or ""),
            )
        )
    if summary.get("review_urls"):
        lines.extend(["", "## Review URLs", ""])
        for url in summary.get("review_urls") or []:
            lines.append(f"- `{url}`")
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
    parser.add_argument(
        "--intervention-type",
        default="",
        help="Optional intervention type filter, for example entity_alias_confirmation.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("out/evidence_vnext/intervention_board"),
        help="Directory for intervention board artifacts.",
    )
    return parser.parse_args(argv)


def _input_files(args: argparse.Namespace) -> list[Path]:
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


def _load_packets(input_files: list[Path], *, intervention_type: str = "") -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for path in input_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        report = payload.get("report") if isinstance(payload.get("report"), dict) else {}
        for packet in report.get("intervention_packets") or []:
            if not isinstance(packet, dict):
                continue
            if intervention_type and str(packet.get("intervention_type") or "") != intervention_type:
                continue
            packet = dict(packet)
            packet["source_file"] = str(path)
            packets.append(packet)
    return packets


def _card(packet: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    run_id = run.get("run_id")
    intervention_type = str(packet.get("intervention_type") or "unknown")
    record_id = f"{intervention_type}_{run_id}".replace(":", "_").replace("/", "_")
    review_examples = list(run.get("remaining_review_examples") or [])
    material_overlaps = list(run.get("projected_material_overlaps") or [])
    changed_fields = list(run.get("changed_material_fields") or [])
    return {
        "record_id": record_id,
        "packet_id": packet.get("packet_id") or "",
        "source_file": packet.get("source_file") or "",
        "run_id": run_id,
        "brand_name": run.get("brand_name") or "",
        "intervention_type": intervention_type,
        "title": packet.get("title") or "",
        "priority": packet.get("priority") or "",
        "automation_lane": run.get("automation_lane") or packet.get("automation_lane") or "",
        "next_action": run.get("next_action") or "",
        "closure_criteria": packet.get("closure_criteria") or "",
        "checklist": list(packet.get("checklist") or []),
        "allowed_decisions": list(packet.get("allowed_decisions") or []),
        "decision_required_fields": list(packet.get("decision_required_fields") or []),
        "promotion_after_closure": packet.get("promotion_after_closure") or "",
        "remaining_review_examples": review_examples,
        "projected_material_overlaps": material_overlaps,
        "changed_material_fields": changed_fields,
        "review_urls": _review_urls(review_examples, material_overlaps),
        "affected_material_fields": _affected_material_fields(material_overlaps, changed_fields),
    }


def _record(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": card.get("record_id") or "",
        "status": "pending_decision",
        "intervention_type": card.get("intervention_type") or "",
        "recommended_action": card.get("next_action") or "",
        "allowed_decisions": list(card.get("allowed_decisions") or []),
        "required_fields": list(card.get("decision_required_fields") or []),
        "requires_recompute": card.get("promotion_after_closure") == "recompute_required",
        "review_urls": list(card.get("review_urls") or []),
        "affected_material_fields": list(card.get("affected_material_fields") or []),
        "checklist": list(card.get("checklist") or []),
        "card": dict(card),
    }


def _summary(packets: list[dict[str, Any]], cards: list[dict[str, Any]]) -> dict[str, Any]:
    intervention_type_counts = Counter(str(packet.get("intervention_type") or "") for packet in packets)
    decision_counts = Counter()
    recompute_run_ids = sorted(
        {
            int(card["run_id"])
            for card in cards
            if card.get("promotion_after_closure") == "recompute_required" and card.get("run_id") is not None
        }
    )
    review_urls: list[str] = []
    seen_urls: set[str] = set()
    for card in cards:
        decision_counts.update(card.get("allowed_decisions") or [])
        for url in card.get("review_urls") or []:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            review_urls.append(url)
    return {
        "packet_count": len(packets),
        "record_count": len(cards),
        "intervention_type_counts": _count_dict(intervention_type_counts),
        "decision_counts": _count_dict(decision_counts),
        "recompute_run_ids": recompute_run_ids,
        "review_urls": review_urls,
    }


def _review_urls(*groups: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            url = str(item.get("url") or "").strip()
            key = _url_key(url)
            if not url or key in seen:
                continue
            seen.add(key)
            urls.append(url)
    return urls


def _url_key(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/")
    return f"{host}{path}".lower()


def _affected_material_fields(*groups: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            field = str(item.get("field") or "").strip()
            if not field or field in seen:
                continue
            seen.add(field)
            fields.append(field)
    return fields


def _count_dict(counter: Counter[str]) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0]))}


def _md_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
