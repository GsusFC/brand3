"""Promotion gate for Context.dev candidate evidence.

The gate keeps Context.dev lab outputs outside production Research Pack
contracts until each candidate has an explicit promotion decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

from src.research.contextdev_candidates import ContextDevEvidenceCandidate


CONTEXTDEV_PROMOTION_GATE_VERSION = "contextdev_promotion_gate_v0_1"

PROMOTABLE = "promotable"
REVIEW_REQUIRED = "review_required"
BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ContextDevPromotionDecision:
    candidate_id: str
    candidate_type: str
    supports_channel: str
    status: str
    target_contract: str
    reason_codes: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        payload["notes"] = list(self.notes)
        return payload


@dataclass(frozen=True, slots=True)
class ContextDevPromotionReport:
    version: str
    decisions: tuple[ContextDevPromotionDecision, ...]

    @property
    def status_counts(self) -> dict[str, int]:
        counts = {PROMOTABLE: 0, REVIEW_REQUIRED: 0, BLOCKED: 0}
        for decision in self.decisions:
            counts[decision.status] = counts.get(decision.status, 0) + 1
        return counts

    @property
    def channel_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for decision in self.decisions:
            counts[decision.supports_channel] = counts.get(decision.supports_channel, 0) + 1
        return dict(sorted(counts.items()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "decision_count": len(self.decisions),
            "status_counts": self.status_counts,
            "channel_counts": self.channel_counts,
            "decisions": [decision.to_dict() for decision in self.decisions],
        }


def evaluate_contextdev_candidate_promotion(candidates: list[ContextDevEvidenceCandidate]) -> ContextDevPromotionReport:
    """Evaluate which Context.dev candidates are safe to promote."""

    return ContextDevPromotionReport(
        version=CONTEXTDEV_PROMOTION_GATE_VERSION,
        decisions=tuple(_decision(candidate) for candidate in candidates),
    )


def evaluate_contextdev_summary_promotion(summary: dict[str, Any]) -> ContextDevPromotionReport:
    """Evaluate a serialized candidate summary produced by the lab scripts."""

    candidates = [_candidate_from_dict(item) for item in _list(summary.get("candidates"))]
    return evaluate_contextdev_candidate_promotion(candidates)


def _decision(candidate: ContextDevEvidenceCandidate) -> ContextDevPromotionDecision:
    structural_blocks = _structural_blocks(candidate)
    if structural_blocks:
        return _build_decision(
            candidate,
            status=BLOCKED,
            target_contract="none",
            reason_codes=tuple(structural_blocks),
            notes=("Candidate failed minimum traceability requirements.",),
        )

    if candidate.supports_channel == "entity_resolution":
        return _build_decision(
            candidate,
            status=REVIEW_REQUIRED,
            target_contract="research_pack.resolved_entity",
            reason_codes=("identity_affects_target_selection",),
            notes=("Entity data can redirect the scan target and must not auto-promote.",),
        )

    if candidate.supports_channel == "industry_classification":
        return _build_decision(
            candidate,
            status=REVIEW_REQUIRED,
            target_contract="research_pack.category",
            reason_codes=("taxonomy_requires_human_acceptance",),
        )

    if candidate.supports_channel == "visual_identity":
        return _build_decision(
            candidate,
            status=PROMOTABLE,
            target_contract="research_pack.visual_or_conceptual_signals",
            reason_codes=("textual_visual_signal",),
        )

    if candidate.supports_channel == "visual_evidence":
        return _build_decision(
            candidate,
            status=REVIEW_REQUIRED,
            target_contract="visual_signature.input",
            reason_codes=("binary_visual_asset_not_research_pack_text",),
            notes=("Screenshots and image URLs need a visual evidence contract before auto-promotion.",),
        )

    if candidate.supports_channel == "product_extraction":
        if len(candidate.text.split()) < 4:
            return _build_decision(
                candidate,
                status=REVIEW_REQUIRED,
                target_contract="research_pack.product_summary",
                reason_codes=("product_candidate_too_short",),
            )
        return _build_decision(
            candidate,
            status=PROMOTABLE,
            target_contract="research_pack.product_summary",
            reason_codes=("product_candidate_has_substance",),
        )

    return _build_decision(
        candidate,
        status=REVIEW_REQUIRED,
        target_contract="evidence_graph.pending",
        reason_codes=("unknown_candidate_channel",),
    )


def _structural_blocks(candidate: ContextDevEvidenceCandidate) -> list[str]:
    blocks = []
    if not candidate.text.strip():
        blocks.append("missing_candidate_text")
    if not _is_http_url(candidate.source_url):
        blocks.append("invalid_or_missing_source_url")
    if candidate.provider != "contextdev":
        blocks.append("unexpected_provider")
    return blocks


def _build_decision(
    candidate: ContextDevEvidenceCandidate,
    *,
    status: str,
    target_contract: str,
    reason_codes: tuple[str, ...],
    notes: tuple[str, ...] = (),
) -> ContextDevPromotionDecision:
    return ContextDevPromotionDecision(
        candidate_id=candidate.candidate_id,
        candidate_type=candidate.candidate_type,
        supports_channel=candidate.supports_channel,
        status=status,
        target_contract=target_contract,
        reason_codes=reason_codes,
        notes=notes,
    )


def _candidate_from_dict(data: dict[str, Any]) -> ContextDevEvidenceCandidate:
    return ContextDevEvidenceCandidate(
        candidate_id=str(data.get("candidate_id") or ""),
        candidate_type=str(data.get("candidate_type") or ""),
        supports_channel=str(data.get("supports_channel") or ""),
        text=str(data.get("text") or ""),
        source_url=str(data.get("source_url") or ""),
        provider=str(data.get("provider") or "contextdev"),
        confidence=str(data.get("confidence") or "candidate"),
        raw_ref=str(data.get("raw_ref") or ""),
        notes=[str(item) for item in _list(data.get("notes"))],
    )


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
