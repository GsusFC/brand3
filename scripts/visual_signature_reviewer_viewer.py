#!/usr/bin/env python3
"""Generate the Visual Signature reviewer workflow static viewer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.corpus_expansion import (  # noqa: E402
    build_reviewer_viewer_bundle,
    validate_reviewer_viewer_bundle,
    write_reviewer_viewer_bundle,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Visual Signature reviewer workflow viewer.")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "examples" / "visual_signature" / "corpus_expansion" / "reviewer_viewer")
    args = parser.parse_args(argv)

    outputs = write_reviewer_viewer_bundle(output_root=args.output_root)
    payload = build_reviewer_viewer_bundle(output_root=args.output_root)
    validation_errors = validate_reviewer_viewer_bundle(viewer_root=args.output_root)
    print(
        json.dumps(
            {
                **outputs,
                "schema_version": payload["schema_version"],
                "record_type": payload["record_type"],
                "generated_at": payload["generated_at"],
                "readiness_scope": payload["readiness_scope"],
                "pilot_run_id": payload["pilot_run_id"],
                "packet_count": payload["packet_count"],
                "validation_errors": validation_errors,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
