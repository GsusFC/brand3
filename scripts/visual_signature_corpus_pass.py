#!/usr/bin/env python3
"""Run the screenshot-backed Visual Signature corpus capture pass.

This developer utility writes evidence artifacts only. It does not modify
Brand3 scoring, rubric dimensions, production reports, or web UI.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_signature_build_baselines import build_baseline_artifacts  # noqa: E402
from scripts.visual_signature_calibrate import (  # noqa: E402
    CalibrationBrand,
    _obstruction_audit_markdown,
    build_obstruction_audit,
    run_calibration_batch,
)
from scripts.visual_signature_capture_screenshots import (  # noqa: E402
    CaptureBrand,
    _capture_with_playwright,
    capture_screenshots,
)
from src.visual_signature.corpus import baseline_eligibility  # noqa: E402


DEFAULT_CORPUS_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "calibration_corpus"


def run_corpus_pass(
    *,
    corpus_root: str | Path = DEFAULT_CORPUS_ROOT,
    skip_capture: bool = False,
    skip_calibration: bool = False,
) -> dict[str, Any]:
    root = Path(corpus_root)
    run_started_at = datetime.now().isoformat()
    manifests_dir = root / "manifests"
    payloads_dir = root / "payloads"
    failures_dir = root / "failures"
    baselines_dir = root / "baselines" / "first_pass"
    eligible_payloads_dir = baselines_dir / "eligible_payloads"
    screenshots_dir = root / "screenshots" / "viewport"
    for path in (manifests_dir, payloads_dir, failures_dir, baselines_dir, eligible_payloads_dir, screenshots_dir):
        path.mkdir(parents=True, exist_ok=True)

    records = _load_seed_records(root / "categories")
    capture_input_path = manifests_dir / "capture_input.json"
    calibration_input_path = manifests_dir / "calibration_input.json"
    capture_manifest_path = manifests_dir / "viewport_capture_manifest.json"

    capture_brands = _build_capture_brands(records, root)
    _write_json(
        capture_input_path,
        {
            "schema_version": "visual-signature-corpus-capture-input-1",
            "generated_at": datetime.now().isoformat(),
            "capture_type": "viewport",
            "viewport_width": 1440,
            "viewport_height": 900,
            "brands": [brand.__dict__ for brand in capture_brands],
        },
    )

    if skip_capture and capture_manifest_path.exists():
        capture_manifest = _load_json(capture_manifest_path)
    else:
        capture_manifest = capture_screenshots(
            capture_brands,
            output_dir=screenshots_dir,
            manifest_path=capture_manifest_path,
            capture_fn=_capture_with_playwright,
            capture_both=False,
        )

    screenshot_failures = _screenshot_failures(capture_manifest)
    _write_json(
        failures_dir / "screenshot_failures.json",
        {
            "schema_version": "visual-signature-corpus-screenshot-failures-1",
            "generated_at": datetime.now().isoformat(),
            "total": len(screenshot_failures),
            "failures": screenshot_failures,
        },
    )

    capture_index = _capture_index(capture_manifest)
    calibration_brands = _build_calibration_brands(records, root, capture_index)
    _write_json(
        calibration_input_path,
        {
            "schema_version": "visual-signature-corpus-calibration-input-1",
            "generated_at": datetime.now().isoformat(),
            "with_vision": True,
            "brands": [
                {
                    "brand_name": brand.brand_name,
                    "website_url": brand.website_url,
                    "expected_category": brand.expected_category,
                    "notes": brand.notes,
                    "capture_type": brand.capture_type,
                    "screenshot_path": brand.screenshot_path,
                    "screenshot_payload": brand.screenshot_payload,
                }
                for brand in calibration_brands
            ],
        },
    )

    if skip_calibration and (payloads_dir / "manifest.json").exists():
        calibration_manifest = _load_json(payloads_dir / "manifest.json")
    else:
        calibration_manifest = run_calibration_batch(
            calibration_brands,
            output_dir=payloads_dir,
            with_vision=True,
        )
    obstruction_audit = build_obstruction_audit(calibration_manifest)
    _write_json(payloads_dir / "obstruction_audit.json", obstruction_audit)
    (payloads_dir / "obstruction_audit.md").write_text(_obstruction_audit_markdown(obstruction_audit) + "\n", encoding="utf-8")

    acquisition_failures = _acquisition_failures(calibration_manifest, payloads_dir)
    _write_json(
        failures_dir / "acquisition_failures.json",
        {
            "schema_version": "visual-signature-corpus-acquisition-failures-1",
            "generated_at": datetime.now().isoformat(),
            "total": len(acquisition_failures),
            "failures": acquisition_failures,
        },
    )

    eligibility = _annotate_payload_eligibility(payloads_dir, eligible_payloads_dir)
    _write_json(manifests_dir / "eligibility_manifest.json", eligibility)
    (root / "eligibility_summary.md").write_text(_eligibility_summary(eligibility) + "\n", encoding="utf-8")

    baseline_result = build_baseline_artifacts(input_dir=eligible_payloads_dir, output_dir=baselines_dir)
    corpus_metrics = _corpus_metrics(
        records=records,
        capture_manifest=capture_manifest,
        calibration_manifest=calibration_manifest,
        eligibility=eligibility,
    )
    _write_json(manifests_dir / "corpus_metrics.json", corpus_metrics)

    run_manifest = {
        "schema_version": "visual-signature-corpus-pass-1",
        "started_at": run_started_at,
        "completed_at": datetime.now().isoformat(),
        "corpus_root": str(root),
        "record_count": len(records),
        "capture_manifest": str(capture_manifest_path),
        "calibration_manifest": str(payloads_dir / "manifest.json"),
        "obstruction_audit": str(payloads_dir / "obstruction_audit.json"),
        "eligibility_manifest": str(manifests_dir / "eligibility_manifest.json"),
        "corpus_metrics": str(manifests_dir / "corpus_metrics.json"),
        "screenshot_failures": str(failures_dir / "screenshot_failures.json"),
        "acquisition_failures": str(failures_dir / "acquisition_failures.json"),
        "baseline_result": baseline_result,
    }
    _write_json(manifests_dir / "corpus_pass_manifest.json", run_manifest)
    return run_manifest


def _load_seed_records(categories_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(categories_dir.glob("*.json")):
        payload = _load_json(path)
        category = str(payload.get("category") or path.stem)
        for row in payload.get("records") or []:
            if not isinstance(row, dict):
                continue
            record = dict(row)
            record["category"] = str(record.get("category") or category)
            record["_seed_path"] = str(path)
            records.append(record)
    return records


def _build_capture_brands(records: list[dict[str, Any]], root: Path) -> list[CaptureBrand]:
    brands: list[CaptureBrand] = []
    for record in records:
        category = str(record.get("category") or "uncategorized")
        screenshot_path = root / "screenshots" / "viewport" / category / f"{_slugify(record['brand_name'])}.png"
        brands.append(
            CaptureBrand(
                brand_name=str(record["brand_name"]),
                website_url=str(record["website_url"]),
                screenshot_path=str(screenshot_path),
                capture_type="viewport",
            )
        )
    return brands


def _build_calibration_brands(
    records: list[dict[str, Any]],
    root: Path,
    capture_index: dict[str, dict[str, Any]],
) -> list[CalibrationBrand]:
    brands: list[CalibrationBrand] = []
    for record in records:
        category = str(record.get("category") or "uncategorized")
        screenshot_path = root / "screenshots" / "viewport" / category / f"{_slugify(record['brand_name'])}.png"
        metadata = capture_index.get(str(screenshot_path.resolve())) or {}
        brands.append(
            CalibrationBrand(
                brand_name=str(record["brand_name"]),
                website_url=str(record["website_url"]),
                expected_category=category,
                notes=str(record.get("selection_reason") or ""),
                capture_type="viewport",
                screenshot_path=str(screenshot_path),
                screenshot_payload={
                    "capture_type": "viewport",
                    "page_url": metadata.get("page_url") or record.get("website_url"),
                    "viewport_width": metadata.get("viewport_width") or 1440,
                    "viewport_height": metadata.get("viewport_height") or 900,
                    "width": metadata.get("width"),
                    "height": metadata.get("height"),
                    "file_size_bytes": metadata.get("file_size_bytes"),
                    "source": metadata.get("source") or "playwright",
                    "capture_status": metadata.get("status") or "pending",
                    "capture_error": metadata.get("error"),
                },
            )
        )
    return brands


def _annotate_payload_eligibility(payloads_dir: Path, eligible_payloads_dir: Path) -> dict[str, Any]:
    if eligible_payloads_dir.exists():
        shutil.rmtree(eligible_payloads_dir)
    eligible_payloads_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for path in sorted(payloads_dir.glob("*.json")):
        if path.name == "manifest.json" or path.name.endswith(".error.json"):
            continue
        payload = _load_json(path)
        if not _looks_like_visual_signature_payload(payload):
            continue
        result = baseline_eligibility(payload)
        payload["baseline_eligible"] = bool(result["baseline_eligible"])
        payload["baseline_eligibility"] = result
        _write_json(path, payload)
        if result["baseline_eligible"]:
            shutil.copy2(path, eligible_payloads_dir / path.name)
        category = str((payload.get("calibration") or {}).get("expected_category") or "uncategorized")
        by_category[category]["total"] += 1
        by_category[category]["eligible" if result["baseline_eligible"] else "ineligible"] += 1
        results.append(
            {
                "brand_name": payload.get("brand_name"),
                "website_url": payload.get("website_url"),
                "category": category,
                "payload_path": str(path),
                **result,
            }
        )

    total = len(results)
    eligible = sum(1 for row in results if row["baseline_eligible"])
    return {
        "schema_version": "visual-signature-corpus-eligibility-1",
        "generated_at": datetime.now().isoformat(),
        "total": total,
        "eligible": eligible,
        "ineligible": total - eligible,
        "eligible_payloads_dir": str(eligible_payloads_dir),
        "per_category": {
            category: {
                "total": counts["total"],
                "eligible": counts["eligible"],
                "ineligible": counts["ineligible"],
                "eligibility_rate": round(counts["eligible"] / counts["total"], 3) if counts["total"] else 0.0,
            }
            for category, counts in sorted(by_category.items())
        },
        "results": results,
    }


def _corpus_metrics(
    *,
    records: list[dict[str, Any]],
    capture_manifest: dict[str, Any],
    calibration_manifest: dict[str, Any],
    eligibility: dict[str, Any],
) -> dict[str, Any]:
    total = len(records)
    interpretable = int(calibration_manifest.get("ok") or 0)
    viewport_available = int(calibration_manifest.get("viewport_available") or 0)
    agreement_available = int(calibration_manifest.get("agreement_high") or 0) + int(calibration_manifest.get("agreement_medium") or 0) + int(calibration_manifest.get("agreement_low") or 0)
    obstruction_present = int(calibration_manifest.get("obstruction_present") or 0)
    invalid_first_impression = int(calibration_manifest.get("invalid_first_impression") or 0)
    per_category_total = Counter(str(record.get("category") or "uncategorized") for record in records)
    per_category_interpretable = Counter(
        str(row.get("expected_category") or "uncategorized")
        for row in calibration_manifest.get("results", [])
        if row.get("status") == "ok"
    )
    per_category_viewport = Counter(
        str(row.get("expected_category") or "uncategorized")
        for row in calibration_manifest.get("results", [])
        if row.get("viewport_available")
    )
    per_category_obstruction = Counter(
        str(row.get("expected_category") or "uncategorized")
        for row in calibration_manifest.get("results", [])
        if row.get("obstruction_present")
    )
    per_category_invalid_first_impression = Counter(
        str(row.get("expected_category") or "uncategorized")
        for row in calibration_manifest.get("results", [])
        if row.get("first_impression_valid") is False
    )
    return {
        "schema_version": "visual-signature-corpus-metrics-1",
        "generated_at": datetime.now().isoformat(),
        "total_records": total,
        "screenshot_capture_ok": int(capture_manifest.get("ok") or 0),
        "screenshot_capture_failed": int(capture_manifest.get("error") or 0),
        "interpretable_rate": _rate(interpretable, total),
        "viewport_availability_rate": _rate(viewport_available, total),
        "agreement_availability_rate": _rate(agreement_available, total),
        "viewport_obstruction_rate": _rate(obstruction_present, total),
        "invalid_first_impression_rate": _rate(invalid_first_impression, total),
        "baseline_eligibility_rate": _rate(int(eligibility.get("eligible") or 0), total),
        "per_category": {
            category: {
                "total": count,
                "interpretable": per_category_interpretable[category],
                "interpretable_rate": _rate(per_category_interpretable[category], count),
                "viewport_available": per_category_viewport[category],
                "viewport_availability_rate": _rate(per_category_viewport[category], count),
                "viewport_obstructed": per_category_obstruction[category],
                "viewport_obstruction_rate": _rate(per_category_obstruction[category], count),
                "invalid_first_impression": per_category_invalid_first_impression[category],
                "invalid_first_impression_rate": _rate(per_category_invalid_first_impression[category], count),
                "eligible": (eligibility.get("per_category") or {}).get(category, {}).get("eligible", 0),
                "eligibility_rate": (eligibility.get("per_category") or {}).get(category, {}).get("eligibility_rate", 0.0),
            }
            for category, count in sorted(per_category_total.items())
        },
    }


def _eligibility_summary(eligibility: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Corpus Eligibility Summary",
        "",
        f"- Total payloads: {eligibility.get('total', 0)}",
        f"- Baseline eligible: {eligibility.get('eligible', 0)}",
        f"- Ineligible: {eligibility.get('ineligible', 0)}",
        f"- Eligible payloads dir: `{eligibility.get('eligible_payloads_dir')}`",
        "",
        "| Category | Total | Eligible | Ineligible | Eligibility |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for category, row in (eligibility.get("per_category") or {}).items():
        lines.append(
            f"| {category} | {row['total']} | {row['eligible']} | {row['ineligible']} | {row['eligibility_rate']:.0%} |"
        )
    failure_counts = Counter()
    for row in eligibility.get("results") or []:
        for failure in row.get("failures") or []:
            failure_counts[failure] += 1
    lines.extend(["", "## Ineligibility Reasons", ""])
    if failure_counts:
        for failure, count in failure_counts.most_common():
            lines.append(f"- `{failure}`: {count}")
    else:
        lines.append("- None")
    return "\n".join(lines)


def _screenshot_failures(capture_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in capture_manifest.get("results", [])
        if isinstance(row, dict) and row.get("status") == "error"
    ]


def _acquisition_failures(calibration_manifest: dict[str, Any], payloads_dir: Path) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in calibration_manifest.get("results", []):
        if not isinstance(row, dict):
            continue
        if row.get("status") not in {"not_interpretable", "error"}:
            continue
        payload_path = Path(str(row.get("output_json") or ""))
        acquisition = {}
        if payload_path.exists() and payload_path.parent == payloads_dir:
            try:
                payload = _load_json(payload_path)
                acquisition = payload.get("acquisition") if isinstance(payload.get("acquisition"), dict) else {}
            except Exception:
                acquisition = {}
        failures.append(
            {
                "brand_name": row.get("brand_name"),
                "website_url": row.get("website_url"),
                "expected_category": row.get("expected_category"),
                "status": row.get("status"),
                "interpretation_status": row.get("interpretation_status"),
                "error": row.get("error"),
                "acquisition_errors": acquisition.get("errors") or [],
                "output_json": row.get("output_json"),
            }
        )
    return failures


def _capture_index(capture_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in capture_manifest.get("results") or []:
        if not isinstance(row, dict):
            continue
        path = str(row.get("screenshot_path") or "")
        if path:
            index[str(Path(path).resolve())] = row
    return index


def _looks_like_visual_signature_payload(payload: dict[str, Any]) -> bool:
    return bool(payload.get("version") == "visual-signature-mvp-1" or payload.get("vision"))


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part) or "brand"


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Visual Signature calibration corpus capture pass.")
    parser.add_argument("--corpus-root", default=str(DEFAULT_CORPUS_ROOT), help="Calibration corpus root.")
    parser.add_argument("--skip-capture", action="store_true", help="Reuse an existing viewport capture manifest.")
    parser.add_argument("--skip-calibration", action="store_true", help="Reuse existing payloads/manifest.")
    args = parser.parse_args(argv)
    result = run_corpus_pass(
        corpus_root=args.corpus_root,
        skip_capture=args.skip_capture,
        skip_calibration=args.skip_calibration,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
