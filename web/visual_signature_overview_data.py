"""Visual Signature overview and screenshot preview builders."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .visual_signature_data_support import ARTIFACTS
from .visual_signature_data_support import _as_list
from .visual_signature_data_support import _artifact_payload
from .visual_signature_data_support import _artifacts_for_section
from .visual_signature_data_support import _cards_for_section
from .visual_signature_data_support import _find_manifest_row
from .visual_signature_data_support import _is_under_root
from .visual_signature_data_support import _items_for_section
from .visual_signature_data_support import _load_json
from .visual_signature_data_support import _pretty_json
from .visual_signature_data_support import _related_variant_payload
from .visual_signature_data_support import _slugify
from .visual_signature_data_support import _nested
from .visual_signature_data_support import artifact_file_response_payload
from .visual_signature_data_support import artifact_path
from .visual_signature_data_support import screenshot_file_response_payload
from .visual_signature_data_support import visual_signature_root
from .visual_signature_display_data import SECTION_INTROS
from .visual_signature_display_data import SECTION_TITLES
from .visual_signature_display_data import visual_signature_guardrails
from .visual_signature_display_data import visual_signature_nav
from .visual_signature_display_data import visual_signature_next_steps


def build_screenshot_preview_model(filename: str) -> dict[str, Any] | None:
    return build_screenshot_preview_model_for_lang(filename, "es")


def build_screenshot_preview_model_for_lang(filename: str, lang: str = "es") -> dict[str, Any] | None:
    payload = screenshot_file_response_payload(filename)
    if payload is None:
        return None

    selected_path, _media_type = payload
    selected_brand, selected_label = _variant_from_filename(selected_path)
    evidence = _visual_evidence_model()
    selected_item = None
    for item in evidence["items"]:
        if item.get("capture_id") == selected_brand:
            selected_item = item
            break
    if selected_item is None:
        selected_item = {
            "brand_name": selected_brand.replace("-", " ").title(),
            "capture_id": selected_brand,
            "website_url": "",
            "capture_status": "available",
            "obstruction_type": "unknown",
            "obstruction_severity": "unknown",
            "dismissal_attempted": False,
            "dismissal_successful": False,
            "perceptual_state": "evidence_record",
            "evidence_notes": [],
            "variants": [
                _screenshot_variant_payload("raw viewport", visual_signature_root() / "screenshots" / f"{selected_brand}.png"),
                _screenshot_variant_payload("clean attempt", visual_signature_root() / "screenshots" / f"{selected_brand}.clean-attempt.png"),
                _screenshot_variant_payload("full page", visual_signature_root() / "screenshots" / f"{selected_brand}.full-page.png"),
            ],
        }

    selected_variant = None
    for variant in selected_item["variants"]:
        if variant["filename"] == selected_path.name:
            selected_variant = dict(variant)
            break
    if selected_variant is None:
        selected_variant = _screenshot_variant_payload(selected_label, selected_path)

    root = visual_signature_root()
    capture_manifest = _load_json(root / "screenshots" / "capture_manifest.json") or {}
    dismissal_audit = _load_json(root / "screenshots" / "dismissal_audit.json") or {}
    capture_entry = _find_manifest_row(capture_manifest, selected_item["brand_name"])
    dismissal_entry = _find_manifest_row(dismissal_audit, selected_item["brand_name"])
    related = [_related_variant_payload(variant, selected_variant["filename"]) for variant in selected_item["variants"]]
    available_related = [variant for variant in related if variant["exists"]]
    current_index = next(
        (index for index, variant in enumerate(available_related) if variant["filename"] == selected_variant["filename"]),
        -1,
    )
    previous_variant = available_related[current_index - 1] if current_index > 0 else None
    next_variant = available_related[current_index + 1] if 0 <= current_index < len(available_related) - 1 else None

    return {
        "title": f"{selected_item['brand_name']} {'vista previa de captura' if lang == 'es' else 'screenshot preview'}",
        "brand_name": selected_item["brand_name"],
        "capture_id": selected_item["capture_id"],
        "website_url": selected_item.get("website_url") or "",
        "screenshot_type": selected_variant["label"],
        "selected": selected_variant,
        "related": related,
        "previous": previous_variant,
        "next": next_variant,
        "capture_status": selected_item.get("capture_status") or "available",
        "obstruction_type": selected_item.get("obstruction_type") or "unknown",
        "obstruction_severity": selected_item.get("obstruction_severity") or "unknown",
        "perceptual_state": selected_item.get("perceptual_state") or "evidence_record",
        "evidence_notes": selected_item.get("evidence_notes") or [],
        "source_artifacts": [
            {
                "label": "capture_manifest.json",
                "href": "/visual-signature/artifacts/capture_manifest",
                "path": str(root / "screenshots" / "capture_manifest.json"),
                "raw_json": _pretty_json(capture_entry) if capture_entry else "",
            },
            {
                "label": "dismissal_audit.json",
                "href": "/visual-signature/artifacts/dismissal_audit",
                "path": str(root / "screenshots" / "dismissal_audit.json"),
                "raw_json": _pretty_json(dismissal_entry) if dismissal_entry else "",
            },
        ],
        "nav": visual_signature_nav(lang, active_section="overview"),
    }


def build_visual_signature_model(section: str = "overview", lang: str = "es") -> dict[str, Any]:
    if section not in SECTION_TITLES:
        section = "overview"
    if lang not in ("es", "en"):
        lang = "es"
    artifacts = {key: _artifact_payload(key) for key in ARTIFACTS}
    cards = _cards_for_section(section, artifacts)
    return {
        "section": section,
        "title": SECTION_TITLES[section][lang],
        "intro": SECTION_INTROS[section][lang],
        "nav": visual_signature_nav(lang, active_section=section),
        "guardrails": visual_signature_guardrails(lang),
        "cards": cards,
        "artifacts": _artifacts_for_section(section, artifacts),
        "visual_evidence": _visual_evidence_model() if section == "overview" else {"items": [], "summary": {}},
        "records": _items_for_section(section, artifacts),
        "next_steps": visual_signature_next_steps(section, lang),
        "initial_scoring": {
            "href": "/",
            "reports_href": "/reports",
            "note": "Brand3 Scoring remains the existing executable flow. Dimension prose is render-time derived by the current report renderer, not a persisted Visual Signature artifact.",
        },
    }


def _visual_evidence_model() -> dict[str, Any]:
    root = visual_signature_root()
    screenshots_dir = root / "screenshots"
    capture_manifest = _load_json(root / "screenshots" / "capture_manifest.json") or {}
    dismissal_audit = _load_json(root / "screenshots" / "dismissal_audit.json") or {}
    rows = _as_list(capture_manifest.get("results"))
    audit_rows = {
        str(row.get("brand_name") or "").lower(): row
        for row in _as_list(dismissal_audit.get("results"))
        if isinstance(row, dict)
    }

    items = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        brand_name = str(row.get("brand_name") or "Unknown brand")
        audit = audit_rows.get(brand_name.lower()) or {}
        variants = _screenshot_variants(row, screenshots_dir=screenshots_dir)
        items.append(
            {
                "brand_name": brand_name,
                "capture_id": _slugify(brand_name),
                "website_url": row.get("website_url") or row.get("page_url") or "",
                "capture_status": row.get("status") or "available",
                "obstruction_type": _nested(row, "before_obstruction", "type") or "unknown",
                "obstruction_severity": _nested(row, "before_obstruction", "severity") or "unknown",
                "dismissal_attempted": bool(row.get("dismissal_attempted")),
                "dismissal_successful": bool(row.get("dismissal_successful")),
                "perceptual_state": row.get("perceptual_state") or audit.get("perceptual_state") or "evidence_record",
                "evidence_notes": _as_list(row.get("evidence_integrity_notes"))[:4],
                "variants": variants,
            }
        )

    if not items and screenshots_dir.exists():
        grouped: dict[str, dict[str, Any]] = {}
        for path in sorted(screenshots_dir.glob("*")):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            brand, label = _variant_from_filename(path)
            grouped.setdefault(
                brand,
                {
                    "brand_name": brand.replace("-", " ").title(),
                    "capture_id": brand,
                    "website_url": "",
                    "capture_status": "available",
                    "obstruction_type": "unknown",
                    "obstruction_severity": "unknown",
                    "dismissal_attempted": False,
                    "dismissal_successful": False,
                    "perceptual_state": "evidence_record",
                    "evidence_notes": [],
                    "variants": [],
                },
            )["variants"].append(_screenshot_variant_payload(label, path))
        items = list(grouped.values())

    variant_counts = {
        "raw viewport": sum(1 for item in items for variant in item["variants"] if variant["label"] == "raw viewport" and variant["exists"]),
        "clean attempt": sum(1 for item in items for variant in item["variants"] if variant["label"] == "clean attempt" and variant["exists"]),
        "full page": sum(1 for item in items for variant in item["variants"] if variant["label"] == "full page" and variant["exists"]),
    }
    return {
        "summary": {
            "capture_count": len(items),
            "raw_viewport_count": variant_counts["raw viewport"],
            "clean_attempt_count": variant_counts["clean attempt"],
            "full_page_count": variant_counts["full page"],
        },
        "items": items,
    }


def _screenshot_variants(row: dict[str, Any], *, screenshots_dir: Path) -> list[dict[str, Any]]:
    brand_slug = _slugify(str(row.get("brand_name") or ""))
    candidates = [
        ("raw viewport", row.get("raw_screenshot_path") or row.get("screenshot_path") or screenshots_dir / f"{brand_slug}.png"),
        ("clean attempt", row.get("clean_attempt_screenshot_path") or screenshots_dir / f"{brand_slug}.clean-attempt.png"),
        ("full page", row.get("secondary_screenshot_path") or screenshots_dir / f"{brand_slug}.full-page.png"),
    ]
    return [_screenshot_variant_payload(label, Path(path)) for label, path in candidates if path]


def _screenshot_variant_payload(label: str, path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else (Path(__file__).resolve().parents[1] / path)
    exists = resolved.exists() and _is_under_root(resolved)
    filename = resolved.name
    return {
        "label": label,
        "exists": exists,
        "filename": filename,
        "path": str(resolved),
        "href": f"/visual-signature/screenshots/{filename}",
        "preview_href": f"/visual-signature/screenshots/{filename}/preview",
        "alt": f"{label} screenshot: {filename}",
    }


def _variant_from_filename(path: Path) -> tuple[str, str]:
    name = path.name
    stem = path.stem
    if stem.endswith(".clean-attempt"):
        return stem.removesuffix(".clean-attempt"), "clean attempt"
    if stem.endswith(".full-page"):
        return stem.removesuffix(".full-page"), "full page"
    return stem, "raw viewport"
