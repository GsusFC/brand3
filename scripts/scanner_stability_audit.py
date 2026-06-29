#!/usr/bin/env python3
"""Audit repeated scanner results in a Brand3 SQLite database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import BRAND3_DB_PATH
from src.services.scanner_stability_audit import (
    StabilityAuditOptions,
    analyze_scanner_stability,
    render_stability_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=BRAND3_DB_PATH)
    parser.add_argument("--min-repeats", type=int, default=2)
    parser.add_argument("--days", type=int)
    parser.add_argument("--version", default="")
    parser.add_argument("--limit-groups", type=int, default=50)
    parser.add_argument("--group-by-day", action="store_true")
    parser.add_argument("--format", choices=("json", "md"), default="md")
    parser.add_argument("--output", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = analyze_scanner_stability(
        args.db,
        options=StabilityAuditOptions(
            min_repeats=args.min_repeats,
            days=args.days,
            version=args.version or None,
            limit_groups=args.limit_groups,
            group_by_day=args.group_by_day,
        ),
    )
    rendered = (
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_stability_markdown(report)
    )
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
