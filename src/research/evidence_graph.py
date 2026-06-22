"""Evidence graph primitives for Brand Research.

The first implementation is intentionally deterministic and network-free. It
adapts an existing Brand Audit snapshot into a traceable graph of sources and
claims so the research contract can stabilize before adding new acquisition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse
import re

from src.reports.strategic_evidence_packet import build_strategic_evidence_packet
from src.research.evidence_graph_sources import ALLOWED_SOURCE_TYPES, ResearchSource, build_sources
from src.research.evidence_graph_sources import _dict, _host, _is_social, _normalize_url, _root_domain, _source_id, _str_list, _unique, _validate


GRAPH_VERSION = "brand_research_evidence_graph_v0_1"

ALLOWED_CLAIM_TYPES = {
    "hero_claim",
    "product_offer",
    "audience",
    "outcome",
    "mission",
    "vision",
    "values",
    "personality",
    "proof",
    "founder_press",
    "feature_evidence",
    "noise",
    "unknown",
}

_SUBPAGE_RE = re.compile(r"(?:^|\n)## Subpage:\s*(?P<url>\S+)\s*\n", re.IGNORECASE)

_GROUP_TO_CLAIM_TYPE = {
    "hero_claims": "hero_claim",
    "product_offer": "product_offer",
    "audience": "audience",
    "outcome": "outcome",
    "mission_language": "mission",
    "vision_language": "vision",
    "values_language": "values",
    "personality_tone": "personality",
    "proof_points": "proof",
    "third_party_context": "founder_press",
}

_GROUP_TO_BLOCKS = {
    "hero_claims": ["magnetism", "brand_idea"],
    "product_offer": ["value_proposition", "brand_idea"],
    "audience": ["value_proposition"],
    "outcome": ["core_purpose", "value_proposition"],
    "mission_language": ["core_purpose", "mission"],
    "vision_language": ["vision"],
    "values_language": ["values", "attributes"],
    "personality_tone": ["personality", "attributes"],
    "proof_points": ["value_proposition", "magnetism"],
    "third_party_context": ["brand_idea", "mission", "vision"],
}


@dataclass(slots=True)
class EvidenceClaim:
    """One traceable claim extracted from research evidence."""

    claim_id: str
    text: str
    claim_type: str
    quote: str = ""
    source_id: str = ""
    source_url: str = ""
    source_type: str = "unknown"
    surface_role: str = ""
    entity_scope: str = ""
    confidence: str = ""
    freshness_days: int | None = None
    supports_blocks: list[str] = field(default_factory=list)
    contradicts: list[str] = field(default_factory=list)
    secondary_source_ids: list[str] = field(default_factory=list)
    secondary_source_urls: list[str] = field(default_factory=list)
    secondary_origins: list[str] = field(default_factory=list)
    noise_reason: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate(self.claim_type, ALLOWED_CLAIM_TYPES, "claim_type")
        _validate(self.source_type, ALLOWED_SOURCE_TYPES, "source_type")

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "claim_type": self.claim_type,
            "quote": self.quote,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "surface_role": self.surface_role,
            "entity_scope": self.entity_scope,
            "confidence": self.confidence,
            "freshness_days": self.freshness_days,
            "supports_blocks": list(self.supports_blocks),
            "contradicts": list(self.contradicts),
            "secondary_source_ids": list(self.secondary_source_ids),
            "secondary_source_urls": list(self.secondary_source_urls),
            "secondary_origins": list(self.secondary_origins),
            "noise_reason": self.noise_reason,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceClaim":
        freshness = data.get("freshness_days")
        return cls(
            claim_id=str(data.get("claim_id") or ""),
            text=str(data.get("text") or ""),
            claim_type=str(data.get("claim_type") or "unknown"),
            quote=str(data.get("quote") or ""),
            source_id=str(data.get("source_id") or ""),
            source_url=str(data.get("source_url") or ""),
            source_type=str(data.get("source_type") or "unknown"),
            surface_role=str(data.get("surface_role") or ""),
            entity_scope=str(data.get("entity_scope") or ""),
            confidence=str(data.get("confidence") or ""),
            freshness_days=int(freshness) if freshness is not None else None,
            supports_blocks=_str_list(data.get("supports_blocks")),
            contradicts=_str_list(data.get("contradicts")),
            secondary_source_ids=_str_list(data.get("secondary_source_ids")),
            secondary_source_urls=_str_list(data.get("secondary_source_urls")),
            secondary_origins=_str_list(data.get("secondary_origins")),
            noise_reason=str(data.get("noise_reason") or ""),
            notes=_str_list(data.get("notes")),
        )


@dataclass(slots=True)
class BrandResearchRun:
    """Run-level identity and provenance."""

    run_id: int | None
    brand_name: str
    input_url: str
    resolved_entity: str = ""
    entity_type: str = "unknown"
    parent_brand: str = ""
    confidence: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "brand_name": self.brand_name,
            "input_url": self.input_url,
            "resolved_entity": self.resolved_entity,
            "entity_type": self.entity_type,
            "parent_brand": self.parent_brand,
            "confidence": self.confidence,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrandResearchRun":
        run_id = data.get("run_id")
        return cls(
            run_id=int(run_id) if run_id is not None else None,
            brand_name=str(data.get("brand_name") or ""),
            input_url=str(data.get("input_url") or ""),
            resolved_entity=str(data.get("resolved_entity") or ""),
            entity_type=str(data.get("entity_type") or "unknown"),
            parent_brand=str(data.get("parent_brand") or ""),
            confidence=str(data.get("confidence") or ""),
            notes=_str_list(data.get("notes")),
        )


@dataclass(slots=True)
class EvidenceGraph:
    """Structured evidence base that downstream Brand3 products can consume."""

    version: str
    run: BrandResearchRun
    sources: dict[str, ResearchSource] = field(default_factory=dict)
    claims: list[EvidenceClaim] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    shadow_sources: list[dict[str, Any]] = field(default_factory=list)
    dedupe_stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "run": self.run.to_dict(),
            "sources": {key: value.to_dict() for key, value in self.sources.items()},
            "claims": [claim.to_dict() for claim in self.claims],
            "gaps": list(self.gaps),
            "warnings": list(self.warnings),
            "shadow_sources": [dict(item) for item in self.shadow_sources if isinstance(item, dict)],
            "dedupe_stats": dict(self.dedupe_stats),
            "summary": self.summary(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceGraph":
        sources_raw = data.get("sources") if isinstance(data.get("sources"), dict) else {}
        claims_raw = data.get("claims") if isinstance(data.get("claims"), list) else []
        return cls(
            version=str(data.get("version") or GRAPH_VERSION),
            run=BrandResearchRun.from_dict(_dict(data.get("run"))),
            sources={
                str(key): ResearchSource.from_dict(value)
                for key, value in sources_raw.items()
                if isinstance(value, dict)
            },
            claims=[EvidenceClaim.from_dict(item) for item in claims_raw if isinstance(item, dict)],
            gaps=_str_list(data.get("gaps")),
            warnings=_str_list(data.get("warnings")),
            shadow_sources=_dict_list(data.get("shadow_sources")),
            dedupe_stats=_dict(data.get("dedupe_stats")),
        )

    def summary(self) -> dict[str, Any]:
        source_counts: dict[str, int] = {}
        claim_counts: dict[str, int] = {}
        block_counts: dict[str, int] = {}
        for source in self.sources.values():
            source_counts[source.source_type] = source_counts.get(source.source_type, 0) + 1
        for claim in self.claims:
            claim_counts[claim.claim_type] = claim_counts.get(claim.claim_type, 0) + 1
            for block in claim.supports_blocks:
                block_counts[block] = block_counts.get(block, 0) + 1
        return {
            "source_count": len(self.sources),
            "claim_count": len(self.claims),
            "shadow_source_count": len(self.shadow_sources),
            "dedupe_stats": dict(self.dedupe_stats),
            "source_counts": dict(sorted(source_counts.items())),
            "claim_counts": dict(sorted(claim_counts.items())),
            "supported_block_counts": dict(sorted(block_counts.items())),
            "noise_claim_count": claim_counts.get("noise", 0),
        }


from src.research.evidence_graph_claims import build_claims_from_snapshot


def build_evidence_graph_from_snapshot(snapshot: dict[str, Any]) -> EvidenceGraph:
    """Build an evidence graph from an existing Brand Audit snapshot."""

    run_payload = _dict(snapshot.get("run"))
    input_url = _normalize_url(str(run_payload.get("url") or ""))
    entity_packet = _entity_packet(snapshot)
    strategic_packet = build_strategic_evidence_packet(snapshot)
    run = BrandResearchRun(
        run_id=_optional_int(run_payload.get("id")),
        brand_name=str(run_payload.get("brand_name") or ""),
        input_url=input_url,
        resolved_entity=str((entity_packet or {}).get("entity_name") or run_payload.get("brand_name") or ""),
        entity_type=_entity_type(entity_packet, input_url),
        parent_brand=str((entity_packet or {}).get("parent_brand") or ""),
        confidence=str((entity_packet or {}).get("confidence") or ""),
        notes=_str_list((entity_packet or {}).get("limitations")),
    )

    sources = build_sources(snapshot, entity_packet=entity_packet)
    claims, dedupe_stats = build_claims_from_snapshot(snapshot, sources=sources, strategic_packet=strategic_packet)
    gaps = _graph_gaps(sources, claims)
    warnings = _unique(_str_list(strategic_packet.warnings) + _entity_boundary_warnings(sources))
    return EvidenceGraph(
        version=GRAPH_VERSION,
        run=run,
        sources=sources,
        claims=claims,
        gaps=gaps,
        warnings=warnings,
        shadow_sources=_shadow_sources_from_snapshot(snapshot),
        dedupe_stats=dedupe_stats,
    )


def _dedupe_claims(
    claims: list[EvidenceClaim],
    *,
    sources: dict[str, ResearchSource],
) -> tuple[list[EvidenceClaim], dict[str, Any]]:
    from src.research.evidence_graph_claims import _dedupe_claims as _claims_dedupe_claims

    return _claims_dedupe_claims(claims, sources=sources)


def _graph_gaps(sources: dict[str, ResearchSource], claims: list[EvidenceClaim]) -> list[str]:
    source_types = {source.source_type for source in sources.values()}
    claim_types = {claim.claim_type for claim in claims if claim.claim_type != "noise"}
    gaps: list[str] = []
    if not source_types.intersection({"owned_about", "owned_product", "owned_security", "owned_docs", "owned_proof"}):
        gaps.append("No strategic owned subpage evidence is present in the current graph.")
    if not source_types.intersection({"press_founder", "third_party_review", "third_party_context"}):
        gaps.append("No third-party contextual evidence is present in the current graph.")
    if "proof" not in claim_types:
        gaps.append("No explicit proof claims were extracted.")
    if not any(claim.supports_blocks for claim in claims):
        gaps.append("No claims are mapped to Brand3 TLDR blocks.")
    return gaps


def _entity_boundary_warnings(sources: dict[str, ResearchSource]) -> list[str]:
    if any(_is_entity_boundary_quarantined_source(source) for source in sources.values()):
        return [
            "entity_boundary_collision: external evidence includes near-name collisions; quarantined from TLDR input."
        ]
    return []


def _entity_packet(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") == "entity_research_packet" and isinstance(raw_input.get("payload"), dict):
            return raw_input["payload"]
    audit = (_dict(snapshot.get("run")).get("audit") or {})
    packet = audit.get("entity_research_packet") if isinstance(audit, dict) else None
    return packet if isinstance(packet, dict) else None


def _entity_type(entity_packet: dict[str, Any] | None, input_url: str) -> str:
    if entity_packet:
        architecture = str(entity_packet.get("brand_architecture") or "")
        audited_type = str(entity_packet.get("audited_surface_type") or "")
        if architecture == "single_brand_surface":
            return "company"
        if audited_type in {"product_surface", "product_lab"}:
            return "product"
        if audited_type == "secondary_surface":
            return "sub_brand"
    path = (urlparse(input_url).path or "").lower()
    if any(marker in path for marker in ("/blog", "/news", "/article", "/post")):
        return "content"
    host = _host(input_url)
    root = _root_domain(host)
    if host and root and host != root and not host.startswith("www."):
        return "product"
    return "company" if input_url else "unknown"


def _snapshot_web_url(snapshot: dict[str, Any]) -> str:
    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") == "web" and isinstance(raw_input.get("payload"), dict):
            return _normalize_url(str(raw_input["payload"].get("canonical_url") or raw_input["payload"].get("url") or ""))
    return _normalize_url(str(_dict(snapshot.get("run")).get("url") or ""))


def _classify_source_url(url: str, *, brand_domain: str, text: str = "", external: bool = False) -> str:
    normalized = _normalize_url(url)
    host = _host(normalized)
    path = (urlparse(normalized).path or "/").lower()
    text_low = text.lower()
    if not normalized:
        return "unknown"
    if _is_social(host):
        return "social"
    if brand_domain and (host == brand_domain or host.endswith("." + brand_domain)):
        if path in {"", "/"}:
            return "owned_home"
        if any(marker in path for marker in ("/about", "/company", "/mission", "/manifesto", "/team", "/story", "/principles")):
            return "owned_about"
        if any(marker in path for marker in ("/security", "/privacy", "/trust", "/legal", "/terms", "/compliance")):
            return "owned_security"
        if any(marker in path for marker in ("/docs", "/documentation", "/developers", "/api", "/help", "/support")):
            return "owned_docs"
        if any(marker in path for marker in ("/pricing", "/plans")):
            return "owned_pricing"
        if any(marker in path for marker in ("/customers", "/case", "/stories", "/testimonials", "/reviews")):
            return "owned_proof"
        if any(marker in path for marker in ("/product", "/products", "/platform", "/solution", "/solutions", "/app", "/demo", "/lab", "/natureos")):
            return "owned_product"
        if any(marker in path for marker in ("/blog", "/news", "/feed", "/article", "/post", "/resources")):
            return "noise"
        return "owned_home"
    if external and any(marker in text_low for marker in ("founder", "interview", "launch", "raises", "raised", "funding", "acquired", "press")):
        return "press_founder"
    if external and any(marker in text_low for marker in ("review", "customer", "testimonial", "case study", "trusted by", "used by")):
        return "third_party_review"
    if external:
        return "third_party_context"
    return "unknown"


def _external_entity_boundary_collision(url: str, text: str, *, brand_name: str, brand_domain: str) -> bool:
    token = _identity_token(brand_name=brand_name, brand_domain=brand_domain)
    if len(token) < 5:
        return False
    observed_tokens = _identity_tokens(" ".join([url, text]))
    if not observed_tokens or token in observed_tokens:
        return False
    for observed in observed_tokens:
        if len(observed) < 5:
            continue
        if observed.startswith(token) or token.startswith(observed):
            return True
        if abs(len(observed) - len(token)) <= 2 and _edit_distance_at_most(observed, token, 2):
            return True
    return False


def _identity_token(*, brand_name: str, brand_domain: str) -> str:
    for value in (brand_name, brand_domain.split(".", 1)[0]):
        tokens = sorted(_identity_tokens(value), key=lambda item: (-len(item), item))
        if tokens:
            return tokens[0]
    return ""


def _identity_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) >= 3 and token not in {"www", "com", "app", "ai", "io", "co", "inc", "the"}
    }


def _edit_distance_at_most(left: str, right: str, limit: int) -> bool:
    if abs(len(left) - len(right)) > limit:
        return False
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        row_min = i
        for j, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            value = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            current.append(value)
            row_min = min(row_min, value)
        if row_min > limit:
            return False
        previous = current
    return previous[-1] <= limit


def _is_entity_boundary_quarantined_source(source: ResearchSource) -> bool:
    return source.source_type == "noise" and any(
        str(note).startswith("entity_boundary_collision") for note in source.notes
    )


def _source_type_from_entity_role(role: str, url: str) -> str:
    if role.startswith("product:"):
        return "owned_product"
    if role in {"audited_surface", "parent_home"}:
        return "owned_home"
    if role == "mission_about":
        return "owned_about"
    if role == "product_system":
        return "owned_product"
    if role == "policy_security":
        return "owned_security"
    if role == "pricing":
        return "owned_pricing"
    if role == "proof_customer":
        return "owned_proof"
    return _classify_source_url(url, brand_domain=_root_domain(_host(url)))


def _prefer_source_type(existing: str, candidate: str) -> str:
    priority = {
        "unknown": 0,
        "noise": 1,
        "owned_home": 2,
        "third_party_context": 2,
        "social": 2,
        "competitor_context": 2,
        "press_founder": 3,
        "third_party_review": 3,
        "owned_about": 4,
        "owned_pricing": 4,
        "owned_security": 4,
        "owned_docs": 4,
        "owned_proof": 4,
        "owned_product": 5,
    }
    if priority.get(candidate, 0) > priority.get(existing, 0):
        return candidate
    if existing in {"unknown", "noise"} and candidate not in {"unknown", "noise"}:
        return candidate
    return existing


def _prefer_annotation(existing: str, candidate: str) -> str:
    if not candidate:
        return existing
    if not existing:
        return candidate
    if candidate.startswith("product:") or existing in {"unknown", "external_context", "evidence", "owned_surface"}:
        return candidate
    return existing


def _source_id(url: str) -> str:
    normalized = _normalize_url(url)
    if not normalized:
        return ""
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    return f"src_{digest}"


def _claim_id(claim_type: str, text: str, source_id: str) -> str:
    raw = "|".join([claim_type, source_id, text])
    return f"claim_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _shadow_sources_from_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_input in snapshot.get("raw_inputs") or []:
        if raw_input.get("source") != "parallel_shadow":
            continue
        payload = raw_input.get("payload")
        if not isinstance(payload, dict):
            continue
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        intents = payload.get("intents") if isinstance(payload.get("intents"), dict) else {}
        rows.append(
            {
                "provider": str(payload.get("provider") or "parallel"),
                "mode": str(payload.get("mode") or ""),
                "status": str(payload.get("status") or ""),
                "result_total": int(summary.get("result_total") or 0),
                "unique_domain_count": int(summary.get("unique_domain_count") or 0),
                "unique_domains": _str_list(summary.get("unique_domains"))[:20],
                "intents": {
                    str(name): {
                        "status": str(item.get("status") or ""),
                        "result_count": int(item.get("result_count") or 0),
                        "unique_domains": _str_list(item.get("unique_domains"))[:20],
                        "results": _shadow_results(item.get("results"))[:5],
                    }
                    for name, item in intents.items()
                    if isinstance(item, dict)
                },
                "notes": [
                    "Shadow provider only; not used for scoring, TLDR claims, proof points, or recommendations."
                ],
            }
        )
    return rows


def _shadow_results(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        rows.append(
            {
                "url": url,
                "title": str(item.get("title") or url),
                "excerpt": str(item.get("excerpt") or ""),
            }
        )
    return rows
