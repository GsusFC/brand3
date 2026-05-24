"""Discovery trust-basis summary.

Pure deterministic metadata used to explain what entity basis the audit used.
It does not affect scoring, features, collectors, prompts, cache keys, reports,
or calibration.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field


@dataclass(frozen=True)
class DiscoveryTrustBasis:
    basis: str
    requested_entity: str
    primary_entity: str
    scope_label: str
    user_message: str
    uses_enriched_evidence: bool
    owned_sources_used: list[str] = field(default_factory=list)
    third_party_evidence_used: int = 0
    limitations: list[str] = field(default_factory=list)


def build_discovery_trust_basis(entity_discovery, discovery_search_plan, discovery_evidence_preview, discovery_enrichment) -> dict:
    plan = _dict(discovery_search_plan)
    entity = _dict(entity_discovery)
    preview = _dict(discovery_evidence_preview)
    enrichment = _dict(discovery_enrichment)
    mode = str(plan.get("analysis_mode") or entity.get("analysis_scope") or "url_only")
    enriched = bool(enrichment.get("applied"))
    basis = _basis(mode, enriched)
    requested = str(plan.get("requested_entity") or entity.get("canonical_brand_name") or entity.get("input_name") or "Unknown")
    primary = str(plan.get("primary_entity") or requested)
    result = DiscoveryTrustBasis(
        basis=basis,
        requested_entity=requested,
        primary_entity=primary,
        scope_label=_scope_label(basis),
        user_message=_message(basis, requested, primary, plan, enrichment),
        uses_enriched_evidence=enriched,
        owned_sources_used=list(enrichment.get("urls_used") or []),
        third_party_evidence_used=int(enrichment.get("added_third_party_evidence") or preview.get("third_party_results_count") or 0),
        limitations=list(preview.get("limitations") or []),
    )
    return asdict(result)


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _basis(mode: str, enriched: bool) -> str:
    normalized = "ecosystem_or_protocol" if mode in {"ecosystem", "protocol"} else mode
    if normalized not in {"product_with_parent", "company_brand", "ecosystem_or_protocol"}:
        return "url_only"
    return f"{normalized}_enriched" if enriched else normalized


def _scope_label(basis: str) -> str:
    labels = {
        "product_with_parent_enriched": "product + parent company, discovery-enriched",
        "product_with_parent": "product + parent company",
        "company_brand_enriched": "company brand, discovery-enriched",
        "company_brand": "company brand",
        "ecosystem_or_protocol_enriched": "ecosystem/protocol, discovery-enriched",
        "ecosystem_or_protocol": "ecosystem/protocol",
        "url_only": "URL only",
    }
    return labels.get(basis, "URL only")


def _message(basis: str, requested: str, primary: str, plan: dict, enrichment: dict) -> str:
    urls = list(enrichment.get("urls_used") or plan.get("owned_urls") or [])
    if basis.startswith("product_with_parent"):
        suffix = " with discovery-enriched evidence" if basis.endswith("_enriched") else ""
        return f"Audit basis covers {requested} as a product of {primary}{suffix}; it is not only {urls[-1] if urls else requested}."
    if basis.startswith("company_brand"):
        return f"Audit basis covers {primary} as the company brand{' with discovery-enriched evidence' if basis.endswith('_enriched') else ''}."
    if basis.startswith("ecosystem_or_protocol"):
        return f"Audit basis covers {primary} as an ecosystem/protocol{' with discovery-enriched evidence' if basis.endswith('_enriched') else ''}."
    return f"Audit basis is limited to the provided URL for {requested}."
