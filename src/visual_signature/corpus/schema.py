"""Lightweight schema checks for the Visual Signature calibration corpus."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REQUIRED_CATEGORIES = {
    "saas",
    "template_like_saas",
    "developer_first",
    "ai_native",
    "editorial_media",
    "ecommerce",
    "premium_luxury",
    "wellness_lifestyle",
    "local_service_small_business",
    "consumer_app",
    "finance_fintech",
    "nonprofit_education",
}


@dataclass
class CorpusValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def load_corpus_manifest(path: str | Path) -> dict[str, Any]:
    return _load_json(path)


def load_category_seed(path: str | Path) -> dict[str, Any]:
    return _load_json(path)


def validate_corpus_manifest(manifest: dict[str, Any]) -> CorpusValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    if manifest.get("schema_version") != "visual-signature-corpus-manifest-1":
        errors.append("schema_version_invalid")
    if not manifest.get("corpus_version"):
        errors.append("corpus_version_missing")
    categories = manifest.get("categories")
    if not isinstance(categories, list):
        errors.append("categories_must_be_list")
        categories = []
    slugs = {str(item.get("slug") or "") for item in categories if isinstance(item, dict)}
    missing = sorted(REQUIRED_CATEGORIES - slugs)
    if missing:
        errors.append(f"required_categories_missing:{','.join(missing)}")
    for slug in sorted(slugs - REQUIRED_CATEGORIES):
        warnings.append(f"unknown_category:{slug}")
    return CorpusValidationResult(valid=not errors, errors=errors, warnings=warnings)


def validate_category_seed(seed: dict[str, Any]) -> CorpusValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    category = str(seed.get("category") or "")
    if category not in REQUIRED_CATEGORIES:
        errors.append("category_invalid")
    if seed.get("schema_version") != "visual-signature-category-seed-1":
        errors.append("schema_version_invalid")
    records = seed.get("records")
    if not isinstance(records, list):
        errors.append("records_must_be_list")
        records = []
    if not records:
        warnings.append("records_empty")
    for index, record in enumerate(records, start=1):
        result = validate_corpus_record(record, expected_category=category)
        errors.extend(f"record_{index}:{item}" for item in result.errors)
        warnings.extend(f"record_{index}:{item}" for item in result.warnings)
    return CorpusValidationResult(valid=not errors, errors=errors, warnings=warnings)


def validate_corpus_record(
    record: dict[str, Any],
    *,
    expected_category: str | None = None,
) -> CorpusValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    if record.get("schema_version") != "visual-signature-corpus-record-1":
        errors.append("schema_version_invalid")
    for key in ("brand_name", "website_url", "category", "selection_reason"):
        if not str(record.get(key) or "").strip():
            errors.append(f"{key}_missing")
    if expected_category and record.get("category") != expected_category:
        errors.append("category_mismatch")
    if record.get("category") not in REQUIRED_CATEGORIES:
        errors.append("category_invalid")
    if record.get("brand_fame_level") not in {"low", "medium", "high"}:
        errors.append("brand_fame_level_invalid")
    if record.get("design_maturity_label") not in {"low", "medium", "high"}:
        errors.append("design_maturity_label_invalid")

    capture = record.get("capture")
    if not isinstance(capture, dict):
        warnings.append("capture_pending")
        capture = {}
    elif capture.get("viewport_required") is not True:
        errors.append("viewport_required_must_be_true")
    if isinstance(capture, dict) and not capture.get("viewport_path"):
        warnings.append("viewport_path_pending")
    full_page_path = capture.get("full_page_path")
    if full_page_path in ("", None) and capture.get("full_page_available") is True:
        errors.append("full_page_available_without_path")

    evidence = record.get("evidence")
    if not isinstance(evidence, dict):
        warnings.append("evidence_pending")
        evidence = {"interpretation_status": "pending"}
    if isinstance(evidence, dict) and not evidence.get("payload_path"):
        warnings.append("payload_path_pending")
    if evidence.get("interpretation_status") not in {"pending", "interpretable", "not_interpretable"}:
        errors.append("interpretation_status_invalid")

    if record.get("baseline_eligible") is True and evidence.get("interpretation_status") != "interpretable":
        errors.append("baseline_eligible_requires_interpretable_evidence")
    return CorpusValidationResult(valid=not errors, errors=errors, warnings=warnings)


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload
