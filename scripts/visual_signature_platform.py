#!/usr/bin/env python3
"""Generate the local Brand3 platform dashboard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.platform import (  # noqa: E402
    build_platform_bundle,
    validate_platform_bundle,
    write_platform_bundle,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the local Brand3 platform dashboard.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "examples" / "visual_signature" / "platform",
    )
    parser.add_argument(
        "--visual-signature-root",
        type=Path,
        default=PROJECT_ROOT / "examples" / "visual_signature",
    )
    parser.add_argument(
        "--scoring-output-root",
        type=Path,
        default=PROJECT_ROOT / "output",
    )
    args = parser.parse_args(argv)

    outputs = write_platform_bundle(
        output_root=args.output_root,
        visual_signature_root=args.visual_signature_root,
        scoring_output_root=args.scoring_output_root,
    )
    payload = build_platform_bundle(
        output_root=args.output_root,
        visual_signature_root=args.visual_signature_root,
        scoring_output_root=args.scoring_output_root,
    )
    validation_errors = validate_platform_bundle(
        platform_root=args.output_root,
        visual_signature_root=args.visual_signature_root,
        scoring_output_root=args.scoring_output_root,
    )
    print(
        json.dumps(
            {
                **outputs,
                "schema_version": payload["schema_version"],
                "record_type": payload["record_type"],
                "generated_at": payload["generated_at"],
                "platform_status": payload["platform_status"],
                "section_count": len(payload["sections"]),
                "artifact_count": len(payload["artifacts"]),
                "validation_errors": validation_errors,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
