#!/usr/bin/env python3
"""Build a LEGACY compatibility flow candidate from local JSON files.

This script wraps a Pass 1/TLDR payload in the flow contracts via
scripts/sv9_flow_legacy_compat.py — it is a baseline harness, not the
canonical flow. It is read-only: no SV9 runtime, no LLMs, no database writes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.sv9_flow_legacy_compat import build_flow_candidate_from_current_outputs
from src.sv9_flow.reporting import build_flow_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, help="Path to a current audit snapshot JSON file.")
    parser.add_argument("--tldr", default="", help="Optional path to a current tldr_brand3/Magnetism payload JSON file.")
    parser.add_argument(
        "--visual-signature",
        default="",
        help="Optional path to a visual-signature-evidence-v1 JSON file.",
    )
    parser.add_argument("--output", default="", help="Optional path for the full candidate JSON output.")
    parser.add_argument("--report", action="store_true", help="Print compact report instead of full candidate JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate = build_flow_candidate_from_current_outputs(
        snapshot=_load_json(args.snapshot),
        tldr_payload=_load_optional_json(args.tldr),
        visual_signature_evidence=_load_optional_json(args.visual_signature),
    )
    payload = build_flow_report(candidate) if args.report else candidate.to_dict()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def _load_json(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _load_optional_json(path: str) -> dict[str, Any] | None:
    if not path:
        return None
    return _load_json(path)


if __name__ == "__main__":
    raise SystemExit(main())
