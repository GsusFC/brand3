"""Dismissal and perceptual-state helpers for the Playwright capture runtime."""

from __future__ import annotations

from typing import Any

from src.visual_signature.affordance_semantics import classify_affordance
from src.visual_signature.affordance_semantics import classify_affordance_owner
from src.visual_signature._internal.utils import float_or_none as _float_or_none
from src.visual_signature.perception import PerceptualStateMachine

COOKIE_DISMISS_PHRASES = (
    ("accept all", "accept_all"),
    ("allow all", "allow_all"),
    ("reject all", "reject_all"),
    ("decline all", "decline_all"),
    ("i agree", "agree"),
    ("agree", "agree"),
    ("accept", "accept"),
    ("reject", "reject"),
    ("decline", "decline"),
    ("continue", "continue"),
    ("close", "close"),
    ("dismiss", "dismiss"),
    ("got it", "got_it"),
    ("ok", "ok"),
    ("aceptar todas", "accept_all"),
    ("aceptar todo", "accept_all"),
    ("aceptar", "accept"),
    ("permitir todas", "allow_all"),
    ("rechazar todas", "reject_all"),
    ("rechazar todo", "reject_all"),
    ("rechazar", "reject"),
    ("denegar", "decline"),
    ("de acuerdo", "agree"),
    ("continuar", "continue"),
    ("cerrar", "close"),
    ("entendido", "got_it"),
    ("vale", "ok"),
    ("x", "close"),
    ("×", "close"),
    ("✕", "close"),
    ("✖", "close"),
)
NEWSLETTER_DISMISS_PHRASES = (
    ("close", "close"),
    ("dismiss", "dismiss"),
    ("x", "close"),
    ("×", "close"),
    ("✕", "close"),
    ("✖", "close"),
)
COMMON_DISMISS_IGNORED_TERMS = (
    "manage choices",
    "manage preference",
    "manage preferences",
    "preferences",
    "settings",
    "customize",
    "configurar",
    "configuración",
    "configuracion",
    "preferencias",
    "ajustes",
    "personalizar",
    "subscribe",
    "sign up",
    "signup",
    "join",
    "register",
    "learn more",
)
DISMISSAL_TARGET_SELECTOR = "button, [role='button'], input[type='button'], input[type='submit'], a, [aria-label], [title], [tabindex='0']"


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
        element.click(timeout=4000, force=True)
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


def should_attempt_obstruction_dismissal(obstruction: dict[str, Any] | None) -> bool:
    if not isinstance(obstruction, dict):
        return False
    if obstruction.get("present") is not True:
        return False
    if obstruction.get("type") not in {"cookie_banner", "cookie_modal", "newsletter_modal", "promo_modal"}:
        return False
    if _float_or_none(obstruction.get("confidence")) is not None and _float_or_none(obstruction.get("confidence")) < 0.55:
        return False
    signals = " ".join(str(item) for item in obstruction.get("signals") or []).lower()
    if any(token in signals for token in ("login", "paywall", "geo")):
        return False
    return True


def dismissal_eligibility(obstruction: dict[str, Any] | None) -> str:
    obstruction_type = str((obstruction or {}).get("type") or "none")
    if not isinstance(obstruction, dict) or obstruction.get("present") is not True:
        return "not_eligible"
    if obstruction_type in {"login_wall", "unknown_overlay"}:
        return "not_eligible"
    if obstruction_type in {"cookie_banner", "cookie_modal", "newsletter_modal", "promo_modal"}:
        return "eligible"
    return "not_eligible"


def dismissal_patterns_for_type(obstruction_type: str) -> tuple[tuple[str, str], ...]:
    if obstruction_type in {"newsletter_modal", "promo_modal"}:
        return NEWSLETTER_DISMISS_PHRASES
    if obstruction_type in {"cookie_banner", "cookie_modal"}:
        return COOKIE_DISMISS_PHRASES
    return ()


def dismissal_context_type_for(obstruction: dict[str, Any] | None) -> str:
    obstruction_type = str((obstruction or {}).get("type") or "none")
    if obstruction_type in {"cookie_banner", "cookie_modal"}:
        return obstruction_type
    if obstruction_type in {"newsletter_modal", "promo_modal"} and has_cookie_consent_signal(obstruction):
        return "cookie_modal"
    return obstruction_type


def has_cookie_consent_signal(obstruction: dict[str, Any] | None) -> bool:
    if not isinstance(obstruction, dict):
        return False
    values: list[str] = []
    for key in ("signals", "page_level_signals", "overlay_level_signals", "visual_signals", "limitations"):
        raw_values = obstruction.get(key) or []
        if isinstance(raw_values, list):
            values.extend(str(value) for value in raw_values if value is not None)
    joined = normalize_label(" ".join(values)).replace("_", " ")
    return any(token in joined for token in ("cookie", "cookies", "consent", "privacy", "gdpr", "cmp"))


def match_dismissal_pattern(normalized: str, patterns: tuple[tuple[str, str], ...]) -> dict[str, str] | None:
    if not is_concise_dismissal_label(normalized):
        return None
    for phrase, method in patterns:
        if contains_phrase(normalized, phrase):
            return {"phrase": phrase, "method": method}
    return None


def contains_phrase(text: str, phrase: str) -> bool:
    normalized_text = normalize_label(text)
    normalized_phrase = normalize_label(phrase)
    if not normalized_text or not normalized_phrase:
        return False
    if normalized_text == normalized_phrase:
        return True
    return (
        normalized_text.startswith(f"{normalized_phrase} ")
        or normalized_text.endswith(f" {normalized_phrase}")
        or f" {normalized_phrase} " in f" {normalized_text} "
    )


def is_concise_dismissal_label(normalized: str) -> bool:
    words = [item for item in normalized.split() if item]
    return 0 < len(words) <= 6 and len(normalized) <= 80


def rejection_reason(normalized: str, obstruction_type: str) -> str | None:
    if obstruction_type in {"login_wall", "unknown_overlay"}:
        return f"obstruction_type_not_eligible:{obstruction_type}"
    if obstruction_type in {"newsletter_modal", "promo_modal"}:
        if any(term in normalized for term in ("subscribe", "sign up", "signup", "join", "register")):
            return "newsletter_call_to_action_not_safe"
        if any(term in normalized for term in ("manage choices", "manage preferences", "preferences", "settings", "customize")):
            return "manage_choices_not_safe"
        return "not_close_or_dismiss"
    if obstruction_type in {"cookie_banner", "cookie_modal"}:
        if any(term in normalized for term in ("subscribe", "sign up", "signup", "join", "register")):
            return "unsafe_subscription_action"
        if any(term in normalized for term in COMMON_DISMISS_IGNORED_TERMS):
            return "manage_choices_not_safe"
        return "not_safe_cookie_action"
    return "not_relevant"


def dismissal_skip_note(obstruction: dict[str, Any] | None) -> str:
    if not isinstance(obstruction, dict):
        return "obstruction_unavailable"
    obstruction_type = str(obstruction.get("type") or "none")
    confidence = _float_or_none(obstruction.get("confidence"))
    if obstruction_type in {"login_wall"}:
        return f"obstruction_type_not_eligible:{obstruction_type}"
    if obstruction_type == "unknown_overlay" and (confidence is None or confidence < 0.55):
        return "unknown_overlay_low_confidence"
    if obstruction.get("present") is not True:
        return "no_obstruction_detected"
    return "dismissal_not_safe"


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


def element_localization_snapshot(element: Any) -> dict[str, Any]:
    if not hasattr(element, "evaluate"):
        return {}
    try:
        snapshot = element.evaluate(
            """
            node => {
              const rect = node.getBoundingClientRect ? node.getBoundingClientRect() : null;
              const style = window.getComputedStyle ? window.getComputedStyle(node) : null;
              const ancestry = [];
              let current = node;
              for (let i = 0; current && i < 6; i += 1, current = current.parentElement) {
                const tag = current.tagName ? current.tagName.toLowerCase() : '';
                const className = typeof current.className === 'string' ? current.className : '';
                ancestry.push({
                  tag,
                  id: current.id || '',
                  role: current.getAttribute ? (current.getAttribute('role') || '') : '',
                  aria_modal: current.getAttribute ? (current.getAttribute('aria-modal') || '') : '',
                  aria_label: current.getAttribute ? (current.getAttribute('aria-label') || '') : '',
                  class_name: className,
                  text: (current.textContent || '').trim().slice(0, 120),
                });
              }
              const width = rect ? Math.round(rect.width || 0) : null;
              const height = rect ? Math.round(rect.height || 0) : null;
              const x = rect ? Math.round(rect.x || rect.left || 0) : null;
              const y = rect ? Math.round(rect.y || rect.top || 0) : null;
              const innerWidth = window.innerWidth || 0;
              const innerHeight = window.innerHeight || 0;
              let viewportLocation = null;
              if (rect) {
                const cx = (rect.left || 0) + ((rect.width || 0) / 2);
                const cy = (rect.top || 0) + ((rect.height || 0) / 2);
                const horizontal = cx < innerWidth * 0.33 ? 'left' : cx > innerWidth * 0.66 ? 'right' : 'center';
                const vertical = cy < innerHeight * 0.25 ? 'top' : cy > innerHeight * 0.75 ? 'bottom' : 'center';
                viewportLocation = (vertical === 'center' && horizontal === 'center') ? 'center' : `${vertical}_${horizontal}`;
                if ((rect.width || 0) >= innerWidth * 0.85 && (rect.height || 0) >= innerHeight * 0.55) {
                  viewportLocation = 'full';
                }
              }
              return {
                bounding_box: rect ? { x, y, width, height } : null,
                dom_ancestry: ancestry,
                viewport_location: viewportLocation,
                viewport_width: innerWidth,
                viewport_height: innerHeight,
                position: style ? (style.position || '') : '',
                z_index: style ? (style.zIndex || '') : '',
                aria_modal: node.getAttribute ? (node.getAttribute('aria-modal') || '') : '',
                role_hint: node.getAttribute ? (node.getAttribute('role') || '') : '',
                proximity_context: [],
              };
            }
            """
        )
    except Exception:
        return {}
    if isinstance(snapshot, dict):
        return snapshot
    return {}


def element_intersects_current_viewport(element: Any) -> bool:
    snapshot = element_localization_snapshot(element)
    bounding_box = snapshot.get("bounding_box") if isinstance(snapshot, dict) else None
    if not isinstance(bounding_box, dict):
        return True
    x = _float_or_none(bounding_box.get("x"))
    y = _float_or_none(bounding_box.get("y"))
    width = _float_or_none(bounding_box.get("width"))
    height = _float_or_none(bounding_box.get("height"))
    viewport_width = _float_or_none(snapshot.get("viewport_width"))
    viewport_height = _float_or_none(snapshot.get("viewport_height"))
    if None in (x, y, width, height) or viewport_width is None or viewport_height is None:
        return True
    if width <= 0 or height <= 0 or viewport_width <= 0 or viewport_height <= 0:
        return False
    return x + width > 0 and y + height > 0 and x < viewport_width and y < viewport_height


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


def attribute_value(element: Any, attr: str) -> str:
    try:
        value = element.get_attribute(attr)
        if value and str(value).strip():
            return str(value).strip()
    except Exception:
        pass
    return ""


def affordance_id(obstruction_type: str, normalized_label: str, index: int) -> str:
    return f"{obstruction_type or 'unknown'}:{normalized_label or 'element'}:{index}"


def split_context_tokens(value: str) -> list[str]:
    normalized = normalize_label(value).replace("_", " ")
    tokens = [item for item in normalized.split() if item]
    if not tokens and value:
        tokens = [str(value)]
    return tokens


def find_dismissal_candidate(page: Any) -> dict[str, Any] | None:
    try:
        handles = page.locator("button, [role='button'], input[type='button'], input[type='submit']")
    except Exception:
        return None

    patterns = [
        ("accept all", "accept_all"),
        ("reject all", "reject_all"),
        ("continue", "continue"),
        ("close", "close"),
        ("manage choices", "manage_choices"),
    ]
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


def element_label(element: Any) -> str:
    for getter in ("inner_text", "text_content"):
        try:
            value = getattr(element, getter)()
            if value and str(value).strip():
                return str(value).strip()
        except Exception:
            pass
    for attr in ("aria-label", "title", "value"):
        try:
            value = element.get_attribute(attr)
            if value and str(value).strip():
                return str(value).strip()
        except Exception:
            pass
    return ""


def normalize_label(value: str) -> str:
    return " ".join(str(value or "").lower().replace("\n", " ").split())


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

