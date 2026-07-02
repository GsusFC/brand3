"""Legacy Pass 1/TLDR compatibility wrappers for SV9 Flow harnesses.

This module is NOT canonical architecture. It re-wraps existing Pass 1/TLDR
payloads in the flow contracts so legacy baselines stay comparable while they
are being retired. The canonical path is src/sv9_flow/orchestrator.py
(evidence_pack -> flow-llm interpretation -> tile signals); nothing under
src/ may import this module.
"""

from __future__ import annotations

from typing import Any

from src.sv9_flow._utils import truthy_detected, unique_strings
from src.sv9_flow.contracts import BrandEvidencePack, BrandInterpretation, Sv9FlowCandidate
from src.sv9_flow.evidence_worker import build_evidence_pack_from_snapshot
from src.sv9_flow.tile_signal_worker import build_tile_signals_from_interpretation


def build_flow_candidate_from_current_outputs(
    *,
    snapshot: dict[str, Any],
    tldr_payload: dict[str, Any] | None = None,
    visual_signature_evidence: dict[str, Any] | None = None,
) -> Sv9FlowCandidate:
    """Build a compatibility candidate from current Pass 1/TLDR outputs."""

    evidence_pack = build_evidence_pack_from_snapshot(
        snapshot,
        visual_signature_evidence=visual_signature_evidence,
    )
    interpretation = build_brand_interpretation_from_tldr(
        evidence_pack=evidence_pack,
        tldr_payload=tldr_payload,
    )
    tile_signals = build_tile_signals_from_interpretation(
        interpretation,
        visual_signature_evidence=visual_signature_evidence,
    )
    limitations = list(evidence_pack.limitations) + list(interpretation.limitations)
    return Sv9FlowCandidate(
        evidence_pack=evidence_pack,
        interpretation=interpretation,
        tile_signals=tile_signals,
        limitations=unique_strings(limitations),
    )


def build_brand_interpretation_from_tldr(
    *,
    evidence_pack: BrandEvidencePack,
    tldr_payload: dict[str, Any] | None,
) -> BrandInterpretation:
    """Copy TLDR blocks into the interpretation contract, refs by keyword match.

    The evidence refs here are heuristic (keyword hit or the first records),
    not real citations — one of the reasons this path is legacy-only.
    """

    tldr = _extract_tldr(tldr_payload)
    limitations: list[str] = []
    if not tldr:
        limitations.append("missing_tldr_brand3")

    blocks: dict[str, dict[str, Any]] = {}
    evidence_refs: dict[str, list[str]] = {}
    for block_name, block_payload in sorted(tldr.items()):
        if not isinstance(block_payload, dict):
            continue
        normalized = dict(block_payload)
        detected = truthy_detected(normalized)
        normalized["detected"] = detected
        blocks[str(block_name)] = normalized
        refs = _refs_for_block(str(block_name), evidence_pack)
        if refs:
            evidence_refs[str(block_name)] = refs

    return BrandInterpretation(
        brand_name=evidence_pack.brand_name,
        url=evidence_pack.url,
        blocks=blocks,
        evidence_refs=evidence_refs,
        limitations=unique_strings(limitations),
    )


def _extract_tldr(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    tldr = payload.get("tldr_brand3")
    if isinstance(tldr, dict):
        return tldr
    return payload if any(isinstance(value, dict) for value in payload.values()) else {}


def _refs_for_block(block_name: str, evidence_pack: BrandEvidencePack) -> list[str]:
    needle = block_name.lower().replace("_", " ")
    refs = [
        record.ref
        for record in evidence_pack.evidence
        if needle in record.evidence_type.lower().replace("_", " ")
        or needle in record.content.lower().replace("_", " ")
    ]
    if refs:
        return refs[:5]
    return [record.ref for record in evidence_pack.evidence[:3]]
