"""Experimental online presence inventory for Brand3.

This script is intentionally outside the production scoring path. It discovers
public candidate surfaces for a brand and classifies them conservatively so
editorial evidence can be organized before any scoring changes.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.context_collector import ContextCollector
from src.collectors.exa_collector import ExaCollector
from src.collectors.web_collector import WebCollector
from src.config import EXA_API_KEY, FIRECRAWL_API_KEY
from src.services.brand_service import _has_usable_web_content


COMMON_PUBLIC_PATHS = (
    "/about",
    "/pricing",
    "/docs",
    "/blog",
    "/news",
    "/help",
    "/support",
    "/trust",
    "/security",
    "/enterprise",
    "/customers",
    "/case-studies",
)

OUTPUT_FIELDS = (
    "brand",
    "input_url",
    "candidate_url",
    "host",
    "page_type",
    "relation_to_brand",
    "confidence",
    "source",
    "title_or_snippet",
    "collection_method",
    "status",
    "error",
    "text_chars",
    "usable_for_brand_evidence",
    "usable_for_perception_evidence",
)

BENCHMARK_SUMMARY_FIELDS = (
    "brand",
    "input_url",
    "total_public_pages_found",
    "official_pages_found",
    "official_pages_read",
    "usable_brand_evidence_pages",
    "usable_public_perception_pages",
    "primary_page_read_method",
    "primary_page_text_chars",
    "official_related_usable_count",
    "docs_usable_count",
    "news_or_blog_usable_count",
    "support_usable_count",
    "recommended_evidence_base",
    "recommended_analysis_mode",
)


@dataclass
class InventoryRow:
    brand: str
    input_url: str
    candidate_url: str
    host: str
    page_type: str
    relation_to_brand: str
    confidence: float
    source: str
    title_or_snippet: str = ""
    collection_method: str = "not_attempted"
    status: str = ""
    error: str = ""
    text_chars: int = 0
    usable_for_brand_evidence: bool = False
    usable_for_perception_evidence: bool = False
    enriched: bool = False

    def as_output(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in OUTPUT_FIELDS}


def normalize_url(url: str) -> str:
    value = (url or "").strip()
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    if not parsed.netloc and parsed.path:
        value = f"https://{parsed.path}"
    return value.rstrip("/")


def host_for(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    host = (parsed.netloc or parsed.path).lower()
    return host[4:] if host.startswith("www.") else host


def root_domain(host: str) -> str:
    parts = [part for part in (host or "").lower().split(".") if part]
    if len(parts) <= 2:
        return ".".join(parts)
    return ".".join(parts[-2:])


def common_path_candidates(url: str) -> list[str]:
    parsed = urlparse(normalize_url(url))
    if not parsed.netloc:
        return []
    return [f"{parsed.scheme}://{parsed.netloc}{path}" for path in COMMON_PUBLIC_PATHS]


def classify_page(
    brand: str,
    input_url: str,
    candidate_url: str,
    *,
    title_or_snippet: str = "",
) -> tuple[str, str, float]:
    input = normalize_url(input_url)
    candidate = normalize_url(candidate_url)
    input_host = host_for(input)
    candidate_host = host_for(candidate)
    candidate_path = urlparse(candidate).path.lower()
    evidence_text = f"{candidate_host} {candidate_path} {title_or_snippet}".lower()
    brand_lower = (brand or "").lower()

    if candidate.rstrip("/") == input.rstrip("/"):
        return "primary", "primary_domain", 1.0

    page_type = page_type_for(candidate_url, title_or_snippet=title_or_snippet)
    if candidate_host == input_host:
        return page_type if page_type != "primary" else "same_domain_page", "same_domain", 0.95

    if root_domain(candidate_host) == root_domain(input_host):
        return page_type if page_type != "primary" else "same_domain_page", "same_domain", 0.85

    if _is_claude_official_related(brand_lower, candidate_host, evidence_text):
        confidence = 0.9 if "claude" in evidence_text else 0.82
        return page_type if page_type != "primary" else "official_related", "official_related", confidence

    if _is_general_official_related(brand_lower, candidate_host, evidence_text):
        return page_type if page_type != "primary" else "official_related", "official_related", 0.72

    return "third_party", "third_party", 0.2


def page_type_for(candidate_url: str, *, title_or_snippet: str = "") -> str:
    host = host_for(candidate_url)
    path = urlparse(normalize_url(candidate_url)).path.lower()
    text = f"{host} {path} {title_or_snippet}".lower()
    if re.search(r"(^|\.)docs\.|/docs?(/|$)|documentation|developer", text):
        return "docs"
    if re.search(r"(^|\.)support\.|/support(/|$)|/help(/|$)|help center", text):
        return "support"
    if re.search(r"/news(/|$)|/blog(/|$)|press| newsroom | changelog", f" {text} "):
        return "news_or_blog"
    if re.search(r"/trust(/|$)|/security(/|$)|safety|privacy|compliance", text):
        return "trust_or_safety"
    return "primary"


def _is_claude_official_related(brand_lower: str, candidate_host: str, evidence_text: str) -> bool:
    if brand_lower != "claude":
        return False
    official_hosts = {"anthropic.com", "docs.anthropic.com", "support.anthropic.com"}
    if candidate_host not in official_hosts and not candidate_host.endswith(".anthropic.com"):
        return False
    return "claude" in evidence_text or "anthropic" in evidence_text


def _is_general_official_related(brand_lower: str, candidate_host: str, evidence_text: str) -> bool:
    if not brand_lower or len(brand_lower) < 3:
        return False
    compact_brand = re.sub(r"[^a-z0-9]+", "", brand_lower)
    compact_host = re.sub(r"[^a-z0-9]+", "", candidate_host)
    if compact_brand and compact_brand in compact_host and brand_lower in evidence_text:
        return True
    official_terms = (" official ", " homepage ", " docs ", " documentation ", " support ")
    return brand_lower in evidence_text and any(term in f" {evidence_text} " for term in official_terms)


def make_row(
    *,
    brand: str,
    input_url: str,
    candidate_url: str,
    source: str,
    title_or_snippet: str = "",
    collection_method: str = "not_attempted",
    status: str = "",
    error: str = "",
    text_chars: int = 0,
    snippet_is_search_metadata: bool = False,
) -> InventoryRow:
    candidate = normalize_url(candidate_url)
    page_type, relation, confidence = classify_page(
        brand,
        input_url,
        candidate,
        title_or_snippet=title_or_snippet,
    )
    usable_text = int(text_chars or 0) >= 200
    usable_for_brand = relation in {"primary_domain", "same_domain", "official_related"} and usable_text
    if snippet_is_search_metadata and relation == "official_related":
        usable_for_brand = False
    usable_for_perception = relation == "third_party" and bool(title_or_snippet or usable_text)
    return InventoryRow(
        brand=brand,
        input_url=normalize_url(input_url),
        candidate_url=candidate,
        host=host_for(candidate),
        page_type=page_type,
        relation_to_brand=relation,
        confidence=confidence,
        source=source,
        title_or_snippet=(title_or_snippet or "")[:500],
        collection_method=collection_method,
        status=str(status or ""),
        error=str(error or ""),
        text_chars=int(text_chars or 0),
        usable_for_brand_evidence=usable_for_brand,
        usable_for_perception_evidence=usable_for_perception,
    )


def collect_inventory(
    brand: str,
    url: str,
    *,
    max_page_links: int = 20,
    enrich_official: bool = False,
    max_enrich: int = 12,
) -> list[InventoryRow]:
    input_url = normalize_url(url)
    collector = WebCollector(api_key=FIRECRAWL_API_KEY)
    rows: list[InventoryRow] = []

    primary, page_links = _collect_primary(brand, input_url, collector)
    rows.append(primary)

    for candidate_url in common_path_candidates(input_url):
        rows.append(_collect_direct_candidate(brand, input_url, candidate_url, "common_path", collector))

    for link in page_links[:max_page_links]:
        if _is_public_http_url(link):
            rows.append(make_row(
                brand=brand,
                input_url=input_url,
                candidate_url=link,
                source="page_link",
                collection_method="not_attempted",
            ))

    rows.extend(_context_rows(brand, input_url))
    rows.extend(_exa_rows(brand, input_url))
    rows = dedupe_rows(rows)
    if enrich_official:
        enrich_official_rows(rows, collector=collector, max_enrich=max_enrich)
    return rows


def _collect_primary(
    brand: str,
    input_url: str,
    collector: WebCollector,
) -> tuple[InventoryRow, list[str]]:
    try:
        data = collector.scrape(input_url)
        method = _collection_method_from_web_data(data)
        text_chars = len(data.markdown_content or "")
        row = make_row(
            brand=brand,
            input_url=input_url,
            candidate_url=input_url,
            source="input",
            title_or_snippet=data.title or data.meta_description,
            collection_method=method,
            status=str(data.browser_status or ("ok" if _has_usable_web_content(data) else "thin")),
            error=data.error,
            text_chars=text_chars,
        )
        return row, [str(link) for link in (data.links or []) if link]
    except Exception as exc:
        return make_row(
            brand=brand,
            input_url=input_url,
            candidate_url=input_url,
            source="input",
            collection_method="existing_web_collector",
            status="error",
            error=str(exc),
        ), []


def _collect_direct_candidate(
    brand: str,
    input_url: str,
    candidate_url: str,
    source: str,
    collector: WebCollector,
) -> InventoryRow:
    try:
        html, error = collector._fetch_html_fallback(candidate_url)
        content = collector._html_to_markdown_fallback(html)
        title = collector._extract_html_title(html)
        status = "ok" if len(content.strip()) >= 200 else "thin"
        if error:
            status = "error"
        return make_row(
            brand=brand,
            input_url=input_url,
            candidate_url=candidate_url,
            source=source,
            title_or_snippet=title,
            collection_method="direct_html",
            status=status,
            error=error,
            text_chars=len(content),
        )
    except Exception as exc:
        return make_row(
            brand=brand,
            input_url=input_url,
            candidate_url=candidate_url,
            source=source,
            collection_method="direct_html",
            status="error",
            error=str(exc),
        )


def _context_rows(brand: str, input_url: str) -> list[InventoryRow]:
    try:
        data = ContextCollector().scan(input_url)
    except Exception as exc:
        return [make_row(
            brand=brand,
            input_url=input_url,
            candidate_url=input_url,
            source="context",
            collection_method="not_attempted",
            status="error",
            error=str(exc),
        )]

    rows: list[InventoryRow] = []
    if data.llms_txt_found:
        rows.append(make_row(
            brand=brand,
            input_url=input_url,
            candidate_url=f"{input_url}/llms.txt",
            source="context",
            title_or_snippet="llms.txt found",
            collection_method="not_attempted",
            status="found",
        ))
    for name, found in (data.key_pages or {}).items():
        if not found:
            continue
        rows.append(make_row(
            brand=brand,
            input_url=input_url,
            candidate_url=f"{input_url}/{name.replace('_', '-')}",
            source="context",
            title_or_snippet=f"context key page: {name}",
            collection_method="not_attempted",
            status="found",
        ))
    return rows


def _exa_rows(brand: str, input_url: str) -> list[InventoryRow]:
    if not EXA_API_KEY:
        return []
    collector = ExaCollector(api_key=EXA_API_KEY)
    try:
        results = collector.search(
            collector._brand_query(brand, input_url, "official site docs support pricing blog news"),
            num_results=12,
        )
    except Exception as exc:
        return [make_row(
            brand=brand,
            input_url=input_url,
            candidate_url=input_url,
            source="exa",
            collection_method="exa_metadata",
            status="error",
            error=str(exc),
        )]

    rows: list[InventoryRow] = []
    for result in results:
        snippet = result.summary or result.text or " ".join(str(item) for item in (result.highlights or []))
        rows.append(make_row(
            brand=brand,
            input_url=input_url,
            candidate_url=result.url,
            source="exa",
            title_or_snippet=result.title or snippet,
            collection_method="exa_metadata",
            status="ok",
            text_chars=0,
            snippet_is_search_metadata=True,
        ))
    return rows


def _collection_method_from_web_data(data) -> str:
    source = getattr(data, "content_source", "") or ""
    if source == "browser_fallback":
        return "browser_fallback"
    if source == "html_fallback":
        return "direct_html"
    if source:
        return "existing_web_collector"
    return "existing_web_collector"


def enrich_official_rows(
    rows: list[InventoryRow],
    *,
    collector: WebCollector | None = None,
    max_enrich: int = 12,
) -> int:
    if max_enrich <= 0:
        return 0
    collector = collector or WebCollector(api_key=FIRECRAWL_API_KEY)
    enriched = 0
    for row in sorted(_enrichment_candidates(rows), key=_enrichment_priority):
        if enriched >= max_enrich:
            break
        _enrich_row(row, collector)
        enriched += 1
    return enriched


def _enrichment_candidates(rows: list[InventoryRow]) -> list[InventoryRow]:
    return [
        row for row in rows
        if row.relation_to_brand in {"primary_domain", "same_domain", "official_related"}
        and row.page_type in {
            "primary",
            "same_domain_page",
            "official_related",
            "docs",
            "support",
            "news_or_blog",
            "trust_or_safety",
        }
    ]


def _enrichment_priority(row: InventoryRow) -> tuple[int, str]:
    if row.page_type == "primary":
        priority = 0
    elif row.page_type == "official_related":
        priority = 1
    elif row.page_type == "docs":
        priority = 2
    elif row.page_type == "support":
        priority = 3
    elif row.page_type == "news_or_blog":
        priority = 4
    elif row.page_type == "trust_or_safety":
        priority = 5
    else:
        priority = 6
    return priority, row.candidate_url


def _enrich_row(row: InventoryRow, collector: WebCollector) -> None:
    try:
        data = collector.scrape(row.candidate_url)
        row.collection_method = _collection_method_from_web_data(data)
        row.status = str(data.browser_status or ("ok" if _has_usable_web_content(data) else "thin"))
        row.error = data.error or ""
        row.text_chars = len(data.markdown_content or "")
        if data.title or data.meta_description:
            row.title_or_snippet = (data.title or data.meta_description)[:500]
        row.usable_for_brand_evidence = (
            row.relation_to_brand in {"primary_domain", "same_domain", "official_related"}
            and row.text_chars >= 200
        )
        row.usable_for_perception_evidence = row.relation_to_brand == "third_party" and bool(
            row.title_or_snippet or row.text_chars
        )
        row.enriched = True
    except Exception as exc:
        row.collection_method = "existing_web_collector"
        row.status = "error"
        row.error = str(exc)
        row.text_chars = 0
        row.usable_for_brand_evidence = False
        row.enriched = True


def dedupe_rows(rows: list[InventoryRow]) -> list[InventoryRow]:
    merged: dict[str, InventoryRow] = {}
    order: list[str] = []
    for row in rows:
        key = normalize_url(row.candidate_url)
        if key not in merged:
            merged[key] = row
            order.append(key)
            continue
        current = merged[key]
        current.source = _merge_token(current.source, row.source)
        if not current.title_or_snippet and row.title_or_snippet:
            current.title_or_snippet = row.title_or_snippet
        if current.collection_method == "not_attempted" and row.collection_method != "not_attempted":
            current.collection_method = row.collection_method
            current.status = row.status
            current.error = row.error
            current.text_chars = row.text_chars
        current.usable_for_brand_evidence = current.usable_for_brand_evidence or row.usable_for_brand_evidence
        current.usable_for_perception_evidence = (
            current.usable_for_perception_evidence or row.usable_for_perception_evidence
        )
        current.confidence = max(current.confidence, row.confidence)
    return [merged[key] for key in order]


def _merge_token(left: str, right: str) -> str:
    tokens = []
    for value in (left, right):
        for token in (value or "").split("+"):
            if token and token not in tokens:
                tokens.append(token)
    return "+".join(tokens)


def _is_public_http_url(url: str) -> bool:
    parsed = urlparse(normalize_url(url))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return not re.search(r"\.(css|js|png|jpg|jpeg|gif|svg|ico|pdf|zip)$", parsed.path, re.I)


def summarize_inventory(rows: list[InventoryRow]) -> dict[str, object]:
    owned_or_official = [
        row for row in rows
        if row.relation_to_brand in {"primary_domain", "same_domain", "official_related"}
    ]
    enriched = [row for row in rows if row.enriched]
    usable_brand = [row for row in rows if row.usable_for_brand_evidence]
    usable_perception = [row for row in rows if row.usable_for_perception_evidence]
    has_primary_base = any(
        row.page_type == "primary" and row.usable_for_brand_evidence and row.text_chars >= 1500
        for row in rows
    )
    recommended = len(usable_brand) >= 2 or has_primary_base
    return {
        "total_candidates": len(rows),
        "owned_or_official_candidates": len(owned_or_official),
        "enriched_candidates": len(enriched),
        "usable_brand_evidence_pages": len(usable_brand),
        "usable_perception_evidence_pages": len(usable_perception),
        "recommended_brand_evidence_base": bool(recommended),
    }


def summarize_brand(rows: list[InventoryRow], *, brand: str, input_url: str) -> dict[str, object]:
    primary = next((row for row in rows if row.page_type == "primary"), None)
    official_rows = [
        row for row in rows
        if row.relation_to_brand in {"primary_domain", "same_domain", "official_related"}
    ]
    official_read = [
        row for row in official_rows
        if row.collection_method not in {"not_attempted", "exa_metadata"}
    ]
    usable_brand = [row for row in rows if row.usable_for_brand_evidence]
    usable_perception = [row for row in rows if row.usable_for_perception_evidence]
    summary = {
        "brand": brand,
        "input_url": normalize_url(input_url),
        "total_public_pages_found": len(rows),
        "official_pages_found": len(official_rows),
        "official_pages_read": len(official_read),
        "usable_brand_evidence_pages": len(usable_brand),
        "usable_public_perception_pages": len(usable_perception),
        "primary_page_read_method": primary.collection_method if primary else "",
        "primary_page_text_chars": int(primary.text_chars if primary else 0),
        "official_related_usable_count": sum(
            1 for row in rows
            if row.relation_to_brand == "official_related" and row.usable_for_brand_evidence
        ),
        "docs_usable_count": sum(1 for row in rows if row.page_type == "docs" and row.usable_for_brand_evidence),
        "news_or_blog_usable_count": sum(
            1 for row in rows if row.page_type == "news_or_blog" and row.usable_for_brand_evidence
        ),
        "support_usable_count": sum(1 for row in rows if row.page_type == "support" and row.usable_for_brand_evidence),
    }
    summary["recommended_evidence_base"] = _recommended_evidence_base(rows)
    summary["recommended_analysis_mode"] = recommended_analysis_mode(rows)
    return summary


def _recommended_evidence_base(rows: list[InventoryRow]) -> bool:
    usable_brand = [row for row in rows if row.usable_for_brand_evidence]
    has_primary_base = any(
        row.page_type == "primary" and row.usable_for_brand_evidence and row.text_chars >= 1500
        for row in rows
    )
    return len(usable_brand) >= 2 or has_primary_base


def recommended_analysis_mode(rows: list[InventoryRow]) -> str:
    primary = next((row for row in rows if row.page_type == "primary"), None)
    primary_usable = bool(primary and primary.usable_for_brand_evidence)
    primary_chars = int(primary.text_chars if primary else 0)
    usable_brand = [row for row in rows if row.usable_for_brand_evidence]
    usable_non_primary = [row for row in usable_brand if row.page_type != "primary"]
    related_usable = [
        row for row in usable_brand
        if row.relation_to_brand == "official_related"
    ]
    usable_perception = [row for row in rows if row.usable_for_perception_evidence]

    if primary_usable:
        if len(usable_non_primary) >= 2:
            return "official_pages_bundle"
        return "primary_page_only"
    if related_usable:
        return "related_official_pages_bundle"
    if usable_perception:
        return "public_perception_only"
    if primary and primary_chars >= 1500:
        return "primary_page_only"
    return "not_enough_evidence"


def format_summary(summary: dict[str, object]) -> str:
    lines = ["summary"]
    for key, value in summary.items():
        lines.append(f"{key}\t{_format_value(value)}")
    return "\n".join(lines)


def format_table(rows: list[InventoryRow]) -> str:
    widths = {field: len(field) for field in OUTPUT_FIELDS}
    rendered: list[dict[str, str]] = []
    for row in rows:
        item = {field: _format_value(row.as_output()[field]) for field in OUTPUT_FIELDS}
        rendered.append(item)
        for field, value in item.items():
            widths[field] = min(max(widths[field], len(value)), 38)

    def clip(field: str, value: str) -> str:
        width = widths[field]
        return value if len(value) <= width else value[: width - 1] + "…"

    header = "  ".join(field.ljust(widths[field]) for field in OUTPUT_FIELDS)
    rule = "  ".join("-" * widths[field] for field in OUTPUT_FIELDS)
    body = [
        "  ".join(clip(field, item[field]).ljust(widths[field]) for field in OUTPUT_FIELDS)
        for item in rendered
    ]
    return "\n".join([header, rule, *body])


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.2f}"
    return "" if value is None else str(value)


def write_outputs(
    rows: list[InventoryRow],
    *,
    json_out: Path | None,
    tsv_out: Path | None,
    summary: dict[str, object] | None = None,
) -> None:
    summary = summary or summarize_inventory(rows)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(
            json.dumps(
                {
                    "summary": summary,
                    "rows": [row.as_output() for row in rows],
                },
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
    if tsv_out:
        tsv_out.parent.mkdir(parents=True, exist_ok=True)
        with tsv_out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS, delimiter="\t")
            writer.writeheader()
            for row in rows:
                writer.writerow(row.as_output())
            fh.write("\n")
            fh.write("summary_key\tsummary_value\n")
            for key, value in summary.items():
                fh.write(f"{key}\t{_format_value(value)}\n")


def load_targets(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("benchmark targets must be a JSON list")
    targets: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        brand = str(item.get("brand") or "").strip()
        url = str(item.get("url") or item.get("input_url") or "").strip()
        if not url:
            continue
        targets.append({"brand": brand or host_for(url), "url": normalize_url(url)})
    return targets


def run_benchmark(
    targets: list[dict[str, str]],
    *,
    include_official_pages: bool = False,
    max_pages_per_brand: int = 12,
) -> dict[str, object]:
    all_rows: list[InventoryRow] = []
    summaries: list[dict[str, object]] = []
    for target in targets:
        brand = target["brand"]
        url = normalize_url(target["url"])
        rows = collect_inventory(
            brand,
            url,
            enrich_official=include_official_pages,
            max_enrich=max_pages_per_brand,
        )
        all_rows.extend(rows)
        summaries.append(summarize_brand(rows, brand=brand, input_url=url))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brand_count": len(targets),
        "rows": [row.as_output() for row in all_rows],
        "summary_by_brand": summaries,
    }


def write_benchmark_outputs(result: dict[str, object], *, json_out: Path | None, tsv_out: Path | None) -> None:
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if tsv_out:
        tsv_out.parent.mkdir(parents=True, exist_ok=True)
        with tsv_out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=BENCHMARK_SUMMARY_FIELDS, delimiter="\t")
            writer.writeheader()
            for row in result.get("summary_by_brand", []):
                writer.writerow({field: row.get(field, "") for field in BENCHMARK_SUMMARY_FIELDS})


def format_benchmark_table(summary_rows: list[dict[str, object]]) -> str:
    widths = {field: len(field) for field in BENCHMARK_SUMMARY_FIELDS}
    rendered: list[dict[str, str]] = []
    for row in summary_rows:
        item = {field: _format_value(row.get(field, "")) for field in BENCHMARK_SUMMARY_FIELDS}
        rendered.append(item)
        for field, value in item.items():
            widths[field] = min(max(widths[field], len(value)), 34)

    def clip(field: str, value: str) -> str:
        width = widths[field]
        return value if len(value) <= width else value[: width - 1] + "…"

    header = "  ".join(field.ljust(widths[field]) for field in BENCHMARK_SUMMARY_FIELDS)
    rule = "  ".join("-" * widths[field] for field in BENCHMARK_SUMMARY_FIELDS)
    body = [
        "  ".join(clip(field, item[field]).ljust(widths[field]) for field in BENCHMARK_SUMMARY_FIELDS)
        for item in rendered
    ]
    return "\n".join([header, rule, *body])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Experimental Brand3 online presence inventory")
    sub = parser.add_subparsers(dest="command")

    benchmark = sub.add_parser("benchmark", help="Run inventory for multiple brands from JSON")
    benchmark.add_argument("targets")
    benchmark.add_argument("--include-official-pages", action="store_true")
    benchmark.add_argument("--enrich-official", action="store_true")
    benchmark.add_argument("--max-pages-per-brand", type=int, default=12)
    benchmark.add_argument("--max-enrich", type=int, default=None)
    benchmark.add_argument("--json-out", default="")
    benchmark.add_argument("--tsv-out", default="")
    return parser


def build_single_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Experimental Brand3 online presence inventory")
    parser.add_argument("url", nargs="?")
    parser.add_argument("--brand")
    parser.add_argument("--include-official-pages", action="store_true")
    parser.add_argument("--enrich-official", action="store_true")
    parser.add_argument("--max-pages-per-brand", type=int, default=12)
    parser.add_argument("--max-enrich", type=int, default=None)
    parser.add_argument("--json-out", default="")
    parser.add_argument("--tsv-out", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "benchmark":
        parser = build_parser()
        args = parser.parse_args(argv)
        max_pages = args.max_enrich if args.max_enrich is not None else args.max_pages_per_brand
        result = run_benchmark(
            load_targets(Path(args.targets)),
            include_official_pages=args.include_official_pages or args.enrich_official,
            max_pages_per_brand=max_pages,
        )
        write_benchmark_outputs(
            result,
            json_out=Path(args.json_out) if args.json_out else None,
            tsv_out=Path(args.tsv_out) if args.tsv_out else None,
        )
        print(format_benchmark_table(result["summary_by_brand"]))
        return 0

    parser = build_single_parser()
    args = parser.parse_args(argv)
    if not args.url or not args.brand:
        parser.error("single-brand mode requires URL and --brand")
    max_enrich = args.max_enrich if args.max_enrich is not None else args.max_pages_per_brand
    rows = collect_inventory(
        args.brand,
        args.url,
        enrich_official=args.enrich_official or args.include_official_pages,
        max_enrich=max_enrich,
    )
    summary = summarize_inventory(rows)
    write_outputs(
        rows,
        json_out=Path(args.json_out) if args.json_out else None,
        tsv_out=Path(args.tsv_out) if args.tsv_out else None,
        summary=summary,
    )
    print(format_table(rows))
    print()
    print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
