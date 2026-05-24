#!/usr/bin/env python3
"""Run the local Visual Signature annotation review viewer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.annotations.review.viewer import (  # noqa: E402
    DEFAULT_RECORDS_PATH,
    DEFAULT_SAMPLE_PATH,
    create_review_viewer_app,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local Visual Signature annotation review viewer.")
    parser.add_argument("--sample", default=str(DEFAULT_SAMPLE_PATH), help="Path to review_sample.json.")
    parser.add_argument("--records", default=str(DEFAULT_RECORDS_PATH), help="Path to review_records.json.")
    parser.add_argument("--host", default="127.0.0.1", help="Host for the local server.")
    parser.add_argument("--port", type=int, default=8765, help="Port for the local server.")
    args = parser.parse_args(argv)

    import uvicorn

    app = create_review_viewer_app(sample_path=args.sample, review_records_path=args.records)
    print(f"Visual Signature review viewer: http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
