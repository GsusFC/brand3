"""Deterministic block detection policy for SV9 Flow."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Literal

from src.sv9_flow.calibration_terms import block_detection_policy
from src.sv9_flow.contracts import BrandEvidencePack
from src.sv9_flow.evidence_source import (
    SOURCE_CLASS_ACQUISITION_METADATA,
    SOURCE_CLASS_VISUAL_SIGNAL,
    is_acquisition_noise,
    source_class_for_record,
)

_POLICY = block_detection_policy()

BLOCK_DETECTION_POLICY_VERSION = str(_POLICY["version"])

BlockDetectionOutcome = Literal["supports_detection", "insufficient_evidence"]

SENSITIVE_BLOCKS = frozenset({"mission", "values", "vision", "magnetism"})

_SUPPORT_TERMS: dict[str, tuple[str, ...]] = {
    key: tuple(values) for key, values in _POLICY["support_terms"].items()
}
_WEAKEN_TERMS: dict[str, tuple[str, ...]] = {
    key: tuple(values) for key, values in _POLICY["weaken_terms"].items()
}


@dataclass(frozen=True, slots=True)
class BlockDetectionDecision:
    block: str
    outcome: BlockDetectionOutcome
    evidence_refs: list[str] = field(default_factory=list)
    support_terms: list[str] = field(default_factory=list)
    weaken_terms: list[str] = field(default_factory=list)
    limitation_code: str = ""
    version: str = BLOCK_DETECTION_POLICY_VERSION

    @property
    def supports_detection(self) -> bool:
        return self.outcome == "supports_detection"

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "block": self.block,
            "outcome": self.outcome,
            "evidence_refs": list(self.evidence_refs),
            "support_terms": list(self.support_terms),
            "weaken_terms": list(self.weaken_terms),
            "limitation_code": self.limitation_code,
        }


def resolve_block_detection(
    block: str,
    evidence_pack: BrandEvidencePack,
    *,
    evidence_refs: list[str],
) -> BlockDetectionDecision:
    """Resolve whether cited evidence can support a sensitive block detection.

    Non-sensitive blocks remain controlled by the existing LLM+ref contract. For
    sensitive blocks this worker is the deterministic gate before detected=True
    can be accepted.
    """

    refs = _unique_refs(evidence_refs)
    if not refs:
        return BlockDetectionDecision(
            block=block,
            outcome="insufficient_evidence",
            evidence_refs=[],
            limitation_code=f"{block}_insufficient_evidence_refs",
        )
    if block not in SENSITIVE_BLOCKS:
        return BlockDetectionDecision(block=block, outcome="supports_detection", evidence_refs=refs)

    haystack = _evidence_haystack(refs, evidence_pack)
    support_terms = _matched_terms(haystack, _SUPPORT_TERMS.get(block, ()))
    if support_terms:
        return BlockDetectionDecision(
            block=block,
            outcome="supports_detection",
            evidence_refs=refs,
            support_terms=support_terms,
        )

    weaken_terms = _matched_terms(haystack, _WEAKEN_TERMS.get(block, ()))
    if weaken_terms:
        return BlockDetectionDecision(
            block=block,
            outcome="supports_detection",
            evidence_refs=refs,
            weaken_terms=weaken_terms,
        )

    return BlockDetectionDecision(
        block=block,
        outcome="insufficient_evidence",
        evidence_refs=refs,
        limitation_code=f"{block}_structural_gate_rejected",
    )


def _unique_refs(refs: list[str]) -> list[str]:
    out: list[str] = []
    for ref in refs:
        value = str(ref or "").strip()
        if value and value not in out:
            out.append(value)
    return out


def _evidence_haystack(refs: list[str], evidence_pack: BrandEvidencePack) -> str:
    refs_set = set(refs)
    parts: list[str] = []
    for record in evidence_pack.evidence:
        if record.ref not in refs_set:
            continue
        if is_acquisition_noise(record):
            continue
        if source_class_for_record(record) in {SOURCE_CLASS_ACQUISITION_METADATA, SOURCE_CLASS_VISUAL_SIGNAL}:
            continue
        parts.extend(
            (
                record.source,
                record.evidence_type,
                record.content,
                " ".join(str(value) for value in record.metadata.values()),
            )
        )
    return " ".join(parts).lower()


def _matched_terms(haystack: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if _contains_detection_term(haystack, term)]


def _contains_detection_term(haystack: str, term: str) -> bool:
    escaped = re.escape(" ".join(term.lower().split()))
    normalized = _normalize_detection_text(haystack)
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", normalized) is not None


def _normalize_detection_text(value: str) -> str:
    # Evidence records can contain JSON-serialized page text, where line breaks
    # arrive as literal "\n". Treat those escapes as separators before applying
    # word-boundary matching.
    text = (
        value.replace("\\n", " ")
        .replace("\\r", " ")
        .replace("\\t", " ")
    )
    return " ".join(text.split())
