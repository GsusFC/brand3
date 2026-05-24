#!/usr/bin/env python3
"""Generate the Visual Signature governance integrity report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.governance.governance_integrity import (  # noqa: E402
    governance_integrity_report_markdown,
    write_governance_integrity_report,
    check_governance_integrity,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Visual Signature governance integrity artifacts.")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "examples" / "visual_signature" / "governance")
    args = parser.parse_args(argv)

    outputs = write_governance_integrity_report(
        output_root=args.output_root,
        capability_registry_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "capability_registry.json",
        runtime_policy_matrix_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "runtime_policy_matrix.json",
        calibration_readiness_path=PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_readiness.json",
        calibration_governance_checkpoint_path=PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_governance_checkpoint.md",
        technical_checkpoint_path=PROJECT_ROOT / "examples" / "visual_signature" / "technical_checkpoint.md",
        reliable_visual_perception_path=PROJECT_ROOT / "examples" / "visual_signature" / "reliable_visual_perception.md",
    )
    report = check_governance_integrity(
        capability_registry_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "capability_registry.json",
        runtime_policy_matrix_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "runtime_policy_matrix.json",
        calibration_readiness_path=PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_readiness.json",
        calibration_governance_checkpoint_path=PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_governance_checkpoint.md",
        technical_checkpoint_path=PROJECT_ROOT / "examples" / "visual_signature" / "technical_checkpoint.md",
        reliable_visual_perception_path=PROJECT_ROOT / "examples" / "visual_signature" / "reliable_visual_perception.md",
    )
    print(
        json.dumps(
            {
                **outputs,
                "readiness_scope": report.get("readiness_scope"),
                "readiness_status": report.get("readiness_status"),
                "status": report["status"],
                "error_count": report["error_count"],
                "warning_count": report["warning_count"],
                "checked_at": report["checked_at"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
