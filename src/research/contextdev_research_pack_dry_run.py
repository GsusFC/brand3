"""Dry-run Research Pack enrichment from Context.dev candidates."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

from src.reports.brand_research_pack import BrandResearchPack
from src.research.contextdev_candidate_gate import (
    PROMOTABLE,
    ContextDevPromotionReport,
    evaluate_contextdev_summary_promotion,
)


CONTEXTDEV_RESEARCH_PACK_DRY_RUN_VERSION = "contextdev_research_pack_dry_run_v0_1"


@dataclass(frozen=True, slots=True)
class ContextDevPackFieldUpdate:
    field: str
    action: str
    value: str
    candidate_id: str
    candidate_type: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ContextDevResearchPackDryRun:
    version: str
    original_pack: dict[str, Any]
    enriched_pack: dict[str, Any]
    promotion_report: ContextDevPromotionReport
    field_updates: tuple[ContextDevPackFieldUpdate, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "original_pack": self.original_pack,
            "enriched_pack": self.enriched_pack,
            "promotion_report": self.promotion_report.to_dict(),
            "field_updates": [update.to_dict() for update in self.field_updates],
        }


def build_contextdev_research_pack_dry_run(
    pack: BrandResearchPack | dict[str, Any],
    candidate_summary: dict[str, Any],
) -> ContextDevResearchPackDryRun:
    """Build a non-production enrichment preview from promotable candidates."""

    original_pack = BrandResearchPack.from_dict(pack).to_dict() if isinstance(pack, dict) else pack.to_dict()
    candidate_summary = filter_contextdev_candidate_summary_for_pack(original_pack, candidate_summary)
    enriched_pack = deepcopy(original_pack)
    promotion_report = evaluate_contextdev_summary_promotion(candidate_summary)
    candidates_by_id = {
        str(item.get("candidate_id") or ""): item
        for item in _list(candidate_summary.get("candidates"))
        if isinstance(item, dict)
    }

    updates: list[ContextDevPackFieldUpdate] = []
    for decision in promotion_report.decisions:
        if decision.status != PROMOTABLE:
            continue
        candidate = candidates_by_id.get(decision.candidate_id)
        if not candidate:
            continue
        text = _clean_text(candidate.get("text"))
        if not text:
            continue
        if decision.target_contract == "research_pack.visual_or_conceptual_signals":
            if _append_unique(enriched_pack, "visual_or_conceptual_signals", text):
                updates.append(_update("visual_or_conceptual_signals", "append", text, candidate))
            continue
        if decision.target_contract == "research_pack.product_summary":
            if not _clean_text(enriched_pack.get("product_summary")):
                enriched_pack["product_summary"] = text
                updates.append(_update("product_summary", "set", text, candidate))
            else:
                note = f"Context.dev product candidate: {text}"
                if _append_unique(enriched_pack, "confidence_notes", note):
                    updates.append(_update("confidence_notes", "append", note, candidate))

    _append_unique(
        enriched_pack,
        "confidence_notes",
        _summary_note(promotion_report=promotion_report, update_count=len(updates)),
    )

    return ContextDevResearchPackDryRun(
        version=CONTEXTDEV_RESEARCH_PACK_DRY_RUN_VERSION,
        original_pack=original_pack,
        enriched_pack=enriched_pack,
        promotion_report=promotion_report,
        field_updates=tuple(updates),
    )


def filter_contextdev_candidate_summary_for_pack(
    pack: BrandResearchPack | dict[str, Any],
    candidate_summary: dict[str, Any],
) -> dict[str, Any]:
    """Keep only candidates whose source domain belongs to the Research Pack."""

    pack_payload = BrandResearchPack.from_dict(pack).to_dict() if isinstance(pack, dict) else pack.to_dict()
    allowed_domains = _pack_domains(pack_payload)
    if not allowed_domains:
        return {**candidate_summary, "candidates": []}
    candidates = [
        item
        for item in _list(candidate_summary.get("candidates"))
        if isinstance(item, dict) and _domain_matches(str(item.get("source_url") or ""), allowed_domains)
    ]
    return _summary_with_candidates(candidate_summary, candidates)


def _summary_note(*, promotion_report: ContextDevPromotionReport, update_count: int) -> str:
    counts = promotion_report.status_counts
    return (
        "Context.dev dry-run only: "
        f"{update_count} field updates from {counts.get(PROMOTABLE, 0)} promotable candidates; "
        f"{counts.get('review_required', 0)} candidates require review."
    )


def _update(field: str, action: str, value: str, candidate: dict[str, Any]) -> ContextDevPackFieldUpdate:
    return ContextDevPackFieldUpdate(
        field=field,
        action=action,
        value=value,
        candidate_id=str(candidate.get("candidate_id") or ""),
        candidate_type=str(candidate.get("candidate_type") or ""),
    )


def _append_unique(payload: dict[str, Any], field: str, value: str) -> bool:
    values = payload.get(field)
    if not isinstance(values, list):
        values = []
        payload[field] = values
    existing = {_clean_text(item).lower() for item in values}
    normalized = _clean_text(value)
    if not normalized or normalized.lower() in existing:
        return False
    values.append(normalized)
    return True


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _pack_domains(pack: dict[str, Any]) -> set[str]:
    domains = set()
    for value in [
        pack.get("input_url"),
        *_list(pack.get("official_urls")),
        *_list(pack.get("analyzed_urls")),
    ]:
        domain = _normalized_domain(str(value or ""))
        if domain:
            domains.add(domain)

    source_map = pack.get("source_map")
    if isinstance(source_map, dict):
        for source in source_map.values():
            if isinstance(source, dict):
                domain = _normalized_domain(str(source.get("url") or ""))
                if domain:
                    domains.add(domain)

    resolved = pack.get("resolved_entity")
    if isinstance(resolved, dict):
        domain = _normalized_domain(str(resolved.get("canonical_url") or ""))
        if domain:
            domains.add(domain)
    return domains


def _summary_with_candidates(candidate_summary: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    by_channel: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for candidate in candidates:
        channel = str(candidate.get("supports_channel") or "")
        candidate_type = str(candidate.get("candidate_type") or "")
        if channel:
            by_channel[channel] = by_channel.get(channel, 0) + 1
        if candidate_type:
            by_type[candidate_type] = by_type.get(candidate_type, 0) + 1
    return {
        **candidate_summary,
        "candidate_count": len(candidates),
        "by_channel": dict(sorted(by_channel.items())),
        "by_type": dict(sorted(by_type.items())),
        "candidates": candidates,
    }


def _domain_matches(url: str, allowed_domains: set[str]) -> bool:
    domain = _normalized_domain(url)
    if not domain:
        return False
    return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains)


def _normalized_domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    domain = (parsed.netloc or parsed.path or "").lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain.split("/")[0]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
