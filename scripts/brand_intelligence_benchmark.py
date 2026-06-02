#!/usr/bin/env python3
"""Run a small live benchmark across multiple brand acquisition probes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.brand_intelligence_live_probe import run_probe
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from brand_intelligence_live_probe import run_probe
from src.research.brand_intelligence_benchmark import (
    BrandIntelligenceBenchmarkCase,
    default_benchmark_cases,
    render_brand_intelligence_benchmark_markdown,
    summarize_brand_intelligence_benchmark,
)


def main() -> int:
    args = _parse_args()
    cases = _load_cases(args.cases_file) if args.cases_file and args.cases_file.exists() else default_benchmark_cases()
    cases = _filter_cases_by_providers(cases, args.providers)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = []
    for case in cases:
        case_output = output_dir / f"{_slugify(case.label or case.brand)}.json"
        payload = run_probe(
            brand=case.brand,
            url=case.url,
            use_exa=case.use_exa,
            use_web=case.use_web,
            owned_web_provider=case.owned_web_provider,
            exa_results=case.exa_results,
            output=case_output,
        )
        payload["benchmark_case"] = case.to_dict()
        payloads.append(payload)

    summary = summarize_brand_intelligence_benchmark(payloads, cases=cases)
    summary_path = output_dir / "benchmark.json"
    summary_md_path = output_dir / "benchmark.md"
    summary_path.write_text(json.dumps(_jsonable(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md_path.write_text(render_brand_intelligence_benchmark_markdown(summary), encoding="utf-8")

    print(f"Wrote {summary_path}")
    print(f"Wrote {summary_md_path}")
    print(
        "Summary:"
        f" cases={summary['case_count']}"
        f" ready={summary['inventory_ready_count']}"
        f" providers={len(summary['provider_metrics'])}"
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases-file",
        type=Path,
        default=Path("examples/benchmarks/brand_intelligence_acquisition/cases.json"),
        help="JSON file with benchmark cases.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("out/brand_intelligence_benchmark"))
    parser.add_argument(
        "--providers",
        default="",
        help="Optional comma-separated owned-web providers to run, e.g. firecrawl,playwright or tinyfish.",
    )
    return parser.parse_args()


def _load_cases(path: Path) -> list[BrandIntelligenceBenchmarkCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases: list[BrandIntelligenceBenchmarkCase] = []
    for item in raw:
        cases.append(
            BrandIntelligenceBenchmarkCase(
                brand=str(item.get("brand") or ""),
                url=str(item.get("url") or ""),
                label=str(item.get("label") or ""),
                use_exa=bool(item.get("use_exa", True)),
                use_web=bool(item.get("use_web", True)),
                owned_web_provider=str(item.get("owned_web_provider") or "firecrawl"),
                exa_results=int(item.get("exa_results") or 3),
            )
        )
    return cases


def _filter_cases_by_providers(
    cases: list[BrandIntelligenceBenchmarkCase],
    providers_csv: str,
) -> list[BrandIntelligenceBenchmarkCase]:
    providers = {item.strip().lower() for item in providers_csv.split(",") if item.strip()}
    if not providers:
        return cases
    return [case for case in cases if case.owned_web_provider.lower() in providers]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "brand"


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _jsonable(value.to_dict())
    return value


if __name__ == "__main__":
    raise SystemExit(main())
