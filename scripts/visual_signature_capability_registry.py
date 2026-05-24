#!/usr/bin/env python3
"""Generate the Visual Signature capability registry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.governance import write_capability_registry  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Visual Signature capability registry.")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "examples" / "visual_signature" / "governance")
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    args = parser.parse_args(argv)

    outputs = write_capability_registry(
        output_root=args.output_root,
        output_json_path=args.output_json,
        output_md_path=args.output_md,
    )
    payload = json.loads(Path(outputs["capability_registry_json"]).read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                **outputs,
                "registry_version": payload["registry_version"],
                "capability_count": payload["capability_count"],
                "governance_scope": payload["governance_scope"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
