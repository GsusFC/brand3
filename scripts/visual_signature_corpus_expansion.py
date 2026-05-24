#!/usr/bin/env python3
"""Generate the Visual Signature corpus expansion pilot scaffold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.corpus_expansion import (  # noqa: E402
    assess_corpus_expansion_bundle,
    write_corpus_expansion_bundle,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Visual Signature corpus expansion artifacts.")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "examples" / "visual_signature" / "corpus_expansion")
    parser.add_argument("--target-capture-count", type=int, default=20)
    parser.add_argument("--pilot-run-id", type=str, default="visual-signature-corpus-expansion-pilot-1")
    args = parser.parse_args(argv)

    outputs = write_corpus_expansion_bundle(
        output_root=args.output_root,
        pilot_run_id=args.pilot_run_id,
        target_capture_count=args.target_capture_count,
    )
    assessment = assess_corpus_expansion_bundle(args.output_root)
    manifest_payload = json.loads(Path(outputs["corpus_expansion_manifest_json"]).read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                **outputs,
                "pilot_run_id": manifest_payload["pilot_run_id"],
                "readiness_scope": manifest_payload["readiness_scope"],
                "readiness_status": manifest_payload["readiness_status"],
                "current_capture_count": manifest_payload["current_capture_count"],
                "reviewed_capture_count": manifest_payload["reviewed_capture_count"],
                "block_reasons": assessment.block_reasons,
                "warning_reasons": assessment.warning_reasons,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
