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

    def as_output(self) -> dict[str, object]:
        return asdict(self)


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


def collect_inventory(brand: str, url: str, *, max_page_links: int = 20) -> list[InventoryRow]:
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
    return dedupe_rows(rows)


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


def write_outputs(rows: list[InventoryRow], *, json_out: Path | None, tsv_out: Path | None) -> None:
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(
            json.dumps([row.as_output() for row in rows], indent=2) + "\n",
            encoding="utf-8",
        )
    if tsv_out:
        tsv_out.parent.mkdir(parents=True, exist_ok=True)
        with tsv_out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS, delimiter="\t")
            writer.writeheader()
            for row in rows:
                writer.writerow(row.as_output())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Experimental Brand3 online presence inventory")
    parser.add_argument("url")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--json-out", default="")
    parser.add_argument("--tsv-out", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    rows = collect_inventory(args.brand, args.url)
    write_outputs(
        rows,
        json_out=Path(args.json_out) if args.json_out else None,
        tsv_out=Path(args.tsv_out) if args.tsv_out else None,
    )
    print(format_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
