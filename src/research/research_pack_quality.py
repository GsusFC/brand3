"""Deterministic quality checks for BrandResearchPack inputs.

This module evaluates the evidence bundle before Analyst Pass generation. It is
not a prose judge; it checks whether the pack carries enough objective signal to
support a strategic TLDR without over-relying on noisy summaries or untraceable
claims.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

from src.reports.brand_research_pack import BrandResearchPack


RESEARCH_PACK_QUALITY_VERSION = "brand_research_pack_quality_v0_1"

QUALITY_DIMENSIONS = (
    "offer",
    "audience",
    "differentiation",
    "frictions",
    "proof",
    "traceability",
    "noise",
)

_NOISE_TERMS = {
    "article",
    "blog",
    "cookie",
    "copyright",
    "feed",
    "footer",
    "free pro enterprise",
    "header",
    "login",
    "menu",
    "navigation",
    "plans",
    "pricing",
    "privacy policy",
    "sign in",
    "terms",
}

_AUDIENCE_TERMS = {
    "agencies",
    "brands",
    "builders",
    "buyers",
    "companies",
    "creators",
    "customers",
    "developers",
    "enterprises",
    "founders",
    "marketers",
    "operators",
    "patients",
    "retailers",
    "teams",
    "traders",
    "users",
}

_DIFFERENTIATION_TERMS = {
    "advantage",
    "ai",
    "automated",
    "automation",
    "command",
    "controlled",
    "developer",
    "differentiated",
    "evidence",
    "faster",
    "focused",
    "integrated",
    "layer",
    "native",
    "premium",
    "privacy",
    "reliable",
    "secure",
    "signals",
    "specialized",
    "structured",
    "synthetic",
    "trusted",
    "workflow",
}


@dataclass(frozen=True, slots=True)
class ResearchPackQualityDimension:
    name: str
    score: float
    status: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResearchPackQualityReport:
    version: str
    total_score: float
    status: str
    dimensions: dict[str, ResearchPackQualityDimension]
    warnings: tuple[str, ...]
    pack_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "total_score": self.total_score,
            "status": self.status,
            "dimensions": {key: value.to_dict() for key, value in self.dimensions.items()},
            "warnings": list(self.warnings),
            "pack_summary": dict(self.pack_summary),
        }


def evaluate_research_pack_quality(pack: BrandResearchPack | dict[str, Any]) -> ResearchPackQualityReport:
    """Score whether a Research Pack is safe and useful enough for TLDR generation."""

    payload = BrandResearchPack.from_dict(pack).to_dict() if isinstance(pack, dict) else pack.to_dict()
    dimensions = {
        "offer": _offer_dimension(payload),
        "audience": _audience_dimension(payload),
        "differentiation": _differentiation_dimension(payload),
        "frictions": _frictions_dimension(payload),
        "proof": _proof_dimension(payload),
        "traceability": _traceability_dimension(payload),
        "noise": _noise_dimension(payload),
    }
    total = round(sum(dim.score for dim in dimensions.values()) / len(dimensions), 2)
    warnings = tuple(reason for dim in dimensions.values() for reason in dim.reasons if dim.status != "pass")
    status = _quality_status(total, dimensions)
    return ResearchPackQualityReport(
        version=RESEARCH_PACK_QUALITY_VERSION,
        total_score=total,
        status=status,
        dimensions=dimensions,
        warnings=warnings,
        pack_summary={
            "input_url": payload.get("input_url") or "",
            "entity_type": payload.get("entity_type") or "",
            "parent_brand": payload.get("parent_brand") or "",
            "official_url_count": len(_list(payload.get("official_urls"))),
            "analyzed_url_count": len(_list(payload.get("analyzed_urls"))),
            "proof_point_count": len(_list(payload.get("proof_points"))),
            "evidence_gap_count": len(_list(payload.get("evidence_gaps"))),
        },
    )


def evaluate_research_pack_quality_gate(
    report: ResearchPackQualityReport | dict[str, Any],
    *,
    min_total: float = 75.0,
    min_dimension: float = 60.0,
) -> dict[str, Any]:
    """Return a deterministic pass/fail gate for CI or benchmark scripts."""

    payload = report.to_dict() if isinstance(report, ResearchPackQualityReport) else report
    failures: list[str] = []
    total = float(payload.get("total_score") or 0.0)
    if total < min_total:
        failures.append(f"total_score {total:.1f} below {min_total:.1f}")
    for name, dimension in (payload.get("dimensions") or {}).items():
        score = float((dimension or {}).get("score") or 0.0)
        if score < min_dimension:
            failures.append(f"dimension {name} score {score:.1f} below {min_dimension:.1f}")
    if payload.get("status") == "fail":
        failures.append("research_pack_quality_status_fail")
    return {"passed": not failures, "failures": failures}


def _offer_dimension(pack: dict[str, Any]) -> ResearchPackQualityDimension:
    offer = _clean(pack.get("offer"))
    product_summary = _clean(pack.get("product_summary"))
    reasons: list[str] = []
    score = 100.0
    if not offer:
        score -= 55.0
        reasons.append("missing_offer")
    if not product_summary:
        score -= 30.0
        reasons.append("missing_product_summary")
    if _looks_like_noise(product_summary):
        score -= 45.0
        reasons.append("product_summary_looks_like_noise")
    if offer and product_summary and _token_overlap(offer, product_summary) < 0.12:
        score -= 15.0
        reasons.append("offer_product_summary_weak_overlap")
    return _dimension("offer", score, reasons)


def _audience_dimension(pack: dict[str, Any]) -> ResearchPackQualityDimension:
    audience = _clean(pack.get("audience"))
    offer = _clean(pack.get("offer"))
    reasons: list[str] = []
    score = 100.0
    if not audience:
        score -= 55.0
        reasons.append("missing_audience")
    if audience and not (_tokens(audience) & _AUDIENCE_TERMS):
        score -= 25.0
        reasons.append("audience_not_specific")
    if offer and audience and _token_overlap(audience, offer) < 0.08:
        score -= 10.0
        reasons.append("audience_weakly_connected_to_offer")
    return _dimension("audience", score, reasons)


def _differentiation_dimension(pack: dict[str, Any]) -> ResearchPackQualityDimension:
    text = " ".join(
        [
            _clean(pack.get("category")),
            _clean(pack.get("outcome")),
            _clean(pack.get("offer")),
            " ".join(_str_list(pack.get("visual_or_conceptual_signals"))),
            " ".join(_str_list(pack.get("attributes_signals"))),
        ]
    )
    reasons: list[str] = []
    score = 100.0
    if not _tokens(text):
        score -= 60.0
        reasons.append("missing_differentiation_context")
    if not (_tokens(text) & _DIFFERENTIATION_TERMS):
        score -= 30.0
        reasons.append("thin_differentiation_signal")
    if not _clean(pack.get("outcome")):
        score -= 20.0
        reasons.append("missing_outcome")
    return _dimension("differentiation", score, reasons)


def _frictions_dimension(pack: dict[str, Any]) -> ResearchPackQualityDimension:
    gaps = _str_list(pack.get("evidence_gaps"))
    notes = _str_list(pack.get("confidence_notes"))
    reasons: list[str] = []
    score = 100.0
    if not gaps and not notes:
        score -= 35.0
        reasons.append("missing_uncertainty_notes")
    if gaps and not any(_is_actionable_gap(gap) for gap in gaps):
        score -= 20.0
        reasons.append("evidence_gaps_not_actionable")
    return _dimension("frictions", score, reasons)


def _proof_dimension(pack: dict[str, Any]) -> ResearchPackQualityDimension:
    proof_points = [item for item in _list(pack.get("proof_points")) if isinstance(item, dict)]
    reasons: list[str] = []
    score = 100.0
    if not proof_points:
        score -= 60.0
        reasons.append("missing_proof_points")
    if proof_points and not any(_clean(item.get("source_url")) for item in proof_points):
        score -= 35.0
        reasons.append("proof_points_missing_source_urls")
    if proof_points and all(str(item.get("source_type") or "") in {"press_or_founder", "noise"} for item in proof_points):
        score -= 25.0
        reasons.append("proof_points_not_customer_or_owned_proof")
    return _dimension("proof", score, reasons)


def _traceability_dimension(pack: dict[str, Any]) -> ResearchPackQualityDimension:
    source_map = pack.get("source_map") if isinstance(pack.get("source_map"), dict) else {}
    official_urls = _str_list(pack.get("official_urls"))
    analyzed_urls = _str_list(pack.get("analyzed_urls"))
    reasons: list[str] = []
    score = 100.0
    if not source_map:
        score -= 35.0
        reasons.append("missing_source_map")
    if not official_urls:
        score -= 25.0
        reasons.append("missing_official_urls")
    if not analyzed_urls:
        score -= 25.0
        reasons.append("missing_analyzed_urls")
    if any(not _clean(source.get("source_type")) for source in source_map.values() if isinstance(source, dict)):
        score -= 20.0
        reasons.append("source_map_missing_source_type")
    return _dimension("traceability", score, reasons)


def _noise_dimension(pack: dict[str, Any]) -> ResearchPackQualityDimension:
    reasons: list[str] = []
    score = 100.0
    checked_fields = {
        "offer": _clean(pack.get("offer")),
        "product_summary": _clean(pack.get("product_summary")),
        "company_summary": _clean(pack.get("company_summary")),
        "audience": _clean(pack.get("audience")),
    }
    noisy_fields = [field for field, value in checked_fields.items() if _looks_like_noise(value)]
    if noisy_fields:
        score -= min(70.0, 25.0 * len(noisy_fields))
        reasons.append("noise_terms_in_" + "_".join(noisy_fields))
    if not _list(pack.get("noise_rejected")) and noisy_fields:
        score -= 20.0
        reasons.append("noise_not_recorded_as_rejected")
    return _dimension("noise", score, reasons)


def _dimension(name: str, score: float, reasons: list[str]) -> ResearchPackQualityDimension:
    bounded = round(max(0.0, min(100.0, score)), 2)
    if bounded >= 80.0:
        status = "pass"
    elif bounded >= 60.0:
        status = "warn"
    else:
        status = "fail"
    return ResearchPackQualityDimension(name=name, score=bounded, status=status, reasons=reasons)


def _quality_status(total: float, dimensions: dict[str, ResearchPackQualityDimension]) -> str:
    if any(dim.status == "fail" for dim in dimensions.values()) or total < 60.0:
        return "fail"
    if any(dim.status == "warn" for dim in dimensions.values()) or total < 80.0:
        return "warn"
    return "pass"


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.sub(r"[^a-z0-9\s]+", " ", value.lower()).split()
        if len(token) > 2 and token not in {"and", "for", "the", "with", "that", "this", "from", "into"}
    }


def _token_overlap(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _looks_like_noise(value: str) -> bool:
    low = value.lower()
    if not low:
        return False
    if any(term in low for term in _NOISE_TERMS):
        return True
    tokens = _tokens(low)
    if len(tokens) <= 3 and tokens & {"free", "pro", "enterprise", "basic", "max"}:
        return True
    return False


def _is_actionable_gap(value: str) -> bool:
    low = value.lower()
    return any(term in low for term in ("absent", "missing", "thin", "incomplete", "no ", "only", "unclear"))


def _str_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
