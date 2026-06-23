"""Brand Intelligence Acquisition contracts.

This module is intentionally parallel to the current Brand Audit pipeline. It
does not call providers, does not alter scoring, and does not feed UI. Its job
is to define the first-mile research contract where a URL is only one possible
seed for a brand investigation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Literal
from urllib.parse import urlparse
import hashlib
import re


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
    query_intent: str = ""
    source_class: str = ""
    relation_to_entity: str = ""
    requires_human_review: bool = False
    cost_estimate: float | None = None
    latency_ms: int = 0
    diagnostics: dict[str, object] = field(default_factory=dict)

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
    from src.research.brand_intelligence_identity import resolve_brand_seed as _impl

    return _impl(seed)


def resolve_brand_identity(seed: BrandSeed) -> BrandIdentityResolution:
    from src.research.brand_intelligence_identity import resolve_brand_identity as _impl

    return _impl(seed)


def resolve_brand_identity_from_signals(
    seed: BrandSeed,
    signals: list[BrandIdentitySignal],
) -> BrandIdentityResolution:
    from src.research.brand_intelligence_identity import resolve_brand_identity_from_signals as _impl

    return _impl(seed, signals)


def identity_signals_for_seed(seed: BrandSeed) -> list[BrandIdentitySignal]:
    from src.research.brand_intelligence_identity import identity_signals_for_seed as _impl

    return _impl(seed)


def domain_identity_signal(url: str, *, provided_name: str = "") -> BrandIdentitySignal | None:
    from src.research.brand_intelligence_identity import domain_identity_signal as _impl

    return _impl(url, provided_name=provided_name)


def owned_web_identity_signal(payload: dict[str, object]) -> BrandIdentitySignal | None:
    from src.research.brand_intelligence_identity import owned_web_identity_signal as _impl

    return _impl(payload)


def search_result_identity_signal(result: dict[str, object]) -> BrandIdentitySignal | None:
    from src.research.brand_intelligence_identity import search_result_identity_signal as _impl

    return _impl(result)


def linkedin_identity_signal(profile: dict[str, object]) -> BrandIdentitySignal | None:
    from src.research.brand_intelligence_identity import linkedin_identity_signal as _impl

    return _impl(profile)


def review_identity_signal(listing: dict[str, object]) -> BrandIdentitySignal | None:
    from src.research.brand_intelligence_identity import review_identity_signal as _impl

    return _impl(listing)


def build_brand_source_plan(entity: ResolvedBrandEntity) -> BrandSourcePlan:
    from src.research.brand_intelligence_core import build_brand_source_plan as _impl

    return _impl(entity)


def plan_brand_intelligence(seed: BrandSeed) -> tuple[ResolvedBrandEntity, BrandSourcePlan]:
    from src.research.brand_intelligence_core import plan_brand_intelligence as _impl

    return _impl(seed)


def build_brand_source_inventory(
    plan: BrandSourcePlan,
    observations: list[BrandSourceObservation],
) -> BrandSourceInventory:
    from src.research.brand_intelligence_core import build_brand_source_inventory as _impl

    return _impl(plan, observations)


def search_source_observation(
    result: dict[str, object],
    *,
    provider: str = "exa",
    channel: SourceChannel = "search",
) -> BrandSourceObservation:
    from src.research.brand_intelligence_core import search_source_observation as _impl

    return _impl(result, provider=provider, channel=channel)


def scope_external_observation_to_entity(
    observation: BrandSourceObservation,
    result: dict[str, object],
    *,
    entity: ResolvedBrandEntity,
    seed_url: str = "",
    brand: str = "",
) -> BrandSourceObservation:
    from src.research.brand_intelligence_core import scope_external_observation_to_entity as _impl

    return _impl(
        observation,
        result,
        entity=entity,
        seed_url=seed_url,
        brand=brand,
    )


def owned_web_source_observation(
    capture: dict[str, object],
    *,
    provider: str = "firecrawl",
    channel: SourceChannel = "owned_web",
) -> BrandSourceObservation:
    from src.research.brand_intelligence_core import owned_web_source_observation as _impl

    return _impl(capture, provider=provider, channel=channel)


def review_source_observation(
    listing: dict[str, object],
    *,
    provider: str = "review-source",
    channel: SourceChannel = "reviews",
) -> BrandSourceObservation:
    from src.research.brand_intelligence_core import review_source_observation as _impl

    return _impl(listing, provider=provider, channel=channel)


def profile_source_observation(
    profile: dict[str, object],
    *,
    provider: str = "profile-source",
    channel: SourceChannel = "social",
) -> BrandSourceObservation:
    from src.research.brand_intelligence_core import profile_source_observation as _impl

    return _impl(profile, provider=provider, channel=channel)


def evidence_item_from_observation(
    observation: BrandSourceObservation,
    text: str,
    *,
    kind: BrandEvidenceKind | None = None,
    supports: list[str] | None = None,
) -> BrandEvidenceItem:
    from src.research.brand_intelligence_core import evidence_item_from_observation as _impl

    return _impl(observation, text, kind=kind, supports=supports)


def build_brand_evidence_graph(
    inventory: BrandSourceInventory,
    evidence_items: list[BrandEvidenceItem],
) -> BrandEvidenceGraph:
    from src.research.brand_intelligence_core import build_brand_evidence_graph as _impl

    return _impl(inventory, evidence_items)


def evaluate_brand_identity_bakeoff(cases: list[BrandIdentityBakeoffCase]) -> dict[str, object]:
    from src.research.brand_intelligence_core import evaluate_brand_identity_bakeoff as _impl

    return _impl(cases)


def evaluate_brand_source_bakeoff(cases: list[BrandSourceBakeoffCase]) -> dict[str, object]:
    from src.research.brand_intelligence_core import evaluate_brand_source_bakeoff as _impl

    return _impl(cases)
