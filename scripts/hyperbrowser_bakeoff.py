#!/usr/bin/env python3
"""Compare Hyperbrowser Fetch against Brand3's current web acquisition.

Lab-only script. It does not feed production Brand3 flows, mutate scoring, or
persist provider keys. Provide HYPERBROWSER_API_KEY through the environment.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.collectors.hyperbrowser_collector import (
    HyperbrowserCollector,
    branding_summary,
)
from src.collectors.web_collector import WebCollector, WebData
from src.config import FIRECRAWL_API_KEY


DEFAULT_CASES = (
    ("LangChain", "https://www.langchain.com"),
    ("Vercel", "https://vercel.com"),
    ("Notion", "https://www.notion.com"),
)

DEFAULT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "offer": {"type": "string"},
        "audience": {"type": "string"},
        "proofPoints": {"type": "array", "items": {"type": "string"}},
    },
}


@dataclass(frozen=True)
class BakeoffCase:
    brand: str
    url: str

    @property
    def label(self) -> str:
        return _slugify(self.brand)

    @property
    def domain(self) -> str:
        parsed = urlparse(self.url if "://" in self.url else f"https://{self.url}")
        return (parsed.netloc or parsed.path).removeprefix("www.").strip("/")


@dataclass
class AcquisitionRow:
    brand: str
    url: str
    provider: str
    provider_variant: str = ""
    status: str = ""
    elapsed_ms: int = 0
    text_chars: int = 0
    html_chars: int = 0
    link_count: int = 0
    has_branding: bool = False
    has_screenshot: bool = False
    color_count: int = 0
    font_count: int = 0
    logo_detected: bool = False
    title: str = ""
    final_url: str = ""
    error: str = ""

    @property
    def usable_text(self) -> bool:
        return self.text_chars >= 200


def main() -> int:
    args = _parse_args()
    cases = _load_cases(args.cases_file) if args.cases_file else [BakeoffCase(*item) for item in DEFAULT_CASES]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    payloads = [
        run_case(
            case,
            timeout_seconds=args.timeout_seconds,
            include_branding=args.include_branding,
            include_screenshot=args.include_screenshot,
            cache_max_age_seconds=args.cache_max_age_seconds,
            current_crawl_subpages=not args.no_current_subpages,
            skip_current=args.skip_current,
            variant=args.variant,
            search_query=args.search_query,
            search_limit=args.search_limit,
            extract_wait_seconds=args.extract_wait_seconds,
            extract_poll_interval=args.extract_poll_interval,
            json_schema_path=args.json_schema,
            json_prompt=args.json_prompt,
            exclude_selector=args.exclude_selector,
            include_selector=args.include_selector,
        )
        for case in cases
    ]

    for payload in payloads:
        case = payload["case"]
        path = args.output_dir / f"{case['label']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {path}")

    summary = summarize_bakeoff(payloads)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    print(f"Wrote {args.output_dir / 'summary.json'}")
    print(f"Wrote {args.output_dir / 'summary.md'}")
    print(
        "Summary:"
        f" cases={summary['case_count']}"
        f" hyperbrowser_ok={summary['providers'].get('hyperbrowser', {}).get('ok', 0)}"
        f" hyperbrowser_skipped={summary['providers'].get('hyperbrowser', {}).get('skipped', 0)}"
    )
    return 0


def run_case(
    case: BakeoffCase,
    *,
    timeout_seconds: int,
    include_branding: bool,
    include_screenshot: bool,
    cache_max_age_seconds: int | None,
    current_crawl_subpages: bool,
    skip_current: bool,
    variant: str,
    search_query: str | None = None,
    search_limit: int = 5,
    extract_wait_seconds: int = 90,
    extract_poll_interval: float = 1.0,
    json_schema_path: Path | None,
    json_prompt: str | None,
    exclude_selector: list[str] | None,
    include_selector: list[str] | None,
) -> dict[str, Any]:
    print(f"Running {case.brand}: {case.url}")
    rows: list[AcquisitionRow] = []
    raw: dict[str, Any] = {}
    if not skip_current:
        current_row, current_raw = run_current_collector(case, crawl_subpages=current_crawl_subpages)
        rows.append(current_row)
        raw["current_web_collector"] = current_raw

    hyper_row, hyper_raw = run_hyperbrowser(
        case,
        timeout_seconds=timeout_seconds,
        include_branding=include_branding,
        include_screenshot=include_screenshot,
        cache_max_age_seconds=cache_max_age_seconds,
        variant=variant,
        search_query=search_query,
        search_limit=search_limit,
        extract_wait_seconds=extract_wait_seconds,
        extract_poll_interval=extract_poll_interval,
        json_schema_path=json_schema_path,
        json_prompt=json_prompt,
        exclude_selectors=(
            exclude_selector
            if variant != "fetch-clean"
            else (exclude_selector or ["nav", "footer", "aside"])
        ),
        include_selectors=include_selector,
    )
    rows.append(hyper_row)
    raw["hyperbrowser"] = hyper_raw

    return {
        "version": "hyperbrowser_bakeoff_v0_1",
        "case": {"brand": case.brand, "url": case.url, "domain": case.domain, "label": case.label},
        "rows": [asdict(row) | {"usable_text": row.usable_text} for row in rows],
        "comparison": compare_rows(rows),
        "raw": raw,
    }


def run_current_collector(case: BakeoffCase, *, crawl_subpages: bool) -> tuple[AcquisitionRow, dict[str, Any]]:
    start = time.perf_counter()
    collector = WebCollector(api_key=FIRECRAWL_API_KEY)
    try:
        data = collector.scrape(case.url, crawl_subpages=crawl_subpages)
    except Exception as exc:
        elapsed_ms = _elapsed_ms(start)
        return (
            AcquisitionRow(
                brand=case.brand,
                url=case.url,
                provider="current_web_collector",
                status="error",
                elapsed_ms=elapsed_ms,
                error=str(exc),
            ),
            {"error": str(exc)},
        )
    elapsed_ms = _elapsed_ms(start)
    row = AcquisitionRow(
        brand=case.brand,
        url=case.url,
        provider="current_web_collector",
        status="ok" if data.markdown_content else "empty",
        elapsed_ms=elapsed_ms,
        text_chars=len(data.markdown_content or ""),
        html_chars=len(data.html or ""),
        link_count=len(data.links or []),
        title=data.title,
        final_url=data.canonical_url or data.url,
        error=data.error,
    )
    return row, _web_data_payload(data)


def run_hyperbrowser(
    case: BakeoffCase,
    *,
    timeout_seconds: int,
    include_branding: bool,
    include_screenshot: bool,
    cache_max_age_seconds: int | None,
    variant: str,
    search_query: str | None = None,
    search_limit: int = 5,
    extract_wait_seconds: int = 90,
    extract_poll_interval: float = 1.0,
    json_schema_path: Path | None,
    json_prompt: str | None,
    exclude_selectors: list[str] | None,
    include_selectors: list[str] | None,
) -> tuple[AcquisitionRow, dict[str, Any]]:
    collector = HyperbrowserCollector(timeout_seconds=timeout_seconds)

    if variant == "search" or variant == "search-json":
        raw = collector.search(
            search_query or case.brand,
            limit=search_limit,
        )
        return _run_hyperbrowser_search(
            case,
            raw,
            query=search_query or case.brand,
            variant=variant,
            extractor_uses_titles=False,
        )

    if variant in {"extract", "extract-json"}:
        json_schema = (
            _load_json_schema(json_schema_path)
            if json_schema_path
            else (DEFAULT_JSON_SCHEMA if variant == "extract-json" else None)
        )
        raw = collector.extract(
            case.url,
            prompt=json_prompt if variant == "extract-json" else None,
            schema=json_schema,
            wait_for_completion=True,
            max_wait_seconds=extract_wait_seconds,
            poll_interval_seconds=extract_poll_interval,
        )
        return _run_hyperbrowser_extract(case, raw, variant=variant)

    json_schema = (
        _load_json_schema(json_schema_path)
        if json_schema_path
        else (DEFAULT_JSON_SCHEMA if variant == "fetch-json" else None)
    )
    data = collector.fetch(
        case.url,
        include_branding=include_branding,
        include_screenshot=include_screenshot,
        cache_max_age_seconds=cache_max_age_seconds,
        exclude_selectors=exclude_selectors,
        include_selectors=include_selectors,
        json_schema=json_schema if variant == "fetch-json" else None,
        json_prompt=json_prompt,
    )
    brand = branding_summary(data.branding)
    status = "ok" if not data.error and data.markdown else "error" if data.error else "empty"
    row = AcquisitionRow(
        brand=case.brand,
        url=case.url,
        provider="hyperbrowser",
        provider_variant=variant,
        status=status,
        elapsed_ms=data.elapsed_ms,
        text_chars=data.text_chars,
        html_chars=data.html_chars,
        link_count=len(data.links),
        has_branding=bool(data.branding),
        has_screenshot=bool(data.screenshot),
        color_count=int(brand["color_count"] or 0),
        font_count=int(brand["font_count"] or 0),
        logo_detected=bool(brand["logo_detected"]),
        title=data.title,
        final_url=data.final_url,
        error=data.error,
    )
    return row, {
        "status": data.status,
        "job_id": data.job_id,
        "title": data.title,
        "source_url": data.source_url,
        "markdown_preview": _clip(data.markdown, 1200),
        "html_chars": data.html_chars,
        "links": data.links[:30],
        "screenshot_present": bool(data.screenshot),
        "branding_summary": brand,
        "json_payload": data.json_payload,
        "error": data.error,
        "elapsed_ms": data.elapsed_ms,
    }


def _run_hyperbrowser_search(
    case: BakeoffCase,
    payload: dict[str, Any] | None,
    *,
    query: str,
    variant: str,
    extractor_uses_titles: bool = False,
) -> tuple[AcquisitionRow, dict[str, Any]]:
    raw: dict[str, Any] = payload if isinstance(payload, dict) else {"status": "error", "error": "Invalid search response"}
    results = _as_list(raw.get("results"))
    if not results and isinstance(raw.get("data"), dict):
        results = _as_list(raw["data"].get("results"))
    if not results and isinstance(raw.get("data"), list):
        results = _as_list(raw.get("data"))
    query_used = raw.get("query")
    if not query_used and isinstance(raw.get("data"), dict):
        query_used = raw["data"].get("query")
    text_chunks = [
        _search_item_text(item, include_title=extractor_uses_titles)
        for item in results
    ]
    text = "\n\n".join(text_chunks).strip()
    status = _status_from_payload(raw, text=text)
    row = AcquisitionRow(
        brand=case.brand,
        url=case.url,
        provider="hyperbrowser",
        provider_variant=variant,
        status=status,
        elapsed_ms=int(raw.get("elapsedMs") or 0),
        text_chars=len(text),
        link_count=len(results),
        title="Hyperbrowser search",
        final_url=case.url,
        error=str(raw.get("error") or ""),
    )
    return row, {
        "status": raw.get("status"),
        "query": str(query_used or raw.get("q") or query),
        "raw_results": results[:50],
        "results_count": len(results),
        "error": str(raw.get("error") or ""),
        "elapsed_ms": row.elapsed_ms,
    }


def _run_hyperbrowser_extract(
    case: BakeoffCase,
    payload: dict[str, Any] | None,
    *,
    variant: str,
) -> tuple[AcquisitionRow, dict[str, Any]]:
    raw: dict[str, Any] = payload if isinstance(payload, dict) else {"status": "error", "error": "Invalid extract response"}
    raw_data = raw.get("data")
    if raw_data is None and isinstance(raw.get("outputs"), dict):
        raw_data = raw.get("outputs")
    extracted_payload = raw.get("json") if raw.get("json") is not None else None
    if extracted_payload is None and isinstance(raw_data, dict):
        extracted_payload = raw_data.get("json")
        if extracted_payload is None and "json" in raw and raw["json"] is not None:
            extracted_payload = raw["json"]
    rows = _as_list(raw_data) if isinstance(raw_data, list) else _as_dict(raw_data)
    if not rows and isinstance(extracted_payload, list):
        rows = extracted_payload
    if not rows and isinstance(extracted_payload, dict):
        rows = [extracted_payload]
    text_chunks = [_search_item_text(row) for row in rows]
    text = "\n\n".join(text_chunks).strip()
    status = _status_from_payload(raw, text=text)
    row = AcquisitionRow(
        brand=case.brand,
        url=case.url,
        provider="hyperbrowser",
        provider_variant=variant,
        status=status,
        elapsed_ms=int(raw.get("elapsedMs") or 0),
        text_chars=len(text),
        link_count=0,
        has_screenshot=bool(raw.get("screenshot")),
        title="Hyperbrowser extract",
        final_url=(case.url or ""),
        error=str(raw.get("error") or ""),
    )
    return row, {
        "status": raw.get("status"),
        "job_id": raw.get("jobId"),
        "title": raw.get("title"),
        "source_urls": _as_list(raw.get("source_urls")),
        "markdown_preview": _clip(text, 1200),
        "results_count": len(rows),
        "json_payload": extracted_payload,
        "raw_data": raw_data if isinstance(raw_data, dict) else None,
        "error": str(raw.get("error") or ""),
        "elapsed_ms": row.elapsed_ms,
    }


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _as_dict(value: Any) -> list[dict[str, Any]]:
    return [value] if isinstance(value, dict) else []


def _search_item_text(item: Any, *, include_title: bool = True) -> str:
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return str(item or "").strip()

    parts = [
        item.get("title") if include_title else None,
        item.get("url"),
        item.get("link"),
        item.get("snippet"),
        item.get("description"),
        item.get("text"),
        item.get("content"),
    ]
    return " | ".join([str(part).strip() for part in parts if str(part).strip()])[:2048]


def _status_from_payload(payload: dict[str, Any], *, text: str) -> str:
    status = str(payload.get("status") or "").lower().strip()
    if payload.get("error"):
        return "error"
    if status in {"completed", "succeeded", "done", "ok"}:
        return "ok" if text else "empty"
    if status in {"pending", "running", "queued"}:
        return "pending"
    if status:
        return "error" if text == "" and status not in {"empty", "skipped"} else "ok" if text else status
    return "ok" if text else "empty"


def compare_rows(rows: list[AcquisitionRow]) -> dict[str, Any]:
    by_provider = {row.provider: row for row in rows}
    current = by_provider.get("current_web_collector")
    hyper = by_provider.get("hyperbrowser")
    if not hyper:
        return {}
    comparison: dict[str, Any] = {
        "hyperbrowser_usable_text": hyper.usable_text,
        "hyperbrowser_branding_present": hyper.has_branding,
        "hyperbrowser_screenshot_present": hyper.has_screenshot,
    }
    if current:
        comparison.update(
            {
                "text_char_delta_vs_current": hyper.text_chars - current.text_chars,
                "html_char_delta_vs_current": hyper.html_chars - current.html_chars,
                "link_delta_vs_current": hyper.link_count - current.link_count,
                "current_usable_text": current.usable_text,
            }
        )
    return comparison


def summarize_bakeoff(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    provider_rows: dict[str, list[dict[str, Any]]] = {}
    for payload in payloads:
        for row in payload.get("rows") or []:
            provider_rows.setdefault(row["provider"], []).append(row)

    providers = {}
    for provider, rows in provider_rows.items():
        providers[provider] = {
            "ok": sum(1 for row in rows if row["status"] == "ok"),
            "skipped": sum(1 for row in rows if "API_KEY not set" in str(row.get("error") or "")),
            "usable_text": sum(1 for row in rows if row.get("usable_text")),
            "avg_elapsed_ms": _avg([row.get("elapsed_ms") for row in rows]),
            "avg_text_chars": _avg([row.get("text_chars") for row in rows]),
        }

    return {
        "version": "hyperbrowser_bakeoff_summary_v0_1",
        "case_count": len(payloads),
        "providers": providers,
        "cases": [
            {
                "brand": payload["case"]["brand"],
                "domain": payload["case"]["domain"],
                "rows": payload.get("rows") or [],
                "comparison": payload.get("comparison") or {},
            }
            for payload in payloads
        ],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Hyperbrowser Bakeoff",
        "",
        f"- Cases: `{summary['case_count']}`",
        "",
        "## Provider Summary",
        "",
        "| Provider | OK | Skipped | Usable text | Avg elapsed | Avg text chars |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for provider, stats in sorted((summary.get("providers") or {}).items()):
        lines.append(
            "| "
            + " | ".join(
                [
                    _md(provider),
                    str(stats.get("ok", 0)),
                    str(stats.get("skipped", 0)),
                    str(stats.get("usable_text", 0)),
                    str(stats.get("avg_elapsed_ms", 0)),
                    str(stats.get("avg_text_chars", 0)),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Brand | Provider | Status | Text chars | Links | Branding | Screenshot | Logo | Error |",
            "| --- | --- | --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for case in summary.get("cases") or []:
        for row in case.get("rows") or []:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md(case.get("brand")),
                        _md(row.get("provider")),
                        _md(row.get("status")),
                        str(row.get("text_chars", 0)),
                        str(row.get("link_count", 0)),
                        "yes" if row.get("has_branding") else "no",
                        "yes" if row.get("has_screenshot") else "no",
                        "yes" if row.get("logo_detected") else "no",
                        _md(_clip(row.get("error") or "", 120)),
                    ]
                )
                + " |"
            )
    return "\n".join(lines) + "\n"


def _web_data_payload(data: WebData) -> dict[str, Any]:
    return {
        "url": data.url,
        "title": data.title,
        "canonical_url": data.canonical_url,
        "content_source": data.content_source,
        "browser_status": data.browser_status,
        "markdown_preview": _clip(data.markdown_content, 1200),
        "html_chars": len(data.html or ""),
        "links": list(data.links or [])[:30],
        "owned_fallback_urls": list(data.owned_fallback_urls or []),
        "error": data.error,
    }


def _load_cases(path: Path) -> list[BakeoffCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("cases") if isinstance(raw, dict) else raw
    cases = []
    for item in items or []:
        if isinstance(item, dict):
            brand = item.get("brand") or item.get("brand_name") or item.get("name")
            url = item.get("url") or item.get("website_url") or item.get("website")
        else:
            brand, url = item
        if brand and url:
            cases.append(BakeoffCase(str(brand), str(url)))
    return cases


def _load_json_schema(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return loaded if isinstance(loaded, dict) else None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-file", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("out/hyperbrowser_bakeoff"))
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--cache-max-age-seconds", type=int, default=86400)
    parser.add_argument("--include-branding", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-screenshot", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--variant",
        choices=(
            "fetch",
            "fetch-clean",
            "fetch-json",
            "search",
            "search-json",
            "extract",
            "extract-json",
        ),
        default="fetch",
    )
    parser.add_argument("--json-schema", type=Path)
    parser.add_argument(
        "--json-prompt",
        default="Extract the main offer, target audience, and proof points in concise fields.",
    )
    parser.add_argument("--search-query", help="Search query when variant is search/search-json")
    parser.add_argument("--search-limit", type=int, default=5)
    parser.add_argument(
        "--extract-wait-seconds",
        type=int,
        default=90,
        help="Max seconds to wait for extract jobs to finish",
    )
    parser.add_argument(
        "--extract-poll-interval",
        type=float,
        default=1.0,
        help="Polling interval for extract jobs",
    )
    parser.add_argument("--exclude-selector", action="append")
    parser.add_argument("--include-selector", action="append")
    parser.add_argument("--skip-current", action="store_true")
    parser.add_argument("--no-current-subpages", action="store_true")
    return parser.parse_args()


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _avg(values: list[Any]) -> int:
    nums = [int(value) for value in values if isinstance(value, int)]
    return int(sum(nums) / len(nums)) if nums else 0


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in slug.split("-") if part) or "case"


def _clip(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
