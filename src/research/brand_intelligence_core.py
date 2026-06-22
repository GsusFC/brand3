"""Brand Intelligence source planning and evidence facade."""

from __future__ import annotations

from src.research.brand_intelligence import (
    BrandEntityType,
    BrandEvidenceGraph,
    BrandEvidenceItem,
    BrandIdentityBakeoffCase,
    BrandIdentityBakeoffResult,
    BrandIdentityCandidate,
    BrandIdentityResolution,
    BrandIdentitySignal,
    BrandSeed,
    BrandSourceBakeoffCase,
    BrandSourceBakeoffResult,
    BrandSourceInventory,
    BrandSourceObservation,
    BrandSourcePlan,
    BrandSourceRequest,
    BrandEvidenceKind,
    EvidenceEligibility,
    EvidenceStrength,
    IdentitySignalSource,
    ResolutionStatus,
    ResolvedBrandEntity,
    SeedKind,
    SourceChannel,
    SourceObservationStatus,
    BRAND_EVIDENCE_GRAPH_CONTRACT_VERSION,
    ENTITY_CONTRACT_VERSION,
    IDENTITY_BAKEOFF_VERSION,
    IDENTITY_RESOLUTION_CONTRACT_VERSION,
    SEED_CONTRACT_VERSION,
    SOURCE_INVENTORY_CONTRACT_VERSION,
    SOURCE_OBSERVATION_BAKEOFF_VERSION,
    SOURCE_PLAN_CONTRACT_VERSION,
)
from src.research.brand_intelligence_core_support import (
    build_brand_evidence_graph as _build_brand_evidence_graph,
    build_brand_source_inventory as _build_brand_source_inventory,
    build_brand_source_plan as _build_brand_source_plan,
    evaluate_brand_identity_bakeoff as _evaluate_brand_identity_bakeoff,
    evaluate_brand_source_bakeoff as _evaluate_brand_source_bakeoff,
    evidence_item_from_observation as _evidence_item_from_observation,
    owned_web_source_observation as _owned_web_source_observation,
    plan_brand_intelligence as _plan_brand_intelligence,
    profile_source_observation as _profile_source_observation,
    review_source_observation as _review_source_observation,
    scope_external_observation_to_entity as _scope_external_observation_to_entity,
    search_source_observation as _search_source_observation,
)

__all__ = [
    "BRAND_EVIDENCE_GRAPH_CONTRACT_VERSION",
    "ENTITY_CONTRACT_VERSION",
    "IDENTITY_BAKEOFF_VERSION",
    "IDENTITY_RESOLUTION_CONTRACT_VERSION",
    "SEED_CONTRACT_VERSION",
    "SOURCE_INVENTORY_CONTRACT_VERSION",
    "SOURCE_OBSERVATION_BAKEOFF_VERSION",
    "SOURCE_PLAN_CONTRACT_VERSION",
    "BrandEntityType",
    "BrandEvidenceGraph",
    "BrandEvidenceItem",
    "BrandIdentityBakeoffCase",
    "BrandIdentityBakeoffResult",
    "BrandIdentityCandidate",
    "BrandIdentityResolution",
    "BrandIdentitySignal",
    "BrandSeed",
    "BrandSourceBakeoffCase",
    "BrandSourceBakeoffResult",
    "BrandSourceInventory",
    "BrandSourceObservation",
    "BrandSourcePlan",
    "BrandSourceRequest",
    "BrandEvidenceKind",
    "EvidenceEligibility",
    "EvidenceStrength",
    "IdentitySignalSource",
    "ResolutionStatus",
    "ResolvedBrandEntity",
    "SeedKind",
    "SourceChannel",
    "SourceObservationStatus",
    "build_brand_source_plan",
    "plan_brand_intelligence",
    "build_brand_source_inventory",
    "search_source_observation",
    "scope_external_observation_to_entity",
    "owned_web_source_observation",
    "review_source_observation",
    "profile_source_observation",
    "evidence_item_from_observation",
    "build_brand_evidence_graph",
    "evaluate_brand_identity_bakeoff",
    "evaluate_brand_source_bakeoff",
]


def build_brand_source_plan(entity: ResolvedBrandEntity) -> BrandSourcePlan:
    return _build_brand_source_plan(entity)


def plan_brand_intelligence(seed: BrandSeed) -> tuple[ResolvedBrandEntity, BrandSourcePlan]:
    return _plan_brand_intelligence(seed)


def build_brand_source_inventory(
    plan: BrandSourcePlan,
    observations: list[BrandSourceObservation],
) -> BrandSourceInventory:
    return _build_brand_source_inventory(plan, observations)


def search_source_observation(
    result: dict[str, object],
    *,
    provider: str = "exa",
    channel: SourceChannel = "search",
) -> BrandSourceObservation:
    return _search_source_observation(result, provider=provider, channel=channel)


def scope_external_observation_to_entity(
    observation: BrandSourceObservation,
    result: dict[str, object],
    *,
    entity: ResolvedBrandEntity,
    seed_url: str = "",
    brand: str = "",
) -> BrandSourceObservation:
    return _scope_external_observation_to_entity(
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
    return _owned_web_source_observation(capture, provider=provider, channel=channel)


def review_source_observation(
    listing: dict[str, object],
    *,
    provider: str = "review-source",
    channel: SourceChannel = "reviews",
) -> BrandSourceObservation:
    return _review_source_observation(listing, provider=provider, channel=channel)


def profile_source_observation(
    profile: dict[str, object],
    *,
    provider: str = "profile-source",
    channel: SourceChannel = "social",
) -> BrandSourceObservation:
    return _profile_source_observation(profile, provider=provider, channel=channel)


def evidence_item_from_observation(
    observation: BrandSourceObservation,
    text: str,
    *,
    kind: BrandEvidenceKind | None = None,
    supports: list[str] | None = None,
) -> BrandEvidenceItem:
    return _evidence_item_from_observation(observation, text, kind=kind, supports=supports)


def build_brand_evidence_graph(
    inventory: BrandSourceInventory,
    evidence_items: list[BrandEvidenceItem],
) -> BrandEvidenceGraph:
    return _build_brand_evidence_graph(inventory, evidence_items)


def evaluate_brand_identity_bakeoff(cases: list[BrandIdentityBakeoffCase]) -> dict[str, object]:
    return _evaluate_brand_identity_bakeoff(cases)


def evaluate_brand_source_bakeoff(cases: list[BrandSourceBakeoffCase]) -> dict[str, object]:
    return _evaluate_brand_source_bakeoff(cases)
