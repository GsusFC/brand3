"""Visual Signature evidence contract for downstream scoring consumers.

This contract is evidence-only. It exposes traceable visual observations and
tile-level signals, but it does not compute or modify SV9 scores.
"""

from __future__ import annotations

from typing import Any

from src.visual_signature.evidence_capture import capture_contract, capture_obstruction, screenshot_payload
from src.visual_signature.evidence_fingerprint import fingerprint_contract
from src.visual_signature.evidence_identity import identity_contract
from src.visual_signature.evidence_signals import evidence_health, limitations, tile_signals
from src.visual_signature.evidence_visual_system import (
    copy_visual_alignment_contract,
    first_impression_contract,
    visual_system_contract,
)
from src.visual_signature.versions import VISUAL_SIGNATURE_EVIDENCE_VERSION


def build_visual_signature_evidence_v1(
    visual_signature_payload: dict[str, Any] | None,
    *,
    screenshot_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the stable Visual Signature evidence packet consumed by SV9 shadow mode."""

    payload = visual_signature_payload if isinstance(visual_signature_payload, dict) else {}
    screenshot = screenshot_payload_from_payload(payload, screenshot_payload)
    obstruction = capture_obstruction(payload)
    capture = capture_contract(payload, screenshot=screenshot, obstruction=obstruction)
    identity = identity_contract(payload)
    visual_system = visual_system_contract(payload)
    first_impression = first_impression_contract(payload, capture)
    copy_visual_alignment = copy_visual_alignment_contract(payload, capture)
    semantics_audit = _extract_raw_semantics(payload)
    packet_limitations = limitations(payload, capture)
    return {
        "schema_version": VISUAL_SIGNATURE_EVIDENCE_VERSION,
        "fingerprint": fingerprint_contract(payload, capture, screenshot),
        "capture": capture,
        "identity": identity,
        "visual_system": visual_system,
        "first_impression": first_impression,
        "copy_visual_alignment": copy_visual_alignment,
        "semantics_audit": semantics_audit,
        "evidence_health": evidence_health(
            capture=capture,
            identity=identity,
            visual_system=visual_system,
            copy_visual_alignment=copy_visual_alignment,
            semantics_audit=semantics_audit,
            limitations=packet_limitations,
        ),
        "tile_signals": tile_signals(
            payload,
            capture=capture,
            identity=identity,
            visual_system=visual_system,
            first_impression=first_impression,
            copy_visual_alignment=copy_visual_alignment,
        ),
        "limitations": packet_limitations,
    }


def screenshot_payload_from_payload(
    payload: dict[str, Any],
    explicit_screenshot_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return screenshot_payload(payload, explicit_screenshot_payload)


def _extract_raw_semantics(payload: dict[str, Any]) -> dict[str, Any]:
    semantics = payload.get("semantics")
    return semantics if isinstance(semantics, dict) else {}
