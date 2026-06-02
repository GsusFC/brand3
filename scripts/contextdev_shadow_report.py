#!/usr/bin/env python3
"""Render a local Context.dev shadow enrichment report for a Brand Audit run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from src.config import BRAND3_DB_PATH
from src.services.magnetism_service import run_magnetism_from_audit_run


def main() -> int:
    args = _parse_args()
    result = _run_shadow_report(args.run_id, db_path=args.db_path or BRAND3_DB_PATH)
    report = _build_report(result)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(report), encoding="utf-8")

    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_md}")
    print(
        "Summary: "
        f"status={report['shadow']['status']} "
        f"updates={report['shadow']['field_update_count']} "
        f"tldr_mode={report['tldr_generation_mode']}"
    )
    return 0


def _run_shadow_report(run_id: int, *, db_path: str) -> dict[str, Any]:
    with patch("src.features.magnetism.extractor.BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT", True):
        return run_magnetism_from_audit_run(run_id, llm=None, db_path=db_path)


def _build_report(result: dict[str, Any]) -> dict[str, Any]:
    shadow = result.get("contextdev_visual_enrichment_shadow")
    if not isinstance(shadow, dict):
        shadow = {"status": "missing"}
    research_pack = result.get("research_pack")
    if not isinstance(research_pack, dict):
        research_pack = {}

    updates = shadow.get("field_updates") if isinstance(shadow.get("field_updates"), list) else []
    promotion_report = shadow.get("promotion_report") if isinstance(shadow.get("promotion_report"), dict) else {}
    delta = shadow.get("enriched_pack_delta") if isinstance(shadow.get("enriched_pack_delta"), dict) else {}
    return {
        "version": "contextdev_shadow_report_v0_1",
        "run_id": result.get("source_run_id"),
        "brand_name": result.get("brand_name"),
        "url": result.get("url"),
        "tldr_generation_mode": result.get("tldr_generation_mode"),
        "research_pack": {
            "source": result.get("research_pack_source"),
            "visual_signal_count": len(_list(research_pack.get("visual_or_conceptual_signals"))),
            "product_summary": research_pack.get("product_summary"),
            "confidence_note_count": len(_list(research_pack.get("confidence_notes"))),
        },
        "shadow": {
            "status": shadow.get("status"),
            "version": shadow.get("version"),
            "field_update_count": len(updates),
            "status_counts": promotion_report.get("status_counts") or {},
            "channel_counts": promotion_report.get("channel_counts") or {},
            "field_updates": updates,
            "enriched_pack_delta": {
                "visual_or_conceptual_signals": _list(delta.get("visual_or_conceptual_signals")),
                "product_summary": delta.get("product_summary"),
                "confidence_notes": _list(delta.get("confidence_notes")),
            },
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    shadow = report["shadow"]
    lines = [
        "# Context.dev Shadow Report",
        "",
        f"- Run: `{report.get('run_id')}`",
        f"- Brand: `{report.get('brand_name')}`",
        f"- URL: `{report.get('url')}`",
        f"- TLDR mode: `{report.get('tldr_generation_mode')}`",
        f"- Shadow status: `{shadow.get('status')}`",
        f"- Field updates: `{shadow.get('field_update_count')}`",
        "",
        "## Promotion Counts",
        "",
    ]
    status_counts = shadow.get("status_counts") or {}
    if status_counts:
        for key, value in sorted(status_counts.items()):
            lines.append(f"- `{key}`: {value}")
    else:
        lines.append("- No promotion counts available.")

    lines.extend(["", "## Field Updates", ""])
    updates = shadow.get("field_updates") or []
    if updates:
        for update in updates:
            lines.append(
                "- "
                f"`{update.get('field')}` {update.get('action')} "
                f"from `{update.get('candidate_type')}`: {_truncate(update.get('value'))}"
            )
    else:
        lines.append("- No field updates.")

    lines.extend(["", "## Research Pack Baseline", ""])
    research_pack = report["research_pack"]
    lines.extend(
        [
            f"- Source: `{research_pack.get('source')}`",
            f"- Visual signal count: `{research_pack.get('visual_signal_count')}`",
            f"- Confidence note count: `{research_pack.get('confidence_note_count')}`",
            f"- Product summary: {research_pack.get('product_summary') or 'not detected'}",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _truncate(value: Any, limit: int = 320) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}..."


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--output-json", type=Path, default=Path("out/contextdev_shadow_report/report.json"))
    parser.add_argument("--output-md", type=Path, default=Path("out/contextdev_shadow_report/report.md"))
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
