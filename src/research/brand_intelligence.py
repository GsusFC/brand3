"""Brand Intelligence Acquisition contracts.

This module is intentionally parallel to the current Brand Audit pipeline. It
does not call providers, does not alter scoring, and does not feed UI. Its job
is to define the first-mile research contract where a URL is only one possible
seed for a brand investigation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal
from urllib.parse import urlparse
import hashlib


SEED_CONTRACT_VERSION = "brand_intelligence_seed_v0_1"
IDENTITY_RESOLUTION_CONTRACT_VERSION = "brand_identity_resolution_v0_1"
ENTITY_CONTRACT_VERSION = "brand_intelligence_entity_v0_1"
SOURCE_PLAN_CONTRACT_VERSION = "brand_intelligence_source_plan_v0_1"
SOURCE_INVENTORY_CONTRACT_VERSION = "brand_source_inventory_v0_1"
BRAND_EVIDENCE_GRAPH_CONTRACT_VERSION = "brand_evidence_graph_v0_1"
IDENTITY_BAKEOFF_VERSION = "brand_identity_bakeoff_v0_1"
SOURCE_OBSERVATION_BAKEOFF_VERSION = "brand_source_observation_bakeoff_v0_1"

SeedKind = Literal["url", "name", "linkedin", "app_store", "manual_text"]
ResolutionStatus = Literal["resolved", "provisional", "unresolved"]
BrandEntityType = Literal["company", "product", "ecosystem", "local_brand", "unknown"]
IdentitySignalSource = Literal["domain", "owned_web", "search", "linkedin", "reviews", "social", "app_store", "manual"]
SourceObservationStatus = Literal["observed", "not_observed", "deferred", "error"]
EvidenceEligibility = Literal["eligible", "limited", "ineligible"]
BrandEvidenceKind = Literal[
    "owned_claim",
    "parent_owned_claim",
    "external_context",
    "external_perception",
    "profile_presence",
    "visual_signal",
    "distribution_signal",
    "noise",
    "unknown",
]
EvidenceStrength = Literal["strong", "moderate", "weak", "blocked"]
SourceChannel = Literal[
    "owned_web",
    "parent_owned_web",
    "search",
    "news",
    "reviews",
    "linkedin",
    "social",
    "app_store",
    "docs",
    "community",
    "jobs",
    "visual",
]


@dataclass(frozen=True)
class BrandSeed:
    value: str
    kind: SeedKind = "url"
    provided_name: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"version": SEED_CONTRACT_VERSION, **asdict(self)}


@dataclass(frozen=True)
class BrandIdentitySignal:
    source: IdentitySignalSource
    candidate_name: str
    confidence: float
    value: str = ""
    entity_type: BrandEntityType = "unknown"
    canonical_url: str = ""
    parent_brand: str | None = None
    parent_url: str | None = None
    product_name: str | None = None
    product_url: str | None = None
    signal: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrandIdentityCandidate:
    name: str
    entity_type: BrandEntityType
    confidence: float
    canonical_url: str = ""
    parent_brand: str | None = None
    parent_url: str | None = None
    product_name: str | None = None
    product_url: str | None = None
    evidence: list[dict[str, object]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrandIdentityResolution:
    input_seed: BrandSeed
    status: ResolutionStatus
    candidates: list[BrandIdentityCandidate] = field(default_factory=list)
    selected_candidate: BrandIdentityCandidate | None = None
    missing: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": IDENTITY_RESOLUTION_CONTRACT_VERSION,
            "input_seed": self.input_seed.to_dict(),
            "status": self.status,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "selected_candidate": self.selected_candidate.to_dict() if self.selected_candidate else None,
            "missing": list(self.missing),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class ResolvedBrandEntity:
    requested_value: str
    requested_kind: SeedKind
    resolution_status: ResolutionStatus
    resolved_name: str
    entity_type: BrandEntityType
    analysis_mode: str
    confidence: float
    canonical_url: str = ""
    parent_brand: str | None = None
    parent_url: str | None = None
    product_name: str | None = None
    product_url: str | None = None
    evidence: list[dict[str, object]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"version": ENTITY_CONTRACT_VERSION, **asdict(self)}


@dataclass(frozen=True)
class BrandSourceRequest:
    channel: SourceChannel
    intent: str
    query: str = ""
    url: str = ""
    priority: int = 100
    required: bool = True
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrandSourcePlan:
    resolution_status: ResolutionStatus
    resolved_name: str
    interpretation_ready: bool
    source_requests: list[BrandSourceRequest] = field(default_factory=list)
    required_missing: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": SOURCE_PLAN_CONTRACT_VERSION,
            "resolution_status": self.resolution_status,
            "resolved_name": self.resolved_name,
            "interpretation_ready": self.interpretation_ready,
            "source_requests": [request.to_dict() for request in self.source_requests],
            "required_missing": list(self.required_missing),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class BrandSourceObservation:
    channel: SourceChannel
    status: SourceObservationStatus
    source_url: str = ""
    provider: str = ""
    title: str = ""
    freshness: str = "unknown"
    confidence: float = 0.0
    evidence_eligibility: EvidenceEligibility = "ineligible"
    reason: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrandSourceInventory:
    resolved_name: str
    observations: list[BrandSourceObservation] = field(default_factory=list)
    missing_required_channels: list[str] = field(default_factory=list)
    deferred_channels: list[str] = field(default_factory=list)
    eligible_channels: list[str] = field(default_factory=list)
    duplicate_source_urls: list[str] = field(default_factory=list)
    conflicting_source_urls: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": SOURCE_INVENTORY_CONTRACT_VERSION,
            "resolved_name": self.resolved_name,
            "observations": [observation.to_dict() for observation in self.observations],
            "missing_required_channels": list(self.missing_required_channels),
            "deferred_channels": list(self.deferred_channels),
            "eligible_channels": list(self.eligible_channels),
            "duplicate_source_urls": list(self.duplicate_source_urls),
            "conflicting_source_urls": list(self.conflicting_source_urls),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class BrandEvidenceItem:
    evidence_id: str
    kind: BrandEvidenceKind
    text: str
    source_channel: SourceChannel
    source_url: str = ""
    provider: str = ""
    source_title: str = ""
    quote: str = ""
    attribution: str = ""
    strength: EvidenceStrength = "weak"
    confidence: float = 0.0
    supports: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrandEvidenceGraph:
    resolved_name: str
    evidence: list[BrandEvidenceItem] = field(default_factory=list)
    rejected: list[BrandEvidenceItem] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": BRAND_EVIDENCE_GRAPH_CONTRACT_VERSION,
            "resolved_name": self.resolved_name,
            "evidence": [item.to_dict() for item in self.evidence],
            "rejected": [item.to_dict() for item in self.rejected],
            "gaps": list(self.gaps),
            "warnings": list(self.warnings),
            "summary": self.summary(),
        }

    def summary(self) -> dict[str, object]:
        kind_counts: dict[str, int] = {}
        strength_counts: dict[str, int] = {}
        channel_counts: dict[str, int] = {}
        for item in self.evidence:
            kind_counts[item.kind] = kind_counts.get(item.kind, 0) + 1
            strength_counts[item.strength] = strength_counts.get(item.strength, 0) + 1
            channel_counts[item.source_channel] = channel_counts.get(item.source_channel, 0) + 1
        return {
            "evidence_count": len(self.evidence),
            "rejected_count": len(self.rejected),
            "kind_counts": dict(sorted(kind_counts.items())),
            "strength_counts": dict(sorted(strength_counts.items())),
            "channel_counts": dict(sorted(channel_counts.items())),
        }


@dataclass(frozen=True)
class BrandIdentityBakeoffCase:
    case_id: str
    seed: BrandSeed
    signals: list[BrandIdentitySignal]
    expected_status: ResolutionStatus
    expected_name: str = ""
    known_case: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "seed": self.seed.to_dict(),
            "signals": [signal.to_dict() for signal in self.signals],
            "expected_status": self.expected_status,
            "expected_name": self.expected_name,
            "known_case": self.known_case,
        }


@dataclass(frozen=True)
class BrandIdentityBakeoffResult:
    case_id: str
    expected_status: ResolutionStatus
    actual_status: ResolutionStatus
    expected_name: str
    actual_name: str
    passed: bool
    known_case: bool
    misresolved: bool
    resolution: BrandIdentityResolution

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "expected_status": self.expected_status,
            "actual_status": self.actual_status,
            "expected_name": self.expected_name,
            "actual_name": self.actual_name,
            "passed": self.passed,
            "known_case": self.known_case,
            "misresolved": self.misresolved,
            "resolution": self.resolution.to_dict(),
        }


@dataclass(frozen=True)
class BrandSourceBakeoffCase:
    case_id: str
    plan: BrandSourcePlan
    observations: list[BrandSourceObservation]

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "plan": self.plan.to_dict(),
            "observations": [observation.to_dict() for observation in self.observations],
        }


@dataclass(frozen=True)
class BrandSourceBakeoffResult:
    case_id: str
    inventory_ready: bool
    missing_required_channels: list[str]
    eligible_channels: list[str]
    provider_metrics: dict[str, dict[str, object]]
    inventory: BrandSourceInventory

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "inventory_ready": self.inventory_ready,
            "missing_required_channels": list(self.missing_required_channels),
            "eligible_channels": list(self.eligible_channels),
            "provider_metrics": self.provider_metrics,
            "inventory": self.inventory.to_dict(),
        }


def resolve_brand_seed(seed: BrandSeed) -> ResolvedBrandEntity:
    """Resolve a brand seed without pretending all seeds identify a brand."""
    identity = resolve_brand_identity(seed)
    return _entity_from_identity_resolution(identity)


def resolve_brand_identity(seed: BrandSeed) -> BrandIdentityResolution:
    """Return identity candidates for a seed before committing to an entity."""
    return resolve_brand_identity_from_signals(seed, identity_signals_for_seed(seed))


def resolve_brand_identity_from_signals(
    seed: BrandSeed,
    signals: list[BrandIdentitySignal],
) -> BrandIdentityResolution:
    """Resolve identity candidates from observed or fixture identity signals."""
    if seed.kind == "manual_text":
        return BrandIdentityResolution(
            input_seed=seed,
            status="unresolved",
            missing=["verified_identity_seed", "canonical_owned_surface"],
            limitations=["manual_text_without_identity", "requires_multichannel_validation"],
        )

    candidates = _candidates_from_signals(signals)
    if not candidates:
        return BrandIdentityResolution(
            input_seed=seed,
            status="unresolved",
            missing=["identity_candidates", "canonical_owned_surface"],
            limitations=["insufficient_identity_signal", "requires_multichannel_validation"],
        )
    selected = candidates[0]
    status = _resolution_status_for_candidate(selected)
    missing: list[str] = []
    limitations = list(selected.limitations)
    if status == "provisional":
        missing.append("verified_entity_resolution")
        limitations.append("requires_multichannel_validation")
        if "subdomain_surface_needs_parent_validation" in selected.limitations:
            missing.append("verified_parent_surface")
        if not selected.canonical_url:
            missing.append("canonical_owned_surface")
    return _identity_resolution(seed, status, candidates, selected=selected, missing=missing, limitations=limitations)


def identity_signals_for_seed(seed: BrandSeed) -> list[BrandIdentitySignal]:
    """Build deterministic offline identity signals for contract tests.

    Later provider adapters can produce this same shape from owned web, search,
    LinkedIn, reviews, app stores, or other channels.
    """
    value = (seed.value or "").strip()
    name = (seed.provided_name or "").strip()
    canonical_url = _normalize_url(value) if seed.kind in {"url", "linkedin", "app_store"} else ""
    host = _host(canonical_url or value)
    root = _root_domain(host)
    match_key = _normalize_name(name or _label_from_host(host) or value)
    if seed.kind == "manual_text":
        return []

    signals: list[BrandIdentitySignal] = []

    if match_key == "chatgpt" or root == "chatgpt.com":
        return [
            BrandIdentitySignal("domain", "ChatGPT", 0.9, root or host, "product", canonical_url or "https://chatgpt.com", "OpenAI", "https://openai.com", "ChatGPT", canonical_url or "https://chatgpt.com", "known_product_domain"),
            BrandIdentitySignal("owned_web", "ChatGPT", 0.95, "ChatGPT by OpenAI", "product", canonical_url or "https://chatgpt.com", "OpenAI", "https://openai.com", "ChatGPT", canonical_url or "https://chatgpt.com", "owned_parent_reference"),
            BrandIdentitySignal("search", "ChatGPT", 0.9, "OpenAI ChatGPT", "product", canonical_url or "https://chatgpt.com", "OpenAI", "https://openai.com", "ChatGPT", canonical_url or "https://chatgpt.com", "search_parent_reference"),
        ]

    if match_key == "langchain" or root == "langchain.com":
        return [
            BrandIdentitySignal("domain", "LangChain", 0.85, root or host, "company", canonical_url or "https://www.langchain.com", signal="known_company_domain"),
            BrandIdentitySignal("owned_web", "LangChain", 0.9, "LangChain product platform", "company", canonical_url or "https://www.langchain.com", signal="owned_company_surface"),
            BrandIdentitySignal("search", "LangChain", 0.86, "LangChain AI app development platform", "company", canonical_url or "https://www.langchain.com", signal="search_company_reference"),
        ]

    if match_key == "base" or root == "base.org":
        return [
            BrandIdentitySignal("domain", "Base", 0.85, root or host, "ecosystem", canonical_url or "https://base.org", signal="known_ecosystem_domain"),
            BrandIdentitySignal("search", "Base", 0.9, "Base protocol ecosystem", "ecosystem", canonical_url or "https://base.org", signal="search_ecosystem_reference"),
        ]

    if root == "naturaumana.ai" or root == "lab.naturaumana.ai":
        return [
            BrandIdentitySignal("domain", "Natura Umana", 0.58, root or host, "company", canonical_url or "https://www.naturaumana.ai", signal="domain_family_match"),
            BrandIdentitySignal("owned_web", "Natura Umana", 0.62, "lab surface in naturaumana.ai domain family", "company", canonical_url or "https://www.naturaumana.ai", signal="subdomain_surface"),
        ]

    if seed.kind == "name" and _is_ambiguous_name(value):
        return [
            BrandIdentitySignal("manual", value, 0.25, value, "unknown", signal="ambiguous_name"),
        ]

    if canonical_url and not _looks_like_placeholder(root):
        label = name or _label_from_host(host)
        signals.append(
            BrandIdentitySignal("domain", label or root or "Unknown", 0.35, root or host, "unknown", canonical_url, signal="url_seed")
        )
    return signals


def domain_identity_signal(url: str, *, provided_name: str = "") -> BrandIdentitySignal | None:
    canonical_url = _normalize_url(url)
    host = _host(canonical_url)
    root = _root_domain(host)
    if not canonical_url or _looks_like_placeholder(root):
        return None
    name = (provided_name or _label_from_host(host) or root).strip()
    confidence = 0.55 if provided_name and _normalize_name(provided_name) in _normalize_name(root) else 0.35
    return BrandIdentitySignal(
        source="domain",
        candidate_name=name,
        confidence=confidence,
        value=root or host,
        entity_type="unknown",
        canonical_url=canonical_url,
        signal="domain_seed",
    )


def owned_web_identity_signal(payload: dict[str, object]) -> BrandIdentitySignal | None:
    name = str(payload.get("brand_name") or payload.get("title") or "").strip()
    url = str(payload.get("canonical_url") or payload.get("url") or "").strip()
    title = str(payload.get("title") or "").strip()
    description = str(payload.get("description") or payload.get("meta_description") or "").strip()
    if not name and not title:
        return None
    candidate = _clean_candidate_name(name or title)
    parent = _parent_from_text(" ".join([title, description]))
    entity_type: BrandEntityType = "product" if parent else "company"
    return BrandIdentitySignal(
        source="owned_web",
        candidate_name=candidate,
        confidence=0.86 if url else 0.72,
        value=title or description or candidate,
        entity_type=entity_type,
        canonical_url=_normalize_url(url) if url else "",
        parent_brand=parent,
        parent_url=_known_parent_url(parent),
        product_name=candidate if parent else None,
        product_url=_normalize_url(url) if parent and url else None,
        signal="owned_title_or_meta",
    )


def search_result_identity_signal(result: dict[str, object]) -> BrandIdentitySignal | None:
    title = str(result.get("title") or "").strip()
    url = str(result.get("url") or "").strip()
    text = str(result.get("text") or result.get("summary") or "").strip()
    candidate = _candidate_from_search_title(title)
    if not candidate:
        return None
    parent = _parent_from_text(" ".join([title, text]))
    return BrandIdentitySignal(
        source="search",
        candidate_name=candidate,
        confidence=0.82 if parent or url else 0.68,
        value=title or text,
        entity_type="product" if parent else "unknown",
        canonical_url=_normalize_url(url) if url else "",
        parent_brand=parent,
        parent_url=_known_parent_url(parent),
        product_name=candidate if parent else None,
        product_url=_normalize_url(url) if parent and url else None,
        signal="search_result",
    )


def linkedin_identity_signal(profile: dict[str, object]) -> BrandIdentitySignal | None:
    name = str(profile.get("name") or profile.get("company_name") or "").strip()
    url = str(profile.get("url") or "").strip()
    description = str(profile.get("description") or "").strip()
    if not name:
        return None
    return BrandIdentitySignal(
        source="linkedin",
        candidate_name=_clean_candidate_name(name),
        confidence=0.84,
        value=description or name,
        entity_type="company",
        canonical_url=_normalize_url(str(profile.get("website") or "")),
        signal="company_profile",
    )


def review_identity_signal(listing: dict[str, object]) -> BrandIdentitySignal | None:
    name = str(listing.get("name") or listing.get("product_name") or "").strip()
    url = str(listing.get("url") or "").strip()
    category = str(listing.get("category") or "").strip()
    if not name:
        return None
    return BrandIdentitySignal(
        source="reviews",
        candidate_name=_clean_candidate_name(name),
        confidence=0.7,
        value=category or name,
        entity_type="product",
        canonical_url=_normalize_url(url) if url else "",
        product_name=_clean_candidate_name(name),
        signal="review_listing",
    )


def build_brand_source_plan(entity: ResolvedBrandEntity) -> BrandSourcePlan:
    """Plan multichannel brand evidence before Brand3 interpretation."""
    requests: list[BrandSourceRequest] = []
    missing: list[str] = []
    limitations = list(entity.limitations)

    if entity.canonical_url:
        requests.append(
            BrandSourceRequest(
                channel="owned_web",
                intent="official_brand_claims_and_visual_surface",
                url=entity.canonical_url,
                priority=10,
                reason="Official owned surface is one channel, not the whole brand.",
            )
        )
    else:
        missing.append("canonical_owned_surface")

    if entity.parent_url:
        requests.append(
            BrandSourceRequest(
                channel="parent_owned_web",
                intent="parent_brand_context",
                url=entity.parent_url,
                priority=20,
                reason="Parent brand can change interpretation of product brands.",
            )
        )

    search_entity = _search_label(entity)
    requests.extend(
        [
            BrandSourceRequest("search", "entity_disambiguation", query=f"{search_entity} official brand", priority=30),
            BrandSourceRequest("reviews", "external_perception_and_friction", query=f"{search_entity} reviews", priority=40),
            BrandSourceRequest("news", "reputation_momentum_and_category_context", query=f"{search_entity} news", priority=50, required=False),
            BrandSourceRequest("linkedin", "company_presence_team_and_category", query=f"{search_entity} LinkedIn", priority=60, required=False),
            BrandSourceRequest("social", "performed_voice_and_current_signals", query=f"{search_entity} social profiles", priority=70, required=False),
            BrandSourceRequest("visual", "visual_identity_surface", url=entity.canonical_url, priority=80, required=bool(entity.canonical_url)),
        ]
    )

    if entity.entity_type == "product":
        requests.append(
            BrandSourceRequest("app_store", "app_or_product_distribution_surface", query=f"{search_entity} app", priority=55, required=False)
        )
    if entity.entity_type == "ecosystem":
        requests.extend(
            [
                BrandSourceRequest("docs", "developer_product_reality", query=f"{search_entity} docs", priority=35),
                BrandSourceRequest("community", "ecosystem_adoption_and_participation", query=f"{search_entity} community", priority=65, required=False),
            ]
        )
    if entity.resolution_status != "resolved":
        missing.append("verified_entity_resolution")
        limitations.append("brand_interpretation_must_remain_provisional")

    return BrandSourcePlan(
        resolution_status=entity.resolution_status,
        resolved_name=entity.resolved_name,
        interpretation_ready=entity.resolution_status == "resolved",
        source_requests=sorted(requests, key=lambda item: item.priority),
        required_missing=_unique(missing),
        limitations=_unique(limitations),
    )


def plan_brand_intelligence(seed: BrandSeed) -> tuple[ResolvedBrandEntity, BrandSourcePlan]:
    entity = resolve_brand_seed(seed)
    return entity, build_brand_source_plan(entity)


def build_brand_source_inventory(
    plan: BrandSourcePlan,
    observations: list[BrandSourceObservation],
) -> BrandSourceInventory:
    """Summarize source coverage before evidence extraction or interpretation."""
    required_channels = [request.channel for request in plan.source_requests if request.required]
    observed_eligible = {
        observation.channel
        for observation in observations
        if observation.status == "observed" and observation.evidence_eligibility in {"eligible", "limited"}
    }
    eligible_channels = _unique([channel for channel in required_channels if channel in observed_eligible])
    eligible_channels.extend(
        channel
        for channel in _unique([observation.channel for observation in observations if observation.channel in observed_eligible])
        if channel not in eligible_channels
    )
    missing_required = [
        channel
        for channel in required_channels
        if channel not in observed_eligible
    ]
    deferred_channels = _unique(
        [
            observation.channel
            for observation in observations
            if observation.status == "deferred"
        ]
    )
    duplicate_urls = _duplicate_source_urls(observations)
    conflicting_urls = _conflicting_source_urls(observations)
    limitations = list(plan.limitations)
    if missing_required:
        limitations.append("missing_required_sources")
    if not eligible_channels:
        limitations.append("no_evidence_eligible_sources")
    if plan.required_missing:
        limitations.append("identity_or_source_plan_missing_requirements")
    if duplicate_urls:
        limitations.append("duplicate_source_observations")
    if conflicting_urls:
        limitations.append("conflicting_source_observations")
    return BrandSourceInventory(
        resolved_name=plan.resolved_name,
        observations=observations,
        missing_required_channels=_unique(missing_required),
        deferred_channels=deferred_channels,
        eligible_channels=_unique(eligible_channels),
        duplicate_source_urls=duplicate_urls,
        conflicting_source_urls=conflicting_urls,
        limitations=_unique(limitations),
    )


def search_source_observation(
    result: dict[str, object],
    *,
    provider: str = "exa",
    channel: SourceChannel = "search",
) -> BrandSourceObservation:
    url = str(result.get("url") or "").strip()
    title = str(result.get("title") or "").strip()
    text = str(result.get("text") or result.get("summary") or result.get("snippet") or "").strip()
    score = _coerce_float(result.get("score"), default=0.0)
    freshness = str(result.get("published_date") or result.get("date") or "unknown").strip() or "unknown"
    if not url and not title:
        return BrandSourceObservation(
            channel,
            "not_observed",
            provider=provider,
            freshness=freshness,
            reason="missing_url_and_title",
        )
    if len(text) >= 80:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url) if url else "",
            provider,
            title,
            freshness,
            round(max(0.7, min(0.95, score or 0.74)), 4),
            "eligible",
            "search_result_with_extractable_context",
        )
    return BrandSourceObservation(
        channel,
        "observed",
        _normalize_url(url) if url else "",
        provider,
        title,
        freshness,
        round(max(0.45, min(0.7, score or 0.52)), 4),
        "limited",
        "search_result_without_rich_context",
    )


def owned_web_source_observation(
    capture: dict[str, object],
    *,
    provider: str = "firecrawl",
    channel: SourceChannel = "owned_web",
) -> BrandSourceObservation:
    url = str(capture.get("url") or capture.get("source_url") or capture.get("canonical_url") or "").strip()
    title = str(capture.get("title") or capture.get("metadata_title") or "").strip()
    text = str(capture.get("markdown") or capture.get("text") or capture.get("content") or "").strip()
    freshness = str(capture.get("captured_at") or capture.get("fetched_at") or "unknown").strip() or "unknown"
    error = str(capture.get("error") or "").strip()
    if error:
        return BrandSourceObservation(
            channel,
            "error",
            _normalize_url(url) if url else "",
            provider,
            title,
            freshness,
            0.0,
            "ineligible",
            "provider_error",
            [error],
        )
    if not url:
        return BrandSourceObservation(
            channel,
            "not_observed",
            provider=provider,
            title=title,
            freshness=freshness,
            reason="missing_source_url",
        )
    if len(text) >= 500:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url),
            provider,
            title,
            freshness,
            0.88,
            "eligible",
            "owned_web_capture_with_extractable_content",
        )
    if len(text) >= 120:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url),
            provider,
            title,
            freshness,
            0.62,
            "limited",
            "owned_web_capture_with_thin_content",
        )
    return BrandSourceObservation(
        channel,
        "observed",
        _normalize_url(url),
        provider,
        title,
        freshness,
        0.25,
        "ineligible",
        "owned_web_capture_too_thin_for_evidence",
    )


def review_source_observation(
    listing: dict[str, object],
    *,
    provider: str = "review-source",
    channel: SourceChannel = "reviews",
) -> BrandSourceObservation:
    name = str(listing.get("name") or listing.get("product_name") or listing.get("title") or "").strip()
    url = str(listing.get("url") or listing.get("source_url") or "").strip()
    review_count = _coerce_float(listing.get("review_count") or listing.get("reviews_count"), default=0.0)
    rating = _coerce_float(listing.get("rating"), default=0.0)
    text = str(listing.get("summary") or listing.get("text") or listing.get("description") or "").strip()
    if not name:
        return BrandSourceObservation(
            channel,
            "not_observed",
            _normalize_url(url) if url else "",
            provider,
            freshness=str(listing.get("updated_at") or "unknown"),
            reason="missing_review_listing_name",
        )
    if review_count >= 10 and len(text) >= 80:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url) if url else "",
            provider,
            name,
            str(listing.get("updated_at") or "unknown"),
            round(min(0.9, max(0.72, (rating / 5) if rating else 0.72)), 4),
            "eligible",
            "review_listing_with_volume_and_context",
        )
    if review_count > 0 or len(text) >= 40:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url) if url else "",
            provider,
            name,
            str(listing.get("updated_at") or "unknown"),
            0.55,
            "limited",
            "review_listing_with_limited_volume_or_context",
        )
    return BrandSourceObservation(
        channel,
        "observed",
        _normalize_url(url) if url else "",
        provider,
        name,
        str(listing.get("updated_at") or "unknown"),
        0.25,
        "ineligible",
        "review_listing_without_review_signal",
    )


def profile_source_observation(
    profile: dict[str, object],
    *,
    provider: str = "profile-source",
    channel: SourceChannel = "social",
) -> BrandSourceObservation:
    name = str(profile.get("name") or profile.get("handle") or profile.get("title") or "").strip()
    url = str(profile.get("url") or profile.get("profile_url") or "").strip()
    description = str(profile.get("description") or profile.get("bio") or profile.get("summary") or "").strip()
    verified = bool(profile.get("verified") or profile.get("is_verified"))
    follower_count = _coerce_float(profile.get("followers") or profile.get("follower_count"), default=0.0)
    freshness = str(profile.get("updated_at") or profile.get("captured_at") or "unknown").strip() or "unknown"
    if not name and not url:
        return BrandSourceObservation(
            channel,
            "not_observed",
            provider=provider,
            freshness=freshness,
            reason="missing_profile_identity",
        )
    if verified and len(description) >= 60:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url) if url else "",
            provider,
            name,
            freshness,
            0.82,
            "eligible",
            "verified_profile_with_context",
        )
    if verified or follower_count >= 1000 or len(description) >= 40:
        return BrandSourceObservation(
            channel,
            "observed",
            _normalize_url(url) if url else "",
            provider,
            name,
            freshness,
            0.58,
            "limited",
            "profile_with_partial_authority_or_context",
        )
    return BrandSourceObservation(
        channel,
        "observed",
        _normalize_url(url) if url else "",
        provider,
        name,
        freshness,
        0.22,
        "ineligible",
        "profile_without_authority_or_context",
    )


def evidence_item_from_observation(
    observation: BrandSourceObservation,
    text: str,
    *,
    kind: BrandEvidenceKind | None = None,
    supports: list[str] | None = None,
) -> BrandEvidenceItem:
    cleaned = " ".join(str(text or "").split())
    inferred_kind = kind or _evidence_kind_for_channel(observation.channel)
    limitations: list[str] = []
    if observation.evidence_eligibility == "ineligible" or observation.status != "observed":
        strength: EvidenceStrength = "blocked"
        limitations.append("source_not_evidence_eligible")
    elif len(cleaned) < 40:
        strength = "blocked"
        limitations.append("excerpt_too_short_for_evidence")
    elif observation.evidence_eligibility == "limited":
        strength = "weak"
        limitations.append("limited_source_context")
    elif observation.channel in {"owned_web", "parent_owned_web"}:
        strength = "moderate"
        limitations.append("owned_claim_not_external_validation")
    else:
        strength = "strong" if observation.confidence >= 0.75 else "moderate"
    return BrandEvidenceItem(
        evidence_id=_brand_evidence_id(inferred_kind, cleaned, observation.source_url, observation.provider),
        kind=inferred_kind,
        text=cleaned,
        source_channel=observation.channel,
        source_url=observation.source_url,
        provider=observation.provider,
        source_title=observation.title,
        quote=cleaned,
        attribution=_attribution_for_channel(observation.channel),
        strength=strength,
        confidence=observation.confidence,
        supports=_unique(supports or _supports_for_evidence_kind(inferred_kind)),
        limitations=_unique(limitations),
    )


def build_brand_evidence_graph(
    inventory: BrandSourceInventory,
    evidence_items: list[BrandEvidenceItem],
) -> BrandEvidenceGraph:
    accepted: list[BrandEvidenceItem] = []
    rejected: list[BrandEvidenceItem] = []
    seen_ids: set[str] = set()
    for item in evidence_items:
        if item.evidence_id in seen_ids:
            rejected.append(_reject_evidence_item(item, "duplicate_evidence_item"))
            continue
        seen_ids.add(item.evidence_id)
        if item.strength == "blocked":
            rejected.append(item)
            continue
        accepted.append(item)

    gaps = list(inventory.missing_required_channels)
    warnings = list(inventory.limitations)
    if not accepted:
        gaps.append("no_evidence_items")
    if not any(item.kind == "external_perception" for item in accepted):
        warnings.append("external_perception_not_evidenced")
    if not any(item.kind in {"owned_claim", "parent_owned_claim"} for item in accepted):
        warnings.append("owned_claims_not_evidenced")
    if inventory.duplicate_source_urls:
        warnings.append("evidence_graph_has_duplicate_source_risk")
    if inventory.conflicting_source_urls:
        warnings.append("evidence_graph_has_conflicting_source_risk")
    return BrandEvidenceGraph(
        resolved_name=inventory.resolved_name,
        evidence=accepted,
        rejected=rejected,
        gaps=_unique(gaps),
        warnings=_unique(warnings),
    )


def evaluate_brand_identity_bakeoff(cases: list[BrandIdentityBakeoffCase]) -> dict[str, object]:
    results = [_evaluate_identity_case(case) for case in cases]
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    known = [result for result in results if result.known_case]
    unknown = [result for result in results if not result.known_case]
    return {
        "version": IDENTITY_BAKEOFF_VERSION,
        "case_count": total,
        "passed_count": passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "known_case_count": len(known),
        "unknown_case_count": len(unknown),
        "known_accuracy": round(sum(1 for result in known if result.passed) / len(known), 4) if known else 0.0,
        "unknown_accuracy": round(sum(1 for result in unknown if result.passed) / len(unknown), 4) if unknown else 0.0,
        "misresolved_count": sum(1 for result in results if result.misresolved),
        "results": [result.to_dict() for result in results],
    }


def evaluate_brand_source_bakeoff(cases: list[BrandSourceBakeoffCase]) -> dict[str, object]:
    results = [_evaluate_source_case(case) for case in cases]
    provider_observations: dict[str, list[BrandSourceObservation]] = {}
    for case in cases:
        for observation in case.observations:
            provider_observations.setdefault(observation.provider or "unknown", []).append(observation)
    provider_metrics = {
        provider: _source_observation_metrics(observations)
        for provider, observations in sorted(provider_observations.items())
    }
    return {
        "version": SOURCE_OBSERVATION_BAKEOFF_VERSION,
        "case_count": len(results),
        "inventory_ready_count": sum(1 for result in results if result.inventory_ready),
        "provider_count": len(provider_metrics),
        "provider_metrics": provider_metrics,
        "results": [result.to_dict() for result in results],
    }


def _evaluate_source_case(case: BrandSourceBakeoffCase) -> BrandSourceBakeoffResult:
    inventory = build_brand_source_inventory(case.plan, case.observations)
    inventory_ready = not inventory.missing_required_channels and not case.plan.required_missing
    return BrandSourceBakeoffResult(
        case_id=case.case_id,
        inventory_ready=inventory_ready,
        missing_required_channels=inventory.missing_required_channels,
        eligible_channels=inventory.eligible_channels,
        provider_metrics=_provider_metrics_for_case(case.observations),
        inventory=inventory,
    )


def _evaluate_identity_case(case: BrandIdentityBakeoffCase) -> BrandIdentityBakeoffResult:
    resolution = resolve_brand_identity_from_signals(case.seed, case.signals)
    selected = resolution.selected_candidate
    actual_name = selected.name if selected else ""
    status_pass = resolution.status == case.expected_status
    name_pass = not case.expected_name or _normalize_name(actual_name) == _normalize_name(case.expected_name)
    passed = status_pass and name_pass
    misresolved = case.expected_status != "resolved" and resolution.status == "resolved"
    return BrandIdentityBakeoffResult(
        case_id=case.case_id,
        expected_status=case.expected_status,
        actual_status=resolution.status,
        expected_name=case.expected_name,
        actual_name=actual_name,
        passed=passed,
        known_case=case.known_case,
        misresolved=misresolved,
        resolution=resolution,
    )


def _provider_metrics_for_case(observations: list[BrandSourceObservation]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[BrandSourceObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.provider or "unknown", []).append(observation)
    return {
        provider: _source_observation_metrics(items)
        for provider, items in sorted(grouped.items())
    }


def _source_observation_metrics(observations: list[BrandSourceObservation]) -> dict[str, object]:
    eligible_observations = [
        observation
        for observation in observations
        if observation.status == "observed" and observation.evidence_eligibility in {"eligible", "limited"}
    ]
    confidence_values = [observation.confidence for observation in observations if observation.confidence > 0]
    return {
        "observation_count": len(observations),
        "observed_count": sum(1 for item in observations if item.status == "observed"),
        "eligible_count": sum(1 for item in observations if item.evidence_eligibility == "eligible"),
        "limited_count": sum(1 for item in observations if item.evidence_eligibility == "limited"),
        "ineligible_count": sum(1 for item in observations if item.evidence_eligibility == "ineligible"),
        "error_count": sum(1 for item in observations if item.status == "error"),
        "covered_channels": _unique([item.channel for item in eligible_observations]),
        "average_confidence": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
    }


def _reject_evidence_item(item: BrandEvidenceItem, reason: str) -> BrandEvidenceItem:
    return BrandEvidenceItem(
        evidence_id=item.evidence_id,
        kind=item.kind,
        text=item.text,
        source_channel=item.source_channel,
        source_url=item.source_url,
        provider=item.provider,
        source_title=item.source_title,
        quote=item.quote,
        attribution=item.attribution,
        strength="blocked",
        confidence=item.confidence,
        supports=list(item.supports),
        limitations=_unique(list(item.limitations) + [reason]),
    )


def _evidence_kind_for_channel(channel: SourceChannel) -> BrandEvidenceKind:
    return {
        "owned_web": "owned_claim",
        "parent_owned_web": "parent_owned_claim",
        "search": "external_context",
        "news": "external_context",
        "reviews": "external_perception",
        "linkedin": "profile_presence",
        "social": "profile_presence",
        "app_store": "distribution_signal",
        "visual": "visual_signal",
        "docs": "owned_claim",
        "community": "external_context",
        "jobs": "external_context",
    }.get(channel, "unknown")


def _supports_for_evidence_kind(kind: BrandEvidenceKind) -> list[str]:
    return {
        "owned_claim": ["brand_idea", "value_proposition"],
        "parent_owned_claim": ["brand_architecture", "brand_idea"],
        "external_context": ["category_context", "reputation"],
        "external_perception": ["perception", "proof"],
        "profile_presence": ["presence", "credibility"],
        "visual_signal": ["visual_identity"],
        "distribution_signal": ["availability", "product_reality"],
    }.get(kind, [])


def _attribution_for_channel(channel: SourceChannel) -> str:
    if channel in {"owned_web", "parent_owned_web", "docs"}:
        return "owned_self_declaration"
    if channel in {"reviews", "news", "search", "community", "jobs"}:
        return "external_observation"
    if channel in {"linkedin", "social", "app_store"}:
        return "profile_or_distribution_observation"
    if channel == "visual":
        return "observed_visual_surface"
    return "unknown_attribution"


def _duplicate_source_urls(observations: list[BrandSourceObservation]) -> list[str]:
    counts: dict[str, int] = {}
    for observation in observations:
        key = _source_url_key(observation.source_url)
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return sorted([url for url, count in counts.items() if count > 1])


def _conflicting_source_urls(observations: list[BrandSourceObservation]) -> list[str]:
    titles_by_url: dict[str, set[str]] = {}
    for observation in observations:
        key = _source_url_key(observation.source_url)
        title = _title_key(observation.title)
        if not key or not title:
            continue
        titles_by_url.setdefault(key, set()).add(title)
    return sorted([url for url, titles in titles_by_url.items() if len(titles) > 1])


def _identity_resolution(
    seed: BrandSeed,
    status: ResolutionStatus,
    candidates: list[BrandIdentityCandidate],
    *,
    selected: BrandIdentityCandidate | None,
    missing: list[str] | None = None,
    limitations: list[str] | None = None,
) -> BrandIdentityResolution:
    return BrandIdentityResolution(
        input_seed=seed,
        status=status,
        candidates=candidates,
        selected_candidate=selected,
        missing=_unique(missing or []),
        limitations=_unique(limitations or []),
    )


def _candidates_from_signals(signals: list[BrandIdentitySignal]) -> list[BrandIdentityCandidate]:
    grouped: dict[str, list[BrandIdentitySignal]] = {}
    for signal in signals:
        key = _normalize_name(signal.candidate_name)
        if not key:
            continue
        grouped.setdefault(key, []).append(signal)
    candidates = [_candidate_from_signal_group(items) for items in grouped.values()]
    return sorted(candidates, key=lambda candidate: candidate.confidence, reverse=True)


def _candidate_from_signal_group(signals: list[BrandIdentitySignal]) -> BrandIdentityCandidate:
    best = max(signals, key=lambda item: item.confidence)
    avg_confidence = sum(item.confidence for item in signals) / max(1, len(signals))
    corroboration_bonus = min(0.08, max(0, len({item.source for item in signals}) - 1) * 0.04)
    confidence = round(min(0.99, max(best.confidence, avg_confidence + corroboration_bonus)), 4)
    limitations: list[str] = []
    signal_names = {item.signal for item in signals}
    if "subdomain_surface" in signal_names or "domain_family_match" in signal_names:
        limitations.append("subdomain_surface_needs_parent_validation")
    if "ambiguous_name" in signal_names:
        limitations.extend(["name_only_ambiguous_entity", "requires_external_entity_resolution"])
    if "url_seed" in signal_names:
        limitations.extend(["url_seed_not_verified_as_brand", "requires_multichannel_validation"])
    return BrandIdentityCandidate(
        name=best.candidate_name,
        entity_type=_strongest_entity_type(signals),
        confidence=confidence,
        canonical_url=next((item.canonical_url for item in signals if item.canonical_url), ""),
        parent_brand=next((item.parent_brand for item in signals if item.parent_brand), None),
        parent_url=next((item.parent_url for item in signals if item.parent_url), None),
        product_name=next((item.product_name for item in signals if item.product_name), None),
        product_url=next((item.product_url for item in signals if item.product_url), None),
        evidence=[
            _evidence(item.source, item.signal or "identity_signal", item.value or item.candidate_name, item.confidence)
            for item in signals
        ],
        limitations=_unique(limitations),
    )


def _strongest_entity_type(signals: list[BrandIdentitySignal]) -> BrandEntityType:
    typed = [item for item in signals if item.entity_type != "unknown"]
    if not typed:
        return "unknown"
    return max(typed, key=lambda item: item.confidence).entity_type


def _resolution_status_for_candidate(candidate: BrandIdentityCandidate) -> ResolutionStatus:
    if candidate.confidence >= 0.82 and candidate.entity_type != "unknown" and not candidate.limitations:
        return "resolved"
    if candidate.confidence >= 0.2:
        return "provisional"
    return "unresolved"


def _entity_from_identity_resolution(identity: BrandIdentityResolution) -> ResolvedBrandEntity:
    seed = identity.input_seed
    candidate = identity.selected_candidate
    if candidate is None:
        return _unresolved(seed, identity.limitations[0] if identity.limitations else "insufficient_identity_signal", confidence=0.1)
    return ResolvedBrandEntity(
        requested_value=(seed.value or "").strip(),
        requested_kind=seed.kind,
        resolution_status=identity.status,
        resolved_name=candidate.name,
        entity_type=candidate.entity_type,
        analysis_mode=_analysis_mode_for_candidate(identity.status, candidate),
        confidence=candidate.confidence,
        canonical_url=candidate.canonical_url,
        parent_brand=candidate.parent_brand,
        parent_url=candidate.parent_url,
        product_name=candidate.product_name,
        product_url=candidate.product_url,
        evidence=list(candidate.evidence),
        limitations=_unique(list(candidate.limitations) + list(identity.limitations)),
    )


def _analysis_mode_for_candidate(status: ResolutionStatus, candidate: BrandIdentityCandidate) -> str:
    if status == "unresolved":
        return "unresolved_seed"
    if candidate.entity_type == "product" and candidate.parent_brand:
        return "product_with_parent"
    if candidate.entity_type == "ecosystem":
        return "ecosystem"
    if candidate.entity_type == "company" and candidate.confidence >= 0.8:
        return "company_brand_with_products" if candidate.name == "LangChain" else "company_brand"
    if "subdomain_surface_needs_parent_validation" in candidate.limitations:
        return "subdomain_or_lab_surface"
    if "name_only_ambiguous_entity" in candidate.limitations:
        return "ambiguous_name"
    return "url_seed_unverified_brand"


def _unresolved(seed: BrandSeed, reason: str, *, confidence: float) -> ResolvedBrandEntity:
    value = (seed.value or "").strip()
    return ResolvedBrandEntity(
        requested_value=value,
        requested_kind=seed.kind,
        resolution_status="unresolved",
        resolved_name=(seed.provided_name or value or "Unknown").strip(),
        entity_type="unknown",
        analysis_mode="unresolved_seed",
        confidence=confidence,
        evidence=[_evidence("input", reason, value, confidence)],
        limitations=[reason, "requires_multichannel_validation"],
    )


def _evidence(source: str, signal: str, value: str, confidence: float) -> dict[str, object]:
    return {"source": source, "signal": signal, "value": value, "confidence": confidence}


def _normalize_url(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path).lower()
    path = parsed.path if parsed.netloc else ""
    return f"{parsed.scheme or 'https'}://{host}{path}".rstrip("/")


def _source_url_key(value: str) -> str:
    normalized = _normalize_url(value)
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").rstrip("/")
    return f"https://{host}{path}"


def _brand_evidence_id(kind: str, text: str, source_url: str, provider: str) -> str:
    raw = "|".join([kind, text, _source_url_key(source_url), provider])
    return f"brand_ev_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def _host(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _root_domain(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if parts[-2:] == ["co", "uk"] and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _label_from_host(host: str) -> str:
    label = (host or "").split(".")[0].replace("-", " ")
    known = {"chatgpt": "ChatGPT", "langchain": "LangChain", "naturaumana": "Natura Umana"}
    return known.get(label.lower(), label.title() if label else "")


def _clean_candidate_name(value: str) -> str:
    cleaned = str(value or "").strip()
    for separator in (" | ", " - ", " – ", " — "):
        if separator in cleaned:
            cleaned = cleaned.split(separator, 1)[0].strip()
    return cleaned


def _candidate_from_search_title(title: str) -> str:
    value = _clean_candidate_name(title)
    for prefix in ("official ", "about "):
        if value.lower().startswith(prefix):
            value = value[len(prefix):].strip()
    return value


def _parent_from_text(text: str) -> str | None:
    low = (text or "").lower()
    if "openai" in low:
        return "OpenAI"
    if "anthropic" in low:
        return "Anthropic"
    return None


def _known_parent_url(parent: str | None) -> str | None:
    if parent == "OpenAI":
        return "https://openai.com"
    if parent == "Anthropic":
        return "https://anthropic.com"
    return None


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


def _title_key(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _coerce_float(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _looks_like_placeholder(root: str) -> bool:
    return root in {"example.com", "invalid", "test", "localhost"} or root.endswith(".invalid")


def _is_ambiguous_name(value: str) -> bool:
    return _normalize_name(value) in {"mercury", "atlas", "nova", "base", "linear", "frontier"}


def _search_label(entity: ResolvedBrandEntity) -> str:
    if entity.parent_brand and entity.product_name:
        return f"{entity.parent_brand} {entity.product_name}"
    return entity.resolved_name or entity.requested_value or "Unknown brand"


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
