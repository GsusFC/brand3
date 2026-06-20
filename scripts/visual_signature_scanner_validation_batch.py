#!/usr/bin/env python3
"""Run a curated Visual Signature scanner validation batch.

The batch is intentionally separate from Brand3 scoring. It exercises the
scanner contract, records evidence quality, and highlights review risks.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.collectors.web_collector import WebCollector
from src.services.brand_service import (
    _screenshot_capture_diagnostic,
    _take_screenshot_with_budget,
    _visual_signature_shadow_screenshot_payload,
)
from src.services.feature_pipeline import ScreenshotResult, capture_screenshot
from src.visual_signature import run_visual_signature_scan


@dataclass(frozen=True)
class ValidationTarget:
    brand_name: str
    url: str
    segment: str
    risk_focus: str


DEFAULT_TARGETS = [
    ValidationTarget("Pleo", "https://www.pleo.io/es", "fintech_saas", "cookie banner + customer-logo strip"),
    ValidationTarget("Linear", "https://linear.app", "productivity_saas", "minimal UI + dark visual system"),
    ValidationTarget("Notion", "https://www.notion.com", "productivity_saas", "large content/nav surface"),
    ValidationTarget("Aesop", "https://www.aesop.com", "luxury_retail", "editorial luxury + regional modals"),
    ValidationTarget("Loewe", "https://www.loewe.com", "luxury_fashion", "luxury commerce imagery"),
    ValidationTarget("Headspace", "https://www.headspace.com", "wellness", "illustrative brand system"),
    ValidationTarget("Calm", "https://www.calm.com", "wellness", "consumer app visual identity"),
    ValidationTarget("Airbnb", "https://www.airbnb.com", "marketplace", "marketplace search-first surface"),
    ValidationTarget("Stripe", "https://stripe.com", "fintech_infrastructure", "dense product + motion assets"),
    ValidationTarget("Miro", "https://miro.com", "collaboration_saas", "product imagery + template proof"),
]


def evaluate_scan(
    scan: dict[str, Any],
    *,
    validation_capture: dict[str, object] | None = None,
) -> dict[str, Any]:
    dimensions = scan.get("dimensions") if isinstance(scan.get("dimensions"), dict) else {}
    capture = scan.get("capture") if isinstance(scan.get("capture"), dict) else {}
    obstruction = capture.get("obstruction") if isinstance(capture.get("obstruction"), dict) else {}
    identity = dimensions.get("identity_clarity") if isinstance(dimensions.get("identity_clarity"), dict) else {}
    validation_capture = validation_capture if isinstance(validation_capture, dict) else {}
    flags: list[str] = []
    validation_attempted = bool(validation_capture.get("attempted"))
    validation_success = bool(validation_capture.get("success"))
    validation_error_type = str(validation_capture.get("error_type") or "")
    if validation_attempted and not validation_success:
        flags.append(f"batch_capture_failed:{validation_error_type or 'unknown'}")
    if not capture.get("available"):
        flags.append("missing_screenshot")
    if obstruction.get("present"):
        flags.append(f"obstructed:{obstruction.get('type') or 'unknown'}")
    if float(identity.get("score") or 0) < 55:
        flags.append("weak_identity_detection")
    if scan.get("status") in {"not_evaluable", "partial", "review_required"}:
        flags.append(f"status:{scan.get('status')}")
    if not flags:
        verdict = "usable"
    elif (
        "weak_identity_detection" in flags
        or "missing_screenshot" in flags
        or any(flag.startswith("batch_capture_failed:") for flag in flags)
    ):
        verdict = "needs_review"
    else:
        verdict = "usable_with_limitations"
    return {
        "verdict": verdict,
        "flags": flags,
        "score": scan.get("score"),
        "status": scan.get("status"),
        "capture_available": bool(capture.get("available")),
        "obstruction_type": obstruction.get("type") if obstruction.get("present") else "none",
        "identity_score": identity.get("score"),
        "validation_capture_status": validation_capture.get("status") or "unknown",
    }


def capture_target_screenshot(
    target: ValidationTarget,
    *,
    enabled: bool,
    provider: str,
    timeout_seconds: int,
) -> ScreenshotResult:
    return capture_screenshot(
        url=target.url,
        skip_visual_analysis=not enabled,
        take_screenshot_with_budget=lambda url: _take_screenshot_with_budget(
            url,
            timeout_seconds=timeout_seconds,
            provider=provider,
        ),
        screenshot_capture_diagnostic=_screenshot_capture_diagnostic,
    )


def run_target(
    target: ValidationTarget,
    *,
    capture_screenshots: bool,
    screenshot_provider: str,
    screenshot_timeout_seconds: int,
) -> dict[str, Any]:
    web = WebCollector().scrape(target.url, crawl_subpages=False)
    screenshot = capture_target_screenshot(
        target,
        enabled=capture_screenshots,
        provider=screenshot_provider,
        timeout_seconds=screenshot_timeout_seconds,
    )
    screenshot_payload = _visual_signature_shadow_screenshot_payload(
        screenshot.capture,
        page_url=target.url,
    )
    scan = run_visual_signature_scan(
        brand_name=target.brand_name,
        website_url=target.url,
        web_data=web,
        screenshot_payload=screenshot_payload,
    )
    return {
        "target": asdict(target),
        "web_error": web.error,
        "screenshot_capture": screenshot.capture,
        "scan": scan,
        "quality": evaluate_scan(scan, validation_capture=screenshot.capture),
    }


def markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Scanner Validation Batch",
        "",
        f"Generated: {payload['generated_at']}",
        f"Targets: {len(payload['results'])}",
        "",
        "| Brand | Segment | Score | Status | Capture | Verdict | Flags |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for result in payload["results"]:
        target = result["target"]
        quality = result["quality"]
        flags = ", ".join(quality["flags"]) if quality["flags"] else "-"
        lines.append(
            "| {brand} | {segment} | {score} | {status} | {capture} | {verdict} | {flags} |".format(
                brand=target["brand_name"],
                segment=target["segment"],
                score=quality.get("score"),
                status=quality.get("status"),
                capture=quality.get("validation_capture_status") or "unknown",
                verdict=quality["verdict"],
                flags=flags,
            )
        )
    lines.extend(
        [
            "",
            "## Review Criteria",
            "",
            "- `batch_capture_failed:*`: validation could not produce screenshot evidence.",
            "- `missing_screenshot`: scanner result is useful only as partial evidence.",
            "- `weak_identity_detection`: logo/brand-mark evidence needs manual review.",
            "- `obstructed:*`: first viewport was affected by cookie/chat/modal or similar UI.",
            "- Visual Signature output remains evidence-only and does not modify Brand3 scoring.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_batch(
    targets: list[ValidationTarget],
    *,
    capture_screenshots: bool,
    screenshot_provider: str,
    screenshot_timeout_seconds: int,
) -> dict[str, Any]:
    results = []
    for target in targets:
        print(f"[visual-signature] {target.brand_name} — {target.url}")
        try:
            results.append(
                run_target(
                    target,
                    capture_screenshots=capture_screenshots,
                    screenshot_provider=screenshot_provider,
                    screenshot_timeout_seconds=screenshot_timeout_seconds,
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "target": asdict(target),
                    "web_error": str(exc),
                    "scan": None,
                    "quality": {
                        "verdict": "failed",
                        "flags": ["exception"],
                        "status": "failed",
                    },
                }
            )
    return {
        "schema_version": "visual-signature-scanner-validation-batch-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "capture": {
            "enabled": capture_screenshots,
            "provider": screenshot_provider,
            "timeout_seconds": screenshot_timeout_seconds,
        },
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Visual Signature scanner validation batch")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of default targets")
    parser.add_argument("--output-dir", default="output/visual_signature_validation", help="Output directory")
    parser.add_argument(
        "--skip-screenshot",
        action="store_true",
        help="Run scanner without viewport screenshot capture",
    )
    parser.add_argument(
        "--screenshot-provider",
        default="playwright",
        choices=["playwright", "firecrawl"],
        help="Screenshot provider for validation evidence",
    )
    parser.add_argument(
        "--screenshot-timeout-seconds",
        type=int,
        default=45,
        help="Per-target screenshot capture timeout",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    targets = DEFAULT_TARGETS[: args.limit] if args.limit else list(DEFAULT_TARGETS)
    payload = run_batch(
        targets,
        capture_screenshots=not args.skip_screenshot,
        screenshot_provider=args.screenshot_provider,
        screenshot_timeout_seconds=args.screenshot_timeout_seconds,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "validation_batch.json"
    md_path = output_dir / "validation_batch.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown_report(payload), encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
