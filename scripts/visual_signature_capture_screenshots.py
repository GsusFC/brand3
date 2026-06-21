#!/usr/bin/env python3
"""Capture local PNG screenshots for Visual Signature vision calibration."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.vision.composition import analyze_composition  # noqa: E402
from src.visual_signature.capture.clean_capture import clean_attempt_quality  # noqa: E402
from src.visual_signature.capture.dismissal_audit import build_dismissal_audit  # noqa: E402
from src.visual_signature.capture.dismissal_audit import dismissal_audit_markdown  # noqa: E402
from src.visual_signature.affordance_semantics import classify_affordance, classify_affordance_owner  # noqa: E402
from src.visual_signature.capture.screenshot_capture_models import CaptureBrand  # noqa: E402
from src.visual_signature.capture.screenshot_capture_models import CaptureResult  # noqa: E402
from src.visual_signature.capture.screenshot_capture_models import load_capture_brands  # noqa: E402
from src.visual_signature.vision.palette_from_screenshot import extract_palette_from_screenshot  # noqa: E402
from src.visual_signature.vision.screenshot_quality import load_raster_image  # noqa: E402
from src.visual_signature.vision.viewport_obstruction import analyze_viewport_obstruction  # noqa: E402
from src.visual_signature.perception import PerceptualStateMachine  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "examples" / "visual_signature" / "vision_calibration_brands.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots"
DEFAULT_MANIFEST = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "capture_manifest.json"

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

CaptureFn = Callable[..., dict[str, Any]]


def capture_screenshots(
    brands: list[CaptureBrand],
    *,
    output_dir: str | Path,
    manifest_path: str | Path | None = None,
    capture_fn: CaptureFn,
    capture_both: bool = False,
    attempt_dismiss_obstructions: bool = False,
    now: Callable[[], datetime] = datetime.now,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    started_at = now().isoformat()
    results: list[CaptureResult] = []
    for brand in brands:
        path = Path(brand.screenshot_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            primary_capture_type = _normalize_capture_type(brand.capture_type)
            metadata = _invoke_capture_fn(
                capture_fn,
                brand.brand_name,
                brand.website_url,
                str(path),
                primary_capture_type,
                attempt_dismiss_obstructions=attempt_dismiss_obstructions,
            )
            file_size = path.stat().st_size if path.exists() else None
            secondary_path = None
            secondary_metadata: dict[str, Any] | None = None
            if capture_both:
                secondary_capture_type = "full_page" if primary_capture_type == "viewport" else "viewport"
                secondary_path = _derived_capture_path(path, secondary_capture_type)
                secondary_metadata = _invoke_capture_fn(
                    capture_fn,
                    brand.brand_name,
                    brand.website_url,
                    str(secondary_path),
                    secondary_capture_type,
                    attempt_dismiss_obstructions=False,
                )
                secondary_file_size = secondary_path.stat().st_size if secondary_path.exists() else None
            else:
                secondary_capture_type = None
                secondary_file_size = None
            clean_attempt_capture_variant = "clean_attempt" if metadata.get("clean_attempt_screenshot_path") else None
            results.append(
                CaptureResult(
                    brand_name=brand.brand_name,
                    website_url=brand.website_url,
                    screenshot_path=str(path),
                    status="ok",
                    source=str(metadata.get("source") or "playwright"),
                    capture_type=str(metadata.get("capture_type") or primary_capture_type or "viewport"),
                    capture_variant=str(metadata.get("capture_variant") or ("raw_viewport" if attempt_dismiss_obstructions else primary_capture_type or "viewport")),
                    clean_attempt_capture_variant=str(metadata.get("clean_attempt_capture_variant") or clean_attempt_capture_variant) or None,
                    raw_screenshot_path=str(metadata.get("raw_screenshot_path") or path),
                    clean_attempt_screenshot_path=str(metadata.get("clean_attempt_screenshot_path") or "") or None,
                    secondary_screenshot_path=str(secondary_path) if secondary_path else None,
                    secondary_capture_type=secondary_capture_type,
                    page_url=str(metadata.get("page_url") or brand.website_url),
                    width=_int_or_none(metadata.get("width")),
                    height=_int_or_none(metadata.get("height")),
                    viewport_width=_int_or_none(metadata.get("viewport_width")),
                    viewport_height=_int_or_none(metadata.get("viewport_height")),
                    file_size_bytes=file_size,
                    secondary_width=_int_or_none((secondary_metadata or {}).get("width")),
                    secondary_height=_int_or_none((secondary_metadata or {}).get("height")),
                    secondary_file_size_bytes=secondary_file_size,
                    dismissal_attempted=bool(metadata.get("dismissal_attempted")),
                    dismissal_successful=bool(metadata.get("dismissal_successful")),
                    dismissal_method=str(metadata.get("dismissal_method") or "") or None,
                    clicked_text=str(metadata.get("clicked_text") or "") or None,
                    dismissal_eligibility=str(metadata.get("dismissal_eligibility") or "") or None,
                    dismissal_block_reason=str(metadata.get("dismissal_block_reason") or "") or None,
                    candidate_click_targets=[dict(item) for item in metadata.get("candidate_click_targets") or [] if isinstance(item, dict)],
                    rejected_click_targets=[dict(item) for item in metadata.get("rejected_click_targets") or [] if isinstance(item, dict)],
                    before_obstruction=_coerce_dict_or_none(metadata.get("before_obstruction"), field_name="before_obstruction"),
                    after_obstruction=_coerce_dict_or_none(metadata.get("after_obstruction"), field_name="after_obstruction"),
                    evidence_integrity_notes=[str(item) for item in metadata.get("evidence_integrity_notes") or []],
                    raw_viewport_metrics=_coerce_dict_or_none(metadata.get("raw_viewport_metrics"), field_name="raw_viewport_metrics"),
                    clean_attempt_metrics=_coerce_dict_or_none(metadata.get("clean_attempt_metrics"), field_name="clean_attempt_metrics"),
                    perceptual_state=str(metadata.get("perceptual_state") or "") or None,
                    perceptual_transitions=_coerce_transition_list(metadata.get("perceptual_transitions")),
                    mutation_audit=_coerce_dict_or_none(metadata.get("mutation_audit"), field_name="mutation_audit"),
                    perceptual_state_data=_coerce_dict_or_none(metadata.get("perceptual_state_data"), field_name="perceptual_state_data"),
                    captured_at=now().isoformat(),
                )
            )
        except Exception as exc:
            results.append(
                CaptureResult(
                    brand_name=brand.brand_name,
                    website_url=brand.website_url,
                    screenshot_path=str(path),
                    status="error",
                    error=str(exc),
                    capture_type=_normalize_capture_type(brand.capture_type),
                    capture_variant="error",
                    page_url=brand.website_url,
                    evidence_integrity_notes=[f"capture_error: {exc}"],
                    captured_at=now().isoformat(),
                )
            )
    manifest = {
        "started_at": started_at,
        "completed_at": now().isoformat(),
        "output_dir": str(output_path),
        "total": len(results),
        "ok": sum(1 for item in results if item.status == "ok"),
        "error": sum(1 for item in results if item.status == "error"),
        "attempt_dismiss_obstructions": attempt_dismiss_obstructions,
        "results": [_capture_result_to_dict(item) for item in results],
    }
    if attempt_dismiss_obstructions:
        dismissal_audit = build_dismissal_audit(manifest)
        audit_json_path = output_path / "dismissal_audit.json"
        audit_md_path = output_path / "dismissal_audit.md"
        _write_json(audit_json_path, dismissal_audit)
        audit_md_path.write_text(dismissal_audit_markdown(dismissal_audit) + "\n", encoding="utf-8")
        manifest["dismissal_audit"] = str(audit_json_path)
    _write_json(Path(manifest_path or DEFAULT_MANIFEST), manifest)
    return manifest


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _capture_result_to_dict(item: CaptureResult) -> dict[str, Any]:
    payload = asdict(item)
    perceptual_state_data = payload.pop("perceptual_state_data", None)
    has_state_output = bool(
        payload.get("perceptual_state")
        or payload.get("perceptual_transitions")
        or payload.get("mutation_audit") is not None
        or perceptual_state_data
    )
    if not payload.get("perceptual_state") and perceptual_state_data:
        payload["perceptual_state"] = perceptual_state_data.get("current_state")
    if not payload.get("perceptual_transitions") and perceptual_state_data:
        payload["perceptual_transitions"] = perceptual_state_data.get("transitions") or []
    if payload.get("mutation_audit") is None and perceptual_state_data:
        if perceptual_state_data.get("mutation_results"):
            payload["mutation_audit"] = perceptual_state_data.get("mutation_results")[-1].get("mutation_audit")
        else:
            payload["mutation_audit"] = None
    if not has_state_output:
        payload.pop("perceptual_state", None)
        payload.pop("perceptual_transitions", None)
        payload.pop("mutation_audit", None)
    return payload


def _invoke_capture_fn(
    capture_fn: CaptureFn,
    brand_name: str,
    website_url: str,
    screenshot_path: str,
    capture_type: str,
    *,
    attempt_dismiss_obstructions: bool,
) -> dict[str, Any]:
    try:
        return capture_fn(
            brand_name,
            website_url,
            screenshot_path,
            capture_type,
            attempt_dismiss_obstructions=attempt_dismiss_obstructions,
        )
    except TypeError:
        return capture_fn(brand_name, website_url, screenshot_path, capture_type)


def _snapshot_for_path(path: Path, *, dom_html: str | None = None) -> dict[str, Any]:
    image = load_raster_image(str(path))
    palette = extract_palette_from_screenshot(image)
    composition = analyze_composition(image)
    obstruction = analyze_viewport_obstruction(dom_html=dom_html, viewport_image=image).to_dict()
    return {
        "metrics": {
            "viewport_whitespace_ratio": composition.whitespace_ratio,
            "viewport_visual_density": composition.visual_density,
            "viewport_composition": composition.composition_classification,
            "palette_color_count": palette.color_count,
            "palette_confidence": palette.confidence,
            "composition_confidence": composition.confidence,
        },
        "obstruction": obstruction,
    }


def _attempt_obstruction_dismissal(page: Any, obstruction: dict[str, Any] | None) -> dict[str, Any]:
    discovery = _discover_dismissal_targets(page, obstruction)
    return _attempt_obstruction_dismissal_with_discovery(page, obstruction, discovery)


def _attempt_obstruction_dismissal_with_discovery(
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
            "note": discovery["block_reason"] or _dismissal_skip_note(obstruction),
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
            "note": discovery["block_reason"] or "no_safe_cookie_button_found",
            "dismissal_eligibility": discovery["dismissal_eligibility"],
            "dismissal_block_reason": discovery["block_reason"] or "no_safe_cookie_button_found",
            "candidate_click_targets": discovery["candidate_click_targets"],
            "rejected_click_targets": discovery["rejected_click_targets"],
        }

    try:
        candidate["element"].click(timeout=2500)
        return {
            "attempted": True,
            "successful": False,
            "method": candidate["method"],
            "clicked_text": candidate["clicked_text"],
            "note": "safe_dismissal_button_clicked",
            "dismissal_eligibility": discovery["dismissal_eligibility"],
            "dismissal_block_reason": None,
            "candidate_click_targets": discovery["candidate_click_targets"],
            "rejected_click_targets": discovery["rejected_click_targets"],
        }
    except Exception as exc:
        return {
            "attempted": True,
            "successful": False,
            "method": None,
            "clicked_text": candidate["clicked_text"],
            "note": f"dismissal_click_failed: {exc}",
            "dismissal_eligibility": discovery["dismissal_eligibility"],
            "dismissal_block_reason": "click_failed",
            "candidate_click_targets": discovery["candidate_click_targets"],
            "rejected_click_targets": discovery["rejected_click_targets"],
        }


def _prepare_perceptual_state_machine(
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

    discovery = _discover_dismissal_targets(page, obstruction)
    affordance_labels = [str(item.get("label") or "") for item in discovery.get("candidate_click_targets") or [] if isinstance(item, dict)]
    eligibility = machine.evaluate_eligibility(
        obstruction,
        affordance_labels=affordance_labels,
        evidence_refs=[raw_artifact_ref],
    )
    return {"machine": machine, "discovery": discovery, "eligibility": eligibility}


def _discover_dismissal_targets(page: Any, obstruction: dict[str, Any] | None) -> dict[str, Any]:
    obstruction_type = str((obstruction or {}).get("type") or "none")
    dismissal_context_type = _dismissal_context_type(obstruction)
    eligibility = _dismissal_eligibility(obstruction)
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

    patterns = _dismissal_patterns_for_type(dismissal_context_type)
    for idx in range(count):
        element = handles.nth(idx)
        try:
            if not element.is_visible():
                continue
            if not _element_intersects_current_viewport(element):
                continue
        except Exception:
            continue

        label = _element_label(element)
        normalized = _normalize_label(label)
        if not normalized:
            continue
        affordance_evidence = _affordance_evidence_for_element(element, label, dismissal_context_type)
        localization_evidence = _affordance_localization_evidence_for_element(element, label, obstruction, dismissal_context_type=dismissal_context_type)
        affordance = classify_affordance(
            affordance_evidence,
            affordance_id=_affordance_id(obstruction_type, normalized, idx),
        )
        localization = classify_affordance_owner(
            localization_evidence,
            affordance_id=f"{_affordance_id(obstruction_type, normalized, idx)}:owner",
            affordance_category=affordance.category,
            interaction_policy=affordance.policy,
        )
        reason = _rejection_reason(normalized, dismissal_context_type)
        match = _match_dismissal_pattern(normalized, patterns)
        is_safe_candidate = match is not None and _is_safe_dismissal_candidate_fields(
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
        elif _should_record_rejected_click_target(
            record,
            normalized_label=normalized,
            patterns=patterns,
            has_dismissal_match=match is not None,
        ):
            rejected_click_targets.append(record)

    if eligibility != "eligible":
        block_reason = _dismissal_skip_note(obstruction)
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


def _is_safe_dismissal_candidate_fields(*, affordance_policy: str, affordance_owner: str) -> bool:
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


def _should_record_rejected_click_target(
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
    return any(_contains_phrase(normalized_label, phrase) for phrase, _method in patterns)


def _should_attempt_obstruction_dismissal(obstruction: dict[str, Any] | None) -> bool:
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


def _dismissal_eligibility(obstruction: dict[str, Any] | None) -> str:
    obstruction_type = str((obstruction or {}).get("type") or "none")
    if not isinstance(obstruction, dict) or obstruction.get("present") is not True:
        return "not_eligible"
    if obstruction_type in {"login_wall", "unknown_overlay"}:
        return "not_eligible"
    if obstruction_type in {"cookie_banner", "cookie_modal", "newsletter_modal", "promo_modal"}:
        return "eligible"
    return "not_eligible"


def _dismissal_patterns_for_type(obstruction_type: str) -> tuple[tuple[str, str], ...]:
    if obstruction_type in {"newsletter_modal", "promo_modal"}:
        return NEWSLETTER_DISMISS_PHRASES
    if obstruction_type in {"cookie_banner", "cookie_modal"}:
        return COOKIE_DISMISS_PHRASES
    return ()


def _dismissal_context_type(obstruction: dict[str, Any] | None) -> str:
    obstruction_type = str((obstruction or {}).get("type") or "none")
    if obstruction_type in {"cookie_banner", "cookie_modal"}:
        return obstruction_type
    if obstruction_type in {"newsletter_modal", "promo_modal"} and _has_cookie_consent_signal(obstruction):
        return "cookie_modal"
    return obstruction_type


def _has_cookie_consent_signal(obstruction: dict[str, Any] | None) -> bool:
    if not isinstance(obstruction, dict):
        return False
    values: list[str] = []
    for key in ("signals", "page_level_signals", "overlay_level_signals", "visual_signals", "limitations"):
        raw_values = obstruction.get(key) or []
        if isinstance(raw_values, list):
            values.extend(str(value) for value in raw_values if value is not None)
    joined = _normalize_label(" ".join(values)).replace("_", " ")
    return any(token in joined for token in ("cookie", "cookies", "consent", "privacy", "gdpr", "cmp"))


def _match_dismissal_pattern(normalized: str, patterns: tuple[tuple[str, str], ...]) -> dict[str, str] | None:
    if not _is_concise_dismissal_label(normalized):
        return None
    for phrase, method in patterns:
        if _contains_phrase(normalized, phrase):
            return {"phrase": phrase, "method": method}
    return None


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_text = _normalize_label(text)
    normalized_phrase = _normalize_label(phrase)
    if not normalized_text or not normalized_phrase:
        return False
    if normalized_text == normalized_phrase:
        return True
    return (
        normalized_text.startswith(f"{normalized_phrase} ")
        or normalized_text.endswith(f" {normalized_phrase}")
        or f" {normalized_phrase} " in f" {normalized_text} "
    )


def _is_concise_dismissal_label(normalized: str) -> bool:
    words = [item for item in normalized.split() if item]
    return 0 < len(words) <= 6 and len(normalized) <= 80


def _rejection_reason(normalized: str, obstruction_type: str) -> str | None:
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


def _dismissal_skip_note(obstruction: dict[str, Any] | None) -> str:
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


def _affordance_evidence_for_element(element: Any, label: str, obstruction_type: str) -> dict[str, Any]:
    aria_label = _attribute_value(element, "aria-label")
    title = _attribute_value(element, "title")
    role = _attribute_value(element, "role")
    normalized_label = _normalize_label(label)
    svg_icon_semantics: list[str] = []
    if normalized_label in {"x", "×", "✕", "✖"} or aria_label.lower() in {"x", "close", "dismiss"} or title.lower() in {"x", "close", "dismiss"}:
        svg_icon_semantics.append("x")
    context_tokens = _split_context_tokens(obstruction_type)
    return {
        "visible_text": [label] if label else [],
        "aria_labels": [aria_label] if aria_label else [],
        "titles": [title] if title else [],
        "roles": [role] if role else [],
        "svg_icon_semantics": svg_icon_semantics,
        "dom_context": context_tokens,
        "overlay_context": context_tokens,
    }


def _affordance_localization_evidence_for_element(
    element: Any,
    label: str,
    obstruction: dict[str, Any] | None,
    *,
    dismissal_context_type: str | None = None,
) -> dict[str, Any]:
    obstruction_type = dismissal_context_type or str((obstruction or {}).get("type") or "none")
    base = _affordance_evidence_for_element(element, label, obstruction_type)
    localization = _element_localization_snapshot(element)
    localization["obstruction_context"] = _localization_context_terms(obstruction)
    base.update(localization)
    return base


def _element_localization_snapshot(element: Any) -> dict[str, Any]:
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


def _element_intersects_current_viewport(element: Any) -> bool:
    snapshot = _element_localization_snapshot(element)
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


def _localization_context_terms(obstruction: dict[str, Any] | None) -> list[str]:
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


def _attribute_value(element: Any, attr: str) -> str:
    try:
        value = element.get_attribute(attr)
        if value and str(value).strip():
            return str(value).strip()
    except Exception:
        pass
    return ""


def _affordance_id(obstruction_type: str, normalized_label: str, index: int) -> str:
    return f"{obstruction_type or 'unknown'}:{normalized_label or 'element'}:{index}"


def _split_context_tokens(value: str) -> list[str]:
    normalized = _normalize_label(value).replace("_", " ")
    tokens = [item for item in normalized.split() if item]
    if not tokens and value:
        tokens = [str(value)]
    return tokens


def _find_dismissal_candidate(page: Any) -> dict[str, Any] | None:
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
            if not _element_intersects_current_viewport(element):
                continue
            label = _element_label(element)
        except Exception:
            continue
        normalized = _normalize_label(label)
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


def _element_label(element: Any) -> str:
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


def _visible_obstruction_dom_snapshot(page: Any) -> str:
    if not hasattr(page, "evaluate"):
        try:
            return page.content()
        except Exception:
            return ""
    try:
        rows = page.evaluate(
            """
            () => {
              const selectors = [
                '[role="dialog"]',
                '[role="alertdialog"]',
                '[aria-modal="true"]',
                '[aria-label*="cookie" i]',
                '[aria-label*="consent" i]',
                '[aria-label*="privacy" i]',
                '[class*="cookie" i]',
                '[id*="cookie" i]',
                '[class*="consent" i]',
                '[id*="consent" i]',
                '[class*="modal" i]',
                '[id*="modal" i]',
                '[class*="popup" i]',
                '[id*="popup" i]',
                '[class*="newsletter" i]',
                '[id*="newsletter" i]',
                '[class*="banner" i]',
                '[id*="banner" i]'
              ].join(',');
              const nodes = Array.from(document.querySelectorAll(selectors));
              const candidates = [];
              const seen = new Set();
              for (const node of nodes) {
                if (!node || seen.has(node)) continue;
                seen.add(node);
                const rect = node.getBoundingClientRect ? node.getBoundingClientRect() : null;
                const style = window.getComputedStyle ? window.getComputedStyle(node) : null;
                if (!rect || !style) continue;
                const visible = rect.width > 0 && rect.height > 0
                  && rect.bottom > 0 && rect.right > 0
                  && rect.top < (window.innerHeight || 0)
                  && rect.left < (window.innerWidth || 0)
                  && style.display !== 'none'
                  && style.visibility !== 'hidden'
                  && Number(style.opacity || '1') > 0.02;
                if (!visible) continue;
                const position = style.position || '';
                const zIndex = style.zIndex || '';
                const role = node.getAttribute ? (node.getAttribute('role') || '') : '';
                const ariaModal = node.getAttribute ? (node.getAttribute('aria-modal') || '') : '';
                const ariaLabel = node.getAttribute ? (node.getAttribute('aria-label') || '') : '';
                const className = typeof node.className === 'string' ? node.className : '';
                const id = node.id || '';
                const text = (node.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 600);
                const overlayish = ['fixed', 'sticky'].includes(position)
                  || role === 'dialog'
                  || role === 'alertdialog'
                  || ariaModal === 'true'
                  || /cookie|consent|privacy|modal|popup|newsletter|banner/i.test(`${id} ${className} ${ariaLabel} ${text}`)
                  || Number.parseInt(zIndex || '0', 10) >= 100;
                if (!overlayish) continue;
                candidates.push({
                  tag: node.tagName ? node.tagName.toLowerCase() : '',
                  id,
                  className,
                  role,
                  ariaModal,
                  ariaLabel,
                  position,
                  zIndex,
                  width: Math.round(rect.width || 0),
                  height: Math.round(rect.height || 0),
                  top: Math.round(rect.top || 0),
                  left: Math.round(rect.left || 0),
                  text
                });
              }
              return candidates.slice(0, 24);
            }
            """
        )
    except Exception:
        try:
            return page.content()
        except Exception:
            return ""
    if not isinstance(rows, list):
        return ""
    parts: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        attrs = " ".join(
            f"{key}={value}"
            for key, value in {
                "tag": row.get("tag"),
                "id": row.get("id"),
                "class": row.get("className"),
                "role": row.get("role"),
                "aria-modal": row.get("ariaModal"),
                "aria-label": row.get("ariaLabel"),
                "position": row.get("position"),
                "z-index": row.get("zIndex"),
                "width": row.get("width"),
                "height": row.get("height"),
                "top": row.get("top"),
                "left": row.get("left"),
            }.items()
            if value not in (None, "")
        )
        text = str(row.get("text") or "")
        parts.append(f"<visible-overlay {attrs}>{text}</visible-overlay>")
    return "\n".join(parts)


def _normalize_label(value: str) -> str:
    return " ".join(str(value or "").lower().replace("\n", " ").split())


def _dismissal_successful(before: dict[str, Any] | None, after: dict[str, Any] | None) -> bool:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    if not before.get("present") and not after.get("present"):
        return False
    if before.get("present") and not after.get("present"):
        return True
    severity_before = _severity_rank(str(before.get("severity") or "none"))
    severity_after = _severity_rank(str(after.get("severity") or "none"))
    if severity_after < severity_before:
        return True
    coverage_before = _float_or_none(before.get("coverage_ratio")) or 0.0
    coverage_after = _float_or_none(after.get("coverage_ratio")) or 0.0
    return coverage_after + 0.05 < coverage_before


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _format_percent(value: Any) -> str:
    numeric = _float_or_none(value)
    if numeric is None:
        return "0.0%"
    return f"{numeric * 100:.1f}%"


def _normalize_capture_type(value: Any) -> str:
    capture_type = str(value or "").strip().lower()
    if capture_type in {"viewport", "full_page"}:
        return capture_type
    return "viewport"


def _derived_capture_path(path: Path, capture_type: str) -> Path:
    suffix = ".png"
    stem = path.name[:-len(suffix)] if path.name.endswith(suffix) else path.name
    return path.with_name(f"{stem}.{capture_type.replace('_', '-')}{path.suffix or '.png'}")


def _capture_with_playwright(
    brand_name: str,
    website_url: str,
    screenshot_path: str,
    capture_type: str,
    *,
    attempt_dismiss_obstructions: bool = False,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(
            "playwright is not installed. Run: ./.venv/bin/python -m pip install playwright && ./.venv/bin/python -m playwright install chromium"
        ) from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        normalized_capture_type = "viewport" if str(capture_type).strip().lower() == "viewport" else "full_page"
        viewport_width, viewport_height = (1440, 900) if normalized_capture_type == "viewport" else (1440, 1200)
        context = browser.new_context(viewport={"width": viewport_width, "height": viewport_height})
        page = context.new_page()
        page.goto(website_url, wait_until="domcontentloaded", timeout=45000)
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except PlaywrightTimeoutError:
            pass

        raw_path = Path(screenshot_path)
        raw_dom_html = _visible_obstruction_dom_snapshot(page)
        page.screenshot(path=str(raw_path), full_page=normalized_capture_type != "viewport")
        raw_snapshot = _snapshot_for_path(raw_path, dom_html=raw_dom_html)
        width = page.viewport_size["width"] if page.viewport_size else viewport_width
        height = page.viewport_size["height"] if page.viewport_size else viewport_height

        result: dict[str, Any] = {
            "source": "playwright",
            "capture_type": normalized_capture_type,
            "capture_variant": "raw_viewport" if normalized_capture_type == "viewport" else normalized_capture_type,
            "clean_attempt_capture_variant": None,
            "brand_name": brand_name,
            "website_url": website_url,
            "raw_screenshot_path": str(raw_path),
            "width": width,
            "height": height,
            "viewport_width": width,
            "viewport_height": height,
            "page_url": website_url,
            "before_obstruction": raw_snapshot["obstruction"],
            "raw_viewport_metrics": raw_snapshot["metrics"],
            "evidence_integrity_notes": [
                "raw_viewport_preserved_as_primary_evidence",
            ],
            "dismissal_attempted": False,
            "dismissal_successful": False,
            "dismissal_eligibility": None,
            "dismissal_block_reason": None,
            "candidate_click_targets": [],
            "rejected_click_targets": [],
        }

        if attempt_dismiss_obstructions and normalized_capture_type == "viewport":
            perceptual_context = _prepare_perceptual_state_machine(
                page=page,
                raw_snapshot=raw_snapshot,
                raw_artifact_ref=str(raw_path),
                attempt_dismiss_obstructions=True,
            )
            if perceptual_context is not None:
                machine = perceptual_context["machine"]
                discovery = perceptual_context["discovery"] or {"eligible": False, "candidate_click_targets": [], "rejected_click_targets": [], "block_reason": None, "dismissal_eligibility": None}
                eligibility = perceptual_context["eligibility"]
                result["perceptual_state_data"] = machine.to_dict()
                result["perceptual_state"] = machine.current_state
                result["perceptual_transitions"] = machine.to_dict().get("transitions") or []
                result["mutation_audit"] = None

                if discovery.get("eligible") and discovery.get("selected_candidate") is not None:
                    dismissal = _attempt_obstruction_dismissal_with_discovery(page, raw_snapshot["obstruction"], discovery)
                else:
                    dismissal = {
                        "attempted": False,
                        "successful": False,
                        "method": None,
                        "clicked_text": None,
                        "note": discovery.get("block_reason") or _dismissal_skip_note(raw_snapshot["obstruction"]),
                        "dismissal_eligibility": discovery.get("dismissal_eligibility"),
                        "dismissal_block_reason": discovery.get("block_reason"),
                        "candidate_click_targets": discovery.get("candidate_click_targets") or [],
                        "rejected_click_targets": discovery.get("rejected_click_targets") or [],
                    }

                result["dismissal_attempted"] = dismissal["attempted"]
                result["dismissal_method"] = dismissal.get("method")
                result["clicked_text"] = dismissal.get("clicked_text")
                result["dismissal_eligibility"] = dismissal.get("dismissal_eligibility") or getattr(eligibility, "state", None)
                result["dismissal_block_reason"] = dismissal.get("dismissal_block_reason")
                result["candidate_click_targets"] = dismissal.get("candidate_click_targets") or []
                result["rejected_click_targets"] = dismissal.get("rejected_click_targets") or []

                if dismissal["attempted"]:
                    machine.record_transition(
                        to_state=machine.current_state,
                        reason="safe_mutation_attempted",
                        confidence=_float_or_none(raw_snapshot["obstruction"].get("confidence")) or 0.5,
                        evidence_refs=[str(raw_path)],
                        notes=["safe_mutation_attempted"],
                    )
                    try:
                        page.wait_for_timeout(900)
                    except Exception:
                        pass
                    clean_path = _derived_capture_path(raw_path, "clean_attempt")
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
                    clean_dom_html = _visible_obstruction_dom_snapshot(page)
                    page.screenshot(path=str(clean_path), full_page=False)
                    clean_snapshot = _snapshot_for_path(clean_path, dom_html=clean_dom_html)
                    result["clean_attempt_screenshot_path"] = str(clean_path)
                    result["clean_attempt_capture_variant"] = "clean_attempt"
                    result["after_obstruction"] = clean_snapshot["obstruction"]
                    result["clean_attempt_metrics"] = clean_snapshot["metrics"]
                    mutation = machine.classify_mutation(
                        before_state=machine.current_state,
                        attempted=True,
                        successful=_dismissal_successful(
                            raw_snapshot["obstruction"],
                            clean_snapshot["obstruction"],
                        ),
                        reversible=True,
                        evidence_preserved=True,
                        mutation_type=f"{str(raw_snapshot['obstruction'].get('type') or 'unknown')}_dismissal",
                        trigger=str(dismissal.get("method") or "safe_mutation_attempted"),
                        before_artifact_ref=str(raw_path),
                        after_artifact_ref=str(clean_path),
                        evidence_refs=[str(raw_path), str(clean_path)],
                        confidence=_float_or_none(raw_snapshot["obstruction"].get("confidence")) or 0.5,
                        notes=[
                            "raw_viewport_preserved_as_primary_evidence",
                            "clean_attempt_is_supplemental_only; raw_viewport_remains_primary",
                        ],
                        risk_level="low",
                    )
                    result["perceptual_state_data"] = machine.to_dict()
                    result["perceptual_state"] = machine.current_state
                    result["perceptual_transitions"] = machine.to_dict().get("transitions") or []
                    result["mutation_audit"] = mutation.mutation_audit.to_dict()
                    result["dismissal_successful"] = mutation.state == "MINIMALLY_MUTATED_STATE"
                    result["evidence_integrity_notes"].append(
                        "clean_attempt_is_supplemental_only; raw_viewport_remains_primary"
                    )
                    if result["dismissal_successful"]:
                        result["evidence_integrity_notes"].append("dismissal_reduced_viewport_obstruction")
                    else:
                        result["evidence_integrity_notes"].append("dismissal_did_not_materially_reduce_obstruction")
                else:
                    result["evidence_integrity_notes"].append(dismissal.get("note") or "dismissal_not_attempted")
                    result["after_obstruction"] = raw_snapshot["obstruction"]
                    result["clean_attempt_metrics"] = raw_snapshot["metrics"]
                    result["perceptual_state_data"] = machine.to_dict()
                    result["perceptual_state"] = machine.current_state
                    result["perceptual_transitions"] = machine.to_dict().get("transitions") or []
                    result["mutation_audit"] = None

        context.close()
        browser.close()
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture screenshots for Visual Signature vision calibration.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to a vision calibration JSON file.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for screenshot PNGs.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to the capture manifest JSON.")
    parser.add_argument(
        "--capture-type",
        choices=("viewport", "full_page"),
        default="viewport",
        help="Default capture type when the input row does not specify one.",
    )
    parser.add_argument(
        "--capture-both",
        action="store_true",
        help="Capture both viewport and full-page screenshots for each brand.",
    )
    parser.add_argument(
        "--attempt-dismiss-obstructions",
        action="store_true",
        help="Experimental: capture a raw viewport first, then attempt a safe cookie/consent dismissal and store a clean attempt separately.",
    )
    args = parser.parse_args(argv)

    brands = load_capture_brands(args.input)
    brands = [
        CaptureBrand(
            brand_name=brand.brand_name,
            website_url=brand.website_url,
            screenshot_path=brand.screenshot_path,
            capture_type=brand.capture_type or args.capture_type,
        )
        for brand in brands
    ]
    manifest = capture_screenshots(
        brands,
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        capture_fn=_capture_with_playwright,
        capture_both=args.capture_both,
        attempt_dismiss_obstructions=args.attempt_dismiss_obstructions,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
