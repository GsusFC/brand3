#!/usr/bin/env python3
"""Capture local PNG screenshots for Visual Signature vision calibration."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature._internal.dismissal_audit import build_dismissal_audit  # noqa: E402
from src.visual_signature._internal.dismissal_audit import dismissal_audit_markdown  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import capture_with_playwright as _capture_with_playwright  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _normalize_capture_type  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import DISMISSAL_TARGET_SELECTOR  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import PerceptualStateMachine  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _attempt_obstruction_dismissal  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _attempt_obstruction_dismissal_with_discovery  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _coerce_dict_or_none  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _coerce_transition_list  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _discover_dismissal_targets  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _prepare_perceptual_state_machine  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _visible_obstruction_dom_snapshot  # noqa: E402
from src.visual_signature._internal.playwright_capture_helpers_capture_runtime import _derived_capture_path  # noqa: E402
from src.visual_signature.capture.screenshot_capture_models import CaptureBrand  # noqa: E402
from src.visual_signature.capture.screenshot_capture_models import CaptureResult  # noqa: E402
from src.visual_signature.capture.screenshot_capture_models import load_capture_brands  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "examples" / "visual_signature" / "vision_calibration_brands.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots"
DEFAULT_MANIFEST = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "capture_manifest.json"

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


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
