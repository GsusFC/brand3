#!/usr/bin/env python3
"""Generate the Visual Signature calibration readiness gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.calibration import write_calibration_readiness  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Visual Signature calibration readiness outputs.")
    parser.add_argument("--bundle-root", type=Path, default=PROJECT_ROOT / "examples" / "visual_signature" / "calibration")
    parser.add_argument(
        "--corpus-manifest",
        type=Path,
        default=PROJECT_ROOT / "examples" / "visual_signature" / "calibration_corpus" / "corpus_manifest.json",
    )
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    parser.add_argument(
        "--readiness-scope",
        choices=[
            "broader_corpus_use",
            "provider_pilot_use",
            "human_review_scaling",
            "production_runtime",
            "scoring_integration",
            "model_training",
        ],
        default="broader_corpus_use",
    )
    args = parser.parse_args(argv)

    outputs = write_calibration_readiness(
        args.bundle_root,
        corpus_manifest_path=args.corpus_manifest,
        output_json_path=args.output_json,
        output_md_path=args.output_md,
        readiness_scope=args.readiness_scope,
    )
    readiness_payload = json.loads(Path(outputs["calibration_readiness_json"]).read_text(encoding="utf-8"))
    print(json.dumps({**outputs, "status": readiness_payload["status"], "block_reasons": readiness_payload["block_reasons"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
