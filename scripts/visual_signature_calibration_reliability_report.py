#!/usr/bin/env python3
"""Generate the Visual Signature calibration reliability report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.calibration.calibration_reliability_report import write_calibration_reliability_report  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a Visual Signature calibration reliability report.")
    parser.add_argument("--bundle-root", type=Path, default=PROJECT_ROOT / "examples" / "visual_signature" / "calibration")
    parser.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Where to write the markdown report. Defaults to bundle_root/calibration_reliability_report.md.",
    )
    args = parser.parse_args(argv)
    report_path = write_calibration_reliability_report(args.bundle_root, args.output_path)
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
