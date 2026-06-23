"""Shadow acquisition contract normalization for evidence vNext."""

from __future__ import annotations

from src.research.evidence_vnext_acquisition_contracts_support import (
    AcquisitionContractExclusion,
    AcquisitionContractResult,
    _acquisition_diagnostics_from_snapshot,
    _clean_text,
    apply_evidence_vnext_acquisition_contracts,
    accumulate_acquisition_contract_exclusions,
    accumulate_acquisition_diagnostics,
    build_acquisition_matrix,
    build_provider_acquisition_contracts,
    build_provider_contract,
    build_provider_contract_backlog,
    build_provider_contract_implementation,
    finalize_acquisition_diagnostics,
    finalize_acquisition_matrix,
)

