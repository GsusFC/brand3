"""Thin orchestrator for the parallel SV9 Flow candidate."""

from __future__ import annotations

from typing import Any

from src.sv9_flow._utils import unique_strings
from src.sv9_flow.contracts import Sv9FlowCandidate
from src.sv9_flow.evidence_worker import build_evidence_pack_from_snapshot
from src.sv9_flow.interpretation_worker import build_brand_interpretation_from_tldr
from src.sv9_flow.tile_signal_worker import build_tile_signals_from_interpretation


def build_flow_candidate_from_current_outputs(
    *,
    snapshot: dict[str, Any],
    tldr_payload: dict[str, Any] | None = None,
    visual_signature_evidence: dict[str, Any] | None = None,
) -> Sv9FlowCandidate:
    """Build a shadow flow candidate without touching the current SV9 runtime."""

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
