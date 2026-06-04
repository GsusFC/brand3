"""Publication readiness contract for Magnetism scanner payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ScannerReadinessStatus = Literal["publishable", "degraded", "debug_only", "failed"]


@dataclass(frozen=True)
class ScannerReadiness:
    status: ScannerReadinessStatus
    reason_codes: tuple[str, ...] = ()

    @property
    def publishable(self) -> bool:
        return self.status == "publishable"

    @property
    def error_message(self) -> str | None:
        if not self.reason_codes:
            return None
        return f"{self.status}:{self.reason_codes[0]}"

    def to_payload(self) -> dict:
        return {
            "status": self.status,
            "publishable": self.publishable,
            "reason_codes": list(self.reason_codes),
        }


def assess_scanner_readiness(input_type: str, payload: dict) -> ScannerReadiness:
    """Classify whether a scanner payload can be exposed as a canonical result."""
    normalized_input_type = str(input_type or "url")
    tldr_mode = str(payload.get("tldr_generation_mode") or "")
    source = str(payload.get("source") or "")

    if normalized_input_type == "manual":
        return ScannerReadiness("debug_only", _debug_reason_codes(tldr_mode, source))

    reason_codes: list[str] = []
    if normalized_input_type not in {"url", "audit_run"}:
        reason_codes.append(f"unknown_input_type:{normalized_input_type}")

    if tldr_mode == "legacy_fallback_no_llm":
        reason_codes.append("canonical_tldr_degraded:no_llm")
    elif tldr_mode == "legacy_fallback_llm_error":
        reason_codes.append("canonical_tldr_degraded:llm_error")
    elif tldr_mode and tldr_mode != "analyst_pass_validated":
        reason_codes.append(f"canonical_tldr_unvalidated:{tldr_mode}")

    if source == "legacy_direct":
        reason_codes.append("canonical_source_degraded:legacy_direct")

    if reason_codes:
        return ScannerReadiness("failed", tuple(reason_codes))

    return ScannerReadiness("publishable", ())


def _debug_reason_codes(tldr_mode: str, source: str) -> tuple[str, ...]:
    reason_codes = ["manual_input_debug_path"]
    if tldr_mode:
        reason_codes.append(f"tldr_mode:{tldr_mode}")
    if source:
        reason_codes.append(f"source:{source}")
    return tuple(reason_codes)
