"""Experimental capture benchmarking for Brand3.

This module is intentionally outside the production analysis path. It compares
capture methods so we can decide whether a target has enough owned evidence
before scoring.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.context_collector import ContextCollector
from src.collectors.exa_collector import ExaCollector
from src.collectors.web_collector import WebCollector
from src.config import EXA_API_KEY, FIRECRAWL_API_KEY
from src.services.brand_service import _has_usable_web_content


OUTPUT_FIELDS = (
    "brand",
    "input_url",
    "candidate_url",
    "method",
    "status",
    "error",
    "text_chars",
    "html_chars",
    "usable",
    "title",
    "surface_type",
    "ownership_confidence",
    "capture_confidence",
)

SAME_DOMAIN_PATHS = (
    "/about",
    "/pricing",
    "/docs",
    "/blog",
    "/news",
    "/help",
    "/support",
    "/trust",
    "/security",
)


@dataclass
class CaptureRow:
    brand: str
    input_url: str
    candidate_url: str
    method: str
    status: str = ""
    error: str = ""
    text_chars: int = 0
    html_chars: int = 0
    usable: bool = False
    title: str = ""
    surface_type: str = "primary"
    ownership_confidence: float = 0.0
    capture_confidence: float = 0.0

    def as_output(self) -> dict[str, object]:
        return asdict(self)


def normalize_url(url: str) -> str:
    value = (url or "").strip()
    if "://" not in value:
        value = f"https://{value}"
    return value.rstrip("/")


def host_for(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    host = (parsed.netloc or parsed.path).lower()
    return host[4:] if host.startswith("www.") else host


def same_domain_candidates(url: str) -> list[str]:
    parsed = urlparse(normalize_url(url))
    if not parsed.netloc:
        return []
    return [f"{parsed.scheme}://{parsed.netloc}{path}" for path in SAME_DOMAIN_PATHS]


def classify_surface(input_url: str, candidate_url: str) -> tuple[str, float]:
    input_host = host_for(input_url)
    candidate_host = host_for(candidate_url)
    if not candidate_host:
        return "third_party_candidate", 0.0
    if candidate_host == input_host:
        normalized_input = normalize_url(input_url).rstrip("/")
        normalized_candidate = normalize_url(candidate_url).rstrip("/")
        if normalized_candidate == normalized_input:
            return "primary", 1.0
        return "same_domain_candidate", 0.95
    if candidate_host.endswith(f".{input_host}") or input_host.endswith(f".{candidate_host}"):
        return "official_related_candidate", 0.75
    return "third_party_candidate", 0.2


def capture_confidence(*, usable: bool, text_chars: int, error: str = "") -> float:
    if error and not usable:
        return 0.0
    if not usable:
        return 0.2 if text_chars else 0.0
    if text_chars >= 2000:
        return 0.95
    if text_chars >= 800:
        return 0.8
    if text_chars >= 200:
        return 0.6
    return 0.3


def _row(
    *,
    brand: str,
    input_url: str,
    candidate_url: str,
    method: str,
    status: str = "",
    error: str = "",
    text_chars: int = 0,
    html_chars: int = 0,
    usable: bool = False,
    title: str = "",
) -> CaptureRow:
    surface_type, ownership_confidence = classify_surface(input_url, candidate_url)
    return CaptureRow(
        brand=brand,
        input_url=input_url,
        candidate_url=candidate_url,
        method=method,
        status=str(status or ""),
        error=str(error or ""),
        text_chars=int(text_chars or 0),
        html_chars=int(html_chars or 0),
        usable=bool(usable),
        title=title or "",
        surface_type=surface_type,
        ownership_confidence=ownership_confidence,
        capture_confidence=capture_confidence(
            usable=bool(usable),
            text_chars=int(text_chars or 0),
            error=str(error or ""),
        ),
    )


def probe_target(brand: str, url: str, *, include_candidates: bool = True) -> list[CaptureRow]:
    input_url = normalize_url(url)
    collector = WebCollector(api_key=FIRECRAWL_API_KEY)
    rows: list[CaptureRow] = []

    rows.append(_probe_firecrawl(brand, input_url, input_url, collector))
    rows.append(_probe_direct_html(brand, input_url, input_url, collector))
    rows.append(_probe_browser(brand, input_url, input_url, collector))
    rows.extend(_probe_context(brand, input_url))
    rows.extend(_probe_exa(brand, input_url))

    if include_candidates:
        for candidate_url in same_domain_candidates(input_url):
            rows.append(_probe_direct_html(brand, input_url, candidate_url, collector))
            rows.append(_probe_browser(brand, input_url, candidate_url, collector))

    return rows


def _probe_firecrawl(
    brand: str,
    input_url: str,
    candidate_url: str,
    collector: WebCollector,
) -> CaptureRow:
    if not FIRECRAWL_API_KEY:
        return _row(
            brand=brand,
            input_url=input_url,
            candidate_url=candidate_url,
            method="firecrawl",
            status="skipped",
            error="FIRECRAWL_API_KEY not set",
        )
    try:
        result = collector._run_firecrawl(candidate_url)
        raw = result.get("content", "") if result else ""
        content = collector._clean_markdown_content(raw)
        usable = len(content.strip()) >= 200
        return _row(
            brand=brand,
            input_url=input_url,
            candidate_url=candidate_url,
            method="firecrawl",
            status="ok" if usable else "thin",
            error=result.get("error", "") if result else "",
            text_chars=len(content),
            usable=usable,
            title=collector._extract_title(content),
        )
    except Exception as exc:
        return _row(
            brand=brand,
            input_url=input_url,
            candidate_url=candidate_url,
            method="firecrawl",
            status="error",
            error=str(exc),
        )


def _probe_direct_html(
    brand: str,
    input_url: str,
    candidate_url: str,
    collector: WebCollector,
) -> CaptureRow:
    try:
        html, error = collector._fetch_html_fallback(candidate_url)
        content = collector._html_to_markdown_fallback(html)
        usable = len(content.strip()) >= 200
        return _row(
            brand=brand,
            input_url=input_url,
            candidate_url=candidate_url,
            method="direct_html",
            status="ok" if usable else "thin",
            error=error,
            text_chars=len(content),
            html_chars=len(html or ""),
            usable=usable,
            title=collector._extract_html_title(html),
        )
    except Exception as exc:
        return _row(
            brand=brand,
            input_url=input_url,
            candidate_url=candidate_url,
            method="direct_html",
            status="error",
            error=str(exc),
        )


def _probe_browser(
    brand: str,
    input_url: str,
    candidate_url: str,
    collector: WebCollector,
) -> CaptureRow:
    try:
        payload, error = collector._fetch_browser_fallback(candidate_url)
        content = collector._body_text_to_markdown(
            payload.get("body_text", "") if payload else "",
            title=payload.get("title", "") if payload else "",
            meta_description=payload.get("meta_description", "") if payload else "",
        )
        usable = len(content.strip()) >= 200
        return _row(
            brand=brand,
            input_url=input_url,
            candidate_url=candidate_url,
            method="browser_playwright",
            status=payload.get("status", "ok" if usable else "thin") if payload else "error",
            error=error,
            text_chars=len(content),
            html_chars=len(payload.get("html", "") if payload else ""),
            usable=usable,
            title=payload.get("title", "") if payload else "",
        )
    except Exception as exc:
        return _row(
            brand=brand,
            input_url=input_url,
            candidate_url=candidate_url,
            method="browser_playwright",
            status="error",
            error=str(exc),
        )


def _probe_context(brand: str, input_url: str) -> list[CaptureRow]:
    try:
        data = ContextCollector().scan(input_url)
    except Exception as exc:
        return [_row(
            brand=brand,
            input_url=input_url,
            candidate_url=input_url,
            method="context_scan",
            status="error",
            error=str(exc),
        )]

    rows = [
        _row(
            brand=brand,
            input_url=input_url,
            candidate_url=input_url,
            method="context_scan",
            status=data.homepage_status or "",
            error=data.error,
            text_chars=data.avg_words,
            usable=data.coverage >= 0.3,
            title=f"coverage={data.coverage:.2f} confidence={data.confidence:.2f}",
        )
    ]
    base = normalize_url(input_url)
    for name, found in (data.key_pages or {}).items():
        candidate_url = f"{base}/{name.replace('_', '-')}"
        rows.append(_row(
            brand=brand,
            input_url=input_url,
            candidate_url=candidate_url,
            method="context_key_page",
            status="found" if found else "missing",
            usable=bool(found),
            title=name,
        ))
    return rows


def _probe_exa(brand: str, input_url: str) -> list[CaptureRow]:
    if not EXA_API_KEY:
        return [_row(
            brand=brand,
            input_url=input_url,
            candidate_url=input_url,
            method="exa",
            status="skipped",
            error="EXA_API_KEY not set",
        )]

    collector = ExaCollector(api_key=EXA_API_KEY)
    try:
        results = collector.search(
            collector._brand_query(brand, input_url, "brand official site docs pricing"),
            num_results=8,
        )
    except Exception as exc:
        return [_row(
            brand=brand,
            input_url=input_url,
            candidate_url=input_url,
            method="exa",
            status="error",
            error=str(exc),
        )]

    rows: list[CaptureRow] = []
    for result in results:
        text = result.text or result.summary or " ".join(str(x) for x in result.highlights or [])
        rows.append(_row(
            brand=brand,
            input_url=input_url,
            candidate_url=result.url,
            method="exa",
            status="ok",
            text_chars=len(text or ""),
            usable=bool(result.url),
            title=result.title,
        ))
    return rows or [_row(
        brand=brand,
        input_url=input_url,
        candidate_url=input_url,
        method="exa",
        status="empty",
    )]


def should_score(rows: list[CaptureRow]) -> bool:
    owned_rows = [
        row for row in rows
        if row.usable and row.ownership_confidence >= 0.75 and row.capture_confidence >= 0.6
    ]
    return bool(owned_rows)


def format_table(rows: list[CaptureRow]) -> str:
    widths = {field: len(field) for field in OUTPUT_FIELDS}
    values = []
    for row in rows:
        out = row.as_output()
        item = {field: _format_value(out[field]) for field in OUTPUT_FIELDS}
        values.append(item)
        for field, value in item.items():
            widths[field] = min(max(widths[field], len(value)), 42)

    def clip(field: str, value: str) -> str:
        width = widths[field]
        return value if len(value) <= width else value[: width - 1] + "…"

    header = "  ".join(field.ljust(widths[field]) for field in OUTPUT_FIELDS)
    rule = "  ".join("-" * widths[field] for field in OUTPUT_FIELDS)
    body = [
        "  ".join(clip(field, item[field]).ljust(widths[field]) for field in OUTPUT_FIELDS)
        for item in values
    ]
    return "\n".join([header, rule, *body])


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.2f}"
    return "" if value is None else str(value)


def load_targets(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        try:
            import yaml
        except Exception as exc:
            raise SystemExit(f"YAML input requires PyYAML: {exc}") from exc
        payload = yaml.safe_load(text)

    if isinstance(payload, dict):
        payload = payload.get("targets") or []
    targets = []
    for item in payload:
        if isinstance(item, str):
            targets.append({"brand": host_for(item), "url": item})
        elif isinstance(item, dict):
            url = item.get("url") or item.get("input_url")
            if not url:
                continue
            targets.append({"brand": item.get("brand") or host_for(url), "url": url})
    return targets


def write_outputs(rows: list[CaptureRow], *, json_out: Path | None, tsv_out: Path | None) -> None:
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


def cmd_capture_probe(args: argparse.Namespace) -> int:
    rows = probe_target(args.brand or host_for(args.url), args.url, include_candidates=not args.no_candidates)
    print(format_table(rows))
    print()
    print(f"recommendation\t{'score_candidate' if should_score(rows) else 'do_not_score'}")
    return 0


def cmd_capture_benchmark(args: argparse.Namespace) -> int:
    targets = load_targets(Path(args.targets))
    rows: list[CaptureRow] = []
    for target in targets:
        rows.extend(probe_target(target["brand"], target["url"], include_candidates=not args.no_candidates))
    write_outputs(rows, json_out=Path(args.json_out) if args.json_out else None, tsv_out=Path(args.tsv_out) if args.tsv_out else None)
    print(format_table(rows))
    print()
    print(f"targets\t{len(targets)}")
    print(f"rows\t{len(rows)}")
    print(f"score_candidates\t{sum(1 for target in targets if should_score([row for row in rows if row.input_url == normalize_url(target['url'])]))}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Experimental Brand3 capture benchmarking")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("capture-probe", help="Probe capture methods for one target")
    p.add_argument("url")
    p.add_argument("--brand", default="")
    p.add_argument("--no-candidates", action="store_true")
    p.set_defaults(func=cmd_capture_probe)

    p = sub.add_parser("capture-benchmark", help="Run capture probes for JSON/YAML targets")
    p.add_argument("targets")
    p.add_argument("--json-out", default="")
    p.add_argument("--tsv-out", default="")
    p.add_argument("--no-candidates", action="store_true")
    p.set_defaults(func=cmd_capture_benchmark)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
