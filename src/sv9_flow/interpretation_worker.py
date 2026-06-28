"""Brand interpretation worker for the parallel SV9 Flow."""

from __future__ import annotations

from typing import Any

from src.sv9_flow._utils import truthy_detected, unique_strings
from src.sv9_flow.contracts import BrandEvidencePack, BrandInterpretation


def build_brand_interpretation_from_tldr(
    *,
    evidence_pack: BrandEvidencePack,
    tldr_payload: dict[str, Any] | None,
) -> BrandInterpretation:
    tldr = _extract_tldr(tldr_payload)
    limitations: list[str] = []
    if not tldr:
        limitations.append("missing_tldr_brand3")

    blocks: dict[str, dict[str, Any]] = {}
    evidence_refs: dict[str, list[str]] = {}
    for block_name, block_payload in sorted(tldr.items()):
        if not isinstance(block_payload, dict):
            continue
        normalized = dict(block_payload)
        detected = truthy_detected(normalized)
        normalized["detected"] = detected
        blocks[str(block_name)] = normalized
        refs = _refs_for_block(str(block_name), evidence_pack)
        if refs:
            evidence_refs[str(block_name)] = refs

    return BrandInterpretation(
        brand_name=evidence_pack.brand_name,
        url=evidence_pack.url,
        blocks=blocks,
        evidence_refs=evidence_refs,
        limitations=unique_strings(limitations),
    )


def _extract_tldr(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    tldr = payload.get("tldr_brand3")
    if isinstance(tldr, dict):
        return tldr
    return payload if any(isinstance(value, dict) for value in payload.values()) else {}


def _refs_for_block(block_name: str, evidence_pack: BrandEvidencePack) -> list[str]:
    needle = block_name.lower().replace("_", " ")
    refs = [
        record.ref
        for record in evidence_pack.evidence
        if needle in record.evidence_type.lower().replace("_", " ")
        or needle in record.content.lower().replace("_", " ")
    ]
    if refs:
        return refs[:5]
    return [record.ref for record in evidence_pack.evidence[:3]]
