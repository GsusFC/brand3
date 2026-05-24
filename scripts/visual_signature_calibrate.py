#!/usr/bin/env python3
"""Run Visual Signature calibration batches for manual review.

This is developer tooling. It runs the Visual Signature evidence extractor over
a curated list of real websites, saves payload JSON plus compact summaries, and
records per-brand errors without stopping the batch. It does not modify Brand3
scoring, dimensions, reports, or web UI.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_signature_inspect import (  # noqa: E402
    inspect_payload,
    interpretation_status,
    signal_coverage,
    weak_signals,
)
from src.visual_signature import extract_visual_signature  # noqa: E402
from src.visual_signature.vision import enrich_visual_signature_with_vision  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "examples" / "visual_signature" / "calibration_brands.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "examples" / "visual_signature" / "calibration_outputs"
DEFAULT_CAPTURE_MANIFEST = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "capture_manifest.json"


@dataclass(frozen=True)
class CalibrationBrand:
    brand_name: str
    website_url: str
    expected_category: str
    notes: str = ""
    capture_type: str = ""
    screenshot_path: str = ""
    screenshot_payload: dict[str, Any] | None = None


@dataclass
class CalibrationResult:
    brand_name: str
    website_url: str
    expected_category: str
    notes: str
    status: str
    output_json: str | None = None
    summary_txt: str | None = None
    error: str | None = None
    extraction_confidence: float | None = None
    extraction_level: str | None = None
    interpretation_status: str | None = None
    signal_coverage: float | None = None
    weak_signal_count: int | None = None
    vision_status: str | None = None
    vision_available: bool | None = None
    vision_confidence: float | None = None
    viewport_available: bool | None = None
    viewport_confidence: float | None = None
    agreement_level: str | None = None
    disagreement_flags: list[str] | None = None
    obstruction_present: bool | None = None
    obstruction_type: str | None = None
    obstruction_severity: str | None = None
    obstruction_coverage_ratio: float | None = None
    first_impression_valid: bool | None = None
    obstruction_confidence: float | None = None


Extractor = Callable[..., dict[str, Any]]


def load_calibration_brands(path: str | Path) -> list[CalibrationBrand]:
    source = Path(path)
    if source.suffix.lower() == ".csv":
        return _load_csv(source)
    if source.suffix.lower() == ".json":
        return _load_json(source)
    raise ValueError("Calibration input must be .json or .csv")


def run_calibration_batch(
    brands: list[CalibrationBrand],
    *,
    output_dir: str | Path,
    with_vision: bool = False,
    extractor: Extractor = extract_visual_signature,
    now: Callable[[], datetime] = datetime.now,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    summaries_dir = output_path / "summaries"
    summaries_dir.mkdir(exist_ok=True)
    capture_index = _load_capture_index(DEFAULT_CAPTURE_MANIFEST) if with_vision else {}

    started_at = now().isoformat()
    results: list[CalibrationResult] = []
    for brand in brands:
        slug = _slugify(brand.brand_name)
        json_path = output_path / f"{slug}.json"
        summary_path = summaries_dir / f"{slug}.txt"
        try:
            payload = extractor(
                brand_name=brand.brand_name,
                website_url=brand.website_url,
            )
            payload["calibration"] = {
                "expected_category": brand.expected_category,
                "notes": brand.notes,
            }
            if with_vision:
                screenshot_payload = _merge_screenshot_payloads(
                    brand.screenshot_payload,
                    _lookup_capture_metadata(capture_index, brand.screenshot_path),
                    {"capture_type": brand.capture_type} if brand.capture_type else None,
                )
                payload = enrich_visual_signature_with_vision(
                    visual_signature_payload=payload,
                    screenshot_path=brand.screenshot_path or None,
                    screenshot_payload=screenshot_payload,
                )
            _write_json(json_path, payload)
            summary = _build_summary(brand, payload)
            summary_path.write_text(summary + "\n", encoding="utf-8")
            extraction = payload.get("extraction_confidence") or {}
            payload_interpretation_status = interpretation_status(payload)
            vision = payload.get("vision") if with_vision else None
            vision_screenshot = (vision or {}).get("screenshot") if isinstance(vision, dict) else {}
            vision_confidence = (vision or {}).get("vision_confidence") if isinstance(vision, dict) else {}
            viewport_confidence = (vision or {}).get("viewport_confidence") if isinstance(vision, dict) else {}
            agreement = (vision or {}).get("agreement") if isinstance(vision, dict) else {}
            obstruction = (vision or {}).get("viewport_obstruction") if isinstance(vision, dict) else {}
            vision_status = _vision_status(vision) if with_vision else "disabled"
            results.append(
                CalibrationResult(
                    brand_name=brand.brand_name,
                    website_url=brand.website_url,
                    expected_category=brand.expected_category,
                    notes=brand.notes,
                    status="not_interpretable" if payload_interpretation_status == "not_interpretable" else "ok",
                    output_json=str(json_path),
                    summary_txt=str(summary_path),
                    extraction_confidence=_float_or_none(extraction.get("score")),
                    extraction_level=str(extraction.get("level") or ""),
                    interpretation_status=payload_interpretation_status,
                    signal_coverage=signal_coverage(payload),
                    weak_signal_count=len(weak_signals(payload)),
                    vision_status=vision_status,
                    vision_available=bool(vision_screenshot.get("available")) if with_vision else None,
                    vision_confidence=_float_or_none((vision_confidence or {}).get("score")) if with_vision else None,
                    viewport_available=bool(vision_screenshot.get("available")) if with_vision else None,
                    viewport_confidence=_float_or_none((viewport_confidence or {}).get("score")) if with_vision else None,
                    agreement_level=str((agreement or {}).get("agreement_level") or "") if with_vision else None,
                    disagreement_flags=list((agreement or {}).get("disagreement_flags") or []) if with_vision else None,
                    obstruction_present=bool((obstruction or {}).get("present")) if with_vision else None,
                    obstruction_type=str((obstruction or {}).get("type") or "") if with_vision else None,
                    obstruction_severity=str((obstruction or {}).get("severity") or "") if with_vision else None,
                    obstruction_coverage_ratio=_float_or_none((obstruction or {}).get("coverage_ratio")) if with_vision else None,
                    first_impression_valid=bool((obstruction or {}).get("first_impression_valid")) if with_vision and obstruction else None,
                    obstruction_confidence=_float_or_none((obstruction or {}).get("confidence")) if with_vision else None,
                )
            )
        except Exception as exc:
            error_path = output_path / f"{slug}.error.json"
            error_payload = {
                "brand_name": brand.brand_name,
                "website_url": brand.website_url,
                "expected_category": brand.expected_category,
                "notes": brand.notes,
                "status": "error",
                "error": str(exc),
            }
            _write_json(error_path, error_payload)
            results.append(
                CalibrationResult(
                    brand_name=brand.brand_name,
                    website_url=brand.website_url,
                    expected_category=brand.expected_category,
                    notes=brand.notes,
                    status="error",
                    output_json=str(error_path),
                    error=str(exc),
                )
            )

    manifest = {
        "started_at": started_at,
        "completed_at": now().isoformat(),
        "output_dir": str(output_path),
        "with_vision": with_vision,
        "total": len(results),
        "ok": sum(1 for item in results if item.status == "ok"),
        "not_interpretable": sum(1 for item in results if item.status == "not_interpretable"),
        "error": sum(1 for item in results if item.status == "error"),
        "vision_available": sum(1 for item in results if item.vision_available),
        "vision_missing": sum(1 for item in results if item.vision_available is False),
        "vision_confidence_avg": _average(
            [item.vision_confidence for item in results if item.vision_confidence is not None]
        ),
        "viewport_available": sum(1 for item in results if item.viewport_available),
        "viewport_missing": sum(1 for item in results if item.viewport_available is False),
        "viewport_confidence_avg": _average(
            [item.viewport_confidence for item in results if item.viewport_confidence is not None]
        ),
        "agreement_high": sum(1 for item in results if item.agreement_level == "high"),
        "agreement_medium": sum(1 for item in results if item.agreement_level == "medium"),
        "agreement_low": sum(1 for item in results if item.agreement_level == "low"),
        "obstruction_present": sum(1 for item in results if item.obstruction_present),
        "obstruction_absent": sum(1 for item in results if item.obstruction_present is False),
        "invalid_first_impression": sum(1 for item in results if item.first_impression_valid is False),
        "results": [asdict(item) for item in results],
    }
    _write_json(output_path / "manifest.json", manifest)
    obstruction_audit = build_obstruction_audit(manifest)
    _write_json(output_path / "obstruction_audit.json", obstruction_audit)
    (output_path / "obstruction_audit.md").write_text(_obstruction_audit_markdown(obstruction_audit) + "\n", encoding="utf-8")
    (output_path / "batch_summary.md").write_text(_batch_summary(manifest) + "\n", encoding="utf-8")
    return manifest


def _build_summary(brand: CalibrationBrand, payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Expected category: {brand.expected_category}",
            f"Notes: {brand.notes or '-'}",
            "",
            inspect_payload(payload, label=brand.brand_name),
        ]
    )


def _batch_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Calibration Batch",
        "",
        f"- Total: {manifest['total']}",
        f"- Interpretable captures: {manifest['ok']}",
        f"- Not interpretable: {manifest.get('not_interpretable', 0)}",
        f"- Errors: {manifest['error']}",
        f"- Vision enabled: {bool(manifest.get('with_vision'))}",
        f"- Vision available: {manifest.get('vision_available', 0)}",
        f"- Vision missing: {manifest.get('vision_missing', 0)}",
        f"- Vision confidence avg: {_format_optional_float(manifest.get('vision_confidence_avg'))}",
        f"- Viewport available: {manifest.get('viewport_available', 0)}",
        f"- Viewport missing: {manifest.get('viewport_missing', 0)}",
        f"- Viewport confidence avg: {_format_optional_float(manifest.get('viewport_confidence_avg'))}",
        f"- Agreement high: {manifest.get('agreement_high', 0)}",
        f"- Agreement medium: {manifest.get('agreement_medium', 0)}",
        f"- Agreement low: {manifest.get('agreement_low', 0)}",
        f"- Viewport obstructions: {manifest.get('obstruction_present', 0)}",
        f"- Invalid first impressions: {manifest.get('invalid_first_impression', 0)}",
        "",
        "| Brand | Category | Status | Interpretation | Confidence | Coverage | Weak visual signals | Vision | Vision confidence | Viewport confidence | Agreement | Obstruction | First impression | Flags |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for item in manifest["results"]:
        confidence = item.get("extraction_confidence")
        coverage = item.get("signal_coverage")
        status = item.get("interpretation_status") or "-"
        vision_status = item.get("vision_status") or "-"
        vision_confidence = item.get("vision_confidence")
        viewport_confidence = item.get("viewport_confidence")
        agreement_level = item.get("agreement_level") or "-"
        obstruction = _format_obstruction(item)
        first_impression = _format_first_impression(item.get("first_impression_valid"))
        flags = ",".join(item.get("disagreement_flags") or []) or "-"
        lines.append(
            f"| {item['brand_name']} | {item['expected_category']} | {item['status']} | "
            f"{status} | {_format_optional_float(confidence)} | {_format_percent(coverage)} | "
            f"{item.get('weak_signal_count') if item.get('weak_signal_count') is not None else '-'} | "
            f"{vision_status} | {_format_optional_float(vision_confidence)} | {_format_optional_float(viewport_confidence)} | "
            f"{agreement_level} | {obstruction} | {first_impression} | {flags} |"
        )
    return "\n".join(lines)


def build_obstruction_audit(manifest: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in manifest.get("results") or [] if isinstance(row, dict)]
    with_vision_rows = [row for row in rows if row.get("obstruction_present") is not None]
    total = len(with_vision_rows)
    present_rows = [row for row in with_vision_rows if row.get("obstruction_present")]
    invalid_rows = [row for row in with_vision_rows if row.get("first_impression_valid") is False]
    severity_counts = _count_by(with_vision_rows, "obstruction_severity", include_empty=False)
    type_counts = _count_by(present_rows, "obstruction_type", include_empty=False)
    category_counts: dict[str, dict[str, Any]] = {}
    for row in with_vision_rows:
        category = str(row.get("expected_category") or "uncategorized")
        bucket = category_counts.setdefault(
            category,
            {"total": 0, "obstructed": 0, "invalid_first_impression": 0, "severity_distribution": {}},
        )
        bucket["total"] += 1
        if row.get("obstruction_present"):
            bucket["obstructed"] += 1
        if row.get("first_impression_valid") is False:
            bucket["invalid_first_impression"] += 1
        severity = str(row.get("obstruction_severity") or "")
        if severity and severity != "none":
            bucket["severity_distribution"][severity] = bucket["severity_distribution"].get(severity, 0) + 1
    for bucket in category_counts.values():
        bucket["obstruction_rate"] = _rate(bucket["obstructed"], bucket["total"])
        bucket["invalid_first_impression_rate"] = _rate(bucket["invalid_first_impression"], bucket["total"])

    return {
        "schema_version": "visual-signature-obstruction-audit-1",
        "generated_at": datetime.now().isoformat(),
        "total": total,
        "obstructed": len(present_rows),
        "obstruction_prevalence": _rate(len(present_rows), total),
        "invalid_first_impressions": len(invalid_rows),
        "invalid_first_impression_rate": _rate(len(invalid_rows), total),
        "severity_distribution": severity_counts,
        "type_distribution": type_counts,
        "per_category": dict(sorted(category_counts.items())),
        "obstructed_results": [
            {
                "brand_name": row.get("brand_name"),
                "website_url": row.get("website_url"),
                "expected_category": row.get("expected_category"),
                "obstruction_type": row.get("obstruction_type"),
                "obstruction_severity": row.get("obstruction_severity"),
                "coverage_ratio": row.get("obstruction_coverage_ratio"),
                "first_impression_valid": row.get("first_impression_valid"),
                "confidence": row.get("obstruction_confidence"),
                "output_json": row.get("output_json"),
            }
            for row in present_rows
        ],
    }


def _obstruction_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Viewport Obstruction Audit",
        "",
        "Evidence-quality diagnostics only. This report does not dismiss banners, modify pages, or affect scoring.",
        "",
        f"- Total vision rows: {audit.get('total', 0)}",
        f"- Obstructed viewports: {audit.get('obstructed', 0)} ({_format_percent(audit.get('obstruction_prevalence'))})",
        f"- Invalid first impressions: {audit.get('invalid_first_impressions', 0)} ({_format_percent(audit.get('invalid_first_impression_rate'))})",
        "",
        "## Severity Distribution",
        "",
    ]
    severity = audit.get("severity_distribution") or {}
    if severity:
        for key, count in sorted(severity.items()):
            lines.append(f"- `{key}`: {count}")
    else:
        lines.append("- None")
    lines.extend(["", "## Per Category", "", "| Category | Total | Obstructed | Obstruction Rate | Invalid First Impression |", "| --- | ---: | ---: | ---: | ---: |"])
    for category, row in (audit.get("per_category") or {}).items():
        lines.append(
            f"| {category} | {row['total']} | {row['obstructed']} | "
            f"{_format_percent(row['obstruction_rate'])} | {_format_percent(row['invalid_first_impression_rate'])} |"
        )
    lines.extend(["", "## Obstructed Results", "", "| Brand | Category | Type | Severity | Coverage | First Impression Valid |", "| --- | --- | --- | --- | ---: | --- |"])
    obstructed = audit.get("obstructed_results") or []
    if not obstructed:
        lines.append("| - | - | - | - | - | - |")
    for row in obstructed:
        lines.append(
            f"| {row.get('brand_name')} | {row.get('expected_category')} | {row.get('obstruction_type') or '-'} | "
            f"{row.get('obstruction_severity') or '-'} | {_format_percent(row.get('coverage_ratio'))} | "
            f"{_format_first_impression(row.get('first_impression_valid'))} |"
        )
    return "\n".join(lines)


def _load_json(path: Path) -> list[CalibrationBrand]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("brands") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("JSON input must be a list or an object with a 'brands' list")
    return [_brand_from_row(row, row_index=index + 1) for index, row in enumerate(rows)]


def _load_csv(path: Path) -> list[CalibrationBrand]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [_brand_from_row(row, row_index=index + 1) for index, row in enumerate(reader)]


def _brand_from_row(row: dict[str, Any], *, row_index: int) -> CalibrationBrand:
    if not isinstance(row, dict):
        raise ValueError(f"Row {row_index} must be an object")
    brand_name = str(row.get("brand_name") or row.get("brandName") or "").strip()
    website_url = str(row.get("website_url") or row.get("websiteUrl") or "").strip()
    expected_category = str(row.get("expected_category") or row.get("expectedCategory") or "").strip()
    notes = str(row.get("notes") or "").strip()
    screenshot_path = str(row.get("screenshot_path") or row.get("screenshotPath") or "").strip()
    screenshot_payload = row.get("screenshot_payload") or row.get("screenshotPayload")
    screenshot_payload = _coerce_dict_or_none(screenshot_payload, row_index=row_index, field_name="screenshot_payload")
    missing = [
        name
        for name, value in (
            ("brand_name", brand_name),
            ("website_url", website_url),
            ("expected_category", expected_category),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"Row {row_index} missing required field(s): {', '.join(missing)}")
    return CalibrationBrand(
        brand_name=brand_name,
        website_url=website_url,
        expected_category=expected_category,
        notes=notes,
        capture_type=str(row.get("capture_type") or row.get("captureType") or "").strip(),
        screenshot_path=screenshot_path,
        screenshot_payload=screenshot_payload,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part) or "brand"


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_optional_float(value: Any) -> str:
    number = _float_or_none(value)
    return f"{number:.2f}" if number is not None else "-"


def _format_percent(value: Any) -> str:
    number = _float_or_none(value)
    return f"{number:.0%}" if number is not None else "-"


def _average(values: list[float | None]) -> float | None:
    numbers = [value for value in values if value is not None]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 3)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def _count_by(rows: list[dict[str, Any]], field_name: str, *, include_empty: bool = True) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(field_name) or "")
        if not value and not include_empty:
            continue
        if value == "none" and not include_empty:
            continue
        key = value or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _format_obstruction(item: dict[str, Any]) -> str:
    if item.get("obstruction_present") is None:
        return "-"
    if not item.get("obstruction_present"):
        return "none"
    obstruction_type = item.get("obstruction_type") or "unknown_overlay"
    severity = item.get("obstruction_severity") or "unknown"
    coverage = _format_percent(item.get("obstruction_coverage_ratio"))
    return f"{obstruction_type}/{severity}/{coverage}"


def _format_first_impression(value: Any) -> str:
    if value is True:
        return "valid"
    if value is False:
        return "invalid"
    return "-"


def _vision_status(vision: dict[str, Any] | None) -> str:
    if not isinstance(vision, dict):
        return "disabled"
    screenshot = vision.get("screenshot") or {}
    if not isinstance(screenshot, dict):
        return "missing"
    quality = str(screenshot.get("quality") or "missing").strip()
    return quality or "missing"


def _load_capture_index(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        screenshot_path = str(row.get("screenshot_path") or "").strip()
        if not screenshot_path:
            continue
        metadata = {
            "capture_type": row.get("capture_type"),
            "page_url": row.get("page_url") or row.get("website_url"),
            "viewport_width": row.get("viewport_width") or row.get("width"),
            "viewport_height": row.get("viewport_height") or row.get("height"),
            "source": row.get("source"),
            "width": row.get("width"),
            "height": row.get("height"),
            "file_size_bytes": row.get("file_size_bytes"),
        }
        keys = _screenshot_index_keys(screenshot_path)
        for key in keys:
            index[key] = metadata
    return index


def _screenshot_index_keys(path: str | None) -> list[tuple[str, str]]:
    if not path:
        return []
    resolved = Path(path)
    return [
        ("abs", str(resolved.resolve())),
        ("base", resolved.name),
    ]


def _lookup_capture_metadata(
    capture_index: dict[tuple[str, str], dict[str, Any]],
    screenshot_path: str | None,
) -> dict[str, Any] | None:
    for key in _screenshot_index_keys(screenshot_path):
        metadata = capture_index.get(key)
        if metadata:
            return metadata
    return None


def _merge_screenshot_payloads(*payloads: dict[str, Any] | None) -> dict[str, Any] | None:
    merged: dict[str, Any] = {}
    for payload in payloads:
        if isinstance(payload, dict):
            merged.update({key: value for key, value in payload.items() if value not in (None, "")})
    return merged or None


def _coerce_dict_or_none(value: Any, *, row_index: int, field_name: str) -> dict[str, Any] | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Row {row_index} field '{field_name}' must be valid JSON if provided as a string") from exc
        if parsed is None:
            return None
        if not isinstance(parsed, dict):
            raise ValueError(f"Row {row_index} field '{field_name}' must decode to an object")
        return parsed
    raise ValueError(f"Row {row_index} field '{field_name}' must be an object or JSON object string")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Visual Signature calibration batch.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="CSV or JSON calibration input file.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for payloads, summaries, and manifest.")
    parser.add_argument("--with-vision", action="store_true", help="Enrich payloads with local screenshot-derived Vision evidence.")
    args = parser.parse_args(argv)

    brands = load_calibration_brands(args.input)
    manifest = run_calibration_batch(brands, output_dir=args.output_dir, with_vision=args.with_vision)
    print(_batch_summary(manifest))
    return 0 if manifest["error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
