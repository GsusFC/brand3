"""SV9: the Brand3 Scanner scoring engine (9 components + Coherencia).

Shadow phase: SV9 runs over persisted Brand Audit snapshots and persists to
sv9_* tables only. It does not touch V5 scoring, dimension scores, report
semantics, or any public surface.
"""

from src.sv9.models import ComponentResult, RungVerdict, Sv9ScanResult
from src.sv9.rubric import COMPONENTS, PRESENTATION_ORDER, RUBRIC_VERSION
from src.sv9.service import run_sv9_from_audit_run, run_sv9_from_audit_snapshot

__all__ = [
    "COMPONENTS",
    "ComponentResult",
    "PRESENTATION_ORDER",
    "RUBRIC_VERSION",
    "RungVerdict",
    "Sv9ScanResult",
    "run_sv9_from_audit_run",
    "run_sv9_from_audit_snapshot",
]
