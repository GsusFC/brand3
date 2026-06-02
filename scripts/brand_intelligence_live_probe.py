#!/usr/bin/env python3
"""Run a small live Brand Intelligence Acquisition probe.

This script is intentionally outside the product flow. It calls existing
collectors, converts their outputs into the new acquisition contract, and writes
a JSON artifact for review.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from src.collectors.exa_collector import ExaCollector, ExaResult
from src.collectors.web_collector import WebCollector, WebData
from src.config import EXA_API_KEY, FIRECRAWL_API_KEY
from src.research.brand_intelligence import (
    BrandSeed,
    build_brand_evidence_graph,
    build_brand_source_inventory,
    evidence_item_from_observation,
    owned_web_source_observation,
    plan_brand_intelligence,
    search_source_observation,
)


def main() -> int:
    args = _parse_args()
    payload = run_probe(
        brand=args.brand,
        url=args.url,
        use_exa=args.use_exa,
        use_web=args.use_web,
        owned_web_provider=args.owned_web_provider,
        exa_results=args.exa_results,
        output=args.output,
    )
    inventory = payload["inventory"]
    graph = payload["evidence_graph"]
    print(
        "Summary:"
        f" observations={len(payload['observations'])}"
        f" eligible_channels={len(inventory.eligible_channels)}"
        f" evidence={graph.summary()['evidence_count']}"
        f" rejected={graph.summary()['rejected_count']}"
    )
    if inventory.limitations:
        print(f"Inventory limitations: {', '.join(inventory.limitations)}")
    if graph.warnings:
        print(f"Graph warnings: {', '.join(graph.warnings)}")
    return 0


def run_probe(
    *,
    brand: str,
    url: str,
    use_exa: bool = True,
    use_web: bool = True,
    owned_web_provider: str = "firecrawl",
    exa_results: int = 3,
    output: Path | None = None,
) -> dict[str, Any]:
    entity, plan = plan_brand_intelligence(BrandSeed(url, kind="url", provided_name=brand))

    observations = []
    evidence_items = []
    probe_errors: list[str] = []

    exa_results_data: list[ExaResult] = []
    if use_exa:
        try:
            exa_results_data = _collect_exa(brand, url, exa_results)
        except Exception as exc:
            message = f"exa_error: {exc}"
            print(f"Exa search error: {exc}")
            probe_errors.append(message)
    for result in exa_results_data:
        observation = search_source_observation(
            _exa_result_payload(result),
            provider="exa",
            channel=_channel_for_exa_result(result),
        )
        observations.append(observation)
        evidence_items.append(
            evidence_item_from_observation(
                observation,
                _evidence_excerpt(result.text or result.summary or " ".join(str(item) for item in result.highlights)),
            )
        )

    web_data = None
    if use_web:
        try:
            web_data = _collect_web(url, owned_web_provider=owned_web_provider)
        except Exception as exc:
            message = f"web_error:{owned_web_provider}:{exc}"
            print(f"Web capture error ({owned_web_provider}): {exc}")
            probe_errors.append(message)
    if web_data is not None:
        observation = owned_web_source_observation(
            _web_data_payload(web_data),
            provider=owned_web_provider,
            channel="owned_web",
        )
        observations.append(observation)
        evidence_items.append(evidence_item_from_observation(observation, web_data.markdown_content))

    inventory = build_brand_source_inventory(plan, observations)
    graph = build_brand_evidence_graph(inventory, evidence_items)
    payload = {
        "input": {"brand": brand, "url": url, "owned_web_provider": owned_web_provider},
        "entity": entity.to_dict(),
        "plan": plan.to_dict(),
        "inventory": inventory.to_dict(),
        "evidence_graph": graph.to_dict(),
        "observations": [observation.to_dict() for observation in observations],
        "raw_counts": {
            "exa_results": len(exa_results_data),
            "web_chars": len(web_data.markdown_content) if web_data else 0,
            "owned_web_provider": owned_web_provider,
        },
        "errors": probe_errors,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {output}")
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, default=Path("out/brand_intelligence_live_probe.json"))
    parser.add_argument("--exa-results", type=int, default=3)
    parser.add_argument("--use-exa", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--use-web", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--owned-web-provider",
        choices=("firecrawl", "playwright", "none"),
        default="firecrawl",
        help="Owned-web capture provider used when --use-web is enabled.",
    )
    return parser.parse_args()


def _collect_exa(brand: str, url: str, limit: int) -> list[ExaResult]:
    if not EXA_API_KEY:
        print("Exa skipped: EXA_API_KEY not set")
        return []
    collector = ExaCollector(api_key=EXA_API_KEY)
    query = f'"{brand}" "{_domain_anchor(url)}" brand company reviews'
    return collector.search(query, num_results=limit, intent="mentions", brand_name=brand, brand_url=url)


def _collect_web(url: str, *, owned_web_provider: str = "firecrawl") -> WebData | None:
    if owned_web_provider == "none":
        print("Web skipped: owned web provider disabled")
        return None
    collector = WebCollector(api_key=FIRECRAWL_API_KEY)
    if owned_web_provider == "playwright":
        payload, error = collector._fetch_browser_fallback(url)
        if error:
            return WebData(url=url, error=error, content_source="browser_fallback")
        return WebData(
            url=url,
            title=str(payload.get("title") or ""),
            meta_description=str(payload.get("meta_description") or ""),
            markdown_content=str(payload.get("body_text") or ""),
            html=str(payload.get("html") or ""),
            canonical_url=str(payload.get("canonical_url") or url),
            links=list(payload.get("links") or []),
            content_source="browser_fallback",
        )
    if not FIRECRAWL_API_KEY:
        print("Web skipped: FIRECRAWL_API_KEY not set")
        return None
    return collector.scrape(url, crawl_subpages=False)


def _exa_result_payload(result: ExaResult) -> dict[str, Any]:
    return {
        "url": result.url,
        "title": result.title,
        "text": result.text,
        "summary": result.summary,
        "score": result.score,
        "published_date": result.published_date,
    }


def _web_data_payload(web_data: WebData) -> dict[str, Any]:
    return {
        "url": web_data.canonical_url or web_data.url,
        "title": web_data.title,
        "markdown": web_data.markdown_content,
        "error": web_data.error,
    }


def _channel_for_exa_result(result: ExaResult) -> str:
    haystack = " ".join(
        [
            str(result.url or ""),
            str(result.title or ""),
            str(result.text or "")[:500],
            str(result.summary or "")[:500],
        ]
    ).lower()
    if any(token in haystack for token in ("review", "reviews", "ratings", "g2.com", "trustpilot", "capterra")):
        return "reviews"
    if any(token in haystack for token in ("news", "press", "launch", "announces", "funding")):
        return "news"
    return "search"


def _evidence_excerpt(text: str, limit: int = 1400) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0]


def _domain_anchor(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").strip("/").removeprefix("www.")


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
