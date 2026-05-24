"""Non-invasive discovery evidence preview.

The preview only inspects data already collected elsewhere. It does not call
external APIs and is not used by scoring, prompts, cache keys, or reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass(frozen=True)
class DiscoveryEvidencePreview:
    attempted: bool
    queries_used: list[str] = field(default_factory=list)
    results_count: int = 0
    owned_results_count: int = 0
    third_party_results_count: int = 0
    top_domains: list[str] = field(default_factory=list)
    official_domains: list[str] = field(default_factory=list)
    third_party_domains: list[str] = field(default_factory=list)
    recommended_to_use_for_scoring: bool = False
    limitations: list[str] = field(default_factory=list)


def build_discovery_evidence_preview(search_plan, exa_data=None, web_data=None, context_data=None) -> DiscoveryEvidencePreview:
    queries = list(_get(search_plan, "queries") or [])
    primary_entity = str(_get(search_plan, "primary_entity") or "").strip()
    requested_entity = str(_get(search_plan, "requested_entity") or "").strip()
    owned_domains = _owned_domains(search_plan, web_data, context_data)
    terms = _match_terms(queries, primary_entity, requested_entity)

    if not queries and not terms:
        return DiscoveryEvidencePreview(
            attempted=False,
            queries_used=[],
            limitations=["search_plan_missing"],
        )

    matched_domains: list[str] = []
    owned_count = 0
    third_party_count = 0
    for result in _exa_results(exa_data):
        if not _matches_result(result, terms):
            continue
        domain = _domain(getattr(result, "url", ""))
        if not domain:
            continue
        matched_domains.append(domain)
        if domain in owned_domains:
            owned_count += 1
        else:
            third_party_count += 1

    top_domains = _rank_domains(matched_domains)
    official_domains = [domain for domain in top_domains if domain in owned_domains]
    third_party_domains = [domain for domain in top_domains if domain not in owned_domains]
    results_count = owned_count + third_party_count
    recommended = results_count >= 5 and owned_count >= 1 and third_party_count >= 2
    limitations = _limitations(
        results_count=results_count,
        owned_results_count=owned_count,
        third_party_results_count=third_party_count,
        recommended=recommended,
        exa_data=exa_data,
    )

    return DiscoveryEvidencePreview(
        attempted=True,
        queries_used=queries,
        results_count=results_count,
        owned_results_count=owned_count,
        third_party_results_count=third_party_count,
        top_domains=top_domains,
        official_domains=official_domains,
        third_party_domains=third_party_domains,
        recommended_to_use_for_scoring=recommended,
        limitations=limitations,
    )


def _get(value, field_name: str):
    if isinstance(value, dict):
        return value.get(field_name)
    return getattr(value, field_name, None)


def _owned_domains(search_plan, web_data, context_data) -> set[str]:
    domains = {_domain(url) for url in (_get(search_plan, "owned_urls") or [])}
    for value in [
        getattr(web_data, "url", ""),
        getattr(web_data, "canonical_url", ""),
        getattr(context_data, "url", ""),
    ]:
        domains.add(_domain(value))
    return {domain for domain in domains if domain}


def _match_terms(queries: list[str], primary_entity: str, requested_entity: str) -> set[str]:
    terms = {_normalize(primary_entity), _normalize(requested_entity)}
    for query in queries:
        words = [_normalize(part) for part in str(query).split()]
        terms.update(word for word in words if len(word) >= 4)
    return {term for term in terms if term}


def _exa_results(exa_data) -> list:
    if not exa_data:
        return []
    return (
        list(getattr(exa_data, "mentions", []) or [])
        + list(getattr(exa_data, "news", []) or [])
        + list(getattr(exa_data, "ai_visibility_results", []) or [])
        + list(getattr(exa_data, "competitors", []) or [])
    )


def _matches_result(result, terms: set[str]) -> bool:
    text = " ".join(
        [
            getattr(result, "title", "") or "",
            getattr(result, "text", "") or "",
            getattr(result, "summary", "") or "",
            " ".join(str(item) for item in (getattr(result, "highlights", []) or [])),
        ]
    )
    normalized = _normalize(text)
    return any(term in normalized for term in terms)


def _rank_domains(domains: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    for domain in domains:
        counts[domain] = counts.get(domain, 0) + 1
    return sorted(counts, key=lambda domain: (-counts[domain], domain))


def _limitations(
    *,
    results_count: int,
    owned_results_count: int,
    third_party_results_count: int,
    recommended: bool,
    exa_data,
) -> list[str]:
    if recommended:
        return []
    limitations: list[str] = []
    if not exa_data:
        limitations.append("exa_data_missing")
    if results_count < 5:
        limitations.append("insufficient_results")
    if owned_results_count < 1:
        limitations.append("owned_evidence_missing")
    if third_party_results_count < 2:
        limitations.append("third_party_evidence_insufficient")
    return limitations


def _domain(value: str | None) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _normalize(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split())
