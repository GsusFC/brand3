"""Validated loader for the experimental perceptual corpus.

This module keeps the corpus as a research-only asset. It does not feed
scoring or product routing directly; it only validates and loads the static
case library used by the experimental perceptual narrative layer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PERCEPTUAL_ROOT = ROOT / "examples" / "perceptual_library"
PATTERN_REGISTRY_PATH = PERCEPTUAL_ROOT / "patterns" / "perceptual_pattern_registry.json"
READING_SEMANTICS_PATH = PERCEPTUAL_ROOT / "patterns" / "perceptual_reading_semantics.json"
CASE_RECORD_GLOB = "cases/*/perceptual_case_record.json"


class PerceptualCorpusError(ValueError):
    """Raised when a perceptual case record fails validation."""


_SECTION_TEXT_FIELDS = {
    "extracted_facts": "fact",
    "visual_observations": "observation",
    "strategic_interpretation": "interpretation",
    "weak_inferences": "inference",
    "human_review_requirements": "requirement",
}

_PATTERN_CONFIDENCE_VALUES = {"high", "medium", "low"}
_DOMAIN_CONTEXT_ORIGINAL_VALUES = {"web3", "crypto", "fintech", "culture", "SaaS", "other"}
_DOMAIN_CONTEXT_NORMALIZATION_VALUES = {"normalized", "unnormalized", "needs_human_review"}
_WEB3_OR_CRYPTO_VALUES = {"web3", "crypto"}

_REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "record_type",
    "case_id",
    "brand_name",
    "document_title",
    "source_ref",
    "workspace_location",
    "source_family",
    "status",
    "language",
)

_REQUIRED_COMPANY_CONTEXT_FIELDS = (
    "company_name",
    "category",
    "business_model",
    "offer_summary",
    "target_audience_summary",
    "stage_or_context",
    "project_scope",
    "source_confidence",
    "sensitive_notes",
)


def load_perceptual_artifacts(root: Path | None = None) -> dict[str, Any]:
    """Load the perceptual registry, semantics and pilot case records.

    Returns an empty dict when the corpus is absent. Raises on malformed
    records so the caller can fail closed and fall back to the built-in
    hints bundle.
    """

    root = Path(root) if root is not None else PERCEPTUAL_ROOT
    registry_path = root / "patterns" / "perceptual_pattern_registry.json"
    semantics_path = root / "patterns" / "perceptual_reading_semantics.json"
    if not registry_path.exists() or not semantics_path.exists():
        return {}

    registry = _load_json_dict(registry_path, label="pattern registry")
    semantics = _load_json_dict(semantics_path, label="reading semantics")
    case_records = [
        load_perceptual_case_record(path)
        for path in sorted(root.glob(CASE_RECORD_GLOB))
        if path.is_file()
    ]
    if not case_records:
        return {}
    return {
        "registry": registry,
        "semantics": semantics,
        "case_records": case_records,
    }


def load_perceptual_case_record(path: Path | str) -> dict[str, Any]:
    """Load and validate a single perceptual case record."""

    path = Path(path)
    record = _load_json_dict(path, label=f"case record {path.name}")
    return validate_perceptual_case_record(record)


def validate_perceptual_case_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate the minimal perceptual case record schema."""

    if not isinstance(record, dict):
        raise PerceptualCorpusError("perceptual case record must be a JSON object")

    for field in _REQUIRED_TOP_LEVEL_FIELDS:
        _require_string(record, field, "top-level")

    company_context = record.get("company_context")
    if not isinstance(company_context, dict):
        raise PerceptualCorpusError("company_context must be an object")
    for field in _REQUIRED_COMPANY_CONTEXT_FIELDS:
        if field == "sensitive_notes":
            value = company_context.get(field)
            if not isinstance(value, str):
                raise PerceptualCorpusError("company_context.sensitive_notes must be a string")
            continue
        _require_string(company_context, field, "company_context")

    domain_context = record.get("domain_context")
    if not isinstance(domain_context, dict):
        raise PerceptualCorpusError("domain_context must be an object")
    _require_string(domain_context, "original_domain", "domain_context")
    original_domain = domain_context["original_domain"]
    if original_domain not in _DOMAIN_CONTEXT_ORIGINAL_VALUES:
        raise PerceptualCorpusError(
            "domain_context.original_domain must be one of: web3, crypto, fintech, culture, SaaS, other"
        )
    technology_context = domain_context.get("technology_context")
    if not isinstance(technology_context, list):
        raise PerceptualCorpusError("domain_context.technology_context must be a list")
    for index, item in enumerate(technology_context):
        if not isinstance(item, str) or not item.strip():
            raise PerceptualCorpusError(
                f"domain_context.technology_context[{index}] must be a non-empty string"
            )
    _require_string(domain_context, "business_model_analogy", "domain_context")
    transferable_patterns = domain_context.get("transferable_brand_patterns")
    if not isinstance(transferable_patterns, list) or not transferable_patterns:
        raise PerceptualCorpusError(
            "domain_context.transferable_brand_patterns must be a non-empty list"
        )
    for index, item in enumerate(transferable_patterns):
        if not isinstance(item, str) or not item.strip():
            raise PerceptualCorpusError(
                f"domain_context.transferable_brand_patterns[{index}] must be a non-empty string"
            )
    domain_noise = domain_context.get("domain_specific_noise")
    if not isinstance(domain_noise, list):
        raise PerceptualCorpusError("domain_context.domain_specific_noise must be a list")
    for index, item in enumerate(domain_noise):
        if not isinstance(item, str) or not item.strip():
            raise PerceptualCorpusError(
                f"domain_context.domain_specific_noise[{index}] must be a non-empty string"
            )
    normalization_status = domain_context.get("normalization_status")
    if normalization_status not in _DOMAIN_CONTEXT_NORMALIZATION_VALUES:
        raise PerceptualCorpusError(
            "domain_context.normalization_status must be one of: normalized, unnormalized, needs_human_review"
        )
    if original_domain in _WEB3_OR_CRYPTO_VALUES:
        _require_string(domain_context, "traditional_equivalent_category", "domain_context")
        if not domain_context.get("traditional_equivalent_category"):
            raise PerceptualCorpusError(
                "domain_context.traditional_equivalent_category is required for web3/crypto records"
            )
        if not domain_noise:
            raise PerceptualCorpusError(
                "domain_context.domain_specific_noise is required for web3/crypto records"
            )

    for section, text_field in _SECTION_TEXT_FIELDS.items():
        items = record.get(section)
        if not isinstance(items, list):
            raise PerceptualCorpusError(f"{section} must be a list")
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise PerceptualCorpusError(f"{section}[{index}] must be an object")
            _require_string(item, text_field, f"{section}[{index}]")
            if section != "human_review_requirements":
                refs = item.get("evidence_refs")
                if not isinstance(refs, list):
                    raise PerceptualCorpusError(f"{section}[{index}].evidence_refs must be a list")
                for ref_index, ref in enumerate(refs):
                    if not isinstance(ref, str) or not ref.strip():
                        raise PerceptualCorpusError(
                            f"{section}[{index}].evidence_refs[{ref_index}] must be a non-empty string"
                        )
            elif "evidence_refs" in item:
                refs = item.get("evidence_refs")
                if not isinstance(refs, list):
                    raise PerceptualCorpusError(
                        f"{section}[{index}].evidence_refs must be a list when provided"
                    )
                for ref_index, ref in enumerate(refs):
                    if not isinstance(ref, str) or not ref.strip():
                        raise PerceptualCorpusError(
                            f"{section}[{index}].evidence_refs[{ref_index}] must be a non-empty string"
                        )

    pattern_refs = record.get("pattern_refs")
    if not isinstance(pattern_refs, list) or not pattern_refs:
        raise PerceptualCorpusError("pattern_refs must be a non-empty list")
    for index, item in enumerate(pattern_refs):
        if not isinstance(item, dict):
            raise PerceptualCorpusError(f"pattern_refs[{index}] must be an object")
        _require_string(item, "pattern_id", f"pattern_refs[{index}]")
        _require_string(item, "pattern_name", f"pattern_refs[{index}]")
        _require_string(item, "reason", f"pattern_refs[{index}]")
        confidence = item.get("confidence")
        if confidence not in _PATTERN_CONFIDENCE_VALUES:
            raise PerceptualCorpusError(
                f"pattern_refs[{index}].confidence must be one of: high, medium, low"
            )
        refs = item.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            raise PerceptualCorpusError(f"pattern_refs[{index}].evidence_refs must be a non-empty list")
        for ref_index, ref in enumerate(refs):
            if not isinstance(ref, str) or not ref.strip():
                raise PerceptualCorpusError(
                    f"pattern_refs[{index}].evidence_refs[{ref_index}] must be a non-empty string"
                )

    review_requirements = record.get("human_review_requirements")
    if not isinstance(review_requirements, list):
        raise PerceptualCorpusError("human_review_requirements must be a list")
    for index, item in enumerate(review_requirements):
        if not isinstance(item, dict):
            raise PerceptualCorpusError(f"human_review_requirements[{index}] must be an object")
        _require_string(item, "requirement", f"human_review_requirements[{index}]")
        _require_string(item, "reason", f"human_review_requirements[{index}]")

    optional_lists = ("review_notes", "perceptual_tags")
    for field in optional_lists:
        value = record.get(field)
        if value is None:
            continue
        if not isinstance(value, list):
            raise PerceptualCorpusError(f"{field} must be a list when provided")

    return record


def _load_json_dict(path: Path, *, label: str) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise PerceptualCorpusError(f"{label} must be a JSON object")
    return data


def _require_string(payload: dict[str, Any], key: str, scope: str) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PerceptualCorpusError(f"{scope}.{key} must be a non-empty string")
