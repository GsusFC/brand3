from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.visual_signature.phase_two import PHASE_TWO_ROOT, validate_phase_two_output_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Phase Two outputs.")
    parser.add_argument("--root", type=Path, default=PHASE_TWO_ROOT)
    args = parser.parse_args(argv)

    errors = validate_phase_two_output_root(args.root)
    if errors:
        for error in errors:
            print(error)
        return 1

    print(json.dumps({"root": str(args.root), "validated": True}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
