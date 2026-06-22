"""Comparison helpers for evidence vNext snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.reports.brand_research_pack import BrandResearchPack, build_brand_research_pack_from_snapshot
from src.reports.evidence_packet import build_evidence_packet_v0
from src.research.evidence_graph import EvidenceClaim, EvidenceGraph, build_evidence_graph_from_snapshot
from src.research.evidence_vnext_acquisition_contracts import (
    _acquisition_diagnostics_from_snapshot,
    apply_evidence_vnext_acquisition_contracts,
)
from src.research.evidence_vnext_semantics import (
    build_evidence_vnext_semantic_assessment as _build_evidence_vnext_semantic_assessment,
)
from src.research.pack_comparison import FieldComparison
from src.research.research_pack_builder import build_brand_research_pack_from_graph


MATERIAL_FIELDS = {
    "company_summary",
    "product_summary",
    "audience",
    "offer",
    "outcome",
    "declared_purpose",
    "declared_mission",
    "future_direction",
    "proof_points",
    "founder_or_press_context",
    "competitive_context",
}


@dataclass(frozen=True, slots=True)
class EvidenceVNextComparison:
    """Comparison of legacy/current graph/vNext outputs for one snapshot."""

    run_id: int | None
    brand_name: str
    url: str
    current_graph_summary: dict[str, Any]
    vnext_graph_summary: dict[str, Any]
    gate_summary: dict[str, Any]
    reclassified_to_noise_count: int
    fields: tuple[FieldComparison, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "brand_name": self.brand_name,
            "url": self.url,
            "current_graph_summary": dict(self.current_graph_summary),
            "vnext_graph_summary": dict(self.vnext_graph_summary),
            "gate_summary": dict(self.gate_summary),
            "reclassified_to_noise_count": self.reclassified_to_noise_count,
            "fields": [item.to_dict() for item in self.fields],
            "summary": self.summary(),
        }

    def summary(self) -> dict[str, Any]:
        gained = [item.field for item in self.fields if item.legacy_empty and not item.graph_empty]
        lost = [item.field for item in self.fields if not item.legacy_empty and item.graph_empty]
        changed = [item.field for item in self.fields if item.changed]
        material_lost = [
            item.field
            for item in self.fields
            if not item.legacy_empty
            and item.graph_empty
            and item.field in MATERIAL_FIELDS
            and not _preview_looks_nonmaterial(item.legacy_preview)
        ]
        non_material_lost = [field for field in lost if field not in material_lost]
        review_count = int(self.gate_summary.get("review_required_count") or 0)
        rejected_count = int(self.gate_summary.get("rejected_count") or 0)
        scorecard = _scorecard_status(
            material_lost=material_lost,
            non_material_lost=non_material_lost,
            review_count=review_count,
            rejected_count=rejected_count,
        )
        return {
            "gained_fields": gained,
            "lost_fields": lost,
            "material_lost_fields": material_lost,
            "non_material_lost_fields": non_material_lost,
            "changed_fields": changed,
            "gained_count": len(gained),
            "lost_count": len(lost),
            "material_lost_count": len(material_lost),
            "non_material_lost_count": len(non_material_lost),
            "changed_count": len(changed),
            "claim_delta": int(self.vnext_graph_summary.get("claim_count") or 0)
            - int(self.current_graph_summary.get("claim_count") or 0),
            "noise_delta": int(self.vnext_graph_summary.get("noise_claim_count") or 0)
            - int(self.current_graph_summary.get("noise_claim_count") or 0),
            "reclassified_to_noise_count": self.reclassified_to_noise_count,
            "scorecard": scorecard,
        }


def compare_evidence_vnext_from_snapshot(snapshot: dict[str, Any]) -> EvidenceVNextComparison:
    """Compare current graph-backed pack against vNext filtered pack."""

    from src.research.evidence_vnext import (
        build_evidence_vnext_packet_from_snapshot,
        build_vnext_evidence_graph_from_snapshot,
    )

    current_graph = build_evidence_graph_from_snapshot(snapshot)
    current_pack = build_brand_research_pack_from_graph(current_graph).to_dict()
    vnext_graph = build_vnext_evidence_graph_from_snapshot(snapshot)
    vnext_pack = build_brand_research_pack_from_graph(vnext_graph).to_dict()
    gate = build_evidence_vnext_packet_from_snapshot(snapshot)
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    fields = tuple(
        _compare_field(field, current_pack.get(field), vnext_pack.get(field))
        for field in (
            "company_summary",
            "product_summary",
            "audience",
            "offer",
            "outcome",
            "category",
            "declared_purpose",
            "declared_mission",
            "future_direction",
            "tone_of_voice",
            "personality_signals",
            "visual_or_conceptual_signals",
            "values_signals",
            "attributes_signals",
            "proof_points",
            "founder_or_press_context",
            "competitive_context",
            "noise_rejected",
        )
    )
    return EvidenceVNextComparison(
        run_id=_optional_int(run.get("id")),
        brand_name=str(run.get("brand_name") or ""),
        url=str(run.get("url") or ""),
        current_graph_summary=current_graph.summary(),
        vnext_graph_summary=vnext_graph.summary(),
        gate_summary=gate.summary(),
        reclassified_to_noise_count=_reclassified_to_noise_count(vnext_graph.claims),
        fields=fields,
    )


def compare_legacy_current_and_vnext_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return all three pack payloads for lab inspection."""

    from src.research.evidence_vnext import (
        build_evidence_vnext_packet_from_snapshot,
        build_vnext_evidence_graph_from_snapshot,
    )

    acquisition_contracts = apply_evidence_vnext_acquisition_contracts(snapshot)
    acquisition_diagnostics = _acquisition_diagnostics_from_snapshot(snapshot)
    legacy = build_brand_research_pack_from_snapshot(snapshot)
    current_graph = build_evidence_graph_from_snapshot(snapshot)
    current = build_brand_research_pack_from_graph(current_graph)
    vnext_graph = build_vnext_evidence_graph_from_snapshot(snapshot)
    vnext = build_brand_research_pack_from_graph(vnext_graph)
    gate = build_evidence_vnext_packet_from_snapshot(snapshot)
    semantic = build_evidence_vnext_semantic_assessment(gate)
    semantic_llm = _maybe_build_llm_semantic_assessment(gate)
    return {
        "runtime_effect": False,
        "prompt_effect": False,
        "model_effect": False,
        "legacy_pack": legacy.to_dict(),
        "current_graph_pack": current.to_dict(),
        "vnext_pack": vnext.to_dict(),
        "current_graph": current_graph.to_dict(),
        "vnext_graph": vnext_graph.to_dict(),
        "vnext_gate": gate.to_dict(),
        "vnext_semantic_assessment": semantic,
        "vnext_semantic_llm_assessment": semantic_llm,
        "vnext_acquisition_contracts": acquisition_contracts.to_dict(),
        "vnext_acquisition_diagnostics": acquisition_diagnostics,
        "vnext_comparison": compare_evidence_vnext_from_snapshot(snapshot).to_dict(),
    }


def build_evidence_vnext_semantic_assessment(packet) -> dict[str, Any]:
    return _build_evidence_vnext_semantic_assessment(packet)


def _maybe_build_llm_semantic_assessment(gate) -> dict[str, Any]:
    try:
        from src.research.evidence_semantic_llm import build_llm_semantic_assessment

        return build_llm_semantic_assessment(gate)
    except Exception as exc:
        return {
            "version": "evidence_vnext_llm_semantic_assessment_v0_1",
            "runtime_effect": False,
            "prompt_effect": False,
            "model_effect": False,
            "classifier": "llm_shadow_v0",
            "status": "error",
            "reason": "llm_classifier_exception",
            "detail": str(exc)[:200],
            "assessments": [],
            "summary": {
                "assessment_count": 0,
                "accepted_count": len(gate.accepted),
                "accepted_material_count": 0,
                "accepted_weak_count": 0,
                "accepted_material_rate": 0.0,
                "accepted_weak_rate": 0.0,
                "semantic_class_counts": {},
                "materiality_counts": {},
                "entity_fit_counts": {},
            },
        }


def build_evidence_vnext_packet_from_snapshot(snapshot: dict[str, Any]):
    packet = build_evidence_packet_v0(snapshot)
    observations = _observations_from_packet(packet, snapshot=snapshot)
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    from src.research.evidence_vnext import EVIDENCE_VNEXT_VERSION, EvidenceVNextPacket

    return EvidenceVNextPacket(
        version=EVIDENCE_VNEXT_VERSION,
        run_id=_optional_int(run.get("id")),
        brand_name=str(run.get("brand_name") or ""),
        url=str(run.get("url") or ""),
        observations=tuple(observations),
        legacy_packet_summary={
            "case_id": packet.get("case_id") or "",
            "counts": (packet.get("metadata") or {}).get("counts") or {},
            "dimension_readiness": packet.get("dimension_readiness") or {},
        },
    )


def build_vnext_evidence_graph_from_snapshot(snapshot: dict[str, Any]):
    base_graph = build_evidence_graph_from_snapshot(snapshot)
    gate = build_evidence_vnext_packet_from_snapshot(snapshot)
    filtered_claims = _filter_claims(base_graph.claims, gate)
    return EvidenceGraph(
        version=f"{base_graph.version}+evidence_vnext",
        run=base_graph.run,
        sources=base_graph.sources,
        claims=filtered_claims,
        gaps=_unique(list(base_graph.gaps) + _vnext_gaps(gate, filtered_claims)),
        warnings=_unique(list(base_graph.warnings) + _vnext_warnings(gate)),
        shadow_sources=base_graph.shadow_sources,
        dedupe_stats={
            **dict(base_graph.dedupe_stats),
            "vnext_input_claim_count": len(base_graph.claims),
            "vnext_filtered_claim_count": len(filtered_claims),
            "vnext_removed_claim_count": len(base_graph.claims) - len(filtered_claims),
        },
    )


def _compare_field(field: str, current_value: Any, vnext_value: Any) -> FieldComparison:
    current_normalized = _normalize_value(current_value)
    vnext_normalized = _normalize_value(vnext_value)
    return FieldComparison(
        field=field,
        legacy_empty=not bool(current_normalized),
        graph_empty=not bool(vnext_normalized),
        changed=current_normalized != vnext_normalized,
        legacy_preview=_preview(current_value),
        graph_preview=_preview(vnext_value),
    )


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split()).strip()
    if isinstance(value, list):
        return "\n".join(_normalize_value(item) for item in value if _normalize_value(item))
    if isinstance(value, dict):
        return " ".join(str(value.get(key) or "") for key in sorted(value))
    return str(value).strip()


def _preview(value: Any, limit: int = 180) -> str:
    if isinstance(value, list):
        parts = []
        for item in value[:3]:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("source_url") or item)[:80])
            else:
                parts.append(str(item)[:80])
        text = " | ".join(parts)
    elif isinstance(value, dict):
        text = str(value)
    else:
        text = str(value or "")
    return " ".join(text.split())[:limit]


def _reclassified_to_noise_count(claims: list[EvidenceClaim]) -> int:
    return sum(
        1
        for claim in claims
        if claim.claim_type == "noise"
        and any("Rejected by evidence vNext gate." == note for note in claim.notes)
    )


def _scorecard_status(
    *,
    material_lost: list[str],
    non_material_lost: list[str],
    review_count: int,
    rejected_count: int,
) -> dict[str, Any]:
    reason_codes: list[str] = []
    if material_lost:
        reason_codes.append("material_fields_lost")
    if non_material_lost:
        reason_codes.append("non_material_fields_lost")
    if review_count:
        reason_codes.append("review_required_evidence_present")
    if rejected_count:
        reason_codes.append("rejected_evidence_present")

    if material_lost:
        status = "blocked"
    elif non_material_lost or review_count:
        status = "review_required"
    else:
        status = "promising"

    return {
        "status": status,
        "reason_codes": reason_codes or ["no_material_regressions_detected"],
        "material_lost_fields": list(material_lost),
        "non_material_lost_fields": list(non_material_lost),
    }


def _preview_looks_nonmaterial(value: str) -> bool:
    low = str(value or "").lower()
    return any(
        marker in low
        for marker in (
            "robots.txt",
            "sitemap.xml",
            "local image analysis",
            "whitespace ratio",
            "dominant color",
            "contrast signal",
            "schema.org",
            "key pages found",
        )
    )


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _filter_claims(claims: list[EvidenceClaim], gate) -> list[EvidenceClaim]:
    accepted_url_keys = {_url_key(item.url) for item in gate.accepted if item.url}
    unresolved_profile_url_keys = {
        _url_key(item.url)
        for item in gate.review_required
        if item.url and item.classification_reason == "same_name_external_profile_not_alias"
    }
    review_or_rejected_url_keys = {
        _url_key(item.url)
        for item in (*gate.review_required, *gate.rejected)
        if item.url
    }
    accepted_text_keys = {_text_key(item.text) for item in gate.accepted if item.text}
    accepted_url_by_text_key = {
        _text_key(item.text): item.url
        for item in gate.accepted
        if item.text and item.url
    }
    review_or_rejected_text_keys = {
        _text_key(item.text)
        for item in (*gate.review_required, *gate.rejected)
        if item.text
    }
    filtered: list[EvidenceClaim] = []
    for claim in claims:
        claim = _claim_with_inferred_url(claim, accepted_url_by_text_key)
        if _claim_rejected_by_gate(
            claim,
            accepted_url_keys=accepted_url_keys,
            unresolved_profile_url_keys=unresolved_profile_url_keys,
            review_or_rejected_url_keys=review_or_rejected_url_keys,
            accepted_text_keys=accepted_text_keys,
            review_or_rejected_text_keys=review_or_rejected_text_keys,
        ):
            filtered.append(
                EvidenceClaim(
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type="noise",
                    quote=claim.quote,
                    source_id=claim.source_id,
                    source_url=claim.source_url,
                    source_type="noise",
                    surface_role=claim.surface_role,
                    entity_scope=claim.entity_scope,
                    confidence="low",
                    noise_reason=claim.noise_reason or _claim_noise_reason(claim, unresolved_profile_url_keys),
                    notes=_unique(
                        list(claim.notes)
                        + [_claim_noise_note(claim, unresolved_profile_url_keys)]
                    ),
                )
            )
            continue
        filtered.append(claim)
    return filtered


def _claim_with_inferred_url(claim: EvidenceClaim, accepted_url_by_text_key: dict[str, str]) -> EvidenceClaim:
    if claim.source_url:
        return claim
    inferred_url = accepted_url_by_text_key.get(_text_key(claim.text or claim.quote))
    if not inferred_url:
        return claim
    return EvidenceClaim(
        claim_id=claim.claim_id,
        text=claim.text,
        claim_type=claim.claim_type,
        quote=claim.quote,
        source_id=claim.source_id,
        source_url=inferred_url,
        source_type=claim.source_type,
        surface_role=claim.surface_role,
        entity_scope=claim.entity_scope,
        confidence=claim.confidence,
        freshness_days=claim.freshness_days,
        supports_blocks=list(claim.supports_blocks),
        contradicts=list(claim.contradicts),
        secondary_source_ids=list(claim.secondary_source_ids),
        secondary_source_urls=list(claim.secondary_source_urls),
        secondary_origins=list(claim.secondary_origins),
        noise_reason=claim.noise_reason,
        notes=_unique(list(claim.notes) + ["Source URL inferred by evidence vNext from same feature evidence_url."]),
    )


def _claim_rejected_by_gate(
    claim: EvidenceClaim,
    *,
    accepted_url_keys: set[str],
    unresolved_profile_url_keys: set[str],
    review_or_rejected_url_keys: set[str],
    accepted_text_keys: set[str],
    review_or_rejected_text_keys: set[str],
) -> bool:
    if claim.claim_type == "noise" or claim.source_type == "noise":
        return False
    claim_url_key = _url_key(claim.source_url)
    claim_text_key = _text_key(claim.text or claim.quote)

    if claim.source_type.startswith("owned_") and claim.claim_type != "feature_evidence":
        return False
    if claim.claim_type == "feature_evidence" and not claim.source_url:
        return True
    if claim_url_key and claim_url_key in unresolved_profile_url_keys:
        return True
    if claim_url_key and claim_url_key in accepted_url_keys:
        return False
    if claim_text_key and claim_text_key in accepted_text_keys:
        return False
    if claim_url_key and claim_url_key in review_or_rejected_url_keys:
        return True
    if claim_text_key and claim_text_key in review_or_rejected_text_keys:
        return True
    if claim.source_type in {"unknown", "third_party_context", "third_party_review", "press_founder"}:
        return claim.claim_type in {"unknown", "feature_evidence"} and not claim.source_url
    return False


def _claim_noise_reason(claim: EvidenceClaim, unresolved_profile_url_keys: set[str]) -> str:
    if _url_key(claim.source_url) in unresolved_profile_url_keys:
        return "unresolved_external_profile_source"
    return "evidence_vnext_gate_rejected"


def _claim_noise_note(claim: EvidenceClaim, unresolved_profile_url_keys: set[str]) -> str:
    if _url_key(claim.source_url) in unresolved_profile_url_keys:
        return "Quarantined by evidence vNext because source URL is an unresolved same-name external profile."
    return "Rejected by evidence vNext gate."


def _vnext_gaps(gate, claims: list[EvidenceClaim]) -> list[str]:
    gaps: list[str] = []
    if gate.review_required:
        gaps.append("Evidence vNext found review-required evidence; excluded from vNext interpretation.")
    if gate.rejected and not any(claim.claim_type != "noise" for claim in claims):
        gaps.append("Evidence vNext rejected all interpretation candidates.")
    return gaps


def _vnext_warnings(gate) -> list[str]:
    warnings: list[str] = []
    if gate.review_required:
        warnings.append("evidence_vnext_review_required")
    if gate.rejected:
        warnings.append("evidence_vnext_rejected_candidates")
    return warnings
