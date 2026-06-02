#!/usr/bin/env python3
"""Evaluate Context.dev candidate summaries against the promotion gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.research.contextdev_candidate_gate import evaluate_contextdev_summary_promotion


def main() -> int:
    args = _parse_args()
    summary = json.loads(args.input.read_text(encoding="utf-8"))
    report = evaluate_contextdev_summary_promotion(summary).to_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Summary: decisions={report['decision_count']} statuses={report['status_counts']}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("out/contextdev_candidates/summary.json"))
    parser.add_argument("--output", type=Path, default=Path("out/contextdev_candidates/promotion_report.json"))
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
