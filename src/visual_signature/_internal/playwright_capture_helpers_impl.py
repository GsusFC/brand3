"""Internal helpers for the Playwright capture runtime."""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.playwright_capture_dismissal_support import COMMON_DISMISS_IGNORED_TERMS
from src.visual_signature._internal.playwright_capture_dismissal_support import COOKIE_DISMISS_PHRASES
from src.visual_signature._internal.playwright_capture_dismissal_support import DISMISSAL_TARGET_SELECTOR
from src.visual_signature._internal.playwright_capture_dismissal_support import NEWSLETTER_DISMISS_PHRASES
from src.visual_signature._internal.playwright_capture_dismissal_support import affordance_evidence_for_element as _affordance_evidence_for_element_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import affordance_id as _affordance_id_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import affordance_localization_evidence_for_element as _affordance_localization_evidence_for_element_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import attempt_obstruction_dismissal as _attempt_obstruction_dismissal_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import attempt_obstruction_dismissal_with_discovery as _attempt_obstruction_dismissal_with_discovery_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import attribute_value as _attribute_value_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import contains_phrase as _contains_phrase_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import discover_dismissal_targets as _discover_dismissal_targets_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import dismissal_context_type_for as _dismissal_context_type_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import dismissal_eligibility as _dismissal_eligibility_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import dismissal_patterns_for_type as _dismissal_patterns_for_type_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import dismissal_skip_note as _dismissal_skip_note_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import dismissal_successful as _dismissal_successful_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import element_intersects_current_viewport as _element_intersects_current_viewport_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import element_label as _element_label_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import element_localization_snapshot as _element_localization_snapshot_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import find_dismissal_candidate as _find_dismissal_candidate_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import has_cookie_consent_signal as _has_cookie_consent_signal_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import is_concise_dismissal_label as _is_concise_dismissal_label_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import is_safe_dismissal_candidate_fields as _is_safe_dismissal_candidate_fields_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import localization_context_terms as _localization_context_terms_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import match_dismissal_pattern as _match_dismissal_pattern_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import normalize_label as _normalize_label_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import prepare_perceptual_state_machine as _prepare_perceptual_state_machine_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import rejection_reason as _rejection_reason_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import severity_rank as _severity_rank_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import should_attempt_obstruction_dismissal as _should_attempt_obstruction_dismissal_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import should_record_rejected_click_target as _should_record_rejected_click_target_impl
from src.visual_signature._internal.playwright_capture_dismissal_support import split_context_tokens as _split_context_tokens_impl
from src.visual_signature._internal.playwright_capture_helpers_capture_runtime import (
    _coerce_dict_or_none,
    _coerce_transition_list,
    _derived_capture_path,
    _snapshot_for_path,
    _visible_obstruction_dom_snapshot,
)

def _prepare_perceptual_state_machine(
    *,
    page: Any,
    raw_snapshot: dict[str, Any],
    raw_artifact_ref: str,
    attempt_dismiss_obstructions: bool,
) -> dict[str, Any] | None:
    return _prepare_perceptual_state_machine_impl(
        page=page,
        raw_snapshot=raw_snapshot,
        raw_artifact_ref=raw_artifact_ref,
        attempt_dismiss_obstructions=attempt_dismiss_obstructions,
    )


def _attempt_obstruction_dismissal(page: Any, obstruction: dict[str, Any] | None) -> dict[str, Any]:
    return _attempt_obstruction_dismissal_impl(page, obstruction)


def _attempt_obstruction_dismissal_with_discovery(
    page: Any,
    obstruction: dict[str, Any] | None,
    discovery: dict[str, Any],
) -> dict[str, Any]:
    return _attempt_obstruction_dismissal_with_discovery_impl(page, obstruction, discovery)


def _discover_dismissal_targets(page: Any, obstruction: dict[str, Any] | None) -> dict[str, Any]:
    return _discover_dismissal_targets_impl(page, obstruction)


def _is_safe_dismissal_candidate_fields(*, affordance_policy: str, affordance_owner: str) -> bool:
    return _is_safe_dismissal_candidate_fields_impl(
        affordance_policy=affordance_policy,
        affordance_owner=affordance_owner,
    )


def _should_record_rejected_click_target(
    record: dict[str, Any],
    *,
    normalized_label: str,
    patterns: tuple[tuple[str, str], ...],
    has_dismissal_match: bool,
) -> bool:
    return _should_record_rejected_click_target_impl(
        record,
        normalized_label=normalized_label,
        patterns=patterns,
        has_dismissal_match=has_dismissal_match,
    )


def _should_attempt_obstruction_dismissal(obstruction: dict[str, Any] | None) -> bool:
    return _should_attempt_obstruction_dismissal_impl(obstruction)


def _dismissal_eligibility(obstruction: dict[str, Any] | None) -> str:
    return _dismissal_eligibility_impl(obstruction)


def _dismissal_patterns_for_type(obstruction_type: str) -> tuple[tuple[str, str], ...]:
    return _dismissal_patterns_for_type_impl(obstruction_type)


def _dismissal_context_type(obstruction: dict[str, Any] | None) -> str:
    return _dismissal_context_type_impl(obstruction)


def _has_cookie_consent_signal(obstruction: dict[str, Any] | None) -> bool:
    return _has_cookie_consent_signal_impl(obstruction)


def _match_dismissal_pattern(normalized: str, patterns: tuple[tuple[str, str], ...]) -> dict[str, str] | None:
    return _match_dismissal_pattern_impl(normalized, patterns)


def _contains_phrase(text: str, phrase: str) -> bool:
    return _contains_phrase_impl(text, phrase)


def _is_concise_dismissal_label(normalized: str) -> bool:
    return _is_concise_dismissal_label_impl(normalized)


def _rejection_reason(normalized: str, obstruction_type: str) -> str | None:
    return _rejection_reason_impl(normalized, obstruction_type)


def _dismissal_skip_note(obstruction: dict[str, Any] | None) -> str:
    return _dismissal_skip_note_impl(obstruction)


def _affordance_evidence_for_element(element: Any, label: str, obstruction_type: str) -> dict[str, Any]:
    return _affordance_evidence_for_element_impl(element, label, obstruction_type)


def _affordance_localization_evidence_for_element(
    element: Any,
    label: str,
    obstruction: dict[str, Any] | None,
    *,
    dismissal_context_type: str | None = None,
) -> dict[str, Any]:
    return _affordance_localization_evidence_for_element_impl(
        element,
        label,
        obstruction,
        dismissal_context_type=dismissal_context_type,
    )


def _element_localization_snapshot(element: Any) -> dict[str, Any]:
    return _element_localization_snapshot_impl(element)


def _element_intersects_current_viewport(element: Any) -> bool:
    return _element_intersects_current_viewport_impl(element)


def _localization_context_terms(obstruction: dict[str, Any] | None) -> list[str]:
    return _localization_context_terms_impl(obstruction)


def _attribute_value(element: Any, attr: str) -> str:
    return _attribute_value_impl(element, attr)


def _affordance_id(obstruction_type: str, normalized_label: str, index: int) -> str:
    return _affordance_id_impl(obstruction_type, normalized_label, index)


def _split_context_tokens(value: str) -> list[str]:
    return _split_context_tokens_impl(value)


def _find_dismissal_candidate(page: Any) -> dict[str, Any] | None:
    return _find_dismissal_candidate_impl(page)


def _element_label(element: Any) -> str:
    return _element_label_impl(element)


def _normalize_label(value: str) -> str:
    return _normalize_label_impl(value)


def _dismissal_successful(before: dict[str, Any] | None, after: dict[str, Any] | None) -> bool:
    return _dismissal_successful_impl(before, after)


def _severity_rank(value: str) -> int:
    return _severity_rank_impl(value)
