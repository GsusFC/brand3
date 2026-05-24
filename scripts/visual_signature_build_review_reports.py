#!/usr/bin/env python3
"""Build offline human-review reports for Visual Signature annotations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.annotations.review import load_review_records  # noqa: E402
from src.visual_signature.annotations.review.reports import build_review_reports, write_review_reports  # noqa: E402


DEFAULT_INPUT = (
    PROJECT_ROOT
    / "examples"
    / "visual_signature"
    / "calibration_corpus"
    / "annotations"
    / "multimodal"
    / "review"
    / "review_records.json"
)
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "examples"
    / "visual_signature"
    / "calibration_corpus"
    / "annotations"
    / "multimodal"
    / "review"
    / "reports"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Visual Signature annotation human-review reports.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Review records JSON file.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for review reports.")
    args = parser.parse_args(argv)
    records = load_review_records(args.input)
    reports = build_review_reports(records)
    written = write_review_reports(args.output_dir, reports)
    print(json.dumps({"records": len(records), "output_dir": args.output_dir, **written}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
