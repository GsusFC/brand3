#!/usr/bin/env python3
"""Build evidence-only Visual Signature category baselines from saved payloads."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.baselines import (  # noqa: E402
    build_category_baselines,
    compare_records_to_baselines,
    metric_row_from_payload,
)
from src.visual_signature.baselines.summaries import (  # noqa: E402
    brand_comparisons_markdown,
    category_baselines_markdown,
)
from src.visual_signature.baselines.metric_diagnostics import (  # noqa: E402
    build_metric_audit,
    metric_audit_markdown,
)


DEFAULT_INPUT_DIR = PROJECT_ROOT / "examples" / "visual_signature" / "calibration_outputs"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "examples" / "visual_signature" / "category_baselines"


def load_payloads(input_dir: str | Path) -> list[tuple[Path, dict[str, Any]]]:
    root = Path(input_dir)
    payloads: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*.json")):
        if path.name in {"manifest.json", "category_baselines.json", "brand_comparisons.json"}:
            continue
        if path.name.endswith(".error.json"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        if not _looks_like_visual_signature_payload(payload):
            continue
        payloads.append((path, payload))
    return payloads


def build_baseline_artifacts(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    payloads = load_payloads(input_dir)
    rows = [
        metric_row_from_payload(payload, source_path=str(path))
        for path, payload in payloads
    ]
    baselines = build_category_baselines(rows)
    comparisons = compare_records_to_baselines(rows, baselines)
    metric_audit = build_metric_audit(rows)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    baseline_payload = {
        "version": "visual-signature-category-baseline-mvp-1",
        "input_dir": str(input_dir),
        "payload_count": len(payloads),
        "categories": {
            category: baseline.to_dict()
            for category, baseline in sorted(baselines.items())
        },
    }
    comparison_payload = {
        "version": "visual-signature-category-comparison-mvp-1",
        "input_dir": str(input_dir),
        "comparison_count": len(comparisons),
        "comparisons": [comparison.to_dict() for comparison in comparisons],
    }
    _write_json(output_path / "category_baselines.json", baseline_payload)
    _write_json(output_path / "brand_comparisons.json", comparison_payload)
    _write_json(output_path / "metric_audit.json", metric_audit)
    (output_path / "category_baselines.md").write_text(
        category_baselines_markdown(baselines) + "\n",
        encoding="utf-8",
    )
    (output_path / "brand_comparisons.md").write_text(
        brand_comparisons_markdown(comparisons) + "\n",
        encoding="utf-8",
    )
    (output_path / "metric_audit.md").write_text(
        metric_audit_markdown(metric_audit) + "\n",
        encoding="utf-8",
    )
    return {
        "input_dir": str(input_dir),
        "output_dir": str(output_path),
        "payload_count": len(payloads),
        "category_count": len(baselines),
        "comparison_count": len(comparisons),
        "category_baselines_json": str(output_path / "category_baselines.json"),
        "category_baselines_md": str(output_path / "category_baselines.md"),
        "brand_comparisons_json": str(output_path / "brand_comparisons.json"),
        "brand_comparisons_md": str(output_path / "brand_comparisons.md"),
        "metric_audit_json": str(output_path / "metric_audit.json"),
        "metric_audit_md": str(output_path / "metric_audit.md"),
    }


def _looks_like_visual_signature_payload(payload: dict[str, Any]) -> bool:
    return bool(payload.get("version") == "visual-signature-mvp-1" or payload.get("visual_signature") or payload.get("vision"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Visual Signature category baselines.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Folder containing saved Visual Signature payload JSON files.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Folder for baseline JSON and Markdown artifacts.")
    args = parser.parse_args(argv)

    result = build_baseline_artifacts(input_dir=args.input_dir, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
