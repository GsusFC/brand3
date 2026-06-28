"""Dismissal and perceptual-state helpers for the Playwright capture runtime."""

from __future__ import annotations

from typing import Any

from src.visual_signature.affordance_semantics import classify_affordance
from src.visual_signature.affordance_semantics import classify_affordance_owner
from src.visual_signature._internal.playwright_capture_dismissal_elements import (
    attribute_value,
    element_intersects_current_viewport,
    element_label,
    element_localization_snapshot,
)
from src.visual_signature._internal.playwright_capture_dismissal_rules import (
    DISMISSAL_TARGET_SELECTOR,
    contains_phrase,
    dismissal_context_type_for,
    dismissal_eligibility,
    dismissal_patterns_for_type,
    dismissal_skip_note,
    find_dismissal_patterns,
    has_cookie_consent_signal,
    match_dismissal_pattern,
    normalize_label,
    rejection_reason,
    should_attempt_obstruction_dismissal,
    split_context_tokens,
)
from src.visual_signature._internal.utils import float_or_none as _float_or_none
from src.visual_signature.perception import PerceptualStateMachine


def prepare_perceptual_state_machine(
    *,
    page: Any,
    raw_snapshot: dict[str, Any],
    raw_artifact_ref: str,
    attempt_dismiss_obstructions: bool,
) -> dict[str, Any] | None:
    if not attempt_dismiss_obstructions:
        return None

    obstruction = raw_snapshot.get("obstruction") if isinstance(raw_snapshot, dict) else None
    machine = PerceptualStateMachine.from_raw_capture(
        evidence_refs=[raw_artifact_ref],
        notes=["raw_viewport_preserved_as_primary_evidence"],
    )
    machine.classify_obstruction(
        obstruction if isinstance(obstruction, dict) else None,
        evidence_refs=[raw_artifact_ref],
    )

    if not isinstance(obstruction, dict) or obstruction.get("present") is not True:
        return {"machine": machine, "discovery": None, "eligibility": None}
    if machine.current_state == "UNSAFE_MUTATION_BLOCKED" or str(obstruction.get("type") or "") == "unknown_overlay":
        return {"machine": machine, "discovery": None, "eligibility": machine.current_state}

    discovery = discover_dismissal_targets(page, obstruction)
    affordance_labels = [str(item.get("label") or "") for item in discovery.get("candidate_click_targets") or [] if isinstance(item, dict)]
    eligibility = machine.evaluate_eligibility(
        obstruction,
        affordance_labels=affordance_labels,
        evidence_refs=[raw_artifact_ref],
    )
    return {"machine": machine, "discovery": discovery, "eligibility": eligibility}


def attempt_obstruction_dismissal(page: Any, obstruction: dict[str, Any] | None) -> dict[str, Any]:
    discovery = discover_dismissal_targets(page, obstruction)
    return attempt_obstruction_dismissal_with_discovery(page, obstruction, discovery)


def attempt_obstruction_dismissal_with_discovery(
    page: Any,
    obstruction: dict[str, Any] | None,
    discovery: dict[str, Any],
) -> dict[str, Any]:
    if not discovery["eligible"]:
        return {
            "attempted": False,
            "successful": False,
            "method": None,
            "clicked_text": None,
            "note": discovery["block_reason"] or dismissal_skip_note(obstruction),
            "dismissal_eligibility": discovery["dismissal_eligibility"],
            "dismissal_block_reason": discovery["block_reason"],
            "candidate_click_targets": discovery["candidate_click_targets"],
            "rejected_click_targets": discovery["rejected_click_targets"],
        }

    candidate = discovery["selected_candidate"]
    if candidate is None:
        return {
            "attempted": False,
            "successful": False,
            "method": None,
            "clicked_text": None,
            "note": discovery["block_reason"] or dismissal_skip_note(obstruction),
            "dismissal_eligibility": discovery["dismissal_eligibility"],
            "dismissal_block_reason": discovery["block_reason"],
            "candidate_click_targets": discovery["candidate_click_targets"],
            "rejected_click_targets": discovery["rejected_click_targets"],
        }

    element = candidate["element"]
    try:
        element.click(timeout=4000)
    except Exception as exc:
        return {
            "attempted": True,
            "successful": False,
            "method": candidate["method"],
            "clicked_text": candidate["clicked_text"],
            "note": f"dismissal_click_failed:{exc}",
            "dismissal_eligibility": discovery["dismissal_eligibility"],
            "dismissal_block_reason": f"dismissal_click_failed:{exc}",
            "candidate_click_targets": discovery["candidate_click_targets"],
            "rejected_click_targets": discovery["rejected_click_targets"],
        }

    return {
        "attempted": True,
        "successful": True,
        "method": candidate["method"],
        "clicked_text": candidate["clicked_text"],
        "note": "dismissal_attempted_and_successful",
        "dismissal_eligibility": discovery["dismissal_eligibility"],
        "dismissal_block_reason": discovery["block_reason"],
        "candidate_click_targets": discovery["candidate_click_targets"],
        "rejected_click_targets": discovery["rejected_click_targets"],
    }


def discover_dismissal_targets(page: Any, obstruction: dict[str, Any] | None) -> dict[str, Any]:
    obstruction_type = str((obstruction or {}).get("type") or "none")
    dismissal_context_type = dismissal_context_type_for(obstruction)
    eligibility = dismissal_eligibility(obstruction)
    candidate_click_targets: list[dict[str, Any]] = []
    rejected_click_targets: list[dict[str, Any]] = []
    block_reason = None
    selected_candidate = None

    try:
        handles = page.locator(DISMISSAL_TARGET_SELECTOR)
        count = handles.count()
    except Exception as exc:
        return {
            "eligible": False,
            "dismissal_eligibility": "not_evaluated",
            "block_reason": f"selector_unavailable:{exc}",
            "candidate_click_targets": [],
            "rejected_click_targets": [],
            "selected_candidate": None,
        }

    patterns = dismissal_patterns_for_type(dismissal_context_type)
    for idx in range(count):
        element = handles.nth(idx)
        try:
            if not element.is_visible():
                continue
            if not element_intersects_current_viewport(element):
                continue
        except Exception:
            continue

        label = element_label(element)
        normalized = normalize_label(label)
        if not normalized:
            continue
        affordance_evidence = affordance_evidence_for_element(element, label, dismissal_context_type)
        localization_evidence = affordance_localization_evidence_for_element(element, label, obstruction, dismissal_context_type=dismissal_context_type)
        affordance = classify_affordance(
            affordance_evidence,
            affordance_id=affordance_id(obstruction_type, normalized, idx),
        )
        localization = classify_affordance_owner(
            localization_evidence,
            affordance_id=f"{affordance_id(obstruction_type, normalized, idx)}:owner",
            affordance_category=affordance.category,
            interaction_policy=affordance.policy,
        )
        reason = rejection_reason(normalized, dismissal_context_type)
        match = match_dismissal_pattern(normalized, patterns)
        is_safe_candidate = match is not None and is_safe_dismissal_candidate_fields(
            affordance_policy=affordance.policy,
            affordance_owner=localization.owner,
        )
        record = {
            "label": label,
            "normalized_label": normalized,
            "method": match["method"] if match else None,
            "selector": DISMISSAL_TARGET_SELECTOR,
            "reason": None if is_safe_candidate else (reason or ("unsafe_dismissal_candidate" if match else "not_exact_match")),
            "affordance_category": affordance.category,
            "interaction_policy": affordance.policy,
            "affordance_confidence": affordance.confidence,
            "affordance_evidence": affordance.evidence.to_dict(),
            "affordance_owner": localization.owner,
            "owner_confidence": localization.owner_confidence,
            "owner_evidence": localization.owner_evidence,
            "owner_limitations": localization.owner_limitations,
        }
        if is_safe_candidate:
            candidate_click_targets.append(record)
            if selected_candidate is None:
                selected_candidate = {
                    "element": element,
                    "clicked_text": label,
                    "method": match["method"],
                    "label": label,
                    "affordance_category": affordance.category,
                    "interaction_policy": affordance.policy,
                    "affordance_confidence": affordance.confidence,
                    "affordance_evidence": affordance.evidence.to_dict(),
                    "affordance_owner": localization.owner,
                    "owner_confidence": localization.owner_confidence,
                    "owner_evidence": localization.owner_evidence,
                    "owner_limitations": localization.owner_limitations,
                }
        elif should_record_rejected_click_target(
            record,
            normalized_label=normalized,
            patterns=patterns,
            has_dismissal_match=match is not None,
        ):
            rejected_click_targets.append(record)

    if eligibility != "eligible":
        block_reason = dismissal_skip_note(obstruction)
    elif selected_candidate is None:
        block_reason = "no_safe_cookie_button_found" if dismissal_context_type in {"cookie_banner", "cookie_modal"} else "no_safe_close_button_found"
    return {
        "eligible": eligibility == "eligible",
        "dismissal_eligibility": eligibility,
        "block_reason": block_reason,
        "candidate_click_targets": candidate_click_targets,
        "rejected_click_targets": rejected_click_targets,
        "selected_candidate": selected_candidate,
    }


def is_safe_dismissal_candidate_fields(*, affordance_policy: str, affordance_owner: str) -> bool:
    if affordance_policy != "safe_to_dismiss":
        return False
    if affordance_owner in {
        "unrelated_chat_widget",
        "unrelated_cart_drawer",
        "header_navigation",
        "social_link",
    }:
        return False
    return True


def should_record_rejected_click_target(
    record: dict[str, Any],
    *,
    normalized_label: str,
    patterns: tuple[tuple[str, str], ...],
    has_dismissal_match: bool,
) -> bool:
    owner = str(record.get("affordance_owner") or "")
    reason = str(record.get("reason") or "")
    category = str(record.get("affordance_category") or "")
    known_unrelated_owner = owner in {
        "unrelated_chat_widget",
        "unrelated_cart_drawer",
        "header_navigation",
        "social_link",
    }
    if known_unrelated_owner and not has_dismissal_match:
        return False
    if has_dismissal_match:
        return True
    if owner == "active_obstruction":
        return True
    if category in {"ambiguous_action", "subscription_action"}:
        return True
    if reason in {
        "manage_choices_not_safe",
        "newsletter_call_to_action_not_safe",
        "unsafe_subscription_action",
    }:
        return True
    return any(contains_phrase(normalized_label, phrase) for phrase, _method in patterns)


def affordance_evidence_for_element(element: Any, label: str, obstruction_type: str) -> dict[str, Any]:
    aria_label = attribute_value(element, "aria-label")
    title = attribute_value(element, "title")
    role = attribute_value(element, "role")
    normalized_label = normalize_label(label)
    svg_icon_semantics: list[str] = []
    if normalized_label in {"x", "×", "✕", "✖"} or aria_label.lower() in {"x", "close", "dismiss"} or title.lower() in {"x", "close", "dismiss"}:
        svg_icon_semantics.append("x")
    context_tokens = split_context_tokens(obstruction_type)
    return {
        "visible_text": [label] if label else [],
        "aria_labels": [aria_label] if aria_label else [],
        "titles": [title] if title else [],
        "roles": [role] if role else [],
        "svg_icon_semantics": svg_icon_semantics,
        "dom_context": context_tokens,
        "overlay_context": context_tokens,
    }


def affordance_localization_evidence_for_element(
    element: Any,
    label: str,
    obstruction: dict[str, Any] | None,
    *,
    dismissal_context_type: str | None = None,
) -> dict[str, Any]:
    obstruction_type = dismissal_context_type or str((obstruction or {}).get("type") or "none")
    base = affordance_evidence_for_element(element, label, obstruction_type)
    localization = element_localization_snapshot(element)
    localization["obstruction_context"] = localization_context_terms(obstruction)
    base.update(localization)
    return base


def localization_context_terms(obstruction: dict[str, Any] | None) -> list[str]:
    if not isinstance(obstruction, dict):
        return []
    terms: list[str] = []
    obstruction_type = str(obstruction.get("type") or "").strip()
    if obstruction_type:
        terms.append(obstruction_type)
    for key in ("signals", "page_level_signals", "overlay_level_signals", "visual_signals", "limitations"):
        values = obstruction.get(key) or []
        if not isinstance(values, list):
            continue
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                terms.append(text)
    return terms


def affordance_id(obstruction_type: str, normalized_label: str, index: int) -> str:
    return f"{obstruction_type or 'unknown'}:{normalized_label or 'element'}:{index}"


def find_dismissal_candidate(page: Any) -> dict[str, Any] | None:
    try:
        handles = page.locator("button, [role='button'], input[type='button'], input[type='submit']")
    except Exception:
        return None

    patterns = find_dismissal_patterns()
    count = handles.count()
    candidates: list[dict[str, Any]] = []
    for idx in range(count):
        element = handles.nth(idx)
        try:
            if not element.is_visible():
                continue
            if not element_intersects_current_viewport(element):
                continue
            label = element_label(element)
        except Exception:
            continue
        normalized = normalize_label(label)
        if not normalized:
            continue
        if "manage choices" in normalized and count > 6:
            continue
        for needle, method in patterns:
            if needle in normalized:
                candidates.append(
                    {
                        "element": element,
                        "clicked_text": label,
                        "method": method,
                        "rank": patterns.index((needle, method)),
                    }
                )
                break
    if not candidates:
        return None
    candidates.sort(key=lambda item: item["rank"])
    return candidates[0]


def dismissal_successful(before: dict[str, Any] | None, after: dict[str, Any] | None) -> bool:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    if not before.get("present") and not after.get("present"):
        return False
    if before.get("present") and not after.get("present"):
        return True
    severity_before = severity_rank(str(before.get("severity") or "none"))
    severity_after = severity_rank(str(after.get("severity") or "none"))
    if severity_after < severity_before:
        return True
    coverage_before = _float_or_none(before.get("coverage_ratio")) or 0.0
    coverage_after = _float_or_none(after.get("coverage_ratio")) or 0.0
    return coverage_after + 0.05 < coverage_before


def severity_rank(value: str) -> int:
    order = {"none": 0, "minor": 1, "moderate": 2, "major": 3, "blocking": 4}
    return order.get(value, 0)
