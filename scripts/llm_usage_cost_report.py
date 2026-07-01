#!/usr/bin/env python3
"""Estimate LLM cost from Brand3 llm_usage payloads."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRICING_USD_PER_1M_TOKENS = {
    # Google Gemini Developer API, Paid Standard, checked 2026-07-01.
    "gemini-3.5-flash": {"input": 1.50, "output": 9.00},
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
    "gemini-3.1-pro-preview": {"input": 2.00, "output": 12.00},
}

DEFAULT_SCENARIOS = {
    "low": {"input_tokens_per_call": 2_000, "output_tokens_per_call": 500},
    "mid": {"input_tokens_per_call": 6_000, "output_tokens_per_call": 1_000},
    "high": {"input_tokens_per_call": 12_000, "output_tokens_per_call": 2_000},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", nargs="+", help="JSON payloads containing llm_usage.")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payloads = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.json_file]
    report = build_cost_report(payloads, sources=args.json_file)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(render_markdown(report))
    return 0


def build_cost_report(payloads: list[dict[str, Any]], *, sources: list[str] | None = None) -> dict[str, Any]:
    observations = list(_iter_observations(payloads, sources=sources))
    provider_calls = [obs for obs in observations if obs["event"] == "provider_call"]
    billable_estimated = [obs for obs in provider_calls if obs.get("status") == "ok"]
    by_model: dict[str, Counter[str]] = defaultdict(Counter)
    for obs in provider_calls:
        by_model[str(obs.get("model") or "unknown")][str(obs.get("status") or "unknown")] += 1
    return {
        "schema_version": "brand3-llm-usage-cost-report-v1",
        "pricing_basis": {
            "provider": "Google Gemini Developer API",
            "tier": "Paid Standard",
            "currency": "USD",
            "prices_per_1m_tokens": PRICING_USD_PER_1M_TOKENS,
            "token_usage_source": "usage_metadata when available; scenario estimate otherwise",
        },
        "summary": {
            "payloads": len(payloads),
            "provider_call_attempts": len(provider_calls),
            "provider_call_ok": len(billable_estimated),
            "provider_call_non_ok": len(provider_calls) - len(billable_estimated),
            "usage_metadata_available": any(bool(obs.get("usage_metadata")) for obs in observations),
        },
        "provider_calls_by_model": {
            model: dict(sorted(counts.items())) for model, counts in sorted(by_model.items())
        },
        "scenario_estimates": _scenario_estimates(billable_estimated),
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# LLM Usage Cost Report",
        "",
        f"- schema: `{report.get('schema_version')}`",
        f"- provider call attempts: `{summary.get('provider_call_attempts')}`",
        f"- provider call ok: `{summary.get('provider_call_ok')}`",
        f"- provider call non-ok: `{summary.get('provider_call_non_ok')}`",
        f"- usage metadata available: `{str(summary.get('usage_metadata_available')).lower()}`",
        "",
        "| scenario | assumed input/call | assumed output/call | estimated USD |",
        "|---|---:|---:|---:|",
    ]
    for scenario in report.get("scenario_estimates") or []:
        lines.append(
            "| {name} | {input_tokens_per_call:,} | {output_tokens_per_call:,} | ${estimated_usd:.4f} |".format(
                **scenario
            )
        )
    return "\n".join(lines)


def _iter_observations(payloads: list[dict[str, Any]], *, sources: list[str] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    source_list = sources or ["" for _ in payloads]
    for index, payload in enumerate(payloads):
        source = source_list[index] if index < len(source_list) else ""
        usage = payload.get("llm_usage") if isinstance(payload.get("llm_usage"), dict) else {}
        roles = usage.get("roles") if isinstance(usage.get("roles"), dict) else {}
        for role_name, role in roles.items():
            if not isinstance(role, dict):
                continue
            for obs in role.get("observations") or []:
                if not isinstance(obs, dict):
                    continue
                item = dict(obs)
                item["role"] = role_name
                item["source"] = source
                out.append(item)
    return out


def _scenario_estimates(provider_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    estimates: list[dict[str, Any]] = []
    for name, scenario in DEFAULT_SCENARIOS.items():
        input_tokens = int(scenario["input_tokens_per_call"])
        output_tokens = int(scenario["output_tokens_per_call"])
        total = 0.0
        for call in provider_calls:
            model = str(call.get("model") or "")
            pricing = PRICING_USD_PER_1M_TOKENS.get(model)
            if not pricing:
                continue
            total += (input_tokens / 1_000_000) * pricing["input"]
            total += (output_tokens / 1_000_000) * pricing["output"]
        estimates.append(
            {
                "name": name,
                "input_tokens_per_call": input_tokens,
                "output_tokens_per_call": output_tokens,
                "estimated_usd": round(total, 6),
            }
        )
    return estimates


if __name__ == "__main__":
    raise SystemExit(main())
