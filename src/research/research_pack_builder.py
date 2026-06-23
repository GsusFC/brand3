"""Build BrandResearchPack objects from the Brand Research evidence graph."""

from __future__ import annotations

from src.reports.brand_research_pack import (
    BrandResearchPack,
    EntityResolution,
    ResearchEvidence,
    ResearchSource,
)
from src.research.evidence_graph import EvidenceClaim, EvidenceGraph
from src.research.research_pack_builder_helpers import (
    _competitive_context_evidence,
    _company_summary_text,
    _first_claim_text,
    _offer_text,
    _product_summary_text,
    _research_evidence,
)
from src.research.research_pack_builder_text_helpers import (
    _audience_text,
    _attribute_signals,
    _category_from_graph,
    _claim_texts,
    _confidence_notes,
    _concept_signals,
    _evidence_gaps,
    _infer_outcome,
    _official_urls,
    _pack_entity_type,
    _pack_source_type,
    _primary_entity_scope,
    _primary_surface_role,
    _signal_texts,
    _tone_summary,
    _unique,
)
from src.research.research_pack_builder_text_preprocessing import _normalize_research_pack_text as _normalize_research_pack_text


def build_brand_research_pack_from_graph(graph: EvidenceGraph) -> BrandResearchPack:
    """Adapt the BrandResearch EvidenceGraph into the existing pack contract.

    This bridge lets downstream TLDR code consume the new research substrate
    without forcing a rewrite of the current Magnetism integration.
    """

    resolved = EntityResolution(
        resolved_entity=graph.run.resolved_entity or graph.run.brand_name,
        entity_type=_pack_entity_type(graph.run.entity_type),
        canonical_url=graph.run.input_url,
        parent_brand=graph.run.parent_brand,
        surface_role=_primary_surface_role(graph),
        entity_scope=_primary_entity_scope(graph),
        confidence=graph.run.confidence,
        notes=list(graph.run.notes),
    )
    source_map = {
        source.url: ResearchSource(
            url=source.url,
            source_type=_pack_source_type(source.source_type),
            label=source.label,
            surface_role=source.surface_role,
            entity_scope=source.entity_scope,
            title=source.title,
            notes=list(source.notes),
        )
        for source in graph.sources.values()
        if source.url
    }
    claims = [claim for claim in graph.claims if claim.claim_type != "noise"]
    proof_points = _research_evidence(
        [claim for claim in graph.claims if claim.claim_type in {"proof", "feature_evidence"}],
        kind="proof",
    )
    founder_or_press_context = _research_evidence(
        [claim for claim in graph.claims if claim.claim_type == "founder_press"],
        kind="context",
    )
    competitive_context = _competitive_context_evidence(graph)
    noise_rejected = _research_evidence(
        [claim for claim in graph.claims if claim.claim_type == "noise"],
        kind="noise",
    )
    offer = _offer_text(claims, graph=graph)
    product_summary = _normalize_research_pack_text(
        _product_summary_text(claims) or offer or _first_claim_text(claims, ("hero_claim", "outcome"))
    )
    company_summary = _normalize_research_pack_text(_company_summary_text(claims, graph=graph) or offer)
    outcome = _first_claim_text(claims, ("outcome",)) or _infer_outcome([offer, product_summary, company_summary])
    audience = _audience_text(claims, [offer, product_summary, company_summary, outcome])
    declared_mission = _first_claim_text(claims, ("mission",))
    future_direction = _first_claim_text(claims, ("vision",))
    signal_texts = _signal_texts(claims)
    personality_signals = _unique(
        _claim_texts(claims, ("personality",), limit=6)
        + _attribute_signals([product_summary, offer, company_summary] + signal_texts)
    )[:6]
    visual_or_conceptual_signals = _unique(
        _claim_texts(claims, ("hero_claim",), limit=6)
        + _concept_signals([company_summary, product_summary, offer, declared_mission, future_direction])
    )[:6]
    values_signals = _claim_texts(claims, ("values",), limit=6, reject_form_noise=True)
    attributes_signals = _unique(
        values_signals
        + _claim_texts(claims, ("personality",), limit=6, reject_form_noise=True)
        + _attribute_signals([company_summary, product_summary, offer, outcome, declared_mission] + signal_texts)
    )[:8]
    category = _category_from_graph(graph, offer=offer, product_summary=product_summary, company_summary=company_summary)
    evidence_gaps = _evidence_gaps(
        graph=graph,
        offer=offer,
        audience=audience,
        outcome=outcome,
        mission=declared_mission,
        proof_points=proof_points,
        official_urls=_official_urls(graph),
        company_summary=company_summary,
        product_summary=product_summary,
    )

    return BrandResearchPack(
        version="brand_research_pack_v0_1",
        input_url=graph.run.input_url,
        resolved_entity=resolved,
        entity_type=resolved.entity_type,
        parent_brand=graph.run.parent_brand,
        official_urls=_official_urls(graph),
        analyzed_urls=[source.url for source in graph.sources.values() if source.url],
        source_map=source_map,
        company_summary=company_summary,
        product_summary=product_summary,
        audience=audience,
        offer=offer,
        outcome=outcome,
        category=category,
        declared_purpose=_first_claim_text(claims, ("mission", "hero_claim")),
        declared_mission=declared_mission,
        future_direction=future_direction,
        tone_of_voice=_tone_summary(personality_signals, [product_summary, offer, company_summary]),
        personality_signals=personality_signals,
        visual_or_conceptual_signals=visual_or_conceptual_signals,
        values_signals=values_signals,
        attributes_signals=attributes_signals,
        proof_points=proof_points,
        founder_or_press_context=founder_or_press_context,
        competitive_context=competitive_context,
        noise_rejected=noise_rejected,
        shadow_sources=[dict(item) for item in graph.shadow_sources if isinstance(item, dict)],
        evidence_gaps=evidence_gaps,
        confidence_notes=_confidence_notes(graph),
    )
