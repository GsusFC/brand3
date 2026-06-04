"""Promotion gate for EvidenceGraph-backed BrandResearchPack adoption.

The gate keeps the graph-backed pack behind an explicit decision surface so
we can compare it against the legacy snapshot builder before relying on it as
the canonical contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.research.pack_comparison import compare_pack_builders_from_snapshot


RESEARCH_PACK_PROMOTION_VERSION = "research_pack_promotion_v0_1"

PROMOTABLE = "promotable"
REVIEW_REQUIRED = "review_required"
BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ResearchPackPromotionDecision:
    run_id: int | None
    brand_name: str
    url: str
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
class ResearchPackPromotionReport:
    version: str
    decisions: tuple[ResearchPackPromotionDecision, ...]

    @property
    def status_counts(self) -> dict[str, int]:
        counts = {PROMOTABLE: 0, REVIEW_REQUIRED: 0, BLOCKED: 0}
        for decision in self.decisions:
            counts[decision.status] = counts.get(decision.status, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "decision_count": len(self.decisions),
            "status_counts": self.status_counts,
            "decisions": [decision.to_dict() for decision in self.decisions],
        }


def evaluate_research_pack_promotion(snapshot: dict[str, Any]) -> ResearchPackPromotionReport:
    """Evaluate whether the EvidenceGraph-backed pack is ready to promote."""

    comparison = compare_pack_builders_from_snapshot(snapshot)
    summary = comparison.summary()
    graph_summary = comparison.graph_summary or {}
    run_id = comparison.run_id
    if int(graph_summary.get("claim_count") or 0) <= 0 or int(graph_summary.get("source_count") or 0) <= 0:
        decision = _build_decision(
            comparison,
            run_id=run_id,
            status=BLOCKED,
            target_contract="research_pack.graph",
            reason_codes=("graph_empty",),
            notes=("The graph builder produced no usable evidence for this snapshot.",),
        )
    elif summary["lost_count"] > 0:
        decision = _build_decision(
            comparison,
            run_id=run_id,
            status=BLOCKED,
            target_contract="research_pack.graph",
            reason_codes=("legacy_fields_lost", *tuple(summary["lost_fields"])),
            notes=("The graph builder regressed fields that were already present in the legacy pack.",),
        )
    elif summary["entity_type_changed"] or summary["parent_brand_changed"]:
        decision = _build_decision(
            comparison,
            run_id=run_id,
            status=REVIEW_REQUIRED,
            target_contract="research_pack.graph",
            reason_codes=_identity_change_codes(summary),
            notes=("Identity-sensitive fields changed and need human review before promotion.",),
        )
    else:
        decision = _build_decision(
            comparison,
            run_id=run_id,
            status=PROMOTABLE,
            target_contract="research_pack.graph",
            reason_codes=("graph_no_regressions",),
            notes=_promotion_notes(summary),
        )
    return ResearchPackPromotionReport(version=RESEARCH_PACK_PROMOTION_VERSION, decisions=(decision,))


def _build_decision(
    comparison,
    *,
    run_id: int | None,
    status: str,
    target_contract: str,
    reason_codes: tuple[str, ...],
    notes: tuple[str, ...] = (),
) -> ResearchPackPromotionDecision:
    return ResearchPackPromotionDecision(
        run_id=run_id,
        brand_name=comparison.brand_name,
        url=comparison.url,
        status=status,
        target_contract=target_contract,
        reason_codes=reason_codes,
        notes=notes,
    )


def _identity_change_codes(summary: dict[str, Any]) -> tuple[str, ...]:
    reason_codes = []
    if summary.get("entity_type_changed"):
        reason_codes.append("entity_type_changed")
    if summary.get("parent_brand_changed"):
        reason_codes.append("parent_brand_changed")
    return tuple(reason_codes or ("identity_changed",))


def _promotion_notes(summary: dict[str, Any]) -> tuple[str, ...]:
    notes: list[str] = []
    gained = summary.get("gained_count") or 0
    changed = summary.get("changed_count") or 0
    if gained:
        notes.append(f"graph builder gained {gained} field(s) versus legacy.")
    if changed:
        notes.append(f"{changed} field(s) changed but no critical regressions were detected.")
    return tuple(notes)
