"""Contract checks for BrandResearchPack payloads.

The dataclasses in ``src.reports.brand_research_pack`` validate basic enum
shape. This module validates cross-field invariants that matter before a pack
is handed to the Analyst Pass: identity, source traceability, and minimum
strategic substance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from src.reports.brand_research_pack import BrandResearchPack


CONTRACT_VERSION = "brand_research_pack_contract_v0_1"
EXPECTED_PACK_VERSION = "brand_research_pack_v0_1"

PACK_SOURCE_TYPES = {
    "owned_official",
    "owned_product",
    "owned_about",
    "owned_security_trust",
    "proof_point",
    "press_or_founder",
    "competitive_context",
    "social",
    "noise",
    "unknown",
}

CRITICAL_TEXT_FIELDS = (
    "company_summary",
    "product_summary",
    "offer",
    "audience",
    "outcome",
)


@dataclass(frozen=True, slots=True)
class ResearchPackContractIssue:
    """One contract finding."""

    code: str
    field: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "field": self.field,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ResearchPackContractReport:
    """Structured result of validating a BrandResearchPack."""

    version: str
    errors: tuple[ResearchPackContractIssue, ...]
    warnings: tuple[ResearchPackContractIssue, ...]

    @property
    def passed(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "passed": self.passed,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }

    def error_summary(self) -> str:
        return "; ".join(f"{issue.field}: {issue.message}" for issue in self.errors)


def validate_brand_research_pack_contract(pack: BrandResearchPack | dict[str, Any]) -> ResearchPackContractReport:
    """Validate a BrandResearchPack against cross-field data contracts."""

    pack_obj = BrandResearchPack.from_dict(pack) if isinstance(pack, dict) else pack
    errors: list[ResearchPackContractIssue] = []
    warnings: list[ResearchPackContractIssue] = []

    def error(code: str, field: str, message: str) -> None:
        errors.append(ResearchPackContractIssue(code=code, field=field, message=message))

    def warning(code: str, field: str, message: str) -> None:
        warnings.append(ResearchPackContractIssue(code=code, field=field, message=message, severity="warning"))

    if pack_obj.version != EXPECTED_PACK_VERSION:
        error("invalid_version", "version", f"Expected {EXPECTED_PACK_VERSION}.")
    if not _is_url(pack_obj.input_url):
        error("invalid_input_url", "input_url", "input_url must be a valid http(s) URL.")
    if not pack_obj.resolved_entity.resolved_entity.strip():
        error("missing_resolved_entity", "resolved_entity.resolved_entity", "Resolved entity name is required.")
    if pack_obj.resolved_entity.entity_type != pack_obj.entity_type:
        error("entity_type_mismatch", "resolved_entity.entity_type", "Resolved entity type must match pack entity_type.")
    if pack_obj.parent_brand and pack_obj.resolved_entity.parent_brand and pack_obj.parent_brand != pack_obj.resolved_entity.parent_brand:
        error("parent_brand_mismatch", "parent_brand", "Pack parent_brand must match resolved_entity.parent_brand.")

    _validate_url_list(pack_obj.official_urls, "official_urls", errors)
    _validate_url_list(pack_obj.analyzed_urls, "analyzed_urls", errors)

    if not pack_obj.source_map:
        error("missing_source_map", "source_map", "At least one traceable source is required.")

    source_urls = set()
    for key, source in pack_obj.source_map.items():
        if not _is_url(source.url):
            error("invalid_source_url", f"source_map.{key}.url", "Source URL must be valid.")
            continue
        source_urls.add(source.url)
        if key != source.url:
            warning("source_key_url_mismatch", f"source_map.{key}", "Source map key should match source.url for stable lookup.")
        if source.source_type not in PACK_SOURCE_TYPES:
            warning("unknown_source_type", f"source_map.{key}.source_type", f"Unexpected source_type '{source.source_type}'.")

    known_urls = source_urls | set(pack_obj.official_urls) | set(pack_obj.analyzed_urls)
    if pack_obj.input_url and known_urls and pack_obj.input_url not in known_urls:
        warning("input_url_not_traced", "input_url", "input_url is not present in source_map, official_urls, or analyzed_urls.")

    _validate_evidence_collection(
        pack_obj.proof_points,
        field="proof_points",
        expected_kind="proof",
        known_urls=known_urls,
        errors=errors,
        warnings=warnings,
    )
    _validate_evidence_collection(
        pack_obj.founder_or_press_context,
        field="founder_or_press_context",
        expected_kind="context",
        known_urls=known_urls,
        errors=errors,
        warnings=warnings,
    )
    _validate_evidence_collection(
        pack_obj.competitive_context,
        field="competitive_context",
        expected_kind="context",
        known_urls=known_urls,
        errors=errors,
        warnings=warnings,
    )
    _validate_evidence_collection(
        pack_obj.noise_rejected,
        field="noise_rejected",
        expected_kind="noise",
        known_urls=known_urls,
        errors=errors,
        warnings=warnings,
    )

    has_strategic_substance = any(str(getattr(pack_obj, field) or "").strip() for field in CRITICAL_TEXT_FIELDS)
    has_positive_evidence = bool(pack_obj.proof_points or pack_obj.founder_or_press_context)
    if not has_strategic_substance and not has_positive_evidence and not pack_obj.evidence_gaps:
        error(
            "empty_pack_without_gap",
            "evidence_gaps",
            "A pack with no strategic text or positive evidence must explain the gap.",
        )

    if pack_obj.noise_rejected and not pack_obj.evidence_gaps and not has_strategic_substance:
        warning("noise_without_gap", "noise_rejected", "Noise-only packs should explain why positive evidence was unavailable.")

    return ResearchPackContractReport(
        version=CONTRACT_VERSION,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def assert_brand_research_pack_contract(pack: BrandResearchPack | dict[str, Any]) -> ResearchPackContractReport:
    """Validate and raise ValueError when the contract fails."""

    report = validate_brand_research_pack_contract(pack)
    if not report.passed:
        raise ValueError(f"BrandResearchPack contract failed: {report.error_summary()}")
    return report


def _validate_url_list(
    values: list[str],
    field: str,
    errors: list[ResearchPackContractIssue],
) -> None:
    seen: set[str] = set()
    for index, value in enumerate(values):
        if value in seen:
            errors.append(
                ResearchPackContractIssue(
                    code="duplicate_url",
                    field=f"{field}.{index}",
                    message=f"Duplicate URL '{value}'.",
                )
            )
        seen.add(value)
        if not _is_url(value):
            errors.append(
                ResearchPackContractIssue(
                    code="invalid_url",
                    field=f"{field}.{index}",
                    message="URL must be valid http(s).",
                )
            )


def _validate_evidence_collection(
    items: list[Any],
    *,
    field: str,
    expected_kind: str,
    known_urls: set[str],
    errors: list[ResearchPackContractIssue],
    warnings: list[ResearchPackContractIssue],
) -> None:
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(items):
        path = f"{field}.{index}"
        text = str(getattr(item, "text", "") or "").strip()
        source_url = str(getattr(item, "source_url", "") or "").strip()
        kind = str(getattr(item, "kind", "") or "").strip()
        if not text:
            errors.append(ResearchPackContractIssue("missing_evidence_text", f"{path}.text", "Evidence text is required."))
        if kind != expected_kind:
            errors.append(
                ResearchPackContractIssue(
                    "wrong_evidence_kind",
                    f"{path}.kind",
                    f"Expected kind '{expected_kind}', got '{kind}'.",
                )
            )
        duplicate_key = (text.lower(), source_url)
        if duplicate_key in seen:
            errors.append(ResearchPackContractIssue("duplicate_evidence", path, "Duplicate evidence item."))
        seen.add(duplicate_key)
        if source_url:
            if not _is_url(source_url):
                errors.append(ResearchPackContractIssue("invalid_evidence_source_url", f"{path}.source_url", "Evidence source_url must be valid."))
            elif known_urls and source_url not in known_urls:
                errors.append(
                    ResearchPackContractIssue(
                        "untraced_evidence_source",
                        f"{path}.source_url",
                        "Evidence source_url must exist in source_map, official_urls, or analyzed_urls.",
                    )
                )
        else:
            warnings.append(
                ResearchPackContractIssue(
                    "missing_evidence_source_url",
                    f"{path}.source_url",
                    "Evidence without source_url is less auditable.",
                    severity="warning",
                )
            )


def _is_url(value: str) -> bool:
    parsed = urlparse(str(value or ""))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
