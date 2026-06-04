"""Scan mode policy for Magnetism comparability and public surfacing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ScanMode = Literal["canonical_url", "from_audit_run", "legacy_manual", "unknown"]


@dataclass(frozen=True)
class ScanModePolicy:
    mode: ScanMode
    comparable: bool
    reason_codes: tuple[str, ...] = ()

    def to_payload(self) -> dict:
        return {
            "mode": self.mode,
            "comparable": self.comparable,
            "reason_codes": list(self.reason_codes),
        }


def scan_mode_from_payload(
    payload: dict,
    *,
    input_type: str | None = None,
    source_run_id: int | None = None,
) -> ScanModePolicy:
    normalized_input_type = str(input_type or "").strip()
    payload_mode = payload.get("scan_mode")
    if isinstance(payload_mode, dict):
        mode = str(payload_mode.get("mode") or "")
        comparable = payload_mode.get("comparable")
        if mode in {"canonical_url", "from_audit_run", "legacy_manual", "unknown"} and isinstance(comparable, bool):
            return ScanModePolicy(
                mode=mode,  # type: ignore[arg-type]
                comparable=comparable,
                reason_codes=tuple(str(item) for item in payload_mode.get("reason_codes") or []),
            )

    if _is_manual_payload(payload) or normalized_input_type == "manual":
        return ScanModePolicy(
            mode="legacy_manual",
            comparable=False,
            reason_codes=("manual_input_debug_path", "bypasses_brand_audit_acquisition"),
        )
    if source_run_id or payload.get("source_run_id") or normalized_input_type == "audit_run":
        return ScanModePolicy(mode="from_audit_run", comparable=True)
    if normalized_input_type in {"", "url"}:
        return ScanModePolicy(mode="canonical_url", comparable=True)
    return ScanModePolicy(
        mode="unknown",
        comparable=False,
        reason_codes=(f"unknown_input_type:{normalized_input_type}",),
    )


def scan_mode_from_row(row: dict) -> ScanModePolicy:
    payload: dict = {}
    raw_payload = row.get("raw_payload")
    if raw_payload:
        import json

        try:
            loaded = json.loads(raw_payload)
        except Exception:
            loaded = {}
        if isinstance(loaded, dict):
            payload = loaded
    source_run_id = row.get("source_run_id")
    try:
        normalized_source_run_id = int(source_run_id) if source_run_id is not None else None
    except Exception:
        normalized_source_run_id = None
    return scan_mode_from_payload(
        payload,
        input_type=str(row.get("input_type") or ""),
        source_run_id=normalized_source_run_id,
    )


def _is_manual_payload(payload: dict) -> bool:
    return (
        payload.get("source") in {"legacy_direct", "direct_magnetism_legacy"}
        or payload.get("extraction_mode") == "legacy_direct"
        or bool(payload.get("direct_source_provider"))
        or payload.get("url") == "manual"
    )
