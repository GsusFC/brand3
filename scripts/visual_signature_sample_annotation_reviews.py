#!/usr/bin/env python3
"""Create offline human-review samples for Visual Signature annotations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.annotations.review import build_review_sample, save_review_batch  # noqa: E402


DEFAULT_ANNOTATION_DIR = (
    PROJECT_ROOT
    / "examples"
    / "visual_signature"
    / "calibration_corpus"
    / "annotations"
    / "multimodal"
    / "mock_first_pass"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "examples"
    / "visual_signature"
    / "calibration_corpus"
    / "annotations"
    / "multimodal"
    / "review"
    / "review_sample.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sample Visual Signature annotations for human review.")
    parser.add_argument("--annotation-dir", default=str(DEFAULT_ANNOTATION_DIR), help="Folder containing annotated payload JSON files.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path for the review sample JSON.")
    parser.add_argument("--size", type=int, default=36, help="Maximum sample size.")
    parser.add_argument("--high-confidence", type=int, default=8, help="High-confidence sample count.")
    parser.add_argument("--low-confidence", type=int, default=8, help="Low-confidence sample count.")
    parser.add_argument("--disagreement-heavy", type=int, default=10, help="Disagreement-heavy sample count.")
    parser.add_argument("--category-diverse", type=int, default=12, help="Category-diverse sample count.")
    args = parser.parse_args(argv)
    batch = build_review_sample(
        annotation_dir=args.annotation_dir,
        output_size=args.size,
        high_confidence_count=args.high_confidence,
        low_confidence_count=args.low_confidence,
        disagreement_heavy_count=args.disagreement_heavy,
        category_diverse_count=args.category_diverse,
    )
    save_review_batch(args.output, batch)
    print(json.dumps({"output": args.output, "items": len(batch.items), "sample_strategy": batch.sample_strategy}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
