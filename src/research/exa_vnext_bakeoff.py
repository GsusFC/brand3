from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.collectors.exa_collector import ExaCollector, ExaResult
from src.research.evidence_vnext import compare_legacy_current_and_vnext_from_snapshot
from src.research.evidence_vnext_report import build_batch_report, render_batch_report_markdown


EXA_VNEXT_BAKEOFF_VERSION = "exa_vnext_bakeoff_v0_1"


@dataclass(frozen=True)
class ExaBakeoffCase:
    brand: str
    url: str

    @property
    def domain(self) -> str:
        return _domain(self.url)

    @property
    def label(self) -> str:
        return _slugify(self.brand or self.domain)

    def to_dict(self) -> dict[str, str]:
        return {"brand": self.brand, "url": self.url, "domain": self.domain, "label": self.label}


@dataclass(frozen=True)
class ExaSearchRequest:
    key: str
    intent: str
    query: str
    collection: str
    num_results: int = 5
    params: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "intent": self.intent,
            "query": self.query,
            "collection": self.collection,
            "num_results": self.num_results,
            "params": dict(self.params or {}),
        }


def current_exa_plan(case: ExaBakeoffCase, *, results_per_request: int = 5) -> list[ExaSearchRequest]:
    """Mirror the current production Exa collector acquisition."""

    brand_query = _brand_query(case.brand, case.url)
    domain = case.domain
    requests = [
        ExaSearchRequest(
            "owned_confirmation",
            "owned_confirmation",
            f"{brand_query} official website product company about",
            "mentions",
            results_per_request,
            {"include_domains": [domain]} if domain else {},
        ),
        ExaSearchRequest(
            "external_mentions",
            "external_mentions",
            f"{brand_query} review case study customer integration",
            "mentions",
            results_per_request,
            {"exclude_domains": [domain]} if domain else {},
        ),
        ExaSearchRequest(
            "news",
            "news",
            f"{brand_query} announcement launch funding partnership product",
            "news",
            results_per_request,
        ),
        ExaSearchRequest(
            "ai_visibility",
            "ai_visibility",
            f"{brand_query} AI recommendation alternatives best tools",
            "ai_visibility_results",
            results_per_request,
        ),
    ]
    if domain:
        requests.append(
            ExaSearchRequest(
                "competitors",
                "competitors",
                f"alternatives competitors similar to {case.brand} {domain} category",
                "competitors",
                results_per_request,
                {"exclude_domains": [domain]},
            )
        )
    return requests


def vnext_exa_plan(case: ExaBakeoffCase, *, results_per_request: int = 5) -> list[ExaSearchRequest]:
    """A more typed Exa plan intended to reduce empty/context-poor results."""

    brand = case.brand.strip()
    domain = case.domain
    anchored = _brand_query(brand, case.url)
    requests = [
        ExaSearchRequest(
            "owned_confirmation",
            "mentions",
            f'{anchored} official website product company about',
            "mentions",
            results_per_request,
            {"include_domains": [domain]} if domain else {},
        ),
        ExaSearchRequest(
            "external_profile",
            "mentions",
            f'{anchored} company profile customers product',
            "mentions",
            results_per_request,
            {"category": "company"},
        ),
        ExaSearchRequest(
            "press_context",
            "news",
            f'{anchored} announcement launch funding partnership product',
            "news",
            results_per_request,
        ),
        ExaSearchRequest(
            "external_mentions",
            "mentions",
            f'{anchored} review case study customer integration',
            "mentions",
            results_per_request,
            {"exclude_domains": [domain]} if domain else {},
        ),
        ExaSearchRequest(
            "ai_visibility",
            "ai_visibility",
            f'{anchored} AI recommendation alternatives best tools',
            "ai_visibility_results",
            results_per_request,
        ),
    ]
    if domain:
        requests.append(
            ExaSearchRequest(
                "competitors",
                "competitors",
                f"alternatives competitors similar to {brand} {domain} category",
                "competitors",
                results_per_request,
                {"exclude_domains": [domain]},
            )
        )
    return requests


def vnext_precision_exa_plan(case: ExaBakeoffCase, *, results_per_request: int = 5) -> list[ExaSearchRequest]:
    """A stricter plan for measuring whether better Exa acquisition improves acceptance rate."""

    anchored = _brand_query(case.brand, case.url)
    domain = case.domain
    requests = [
        ExaSearchRequest(
            "owned_confirmation",
            "mentions",
            f"{anchored} official website product company about",
            "mentions",
            results_per_request,
            {"include_domains": [domain]} if domain else {},
        ),
        ExaSearchRequest(
            "exact_external_mentions",
            "mentions",
            f"{anchored} review case study customer integration",
            "mentions",
            results_per_request,
            {"exclude_domains": [domain]} if domain else {},
        ),
        ExaSearchRequest(
            "exact_press_context",
            "news",
            f"{anchored} announcement launch funding partnership product",
            "news",
            results_per_request,
        ),
        ExaSearchRequest(
            "exact_ai_visibility",
            "ai_visibility",
            f"{anchored} AI recommendation alternatives best tools",
            "ai_visibility_results",
            results_per_request,
        ),
    ]
    return requests


def run_exa_vnext_bakeoff(
    cases: list[ExaBakeoffCase],
    *,
    collector: ExaCollector,
    results_per_request: int = 5,
    dry_plan: bool = False,
) -> dict[str, Any]:
    payloads = [
        run_exa_vnext_case(
            case,
            collector=collector,
            results_per_request=results_per_request,
            dry_plan=dry_plan,
        )
        for case in cases
    ]
    return {
        "version": EXA_VNEXT_BAKEOFF_VERSION,
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "dry_plan": dry_plan,
        "case_count": len(payloads),
        "cases": payloads,
        "summary": summarize_exa_vnext_bakeoff(payloads),
    }


def run_exa_vnext_case(
    case: ExaBakeoffCase,
    *,
    collector: ExaCollector,
    results_per_request: int = 5,
    dry_plan: bool = False,
) -> dict[str, Any]:
    variants = {
        "current": current_exa_plan(case, results_per_request=results_per_request),
        "vnext_query_plan": vnext_exa_plan(case, results_per_request=results_per_request),
        "vnext_precision_plan": vnext_precision_exa_plan(case, results_per_request=results_per_request),
    }
    outputs = {
        name: run_exa_variant(
            case,
            name,
            requests,
            collector=collector,
            dry_plan=dry_plan,
        )
        for name, requests in variants.items()
    }
    return {"case": case.to_dict(), "variants": outputs}


def run_exa_variant(
    case: ExaBakeoffCase,
    variant: str,
    requests: list[ExaSearchRequest],
    *,
    collector: ExaCollector,
    dry_plan: bool = False,
) -> dict[str, Any]:
    if dry_plan:
        return {
            "variant": variant,
            "status": "dry_plan",
            "requests": [request.to_dict() for request in requests],
            "results": [],
            "report": _empty_report(),
        }
    started = time.perf_counter()
    request_payloads = []
    rows: list[dict[str, Any]] = []
    for request in requests:
        request_started = time.perf_counter()
        try:
            results = collector.search(
                request.query,
                num_results=request.num_results,
                intent=request.intent,
                brand_name=case.brand,
                brand_url=case.url,
                **dict(request.params or {}),
            )
            status = "ok"
            error = ""
        except Exception as exc:
            results = []
            status = "error"
            error = str(exc)
        request_rows = [_result_row(result, request=request) for result in results]
        rows.extend(request_rows)
        request_payloads.append(
            {
                **request.to_dict(),
                "status": status,
                "error": error,
                "elapsed_ms": _elapsed_ms(request_started),
                "result_count": len(request_rows),
            }
        )
    snapshot = exa_results_to_synthetic_snapshot(case, variant=variant, rows=rows)
    comparison = compare_legacy_current_and_vnext_from_snapshot(snapshot)
    report = build_batch_report([comparison], db_path="synthetic://exa_vnext_bakeoff")
    return {
        "variant": variant,
        "status": "ok",
        "elapsed_ms": _elapsed_ms(started),
        "requests": request_payloads,
        "result_count": len(rows),
        "unique_domains": sorted({_domain(row.get("url", "")) for row in rows if row.get("url")}),
        "results": rows,
        "vnext": comparison,
        "report": report,
    }


def exa_results_to_synthetic_snapshot(
    case: ExaBakeoffCase,
    *,
    variant: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    collections = {
        "mentions": [],
        "news": [],
        "ai_visibility_results": [],
        "competitors": [],
    }
    features = []
    for index, row in enumerate(rows, start=1):
        collection = str(row.get("collection") or "mentions")
        if collection not in collections:
            collection = "mentions"
        collections[collection].append(_raw_exa_entry(row))
        dimension, feature_name = _feature_for_row(row)
        features.append(
            {
                "dimension_name": dimension,
                "feature_name": feature_name,
                "value": 0.5,
                "raw_value": {
                    "evidence": [
                        {
                            "quote": row.get("evidence_text") or "",
                            "source_url": row.get("url") or "",
                            "title": row.get("title") or "",
                        }
                    ]
                },
                "confidence": 0.7,
                "source": "exa",
            }
        )
    return {
        "run": {
            "id": _synthetic_run_id(case, variant),
            "brand_name": case.brand,
            "url": case.url,
        },
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": case.url,
                    "title": case.brand,
                    "markdown_content": f"# {case.brand}\nSynthetic Exa bakeoff seed for {case.domain}.",
                },
            },
            {
                "source": "exa",
                "payload": collections,
            },
        ],
        "features": features,
        "evidence_items": [],
    }


def summarize_exa_vnext_bakeoff(case_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    totals: dict[str, dict[str, int]] = {}
    for payload in case_payloads:
        case = payload.get("case") or {}
        for variant, output in (payload.get("variants") or {}).items():
            report = output.get("report") if isinstance(output.get("report"), dict) else {}
            provider = _exa_provider_row(report)
            exclusions = report.get("acquisition_contract_exclusions") or {}
            total = int(provider.get("total") or 0)
            accepted = int(provider.get("accepted") or 0)
            review = int(provider.get("review_required") or 0)
            rejected = int(provider.get("rejected") or 0)
            shadow_empty = int(exclusions.get("total") or 0)
            row = {
                "brand": case.get("brand") or "",
                "domain": case.get("domain") or "",
                "variant": variant,
                "status": output.get("status") or "unknown",
                "result_count": int(output.get("result_count") or 0),
                "accepted": accepted,
                "review_required": review,
                "rejected": rejected,
                "total": total,
                "accepted_rate": _rate(accepted, total),
                "review_rate": _rate(review, total),
                "rejected_rate": _rate(rejected, total),
                "shadow_empty_exclusion_count": shadow_empty,
            }
            rows.append(row)
            bucket = totals.setdefault(
                variant,
                {
                    "result_count": 0,
                    "accepted": 0,
                    "review_required": 0,
                    "rejected": 0,
                    "total": 0,
                    "shadow_empty_exclusion_count": 0,
                },
            )
            for key in bucket:
                bucket[key] += int(row.get(key) or 0)
    for variant, bucket in totals.items():
        total = int(bucket.get("total") or 0)
        bucket["accepted_rate"] = _rate(int(bucket.get("accepted") or 0), total)
        bucket["review_rate"] = _rate(int(bucket.get("review_required") or 0), total)
        bucket["rejected_rate"] = _rate(int(bucket.get("rejected") or 0), total)
    return {"variants": dict(sorted(totals.items())), "rows": rows}


def render_exa_vnext_bakeoff_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Exa vNext Bakeoff",
        "",
        f"- Version: `{payload.get('version') or EXA_VNEXT_BAKEOFF_VERSION}`",
        f"- Runtime effect: `{bool(payload.get('runtime_effect'))}`",
        f"- Dry plan: `{bool(payload.get('dry_plan'))}`",
        f"- Cases: `{payload.get('case_count', 0)}`",
        "",
        "## Variant Totals",
        "",
        "| Variant | Results | Accepted | Review | Rejected | Accepted % | Review % | Rejected % | Shadow empty |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for variant, row in (summary.get("variants") or {}).items():
        lines.append(
            "| {variant} | {result_count} | {accepted} | {review} | {rejected} | {accepted_rate:.1%} | {review_rate:.1%} | {rejected_rate:.1%} | {shadow} |".format(
                variant=variant,
                result_count=row.get("result_count", 0),
                accepted=row.get("accepted", 0),
                review=row.get("review_required", 0),
                rejected=row.get("rejected", 0),
                accepted_rate=float(row.get("accepted_rate") or 0),
                review_rate=float(row.get("review_rate") or 0),
                rejected_rate=float(row.get("rejected_rate") or 0),
                shadow=row.get("shadow_empty_exclusion_count", 0),
            )
        )
    lines.extend(
        [
            "",
            "## Case Rows",
            "",
            "| Brand | Domain | Variant | Status | Results | Accepted | Review | Rejected | Shadow empty |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary.get("rows") or []:
        lines.append(
            "| {brand} | {domain} | {variant} | {status} | {result_count} | {accepted} | {review} | {rejected} | {shadow} |".format(
                brand=_md(row.get("brand")),
                domain=_md(row.get("domain")),
                variant=_md(row.get("variant")),
                status=_md(row.get("status")),
                result_count=row.get("result_count", 0),
                accepted=row.get("accepted", 0),
                review=row.get("review_required", 0),
                rejected=row.get("rejected", 0),
                shadow=row.get("shadow_empty_exclusion_count", 0),
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def write_exa_vnext_bakeoff_outputs(payload: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "exa_vnext_bakeoff.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "exa_vnext_bakeoff.md").write_text(
        render_exa_vnext_bakeoff_markdown(payload),
        encoding="utf-8",
    )
    for case_payload in payload.get("cases") or []:
        case = case_payload.get("case") or {}
        label = case.get("label") or _slugify(case.get("brand") or "case")
        (output_dir / f"{label}.json").write_text(
            json.dumps(case_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_cases_from_file(path: Path) -> list[ExaBakeoffCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("cases") or payload.get("rows") or []
    return _cases_from_rows(rows)


def load_cases_from_evidence_report(path: Path, *, limit: int = 10) -> list[ExaBakeoffCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _cases_from_rows(payload.get("rows") or [])[:limit]


def default_cases() -> list[ExaBakeoffCase]:
    return [
        ExaBakeoffCase("LangChain", "https://www.langchain.com"),
        ExaBakeoffCase("Mistral AI", "https://mistral.ai"),
        ExaBakeoffCase("Instantly", "https://instantly.ai"),
    ]


def _cases_from_rows(rows: list[Any]) -> list[ExaBakeoffCase]:
    cases = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if isinstance(row, dict):
            brand = str(row.get("brand") or row.get("brand_name") or "").strip()
            url = str(row.get("url") or "").strip()
        elif isinstance(row, list) and len(row) >= 2:
            brand = str(row[0]).strip()
            url = str(row[1]).strip()
        else:
            continue
        if not brand and url:
            brand = _domain(url)
        key = (brand, url)
        if not url or key in seen:
            continue
        cases.append(ExaBakeoffCase(brand, url))
        seen.add(key)
    return cases


def _result_row(result: ExaResult, *, request: ExaSearchRequest) -> dict[str, Any]:
    text = _clean_text(result.text or result.summary or " ".join(str(item) for item in result.highlights or []))
    return {
        "request_key": request.key,
        "intent": request.intent,
        "collection": request.collection,
        "url": result.url,
        "title": result.title,
        "text": result.text or "",
        "summary": result.summary or "",
        "highlights": list(result.highlights or []),
        "evidence_text": text,
        "text_chars": len(text),
        "published_date": result.published_date,
        "score": result.score,
        "source_class": result.source_class,
        "relation": result.relation,
        "classification_reason": result.classification_reason,
        "requires_human_review": result.requires_human_review,
    }


def _raw_exa_entry(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": row.get("url") or "",
        "title": row.get("title") or "",
        "summary": row.get("summary") or "",
        "text": row.get("text") or "",
        "highlights": list(row.get("highlights") or []),
        "published_date": row.get("published_date") or "",
        "score": row.get("score") or 0,
        "source_class": row.get("source_class") or "",
        "relation": row.get("relation") or "",
        "classification_reason": row.get("classification_reason") or "",
        "requires_human_review": bool(row.get("requires_human_review")),
    }


def _feature_for_row(row: dict[str, Any]) -> tuple[str, str]:
    key = str(row.get("request_key") or row.get("intent") or "")
    if key in {"news", "press_context"}:
        return "vitalidad", "content_recency"
    if key == "competitors":
        return "diferenciacion", "competitive_context"
    if key == "ai_visibility":
        return "presencia", "ai_visibility"
    if key in {"owned_confirmation", "external_profile"}:
        return "presencia", "directory_presence"
    return "percepcion", "search_visibility"


def _exa_provider_row(report: dict[str, Any]) -> dict[str, Any]:
    acquisition = report.get("acquisition_matrix") if isinstance(report.get("acquisition_matrix"), dict) else {}
    for row in acquisition.get("provider_rows") or []:
        if row.get("provider") == "exa":
            return row
    return {}


def _empty_report() -> dict[str, Any]:
    return {
        "acquisition_matrix": {"provider_rows": [], "source_class_rows": []},
        "acquisition_contract_exclusions": {"total": 0, "by_contract": {}, "by_surface": {}, "by_feature": {}},
    }


def _brand_query(brand_name: str, brand_url: str) -> str:
    parts = [f'"{brand_name}"'] if brand_name else []
    domain = _domain(brand_url)
    if domain:
        parts.append(f'"{domain}"')
    return " ".join(parts)


def _synthetic_run_id(case: ExaBakeoffCase, variant: str) -> int:
    seed = f"{case.brand}|{case.url}|{variant}"
    return 900000 + (sum(ord(ch) for ch in seed) % 99999)


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _rate(value: int, total: int) -> float:
    return round(value / total, 4) if total else 0.0


def _domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or parsed.path).removeprefix("www.").strip("/").lower()


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or ""))
    return "-".join(part for part in slug.split("-") if part) or "case"


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")
