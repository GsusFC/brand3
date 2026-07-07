"""Naming contract for the Visual Acquisition Layer.

The legacy implementation still lives under ``src.visual_signature``. Public
payloads should move toward acquisition/evidence wording because this layer
collects visual evidence; it does not score the brand.
"""

from __future__ import annotations

VISUAL_ACQUISITION_LAYER_NAME = "Visual Acquisition Layer"

VISUAL_ACQUISITION_RAW_SOURCE = "visual_acquisition"
LEGACY_VISUAL_SIGNATURE_RAW_SOURCE = "visual_signature"
VISUAL_ACQUISITION_RAW_SOURCES = (
    VISUAL_ACQUISITION_RAW_SOURCE,
    LEGACY_VISUAL_SIGNATURE_RAW_SOURCE,
)

VISUAL_EVIDENCE_PACKET_KEY = "visual_evidence_packet"
LEGACY_VISUAL_SIGNATURE_EVIDENCE_KEY = "visual_signature_evidence"
VISUAL_EVIDENCE_PACKET_KEYS = (
    VISUAL_EVIDENCE_PACKET_KEY,
    LEGACY_VISUAL_SIGNATURE_EVIDENCE_KEY,
)


def is_visual_acquisition_source(source: object) -> bool:
    return str(source or "") in VISUAL_ACQUISITION_RAW_SOURCES


def visual_evidence_packet_from_payload(payload: object) -> dict | None:
    if not isinstance(payload, dict):
        return None
    for key in VISUAL_EVIDENCE_PACKET_KEYS:
        value = payload.get(key)
        if isinstance(value, dict) and value.get("schema_version") == "visual-signature-evidence-v1":
            return value
    return None
