"""Facade for evidence vNext batch report building."""

from __future__ import annotations

from src.research import evidence_vnext_report_batch as _batch
from src.research.evidence_vnext_report_decisions import (
    _append_projected_reason_decision,
    _blocked_evidence_queue_item,
    _contract_projection_row,
    _contract_projection_summary,
    _contract_recommendations,
    _decision_action_counts,
    _decision_queue,
    _is_projected_contract_filtered_observation,
    _is_projected_missing_url_contract_observation,
    _is_projected_social_placeholder_contract_observation,
    _is_reserved_or_placeholder_entity,
    _manual_audit_profile,
    _manual_audit_queue_item,
    _material_quote_contract_queue_item,
    _promotion_after_manual_audit,
    _provider_contract_is_implemented,
    _quote_material_impact,
    _quote_source_review_queue_item,
    _projected_applied_contracts,
    _projected_gate_summary,
    _removed_review_reason_counts,
    _run_manual_audit_decision,
    _run_promotion_decision,
    _social_placeholder_auto_cleared_runs,
    _triage_actions,
)
from src.research.evidence_vnext_report_helpers import (
    _accumulate_semantic_evidence,
    _accumulate_semantic_llm_comparison,
    _batch_recommendation,
    _changed_material_field_previews,
    _collect_examples,
    _compact_review_observations,
    _context_url_identity,
    _count_dict,
    _dedupe_overlap_items,
    _host,
    _join_unique,
    _merge_counts,
    _normalized_overlap_text,
    _observation_reason,
    _pack_field_text,
    _preview_text,
    _review_material_overlaps,
    _root_domain,
    _text_overlaps_field,
    _top_counts,
    _unique,
    _url_identity,
)
from src.research.evidence_vnext_report_projection import (
    _manual_audit_profile as _projection_manual_audit_profile,
    _manual_audit_queue_item as _projection_manual_audit_queue_item,
    _run_manual_audit_decision as _projection_run_manual_audit_decision,
    _run_promotion_decision as _projection_run_promotion_decision,
)
from src.research.evidence_vnext_report_work_orders import (
    _adjudication_intake,
    _intervention_packets,
    _readiness_matrix,
    _shadow_policy_action_counts,
    _shadow_policy_runs,
    _work_orders,
)

for _name in dir(_batch):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_batch, _name)

del _name
del _batch

