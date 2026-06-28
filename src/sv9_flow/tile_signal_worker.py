"""Tile signal worker for the parallel SV9 Flow."""

from __future__ import annotations

from typing import Any

from src.sv9_flow._utils import feature_confidence, truthy_detected
from src.sv9_flow.contracts import BrandInterpretation, TileSignal

_TLDR_TO_TILE: dict[str, tuple[str, str]] = {
    "mission": ("mission", "mission.M1"),
    "vision": ("vision", "vision.V1"),
    "values": ("values", "values.VA1"),
    "attributes": ("attributes", "attributes.A1"),
    "value_proposition": ("value_proposition", "value_proposition.PV1"),
    "offer": ("value_proposition", "value_proposition.PV1"),
    "personality": ("personality", "personality.P1"),
    "brand_idea": ("brand_idea", "brand_idea.I1"),
    "magnetism": ("magnetism", "magnetism.MG1"),
    "purpose": ("core_purpose", "core_purpose.PR1"),
    "core_purpose": ("core_purpose", "core_purpose.PR1"),
}


def build_tile_signals_from_interpretation(
    interpretation: BrandInterpretation,
    *,
    visual_signature_evidence: dict[str, Any] | None = None,
) -> list[TileSignal]:
    signals: list[TileSignal] = []
    for block_name, block_payload in sorted(interpretation.blocks.items()):
        component, tile = _TLDR_TO_TILE.get(block_name, (block_name, f"{block_name}.unknown"))
        detected = truthy_detected(block_payload)
        refs = interpretation.evidence_refs.get(block_name, [])
        content = str(block_payload.get("content") or block_payload.get("answer") or "").strip()
        if detected and content:
            signals.append(
                TileSignal(
                    component=component,
                    tile=tile,
                    effect="supports",
                    confidence="medium",
                    source="brand_interpretation",
                    evidence_refs=refs,
                    rationale=f"{block_name} is detected in brand interpretation.",
                )
            )
        else:
            signals.append(
                TileSignal(
                    component=component,
                    tile=tile,
                    effect="insufficient_evidence",
                    confidence="low",
                    source="brand_interpretation",
                    evidence_refs=refs,
                    rationale=f"{block_name} is not sufficiently detected in brand interpretation.",
                )
            )

    signals.extend(_tile_signals_from_visual_signature(visual_signature_evidence))
    return signals


def _tile_signals_from_visual_signature(evidence: dict[str, Any] | None) -> list[TileSignal]:
    if not isinstance(evidence, dict) or evidence.get("schema_version") != "visual-signature-evidence-v1":
        return []
    capture = evidence.get("capture") if isinstance(evidence.get("capture"), dict) else {}
    if capture.get("status") != "usable":
        return [
            TileSignal(
                component="visual_signature",
                tile="visual_signature.capture",
                effect="capture_unreliable",
                confidence="medium",
                source="visual_signature",
                evidence_refs=["visual_signature.capture"],
                rationale="Visual Signature capture is not usable.",
            )
        ]
    out: list[TileSignal] = []
    for index, item in enumerate(evidence.get("tile_signals") or []):
        if not isinstance(item, dict):
            continue
        tile = str(item.get("tile") or "")
        if not tile:
            continue
        component = tile.split(".", 1)[0] if "." in tile else "visual_signature"
        effect = str(item.get("effect") or "insufficient_evidence")
        if effect not in {"supports", "weakens", "insufficient_evidence", "blocked", "capture_unreliable"}:
            effect = "insufficient_evidence"
        out.append(
            TileSignal(
                component=component,
                tile=tile,
                effect=effect,  # type: ignore[arg-type]
                confidence=feature_confidence(item.get("confidence")),
                source="visual_signature",
                evidence_refs=[f"visual_signature.tile_signals.{index}"],
                rationale=str(item.get("rationale") or "")[:700],
            )
        )
    return out
