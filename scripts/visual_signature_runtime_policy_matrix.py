#!/usr/bin/env python3
"""Generate the Visual Signature runtime policy matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.governance.runtime_policy_matrix import (  # noqa: E402
    build_runtime_policy_matrix,
    write_runtime_policy_matrix,
)
from src.visual_signature.governance.runtime_policy_models import validate_runtime_policy_matrix_payload  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Visual Signature runtime policy matrix artifacts.")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "examples" / "visual_signature" / "governance")
    args = parser.parse_args(argv)

    outputs = write_runtime_policy_matrix(output_root=args.output_root)
    matrix = build_runtime_policy_matrix()
    validation_errors = validate_runtime_policy_matrix_payload(matrix.model_dump(mode="json"))
    print(
        json.dumps(
            {
                **outputs,
                "matrix_version": matrix.matrix_version,
                "governance_scope": matrix.governance_scope,
                "capability_count": matrix.capability_count,
                "policy_count": matrix.policy_count,
                "validation_errors": validation_errors,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
