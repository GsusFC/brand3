"""Benchmark summaries for live Brand Intelligence acquisition probes."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BENCHMARK_VERSION = "brand_intelligence_benchmark_v0_1"


@dataclass(frozen=True)
class BrandIntelligenceBenchmarkCase:
    brand: str
    url: str
    label: str = ""
    use_exa: bool = True
    use_web: bool = True
    owned_web_provider: str = "firecrawl"
    exa_results: int = 3

    def to_dict(self) -> dict[str, object]:
        return {
            "brand": self.brand,
            "url": self.url,
            "label": self.label,
            "use_exa": self.use_exa,
            "use_web": self.use_web,
            "owned_web_provider": self.owned_web_provider,
            "exa_results": self.exa_results,
        }


def default_benchmark_cases() -> list[BrandIntelligenceBenchmarkCase]:
    return [
        BrandIntelligenceBenchmarkCase("ChatGPT", "https://chatgpt.com", label="chatgpt-firecrawl", owned_web_provider="firecrawl", exa_results=3),
        BrandIntelligenceBenchmarkCase("ChatGPT", "https://chatgpt.com", label="chatgpt-playwright", owned_web_provider="playwright", exa_results=3),
        BrandIntelligenceBenchmarkCase("LangChain", "https://www.langchain.com", label="langchain-firecrawl", owned_web_provider="firecrawl", exa_results=3),
        BrandIntelligenceBenchmarkCase("LangChain", "https://www.langchain.com", label="langchain-playwright", owned_web_provider="playwright", exa_results=3),
        BrandIntelligenceBenchmarkCase("Base", "https://base.org", label="base-firecrawl", owned_web_provider="firecrawl", exa_results=3),
        BrandIntelligenceBenchmarkCase("Base", "https://base.org", label="base-playwright", owned_web_provider="playwright", exa_results=3),
        BrandIntelligenceBenchmarkCase("Allbirds", "https://www.allbirds.com", label="allbirds-firecrawl", owned_web_provider="firecrawl", exa_results=3),
        BrandIntelligenceBenchmarkCase("Allbirds", "https://www.allbirds.com", label="allbirds-playwright", owned_web_provider="playwright", exa_results=3),
        BrandIntelligenceBenchmarkCase("Headway", "https://makeheadway.com", label="headway-firecrawl", owned_web_provider="firecrawl", exa_results=3),
        BrandIntelligenceBenchmarkCase("Headway", "https://makeheadway.com", label="headway-playwright", owned_web_provider="playwright", exa_results=3),
        BrandIntelligenceBenchmarkCase("Hasura", "https://hasura.io", label="hasura-firecrawl", owned_web_provider="firecrawl", exa_results=3),
        BrandIntelligenceBenchmarkCase("Hasura", "https://hasura.io", label="hasura-playwright", owned_web_provider="playwright", exa_results=3),
        BrandIntelligenceBenchmarkCase("lab.naturaumana.ai", "https://lab.naturaumana.ai", label="lab-naturaumana-firecrawl", owned_web_provider="firecrawl", exa_results=3),
        BrandIntelligenceBenchmarkCase("Obscure Thing", "https://example.com", label="obscure-example-firecrawl", owned_web_provider="firecrawl", exa_results=3),
    ]


def summarize_brand_intelligence_benchmark(probe_payloads: list[dict[str, Any]], cases: list[BrandIntelligenceBenchmarkCase] | None = None) -> dict[str, object]:
    case_rows = [_summarize_probe_payload(payload, case=case) for payload, case in _pair_cases(probe_payloads, cases)]
    provider_metrics = _aggregate_provider_metrics(probe_payloads)
    channel_coverage = _aggregate_channel_coverage(case_rows)
    ready_case_count = sum(1 for row in case_rows if row["inventory_ready"])
    provisional_case_count = sum(1 for row in case_rows if row["resolution_status"] == "provisional")
    unresolved_case_count = sum(1 for row in case_rows if row["resolution_status"] == "unresolved")
    return {
        "version": BENCHMARK_VERSION,
        "case_count": len(case_rows),
        "inventory_ready_count": ready_case_count,
        "provisional_case_count": provisional_case_count,
        "unresolved_case_count": unresolved_case_count,
        "provider_metrics": provider_metrics,
        "channel_coverage": channel_coverage,
        "cases": case_rows,
        "most_common_missing_channels": _most_common_missing_channels(case_rows),
    }


def render_brand_intelligence_benchmark_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Brand Intelligence Acquisition Benchmark",
        "",
        f"- Cases: {summary.get('case_count', 0)}",
        f"- Inventory ready: {summary.get('inventory_ready_count', 0)}",
        f"- Provisional: {summary.get('provisional_case_count', 0)}",
        f"- Unresolved: {summary.get('unresolved_case_count', 0)}",
        "",
        "## Cases",
        "",
        "| Brand | Web Provider | Status | Eligible | Missing | Evidence | Warnings |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary.get("cases", []):
        lines.append(
            "| {brand} | {provider} | {status} | {eligible} | {missing} | {evidence} | {warnings} |".format(
                brand=row.get("brand", ""),
                provider=row.get("owned_web_provider", ""),
                status=row.get("resolution_status", ""),
                eligible=", ".join(row.get("eligible_channels", [])) or "none",
                missing=", ".join(row.get("missing_required_channels", [])) or "none",
                evidence=row.get("evidence_count", 0),
                warnings=", ".join(row.get("warnings", [])) or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Provider Metrics",
            "",
        "| Provider | Observed | Eligible | Limited | Ineligible | Errors | Owned Web Chars Avg | Covered Channels |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    provider_metrics = summary.get("provider_metrics", {})
    for provider in sorted(provider_metrics):
        row = provider_metrics[provider]
        lines.append(
            "| {provider} | {observed} | {eligible} | {limited} | {ineligible} | {errors} | {chars} | {channels} |".format(
                provider=provider,
                observed=row.get("observed_count", 0),
                eligible=row.get("eligible_count", 0),
                limited=row.get("limited_count", 0),
                ineligible=row.get("ineligible_count", 0),
                errors=row.get("error_count", 0),
                chars=row.get("average_owned_web_chars", 0),
                channels=", ".join(row.get("covered_channels", [])) or "none",
            )
        )
    if summary.get("most_common_missing_channels"):
        lines.extend(
            [
                "",
                "## Missing Channels",
                "",
            ]
        )
        for channel, count in summary["most_common_missing_channels"]:
            lines.append(f"- {channel}: {count}")
    return "\n".join(lines).strip() + "\n"


def _pair_cases(
    probe_payloads: list[dict[str, Any]],
    cases: list[BrandIntelligenceBenchmarkCase] | None,
) -> list[tuple[dict[str, Any], BrandIntelligenceBenchmarkCase | None]]:
    if cases is None:
        return [(payload, None) for payload in probe_payloads]
    paired: list[tuple[dict[str, Any], BrandIntelligenceBenchmarkCase | None]] = []
    for index, payload in enumerate(probe_payloads):
        paired.append((payload, cases[index] if index < len(cases) else None))
    return paired


def _summarize_probe_payload(payload: dict[str, Any], *, case: BrandIntelligenceBenchmarkCase | None) -> dict[str, object]:
    inventory = _dict(payload.get("inventory"))
    evidence_graph = _dict(payload.get("evidence_graph"))
    observations = _list(payload.get("observations"))
    provider_metrics = _aggregate_provider_metrics([payload])
    return {
        "brand": str(_dict(payload.get("input")).get("brand") or (case.brand if case else "")),
        "url": str(_dict(payload.get("input")).get("url") or (case.url if case else "")),
        "label": case.label if case else "",
        "owned_web_provider": str(_dict(payload.get("input")).get("owned_web_provider") or (case.owned_web_provider if case else "")),
        "resolution_status": str(_dict(payload.get("entity")).get("resolution_status") or ""),
        "interpretation_ready": bool(_dict(payload.get("plan")).get("interpretation_ready")),
        "inventory_ready": bool(_dict(payload.get("plan")).get("interpretation_ready")) and not list(inventory.get("missing_required_channels") or []),
        "eligible_channels": list(inventory.get("eligible_channels") or []),
        "missing_required_channels": list(inventory.get("missing_required_channels") or []),
        "duplicate_source_urls": list(inventory.get("duplicate_source_urls") or []),
        "conflicting_source_urls": list(inventory.get("conflicting_source_urls") or []),
        "evidence_count": int(_dict(evidence_graph.get("summary")).get("evidence_count") or 0),
        "rejected_count": int(_dict(evidence_graph.get("summary")).get("rejected_count") or 0),
        "warnings": list(evidence_graph.get("warnings") or []),
        "observation_count": len(observations),
        "provider_metrics": provider_metrics,
    }


def _aggregate_provider_metrics(probe_payloads: list[dict[str, Any]]) -> dict[str, dict[str, object]]:
    aggregated: dict[str, dict[str, object]] = defaultdict(lambda: {
        "observation_count": 0,
        "observed_count": 0,
        "eligible_count": 0,
        "limited_count": 0,
        "ineligible_count": 0,
        "error_count": 0,
        "covered_channels": set(),
        "case_count": 0,
        "confidence_total": 0.0,
        "confidence_count": 0,
        "owned_web_chars_total": 0,
        "owned_web_chars_count": 0,
    })
    seen_cases_by_provider: dict[str, set[str]] = defaultdict(set)
    for payload in probe_payloads:
        case_id = _case_id(payload)
        raw_counts = _dict(payload.get("raw_counts"))
        owned_web_provider = str(raw_counts.get("owned_web_provider") or _dict(payload.get("input")).get("owned_web_provider") or "")
        owned_web_chars = raw_counts.get("web_chars")
        for observation in _list(payload.get("observations")):
            provider = str(observation.get("provider") or "unknown")
            row = aggregated[provider]
            row["observation_count"] += 1
            row["observed_count"] += 1 if observation.get("status") == "observed" else 0
            row["eligible_count"] += 1 if observation.get("evidence_eligibility") == "eligible" else 0
            row["limited_count"] += 1 if observation.get("evidence_eligibility") == "limited" else 0
            row["ineligible_count"] += 1 if observation.get("evidence_eligibility") == "ineligible" else 0
            row["error_count"] += 1 if observation.get("status") == "error" else 0
            row["covered_channels"].add(str(observation.get("channel") or "unknown"))
            confidence = observation.get("confidence")
            if isinstance(confidence, (int, float)):
                row["confidence_total"] += float(confidence)
                row["confidence_count"] += 1
            if provider == owned_web_provider and observation.get("channel") == "owned_web" and isinstance(owned_web_chars, int):
                row["owned_web_chars_total"] += int(owned_web_chars)
                row["owned_web_chars_count"] += 1
            if case_id and case_id not in seen_cases_by_provider[provider]:
                row["case_count"] += 1
                seen_cases_by_provider[provider].add(case_id)
    result: dict[str, dict[str, object]] = {}
    for provider, row in sorted(aggregated.items()):
        confidence_count = int(row["confidence_count"])
        owned_web_chars_count = int(row["owned_web_chars_count"])
        result[provider] = {
            "observation_count": int(row["observation_count"]),
            "observed_count": int(row["observed_count"]),
            "eligible_count": int(row["eligible_count"]),
            "limited_count": int(row["limited_count"]),
            "ineligible_count": int(row["ineligible_count"]),
            "error_count": int(row["error_count"]),
            "covered_channels": sorted(row["covered_channels"]),
            "case_count": int(row["case_count"]),
            "average_confidence": round(float(row["confidence_total"]) / confidence_count, 4) if confidence_count else 0.0,
            "average_owned_web_chars": round(float(row["owned_web_chars_total"]) / owned_web_chars_count, 2) if owned_web_chars_count else 0.0,
            "owned_web_chars_cases": owned_web_chars_count,
        }
    return result


def _aggregate_channel_coverage(case_rows: list[dict[str, object]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in case_rows:
        counts.update(str(channel) for channel in row.get("eligible_channels", []))
    return dict(sorted(counts.items()))


def _most_common_missing_channels(case_rows: list[dict[str, object]], limit: int = 10) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for row in case_rows:
        counts.update(str(channel) for channel in row.get("missing_required_channels", []))
    return counts.most_common(limit)


def _case_id(payload: dict[str, Any]) -> str:
    input_data = _dict(payload.get("input"))
    return str(input_data.get("brand") or input_data.get("url") or "")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []
