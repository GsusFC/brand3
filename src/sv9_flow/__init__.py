"""Parallel SV9 flow contracts.

This package is intentionally isolated from the current SV9 runtime. It defines
the candidate Evidence -> Brand Interpretation -> Tile Signals -> SV9 flow
without changing production scoring, routes, persistence, or imports.
"""

from src.sv9_flow.contracts import (
    BRAND_EVIDENCE_PACK_VERSION,
    BRAND_INTERPRETATION_VERSION,
    SV9_FLOW_CANDIDATE_VERSION,
    SV9_TILE_SIGNALS_VERSION,
    BrandEvidencePack,
    BrandInterpretation,
    EvidenceRecord,
    Sv9FlowCandidate,
    TileSignal,
)
from src.sv9_flow.surface import (
    CURRENT_SURFACE_INVENTORY,
    PRE_SV9_ALLOWED_ROLES,
    SurfaceArtifact,
    legacy_score_artifacts,
    pre_sv9_authority_violations,
    worker_artifacts,
)

__all__ = [
    "BRAND_EVIDENCE_PACK_VERSION",
    "BRAND_INTERPRETATION_VERSION",
    "SV9_FLOW_CANDIDATE_VERSION",
    "SV9_TILE_SIGNALS_VERSION",
    "BrandEvidencePack",
    "BrandInterpretation",
    "EvidenceRecord",
    "Sv9FlowCandidate",
    "TileSignal",
    "CURRENT_SURFACE_INVENTORY",
    "PRE_SV9_ALLOWED_ROLES",
    "SurfaceArtifact",
    "legacy_score_artifacts",
    "pre_sv9_authority_violations",
    "worker_artifacts",
]
