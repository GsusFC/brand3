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


def evaluate_scan(scan: dict[str, Any]) -> dict[str, Any]:
    dimensions = scan.get("dimensions") if isinstance(scan.get("dimensions"), dict) else {}
    capture = scan.get("capture") if isinstance(scan.get("capture"), dict) else {}
    obstruction = capture.get("obstruction") if isinstance(capture.get("obstruction"), dict) else {}
    identity = dimensions.get("identity_clarity") if isinstance(dimensions.get("identity_clarity"), dict) else {}
    flags: list[str] = []
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
    elif "weak_identity_detection" in flags or "missing_screenshot" in flags:
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
    }


def run_target(target: ValidationTarget) -> dict[str, Any]:
    web = WebCollector().scrape(target.url, crawl_subpages=False)
    scan = run_visual_signature_scan(
        brand_name=target.brand_name,
        website_url=target.url,
        web_data=web,
    )
    return {
        "target": asdict(target),
        "web_error": web.error,
        "scan": scan,
        "quality": evaluate_scan(scan),
    }


def markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Scanner Validation Batch",
        "",
        f"Generated: {payload['generated_at']}",
        f"Targets: {len(payload['results'])}",
        "",
        "| Brand | Segment | Score | Status | Verdict | Flags |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for result in payload["results"]:
        target = result["target"]
        quality = result["quality"]
        flags = ", ".join(quality["flags"]) if quality["flags"] else "-"
        lines.append(
            "| {brand} | {segment} | {score} | {status} | {verdict} | {flags} |".format(
                brand=target["brand_name"],
                segment=target["segment"],
                score=quality.get("score"),
                status=quality.get("status"),
                verdict=quality["verdict"],
                flags=flags,
            )
        )
    lines.extend(
        [
            "",
            "## Review Criteria",
            "",
            "- `missing_screenshot`: scanner result is useful only as partial evidence.",
            "- `weak_identity_detection`: logo/brand-mark evidence needs manual review.",
            "- `obstructed:*`: first viewport was affected by cookie/chat/modal or similar UI.",
            "- Visual Signature output remains evidence-only and does not modify Brand3 scoring.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_batch(targets: list[ValidationTarget]) -> dict[str, Any]:
    results = []
    for target in targets:
        print(f"[visual-signature] {target.brand_name} — {target.url}")
        try:
            results.append(run_target(target))
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
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Visual Signature scanner validation batch")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of default targets")
    parser.add_argument("--output-dir", default="output/visual_signature_validation", help="Output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    targets = DEFAULT_TARGETS[: args.limit] if args.limit else list(DEFAULT_TARGETS)
    payload = run_batch(targets)
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
