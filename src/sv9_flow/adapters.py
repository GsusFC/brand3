"""Compatibility facade for current-output adapters.

Keep this module thin. The work lives in explicit workers under sv9_flow:
evidence_worker, interpretation_worker, tile_signal_worker, and orchestrator.
"""

from src.sv9_flow.evidence_worker import build_evidence_pack_from_snapshot
from src.sv9_flow.interpretation_worker import build_brand_interpretation_from_tldr
from src.sv9_flow.orchestrator import build_flow_candidate_from_current_outputs
from src.sv9_flow.tile_signal_worker import build_tile_signals_from_interpretation

__all__ = [
    "build_brand_interpretation_from_tldr",
    "build_evidence_pack_from_snapshot",
    "build_flow_candidate_from_current_outputs",
    "build_tile_signals_from_interpretation",
]
