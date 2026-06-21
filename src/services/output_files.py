"""Output file helpers for Brand3 service commands."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.services.brand_profiles import _slugify


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _save_result(result: dict) -> Path:
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{_slugify(result['brand'])}-{timestamp}.json"
    output_path = output_dir / filename
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return output_path


def _save_benchmark_result(result: dict) -> Path:
    output_dir = PROJECT_ROOT / "output" / "benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    spec_name = _slugify(result.get("benchmark_name", "benchmark"))
    output_path = output_dir / f"{spec_name}-{timestamp}.json"
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return output_path


def _save_benchmark_comparison_result(result: dict) -> Path:
    output_dir = PROJECT_ROOT / "output" / "benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    before_name = _slugify(result.get("before_benchmark", "before"))
    after_name = _slugify(result.get("after_benchmark", "after"))
    output_path = output_dir / f"{after_name}-vs-{before_name}-{timestamp}.json"
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return output_path
