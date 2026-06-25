#!/usr/bin/env python3
"""Capture local PNG screenshots for Visual Signature vision calibration."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature._internal.dismissal_audit import build_dismissal_audit  # noqa: E402
from src.visual_signature._internal.dismissal_audit import dismissal_audit_markdown  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import capture_with_playwright as _capture_with_playwright  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import DISMISSAL_TARGET_SELECTOR  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import PerceptualStateMachine  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _attempt_obstruction_dismissal  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _attempt_obstruction_dismissal_with_discovery  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _coerce_dict_or_none  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _coerce_transition_list  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _discover_dismissal_targets  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _normalize_capture_type  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _prepare_perceptual_state_machine  # noqa: E402
from src.visual_signature.capture.playwright_capture_runtime import _visible_obstruction_dom_snapshot  # noqa: E402
from src.visual_signature.capture.screenshot_capture_manifest import build_error_result  # noqa: E402
from src.visual_signature.capture.screenshot_capture_manifest import build_manifest  # noqa: E402
from src.visual_signature.capture.screenshot_capture_manifest import build_success_result  # noqa: E402
from src.visual_signature.capture.screenshot_capture_manifest import iso_now  # noqa: E402
from src.visual_signature.capture.screenshot_capture_manifest import write_json as _write_json  # noqa: E402
from src.visual_signature.capture.screenshot_capture_models import CaptureBrand  # noqa: E402
from src.visual_signature.capture.screenshot_capture_models import CaptureResult  # noqa: E402
from src.visual_signature.capture.screenshot_capture_models import load_capture_brands  # noqa: E402
from src.visual_signature.capture.screenshot_capture_script_support import capture_brand  # noqa: E402
from src.visual_signature.capture.screenshot_capture_script_support import normalize_brands  # noqa: E402
from src.visual_signature.capture.screenshot_capture_script_support import resolve_capture_path  # noqa: E402


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
    started_at = iso_now(now)
    results: list[CaptureResult] = []
    for brand in brands:
        path = resolve_capture_path(PROJECT_ROOT, brand.screenshot_path)
        try:
            primary_capture_type, metadata, secondary_capture_type, secondary_path, secondary_metadata = capture_brand(
                capture_fn=capture_fn,
                brand=brand,
                screenshot_path=path,
                capture_both=capture_both,
                attempt_dismiss_obstructions=attempt_dismiss_obstructions,
            )
            results.append(
                build_success_result(
                    brand_name=brand.brand_name,
                    website_url=brand.website_url,
                    screenshot_path=path,
                    primary_capture_type=primary_capture_type,
                    metadata=metadata,
                    captured_at=iso_now(now),
                    secondary_path=secondary_path,
                    secondary_capture_type=secondary_capture_type,
                    secondary_metadata=secondary_metadata,
                )
            )
        except Exception as exc:
            results.append(
                build_error_result(
                    brand_name=brand.brand_name,
                    website_url=brand.website_url,
                    screenshot_path=path,
                    capture_type=brand.capture_type,
                    error=exc,
                    captured_at=iso_now(now),
                )
            )
    manifest = build_manifest(
        results=results,
        started_at=started_at,
        completed_at=iso_now(now),
        output_dir=output_path,
        attempt_dismiss_obstructions=attempt_dismiss_obstructions,
    )
    if attempt_dismiss_obstructions:
        dismissal_audit = build_dismissal_audit(manifest)
        audit_json_path = output_path / "dismissal_audit.json"
        audit_md_path = output_path / "dismissal_audit.md"
        _write_json(audit_json_path, dismissal_audit)
        audit_md_path.write_text(dismissal_audit_markdown(dismissal_audit) + "\n", encoding="utf-8")
        manifest["dismissal_audit"] = str(audit_json_path)
    _write_json(Path(manifest_path or DEFAULT_MANIFEST), manifest)
    return manifest


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
    brands = normalize_brands(brands, default_capture_type=args.capture_type)
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
