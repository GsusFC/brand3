#!/usr/bin/env python3
"""Compare Parallel Search against the existing Exa collector.

This is a lab-only benchmark. It does not feed production Brand3 flows and does
not persist API keys. Provide PARALLEL_API_KEY and EXA_API_KEY through the
environment.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from src.collectors.exa_collector import ExaCollector
from src.config import EXA_API_KEY
from src.research.brand_intelligence import (
    BrandSeed,
    resolve_brand_seed,
    scope_external_observation_to_entity,
    search_source_observation,
)


PARALLEL_SEARCH_URL = "https://api.parallel.ai/v1/search"
USER_AGENT = "Brand3-Lab/0.1"

DEFAULT_CASES = (
    ("LangChain", "https://www.langchain.com"),
    ("Vercel", "https://vercel.com"),
    ("Notion", "https://www.notion.com"),
)

INTENTS = {
    "mentions": "brand company external mentions reviews",
    "competitors": "competitors similar alternatives market category",
    "news": "recent news product launches announcements funding",
    "ai_visibility": "AI recommendation artificial intelligence visibility",
}


@dataclass(frozen=True)
class BakeoffCase:
    brand: str
    url: str

    @property
    def domain(self) -> str:
        parsed = urlparse(self.url if "://" in self.url else f"https://{self.url}")
        return (parsed.netloc or parsed.path).removeprefix("www.").strip("/")

    @property
    def label(self) -> str:
        return _slugify(self.brand)


def main() -> int:
    args = _parse_args()
    cases = _load_cases(args.cases_file) if args.cases_file else [BakeoffCase(*item) for item in DEFAULT_CASES]
    intents = _parse_csv(args.intents) or list(INTENTS)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = [
        run_case(
            case,
            intents=intents,
            exa_limit=args.results,
            parallel_limit=args.results,
            parallel_mode=args.parallel_mode,
            timeout_seconds=args.timeout_seconds,
        )
        for case in cases
    ]

    for payload in payloads:
        case = payload["case"]
        path = output_dir / f"{case['label']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {path}")

    summary = summarize_bakeoff(payloads)
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    print(f"Wrote {output_dir / 'summary.json'}")
    print(f"Wrote {output_dir / 'summary.md'}")
    print(
        "Summary:"
        f" cases={summary['case_count']}"
        f" intents={summary['intent_count']}"
        f" exa_ok={summary['providers']['exa']['ok']}"
        f" parallel_ok={summary['providers']['parallel']['ok']}"
    )
    return 0


def run_case(
    case: BakeoffCase,
    *,
    intents: list[str],
    exa_limit: int,
    parallel_limit: int,
    parallel_mode: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for intent in intents:
        suffix = INTENTS[intent]
        query = f'"{case.brand}" "{case.domain}" {suffix}'
        objective = (
            f"Find high-quality web evidence about {case.brand} ({case.domain}) for a Brand3 brand audit. "
            f"Intent: {intent}. Prioritize sources that contain factual, attributable evidence."
        )
        print(f"Running {case.brand}: {intent}")
        exa_payload = run_exa(query, case=case, intent=intent, limit=exa_limit)
        parallel_payload = run_parallel(
            query,
            objective=objective,
            search_queries=_parallel_search_queries(case, intent),
            mode=parallel_mode,
            limit=parallel_limit,
            timeout_seconds=timeout_seconds,
        )
        exa_payload = annotate_provider_entity_boundary(exa_payload, case=case)
        parallel_payload = annotate_provider_entity_boundary(parallel_payload, case=case)
        outputs[intent] = {
            "query": query,
            "objective": objective,
            "exa": exa_payload,
            "parallel": parallel_payload,
            "comparison": compare_provider_outputs(exa_payload, parallel_payload),
        }
    return {
        "version": "parallel_exa_bakeoff_v0_1",
        "case": {"brand": case.brand, "url": case.url, "domain": case.domain, "label": case.label},
        "outputs": outputs,
        "summary": summarize_case(outputs),
    }


def run_exa(query: str, *, case: BakeoffCase, intent: str, limit: int) -> dict[str, Any]:
    if not EXA_API_KEY:
        return {"status": "skipped", "error": "EXA_API_KEY not set", "results": []}
    start = time.perf_counter()
    try:
        collector = ExaCollector(api_key=EXA_API_KEY)
        results = collector.search(query, num_results=limit, intent=intent, brand_name=case.brand, brand_url=case.url)
    except Exception as exc:
        return {"status": "error", "error": str(exc), "elapsed_ms": _elapsed_ms(start), "results": []}
    rows = [
        {
            "url": result.url,
            "title": result.title,
            "published_date": result.published_date,
            "text_chars": len(result.text or ""),
            "excerpt": _clip(result.text or result.summary or " ".join(str(item) for item in result.highlights), 800),
            "source_class": result.source_class,
            "relation": result.relation,
            "score": result.score,
        }
        for result in results
    ]
    return {
        "status": "ok",
        "provider": "exa",
        "elapsed_ms": _elapsed_ms(start),
        "result_count": len(rows),
        "unique_domains": sorted({_domain(row["url"]) for row in rows if row.get("url")}),
        "results": rows,
    }


def run_parallel(
    query: str,
    *,
    objective: str,
    search_queries: list[str] | None = None,
    mode: str,
    limit: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    api_key = os.environ.get("PARALLEL_API_KEY", "").strip()
    if not api_key:
        return {"status": "skipped", "error": "PARALLEL_API_KEY not set", "results": []}
    payload = {
        "objective": objective,
        "search_queries": search_queries or [_compact_query(query)],
        "mode": mode,
        "max_chars_total": max(1000, limit * 1500),
        "client_model": "brand3-lab",
    }
    start = time.perf_counter()
    request = Request(
        PARALLEL_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        return {"status": "error", "error": _http_error_message(exc), "code": exc.code, "elapsed_ms": _elapsed_ms(start), "results": []}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "elapsed_ms": _elapsed_ms(start), "results": []}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "error", "error": "invalid_json_response", "raw_preview": raw[:500], "elapsed_ms": _elapsed_ms(start), "results": []}
    results = []
    for item in _list(parsed.get("results"))[:limit]:
        excerpts = [str(excerpt) for excerpt in _list(item.get("excerpts")) if excerpt]
        results.append(
            {
                "url": str(item.get("url") or ""),
                "title": str(item.get("title") or ""),
                "published_date": str(item.get("publish_date") or item.get("published_date") or ""),
                "text_chars": sum(len(excerpt) for excerpt in excerpts),
                "excerpt": _clip(" ".join(excerpts), 800),
            }
        )
    return {
        "status": "ok",
        "provider": "parallel",
        "elapsed_ms": _elapsed_ms(start),
        "result_count": len(results),
        "unique_domains": sorted({_domain(row["url"]) for row in results if row.get("url")}),
        "usage": parsed.get("usage"),
        "warnings": parsed.get("warnings"),
        "search_id": parsed.get("search_id"),
        "results": results,
    }


def annotate_provider_entity_boundary(payload: dict[str, Any], *, case: BakeoffCase) -> dict[str, Any]:
    """Apply Brand3's URL-first entity gate to provider search results."""
    if payload.get("status") != "ok":
        return payload
    entity = resolve_brand_seed(BrandSeed(case.url, kind="url", provided_name=case.brand))
    annotated_results: list[dict[str, Any]] = []
    counts = {"eligible": 0, "limited": 0, "ineligible": 0}
    blocked_urls: list[str] = []
    for row in _list(payload.get("results")):
        if not isinstance(row, dict):
            continue
        result = {
            "url": row.get("url") or "",
            "title": row.get("title") or "",
            "text": row.get("excerpt") or "",
            "summary": row.get("excerpt") or "",
            "score": row.get("score") or 0,
            "published_date": row.get("published_date") or "",
        }
        observation = scope_external_observation_to_entity(
            search_source_observation(result, provider=str(payload.get("provider") or "provider")),
            result,
            entity=entity,
            seed_url=case.url,
            brand=case.brand,
        )
        eligibility = observation.evidence_eligibility
        counts[eligibility] = counts.get(eligibility, 0) + 1
        if eligibility == "ineligible":
            blocked_urls.append(str(row.get("url") or ""))
        annotated = dict(row)
        annotated["brand3_evidence_eligibility"] = eligibility
        annotated["brand3_boundary_reason"] = observation.reason
        annotated["brand3_boundary_confidence"] = observation.confidence
        annotated_results.append(annotated)
    enriched = dict(payload)
    enriched["results"] = annotated_results
    enriched["entity_boundary"] = {
        "resolved_name": entity.resolved_name,
        "resolution_status": entity.resolution_status,
        "eligible_count": counts.get("eligible", 0),
        "limited_count": counts.get("limited", 0),
        "ineligible_count": counts.get("ineligible", 0),
        "blocked_urls": [url for url in blocked_urls if url],
    }
    return enriched


def compare_provider_outputs(exa_payload: dict[str, Any], parallel_payload: dict[str, Any]) -> dict[str, Any]:
    exa_urls = {str(row.get("url") or "").rstrip("/") for row in _list(exa_payload.get("results")) if row.get("url")}
    parallel_urls = {str(row.get("url") or "").rstrip("/") for row in _list(parallel_payload.get("results")) if row.get("url")}
    exa_domains = set(exa_payload.get("unique_domains") or [])
    parallel_domains = set(parallel_payload.get("unique_domains") or [])
    return {
        "url_overlap_count": len(exa_urls & parallel_urls),
        "domain_overlap_count": len(exa_domains & parallel_domains),
        "exa_only_domains": sorted(exa_domains - parallel_domains),
        "parallel_only_domains": sorted(parallel_domains - exa_domains),
    }


def summarize_case(outputs: dict[str, Any]) -> dict[str, Any]:
    return {
        intent: {
            "exa": _provider_summary(row.get("exa") or {}),
            "parallel": _provider_summary(row.get("parallel") or {}),
            "comparison": row.get("comparison") or {},
        }
        for intent, row in outputs.items()
    }


def summarize_bakeoff(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    provider_rows = {
        "exa": {"ok": 0, "error": 0, "skipped": 0, "result_total": 0, "elapsed_ms_total": 0},
        "parallel": {"ok": 0, "error": 0, "skipped": 0, "result_total": 0, "elapsed_ms_total": 0},
    }
    rows = []
    for payload in payloads:
        for intent, output in payload["outputs"].items():
            row = {
                "brand": payload["case"]["brand"],
                "domain": payload["case"]["domain"],
                "intent": intent,
                "exa": _provider_summary(output.get("exa") or {}),
                "parallel": _provider_summary(output.get("parallel") or {}),
                "comparison": output.get("comparison") or {},
            }
            rows.append(row)
            for provider in ("exa", "parallel"):
                status = row[provider]["status"]
                provider_rows[provider][status if status in provider_rows[provider] else "error"] += 1
                provider_rows[provider]["result_total"] += int(row[provider]["result_count"])
                provider_rows[provider]["elapsed_ms_total"] += int(row[provider]["elapsed_ms"])
    for provider, metrics in provider_rows.items():
        attempts = max(1, metrics["ok"] + metrics["error"])
        metrics["avg_results_when_attempted"] = round(metrics["result_total"] / attempts, 2)
        metrics["avg_elapsed_ms_when_attempted"] = round(metrics["elapsed_ms_total"] / attempts, 2)
    return {
        "version": "parallel_exa_bakeoff_summary_v0_1",
        "case_count": len(payloads),
        "intent_count": len(rows),
        "providers": provider_rows,
        "rows": rows,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Parallel vs Exa Bakeoff",
        "",
        f"- Cases: `{summary['case_count']}`",
        f"- Case-intents: `{summary['intent_count']}`",
        "",
        "## Provider Totals",
        "",
        "| Provider | OK | Error | Skipped | Results | Avg results | Avg latency ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for provider, metrics in summary["providers"].items():
        lines.append(
            f"| {provider} | {metrics['ok']} | {metrics['error']} | {metrics['skipped']} | "
            f"{metrics['result_total']} | {metrics['avg_results_when_attempted']:.2f} | "
            f"{metrics['avg_elapsed_ms_when_attempted']:.0f} |"
        )
    lines.extend(
        [
            "",
            "## Case Results",
            "",
            "| Brand | Intent | Exa | Parallel | Boundary blocked | URL overlap | Domain overlap | Parallel-only domains |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in summary["rows"]:
        comparison = row["comparison"]
        parallel_only = ", ".join(comparison.get("parallel_only_domains") or []) or "-"
        lines.append(
            "| {brand} | {intent} | {exa_status}/{exa_count} ({exa_ms}ms) | "
            "{parallel_status}/{parallel_count} ({parallel_ms}ms) | {blocked} | {url_overlap} | {domain_overlap} | {parallel_only} |".format(
                brand=_md(row["brand"]),
                intent=_md(row["intent"]),
                exa_status=row["exa"]["status"],
                exa_count=row["exa"]["result_count"],
                exa_ms=row["exa"]["elapsed_ms"],
                parallel_status=row["parallel"]["status"],
                parallel_count=row["parallel"]["result_count"],
                parallel_ms=row["parallel"]["elapsed_ms"],
                blocked=int(row["exa"].get("boundary_ineligible_count") or 0)
                + int(row["parallel"].get("boundary_ineligible_count") or 0),
                url_overlap=comparison.get("url_overlap_count", 0),
                domain_overlap=comparison.get("domain_overlap_count", 0),
                parallel_only=_md(parallel_only),
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def _provider_summary(payload: dict[str, Any]) -> dict[str, Any]:
    boundary = payload.get("entity_boundary") if isinstance(payload.get("entity_boundary"), dict) else {}
    return {
        "status": str(payload.get("status") or "unknown"),
        "result_count": int(payload.get("result_count") or len(payload.get("results") or [])),
        "unique_domain_count": len(payload.get("unique_domains") or []),
        "elapsed_ms": int(payload.get("elapsed_ms") or 0),
        "error": str(payload.get("error") or ""),
        "boundary_ineligible_count": int(boundary.get("ineligible_count") or 0),
    }


def _load_cases(path: Path) -> list[BakeoffCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("cases")
    cases = []
    for row in rows or []:
        if isinstance(row, dict):
            cases.append(BakeoffCase(str(row["brand"]), str(row["url"])))
        elif isinstance(row, list) and len(row) >= 2:
            cases.append(BakeoffCase(str(row[0]), str(row[1])))
    if not cases:
        raise SystemExit(f"No cases found in {path}")
    return cases


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-file", type=Path)
    parser.add_argument("--intents", default="mentions,competitors,news,ai_visibility")
    parser.add_argument("--results", type=int, default=5)
    parser.add_argument("--parallel-mode", choices=("basic", "advanced"), default="advanced")
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--output-dir", type=Path, default=Path("out/parallel_exa_bakeoff"))
    return parser.parse_args()


def _parse_csv(value: str) -> list[str]:
    rows = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in rows if item not in INTENTS]
    if unknown:
        raise SystemExit(f"Unknown intents: {', '.join(unknown)}")
    return rows


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _compact_query(query: str) -> str:
    return " ".join(query.replace('"', "").split())[:180]


def _parallel_search_queries(case: BakeoffCase, intent: str) -> list[str]:
    base = f"{case.brand} {case.domain}"
    suffixes = {
        "mentions": ["official brand", "reviews", "company profile"],
        "competitors": ["alternatives", "competitors", "category"],
        "news": ["news", "funding", "product launch"],
        "ai_visibility": ["AI visibility", "AI recommendations", "web search"],
    }.get(intent, ["brand", "reviews", "news"])
    return [_compact_query(f"{base} {suffix}") for suffix in suffixes[:3]]


def _domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or parsed.path).removeprefix("www.").strip("/").lower()


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in slug.split("-") if part) or "case"


def _clip(value: str, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _http_error_message(exc: HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")
    except Exception:
        body = ""
    return f"{exc.reason}: {body[:500]}" if body else str(exc)


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
