"""Compatibility facade for evidence vNext workflow helpers."""

from __future__ import annotations

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
    _changed_material_field_previews,
    _compact_review_observations,
    _context_url_identity,
    _count_dict,
    _dedupe_overlap_items,
    _host,
    _join_unique,
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
from src.research.evidence_vnext_report_work_orders import (
    _adjudication_intake,
    _dominant_count_key,
    _intervention_packet,
    _intervention_packets,
    _intervention_profile,
    _readiness_intervention_type,
    _readiness_matrix,
    _readiness_row,
    _shadow_policy_action_counts,
    _shadow_policy_next_action,
    _shadow_policy_runs,
    _work_order_expected_output,
    _work_orders,
)

PROMOTION_MAX_LIMITED_REVIEW_COUNT = 3
PROMOTION_MAX_LIMITED_MISSING_URL_COUNT = 2
PROMOTION_BLOCKING_REVIEW_REASONS = {"same_name_different_root_domain"}
MANUAL_AUDIT_MATERIAL_FIELDS = {"proof_points", "founder_or_press_context", "competitive_context"}
RESERVED_OR_PLACEHOLDER_ROOTS = {"example.com", "example.net", "example.org", "example.edu"}
RESERVED_OR_PLACEHOLDER_TLDS = {"example", "invalid", "localhost", "test"}
