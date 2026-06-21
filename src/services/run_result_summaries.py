"""Build run result summaries and audit context."""

from __future__ import annotations


def _build_run_result_summaries(
    *,
    service,
    store,
    web_data,
    content_web,
    exa_data,
    content_source: str,
    data_quality: str,
    social_data,
    llm,
    llm_skipped_reason,
    calibration_profile: str,
    niche_classification: dict,
    research_pack_for_feature_prompts,
    discovery_trust_basis: dict,
    context_data,
    features_by_dim: dict,
    brand_score,
) -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    dimension_confidence = service._dimension_confidence_summary(
        features_by_dim,
        evidence_items=service._context_evidence_items(context_data),
        data_quality=data_quality,
        context_data=context_data,
    )
    evidence_summary = service.summarize_evidence_from_features(
        features_by_dim,
        evidence_items=service._context_evidence_items(context_data),
    )
    confidence_summary = service._context_confidence_summary(context_data)
    llm_cache = service._llm_cache_summary(llm, llm_skipped_reason)
    public_presence_inventory = service._public_presence_inventory_summary(
        brand_name=brand_score.brand_name,
        url=brand_score.url,
        web_data=web_data,
        content_web=content_web,
        content_source=content_source,
        exa_data=exa_data,
        context_data=context_data,
    )
    context_enrichment_summary = service._context_enrichment_summary(
        public_presence_inventory=public_presence_inventory,
        context_summary=confidence_summary,
    )
    context_effective_readiness = service._context_effective_readiness(
        public_presence_inventory=public_presence_inventory,
        context_summary=confidence_summary,
    )
    trust_summary = service._trust_summary_payload(
        data_quality=data_quality,
        context_summary=confidence_summary,
        evidence_summary=evidence_summary,
        dimension_confidence=dimension_confidence,
        context_enrichment_summary=context_enrichment_summary,
        context_effective_readiness=context_effective_readiness,
    )
    trust_summary["evidence_basis_summary"] = discovery_trust_basis["user_message"]
    run_audit_context = (
        service._build_run_audit_context(
            store,
            calibration_profile=calibration_profile,
            niche_classification=niche_classification,
        )
        if store
        else service._build_run_audit_context(
            calibration_profile=calibration_profile,
            niche_classification=niche_classification,
        )
    )
    run_audit_context["executive_analysis_v2"] = service.run_brand_audit_analyst_pass(
        llm=service._audit_analyst_llm(llm),
        brand_name=brand_score.brand_name,
        url=brand_score.url,
        research_pack=research_pack_for_feature_prompts,
        dimensions=brand_score.breakdown,
        features_by_dim=features_by_dim,
    )
    return (
        dimension_confidence,
        evidence_summary,
        confidence_summary,
        llm_cache,
        public_presence_inventory,
        context_enrichment_summary,
        context_effective_readiness,
        trust_summary,
    ), run_audit_context
