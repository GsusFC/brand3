#!/usr/bin/env python3
"""Validate Visual Signature calibration artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.calibration import validate_calibration_output_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Visual Signature calibration artifacts.")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "examples" / "visual_signature" / "calibration")
    args = parser.parse_args(argv)

    errors = validate_calibration_output_root(args.output_root)
    result = {
        "output_root": str(args.output_root),
        "validated": not errors,
        "error_count": len(errors),
        "errors": errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
