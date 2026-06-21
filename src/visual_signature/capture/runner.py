"""Visual Signature screenshot capture runner."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from src.visual_signature.affordance_semantics import classify_affordance
from src.visual_signature.affordance_semantics import classify_affordance_owner
from src.visual_signature.capture.clean_capture import clean_attempt_quality
from src.visual_signature.capture._capture_screenshots import CaptureBrand
from src.visual_signature.capture._capture_screenshots import CaptureFn
from src.visual_signature.capture._capture_screenshots import CaptureResult
from src.visual_signature.capture._capture_screenshots import capture_result_to_dict as _capture_result_to_dict_module
from src.visual_signature.capture._capture_screenshots import coerce_dict_or_none as _coerce_dict_or_none_module
from src.visual_signature.capture._capture_screenshots import coerce_transition_list as _coerce_transition_list_module
from src.visual_signature.capture._capture_screenshots import derived_capture_path as _derived_capture_path_module
from src.visual_signature.capture._capture_screenshots import float_or_none as _float_or_none_module
from src.visual_signature.capture._capture_screenshots import format_percent as _format_percent_module
from src.visual_signature.capture._capture_screenshots import int_or_none as _int_or_none_module
from src.visual_signature.capture._capture_screenshots import load_capture_brands
from src.visual_signature.capture._capture_screenshots import normalize_capture_type as _normalize_capture_type_module
from src.visual_signature.capture._capture_screenshots import rate as _rate_module
from src.visual_signature.capture._capture_screenshots import write_json as _write_json_module
from src.visual_signature.capture import _capture_screenshots as capture_helpers
from src.visual_signature.perception import PerceptualStateMachine
from src.visual_signature.vision.composition import analyze_composition
from src.visual_signature.vision.palette_from_screenshot import extract_palette_from_screenshot
from src.visual_signature.vision.screenshot_quality import load_raster_image
from src.visual_signature.vision.viewport_obstruction import analyze_viewport_obstruction


PROJECT_ROOT = Path(__file__).resolve().parents[3]
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
                    clean_attempt_capture_variant=metadata.get("clean_attempt_capture_variant") or clean_attempt_capture_variant,
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
        dismissal_audit = _build_dismissal_audit(manifest, clean_attempt_quality=clean_attempt_quality)
        audit_json_path = output_path / "dismissal_audit.json"
        audit_md_path = output_path / "dismissal_audit.md"
        _write_json(audit_json_path, dismissal_audit)
        audit_md_path.write_text(_dismissal_audit_markdown(dismissal_audit) + "\n", encoding="utf-8")
        manifest["dismissal_audit"] = str(audit_json_path)
    _write_json(Path(manifest_path or DEFAULT_MANIFEST), manifest)
    return manifest


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
        raw_dom_html = capture_helpers.visible_obstruction_dom_snapshot(page)
        page.screenshot(path=str(raw_path), full_page=normalized_capture_type != "viewport")
        raw_snapshot = capture_helpers.snapshot_for_path(raw_path, dom_html=raw_dom_html)
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
                machine_data = machine.to_dict()
                result["perceptual_state_data"] = machine_data
                result["perceptual_state"] = machine.current_state
                result["perceptual_transitions"] = machine_data.get("transitions") or []
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
                    clean_dom_html = capture_helpers.visible_obstruction_dom_snapshot(page)
                    page.screenshot(path=str(clean_path), full_page=False)
                    clean_snapshot = capture_helpers.snapshot_for_path(clean_path, dom_html=clean_dom_html)
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
                    machine_data = machine.to_dict()
                    result["perceptual_state_data"] = machine_data
                    result["perceptual_state"] = machine.current_state
                    result["perceptual_transitions"] = machine_data.get("transitions") or []
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
                    machine_data = machine.to_dict()
                    result["perceptual_state_data"] = machine_data
                    result["perceptual_state"] = machine.current_state
                    result["perceptual_transitions"] = machine_data.get("transitions") or []
                    result["mutation_audit"] = None

        context.close()
        browser.close()
        return result


_write_json = _write_json_module
_capture_result_to_dict = _capture_result_to_dict_module
_coerce_dict_or_none = _coerce_dict_or_none_module
_coerce_transition_list = _coerce_transition_list_module
_derived_capture_path = _derived_capture_path_module
_float_or_none = _float_or_none_module
_format_percent = _format_percent_module
_int_or_none = _int_or_none_module
_normalize_capture_type = _normalize_capture_type_module
_rate = _rate_module
_snapshot_for_path = capture_helpers.snapshot_for_path
_affordance_evidence_for_element = capture_helpers.affordance_evidence_for_element
_affordance_localization_evidence_for_element = capture_helpers.affordance_localization_evidence_for_element
_element_localization_snapshot = capture_helpers.element_localization_snapshot
_element_intersects_current_viewport = capture_helpers.element_intersects_current_viewport
_localization_context_terms = capture_helpers.localization_context_terms
_attribute_value = capture_helpers.attribute_value
_affordance_id = capture_helpers.affordance_id
_split_context_tokens = capture_helpers.split_context_tokens
_find_dismissal_candidate = capture_helpers.find_dismissal_candidate
_element_label = capture_helpers.element_label
_visible_obstruction_dom_snapshot = capture_helpers.visible_obstruction_dom_snapshot
_normalize_label = capture_helpers.normalize_label
_dismissal_successful = capture_helpers.dismissal_successful
_severity_distribution = capture_helpers.severity_distribution
_string_distribution = capture_helpers.string_distribution
_transition_reason_distribution = capture_helpers.transition_reason_distribution
_affordance_distribution = capture_helpers.affordance_distribution
_affordance_count = capture_helpers.affordance_count
_target_distribution = capture_helpers.target_distribution
_all_diagnostic_targets = capture_helpers.all_diagnostic_targets
_material_viewport_change = capture_helpers.material_viewport_change
_clean_attempt_quality_distribution = capture_helpers.clean_attempt_quality_distribution
_severity_rank = capture_helpers.severity_rank
_build_dismissal_audit = capture_helpers.build_dismissal_audit
_dismissal_audit_markdown = capture_helpers.dismissal_audit_markdown
_attempt_obstruction_dismissal = capture_helpers.attempt_obstruction_dismissal
_attempt_obstruction_dismissal_with_discovery = capture_helpers.attempt_obstruction_dismissal_with_discovery
_prepare_perceptual_state_machine = capture_helpers.prepare_perceptual_state_machine
_discover_dismissal_targets = capture_helpers.discover_dismissal_targets
_is_safe_dismissal_candidate_fields = capture_helpers.is_safe_dismissal_candidate_fields
_should_record_rejected_click_target = capture_helpers.should_record_rejected_click_target
_should_attempt_obstruction_dismissal = capture_helpers.should_attempt_obstruction_dismissal
_dismissal_eligibility = capture_helpers.dismissal_eligibility
_dismissal_patterns_for_type = capture_helpers.dismissal_patterns_for_type
_dismissal_context_type = capture_helpers.dismissal_context_type
_has_cookie_consent_signal = capture_helpers.has_cookie_consent_signal
_match_dismissal_pattern = capture_helpers.match_dismissal_pattern
_contains_phrase = capture_helpers.contains_phrase
_is_concise_dismissal_label = capture_helpers.is_concise_dismissal_label
_rejection_reason = capture_helpers.rejection_reason
_dismissal_skip_note = capture_helpers.dismissal_skip_note


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
