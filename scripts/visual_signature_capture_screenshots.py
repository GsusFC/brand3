#!/usr/bin/env python3
"""Capture local PNG screenshots for Visual Signature vision calibration."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.vision.composition import analyze_composition  # noqa: E402
from src.visual_signature.affordance_semantics import classify_affordance, classify_affordance_owner  # noqa: E402
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
    ("i agree", "agree"),
    ("agree", "agree"),
    ("accept", "accept"),
    ("continue", "continue"),
    ("close", "close"),
    ("dismiss", "dismiss"),
    ("got it", "got_it"),
    ("ok", "ok"),
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
    "subscribe",
    "sign up",
    "signup",
    "join",
    "register",
    "learn more",
)
DISMISSAL_TARGET_SELECTOR = "button, [role='button'], input[type='button'], input[type='submit'], a, [aria-label], [title], [tabindex='0']"


@dataclass(frozen=True)
class CaptureBrand:
    brand_name: str
    website_url: str
    screenshot_path: str
    capture_type: str = "viewport"


@dataclass
class CaptureResult:
    brand_name: str
    website_url: str
    screenshot_path: str
    status: str
    error: str | None = None
    source: str = "playwright"
    capture_type: str = "full_page"
    capture_variant: str = "viewport"
    clean_attempt_capture_variant: str | None = None
    raw_screenshot_path: str | None = None
    clean_attempt_screenshot_path: str | None = None
    secondary_screenshot_path: str | None = None
    secondary_capture_type: str | None = None
    page_url: str | None = None
    width: int | None = None
    height: int | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    secondary_width: int | None = None
    secondary_height: int | None = None
    file_size_bytes: int | None = None
    secondary_file_size_bytes: int | None = None
    dismissal_attempted: bool = False
    dismissal_successful: bool = False
    dismissal_method: str | None = None
    clicked_text: str | None = None
    dismissal_eligibility: str | None = None
    dismissal_block_reason: str | None = None
    candidate_click_targets: list[dict[str, Any]] = field(default_factory=list)
    rejected_click_targets: list[dict[str, Any]] = field(default_factory=list)
    before_obstruction: dict[str, Any] | None = None
    after_obstruction: dict[str, Any] | None = None
    evidence_integrity_notes: list[str] = field(default_factory=list)
    raw_viewport_metrics: dict[str, Any] | None = None
    clean_attempt_metrics: dict[str, Any] | None = None
    perceptual_state: str | None = None
    perceptual_transitions: list[dict[str, Any]] = field(default_factory=list)
    mutation_audit: dict[str, Any] | None = None
    perceptual_state_data: dict[str, Any] | None = None
    captured_at: str | None = None


CaptureFn = Callable[..., dict[str, Any]]


def load_capture_brands(path: str | Path) -> list[CaptureBrand]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = payload.get("brands") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Capture input must be a list or an object with a 'brands' list")
    brands: list[CaptureBrand] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Row {index} must be an object")
        brand_name = str(row.get("brand_name") or row.get("brandName") or "").strip()
        website_url = str(row.get("website_url") or row.get("websiteUrl") or "").strip()
        screenshot_path = str(row.get("screenshot_path") or row.get("screenshotPath") or "").strip()
        capture_type = str(row.get("capture_type") or row.get("captureType") or "viewport").strip() or "viewport"
        if not brand_name or not website_url or not screenshot_path:
            raise ValueError(f"Row {index} must include brand_name, website_url, and screenshot_path")
        brands.append(
            CaptureBrand(
                brand_name=brand_name,
                website_url=website_url,
                screenshot_path=screenshot_path,
                capture_type=capture_type,
            )
        )
    return brands


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
        audit_md_path.write_text(_dismissal_audit_markdown(dismissal_audit) + "\n", encoding="utf-8")
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

    patterns = _dismissal_patterns_for_type(obstruction_type)
    for idx in range(count):
        element = handles.nth(idx)
        try:
            if not element.is_visible():
                continue
        except Exception:
            continue

        label = _element_label(element)
        normalized = _normalize_label(label)
        if not normalized:
            continue
        affordance_evidence = _affordance_evidence_for_element(element, label, obstruction_type)
        localization_evidence = _affordance_localization_evidence_for_element(element, label, obstruction)
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
        reason = _rejection_reason(normalized, obstruction_type)
        match = _match_dismissal_pattern(normalized, patterns)
        record = {
            "label": label,
            "normalized_label": normalized,
            "method": match["method"] if match else None,
            "selector": DISMISSAL_TARGET_SELECTOR,
            "reason": None if match else (reason or "not_exact_match"),
            "affordance_category": affordance.category,
            "interaction_policy": affordance.policy,
            "affordance_confidence": affordance.confidence,
            "affordance_evidence": affordance.evidence.to_dict(),
            "affordance_owner": localization.owner,
            "owner_confidence": localization.owner_confidence,
            "owner_evidence": localization.owner_evidence,
            "owner_limitations": localization.owner_limitations,
        }
        if match:
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
        else:
            rejected_click_targets.append(record)

    if eligibility != "eligible":
        block_reason = _dismissal_skip_note(obstruction)
    elif selected_candidate is None:
        block_reason = "no_safe_cookie_button_found" if obstruction_type in {"cookie_banner", "cookie_modal"} else "no_safe_close_button_found"
    return {
        "eligible": eligibility == "eligible",
        "dismissal_eligibility": eligibility,
        "block_reason": block_reason,
        "candidate_click_targets": candidate_click_targets,
        "rejected_click_targets": rejected_click_targets,
        "selected_candidate": selected_candidate,
    }


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


def _match_dismissal_pattern(normalized: str, patterns: tuple[tuple[str, str], ...]) -> dict[str, str] | None:
    for phrase, method in patterns:
        if _contains_phrase(normalized, phrase):
            return {"phrase": phrase, "method": method}
    return None


def _contains_phrase(text: str, phrase: str) -> bool:
    return text == phrase


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
        if any(term in normalized for term in COMMON_DISMISS_IGNORED_TERMS):
            return "manage_choices_not_safe"
        if any(term in normalized for term in ("subscribe", "sign up", "signup", "join", "register")):
            return "unsafe_subscription_action"
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


def _affordance_localization_evidence_for_element(element: Any, label: str, obstruction: dict[str, Any] | None) -> dict[str, Any]:
    obstruction_type = str((obstruction or {}).get("type") or "none")
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


def build_dismissal_audit(manifest: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in manifest.get("results") or [] if isinstance(row, dict)]
    attempted = [row for row in rows if row.get("dismissal_attempted")]
    successful = [row for row in attempted if row.get("dismissal_successful")]
    failed = [row for row in attempted if not row.get("dismissal_successful")]
    eligibility_distribution = _string_distribution(rows, key="dismissal_eligibility")
    block_reason_distribution = _string_distribution(rows, key="dismissal_block_reason")
    state_distribution = _string_distribution(rows, key="perceptual_state")
    transition_reason_distribution = _transition_reason_distribution(rows)
    affordance_category_distribution = _affordance_distribution(rows, key="affordance_category")
    interaction_policy_distribution = _affordance_distribution(rows, key="interaction_policy")
    affordance_owner_distribution = _affordance_distribution(rows, key="affordance_owner")
    safe_to_dismiss_candidates_not_clicked = _affordance_count(
        rows,
        target_key="rejected_click_targets",
        field_key="interaction_policy",
        expected="safe_to_dismiss",
    )
    unsafe_to_mutate_candidates_encountered = _affordance_count(
        rows,
        target_key=None,
        field_key="interaction_policy",
        expected="unsafe_to_mutate",
    )
    requires_human_review_candidates_encountered = _affordance_count(
        rows,
        target_key=None,
        field_key="interaction_policy",
        expected="requires_human_review",
    )
    material_changes = [
        row for row in attempted if _material_viewport_change(row.get("raw_viewport_metrics"), row.get("clean_attempt_metrics"))
    ]
    return {
        "schema_version": "visual-signature-dismissal-audit-1",
        "generated_at": datetime.now().isoformat(),
        "total_results": len(rows),
        "attempted": len(attempted),
        "successful": len(successful),
        "failed": len(failed),
        "dismissal_success_rate": _rate(len(successful), len(attempted)),
        "mutation_summary": {
            "attempted": len(attempted),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": _rate(len(successful), len(attempted)),
        },
        "failed_dismissals": [
            {
                "brand_name": row.get("brand_name"),
                "website_url": row.get("website_url"),
                "dismissal_method": row.get("dismissal_method"),
                "clicked_text": row.get("clicked_text"),
                "before_severity": (row.get("before_obstruction") or {}).get("severity"),
                "after_severity": (row.get("after_obstruction") or {}).get("severity"),
                "notes": row.get("evidence_integrity_notes") or [],
            }
            for row in failed
        ],
        "materially_changed_cases": [
            {
                "brand_name": row.get("brand_name"),
                "website_url": row.get("website_url"),
                "before": row.get("raw_viewport_metrics"),
                "after": row.get("clean_attempt_metrics"),
                "before_obstruction": row.get("before_obstruction"),
                "after_obstruction": row.get("after_obstruction"),
            }
            for row in material_changes
        ],
        "before_severity_distribution": _severity_distribution(rows, key="before_obstruction"),
        "after_severity_distribution": _severity_distribution(rows, key="after_obstruction"),
        "eligibility_distribution": eligibility_distribution,
        "block_reason_distribution": block_reason_distribution,
        "state_distribution": state_distribution,
        "transition_reason_distribution": transition_reason_distribution,
        "affordance_category_distribution": affordance_category_distribution,
        "interaction_policy_distribution": interaction_policy_distribution,
        "affordance_owner_distribution": affordance_owner_distribution,
        "safe_to_dismiss_candidates_not_clicked": safe_to_dismiss_candidates_not_clicked,
        "unsafe_to_mutate_candidates_encountered": unsafe_to_mutate_candidates_encountered,
        "requires_human_review_candidates_encountered": requires_human_review_candidates_encountered,
        "results": [
            {
                "brand_name": row.get("brand_name"),
                "website_url": row.get("website_url"),
                "dismissal_attempted": bool(row.get("dismissal_attempted")),
                "dismissal_successful": bool(row.get("dismissal_successful")),
                "dismissal_method": row.get("dismissal_method"),
                "clicked_text": row.get("clicked_text"),
                "dismissal_eligibility": row.get("dismissal_eligibility"),
                "dismissal_block_reason": row.get("dismissal_block_reason"),
                "candidate_click_targets": row.get("candidate_click_targets") or [],
                "rejected_click_targets": row.get("rejected_click_targets") or [],
                "affordance_category_distribution": _target_distribution(row, key="affordance_category"),
                "interaction_policy_distribution": _target_distribution(row, key="interaction_policy"),
                "affordance_owner_distribution": _target_distribution(row, key="affordance_owner"),
                "capture_variant": row.get("capture_variant"),
                "clean_attempt_capture_variant": row.get("clean_attempt_capture_variant"),
                "raw_screenshot_path": row.get("raw_screenshot_path"),
                "clean_attempt_screenshot_path": row.get("clean_attempt_screenshot_path"),
                "perceptual_state": row.get("perceptual_state"),
                "perceptual_transitions": row.get("perceptual_transitions") or [],
                "mutation_audit": row.get("mutation_audit"),
            }
            for row in rows
        ],
    }


def _severity_distribution(rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        obstruction = row.get(key) or {}
        if not isinstance(obstruction, dict):
            continue
        severity = str(obstruction.get("severity") or "none")
        counts[severity] = counts.get(severity, 0) + 1
    return dict(sorted(counts.items()))


def _string_distribution(rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "none")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _transition_reason_distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        transitions = row.get("perceptual_transitions") or []
        if not isinstance(transitions, list):
            continue
        for transition in transitions:
            if not isinstance(transition, dict):
                continue
            reason = str(transition.get("reason") or "none")
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _affordance_distribution(rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for record in _all_diagnostic_targets(row):
            value = str(record.get(key) or "unknown")
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _affordance_count(
    rows: list[dict[str, Any]],
    *,
    target_key: str | None,
    field_key: str,
    expected: str,
) -> int:
    total = 0
    for row in rows:
        if target_key is None:
            records = _all_diagnostic_targets(row)
        else:
            records = row.get(target_key) or []
            if not isinstance(records, list):
                continue
        for record in records:
            if not isinstance(record, dict):
                continue
            if str(record.get(field_key) or "") == expected:
                total += 1
    return total


def _target_distribution(row: dict[str, Any], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in _all_diagnostic_targets(row):
        value = str(record.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _all_diagnostic_targets(row: dict[str, Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for key in ("candidate_click_targets", "rejected_click_targets"):
        records = row.get(key) or []
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict):
                targets.append(record)
    return targets


def _material_viewport_change(before: dict[str, Any] | None, after: dict[str, Any] | None) -> bool:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    if before.get("viewport_visual_density") != after.get("viewport_visual_density"):
        return True
    if before.get("viewport_composition") != after.get("viewport_composition"):
        return True
    if abs((_float_or_none(before.get("viewport_whitespace_ratio")) or 0.0) - (_float_or_none(after.get("viewport_whitespace_ratio")) or 0.0)) >= 0.08:
        return True
    if abs((_float_or_none(before.get("palette_color_count")) or 0.0) - (_float_or_none(after.get("palette_color_count")) or 0.0)) >= 2:
        return True
    return False


def _dismissal_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Dismissal Audit",
        "",
        "Evidence-quality diagnostics only. Raw viewport remains the primary evidence.",
        "",
        f"- Total results: {audit.get('total_results', 0)}",
        f"- Dismissal attempts: {audit.get('attempted', 0)}",
        f"- Successful dismissals: {audit.get('successful', 0)}",
        f"- Failed dismissals: {audit.get('failed', 0)}",
        f"- Dismissal success rate: {_format_percent(audit.get('dismissal_success_rate'))}",
        f"- Mutation summary: {json.dumps(audit.get('mutation_summary') or {}, sort_keys=True)}",
        "",
        "## Severity Transitions",
        "",
        f"- Before: {json.dumps(audit.get('before_severity_distribution') or {}, sort_keys=True)}",
        f"- After: {json.dumps(audit.get('after_severity_distribution') or {}, sort_keys=True)}",
        f"- Eligibility: {json.dumps(audit.get('eligibility_distribution') or {}, sort_keys=True)}",
        f"- Block reasons: {json.dumps(audit.get('block_reason_distribution') or {}, sort_keys=True)}",
        f"- Perceptual states: {json.dumps(audit.get('state_distribution') or {}, sort_keys=True)}",
        f"- Transition reasons: {json.dumps(audit.get('transition_reason_distribution') or {}, sort_keys=True)}",
        f"- Affordance categories: {json.dumps(audit.get('affordance_category_distribution') or {}, sort_keys=True)}",
        f"- Interaction policies: {json.dumps(audit.get('interaction_policy_distribution') or {}, sort_keys=True)}",
        f"- Affordance owners: {json.dumps(audit.get('affordance_owner_distribution') or {}, sort_keys=True)}",
        f"- Safe-to-dismiss candidates not clicked: {audit.get('safe_to_dismiss_candidates_not_clicked', 0)}",
        f"- Unsafe-to-mutate candidates encountered: {audit.get('unsafe_to_mutate_candidates_encountered', 0)}",
        f"- Requires-human-review candidates encountered: {audit.get('requires_human_review_candidates_encountered', 0)}",
        "",
        "## Material Viewport Changes",
        "",
    ]
    changed = audit.get("materially_changed_cases") or []
    if not changed:
        lines.append("- None")
    else:
        for row in changed:
            lines.append(f"- {row.get('brand_name')} ({row.get('website_url')})")
    lines.extend(["", "## Failed Dismissals", "", "| Brand | Method | Clicked Text | Before | After |", "| --- | --- | --- | --- | --- |"])
    failed = audit.get("failed_dismissals") or []
    if not failed:
        lines.append("| - | - | - | - | - |")
    else:
        for row in failed:
            lines.append(
                f"| {row.get('brand_name')} | {row.get('dismissal_method') or '-'} | {row.get('clicked_text') or '-'} | "
                f"{row.get('before_severity') or '-'} | {row.get('after_severity') or '-'} |"
            )
    return "\n".join(lines)


def _severity_rank(value: str) -> int:
    order = {"none": 0, "minor": 1, "moderate": 2, "major": 3, "blocking": 4}
    return order.get(value, 0)


def _coerce_dict_or_none(value: Any, *, field_name: str) -> dict[str, Any] | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Field '{field_name}' must be valid JSON if provided as a string") from exc
        if parsed is None:
            return None
        if not isinstance(parsed, dict):
            raise ValueError(f"Field '{field_name}' must decode to an object")
        return parsed
    raise ValueError(f"Field '{field_name}' must be an object or JSON object string")


def _coerce_transition_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            rows.append(item)
    return rows


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
        raw_dom_html = page.content()
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
                    clean_dom_html = page.content()
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
