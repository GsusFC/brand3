#!/usr/bin/env python3
"""Generate the Visual Signature three-track validation plan artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.governance import (  # noqa: E402
    build_three_track_validation_plan,
    validate_three_track_validation_plan_payload,
    write_three_track_validation_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Visual Signature three-track validation plan.")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "examples" / "visual_signature" / "governance")
    args = parser.parse_args(argv)

    outputs = write_three_track_validation_plan(output_root=args.output_root)
    payload = build_three_track_validation_plan()
    validation_errors = validate_three_track_validation_plan_payload(payload)
    print(
        json.dumps(
            {
                **outputs,
                "schema_version": payload["schema_version"],
                "record_type": payload["record_type"],
                "generated_at": payload["generated_at"],
                "recommended_order": payload["recommended_order"],
                "validation_errors": validation_errors,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
