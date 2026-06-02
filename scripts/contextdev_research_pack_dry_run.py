#!/usr/bin/env python3
"""Preview Research Pack enrichment from Context.dev candidate evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.research.contextdev_research_pack_dry_run import build_contextdev_research_pack_dry_run


def main() -> int:
    args = _parse_args()
    pack = json.loads(args.pack.read_text(encoding="utf-8"))
    summary = json.loads(args.candidate_summary.read_text(encoding="utf-8"))
    result = build_contextdev_research_pack_dry_run(pack, summary).to_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Summary: updates={len(result['field_updates'])} statuses={result['promotion_report']['status_counts']}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--candidate-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("out/contextdev_research_pack_dry_run/report.json"))
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
